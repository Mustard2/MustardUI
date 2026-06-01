import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    StringProperty,
)
from mathutils import Quaternion

from ..model_selection.active_object import mustardui_active_object


def ikfk_snapper_available(arm):
    """Whether the IK/FK Snapper applies to this model.

    Restricted to a generic ("Other") rig — MHX/Rigify/ARP ship their own IK/FK
    switching. Once the model is configured the stored ``model_rig_type`` is
    authoritative, so use it directly; before that it is still the default, so
    detect the type live from the armature.
    """
    rig_settings = arm.MustardUI_RigSettings
    if arm.MustardUI_created:
        return rig_settings.model_rig_type == "other"

    from ..configuration.definitions import mustardui_detect_rig_type

    arm_obj = rig_settings.model_armature_object or _arm_obj(arm)
    if arm_obj is None:
        return False
    return mustardui_detect_rig_type(arm, arm_obj) == "other"


def ikfk_chain_is_complete(chain):
    """A chain is usable only if it has the vital fields: IK bones, FK bones and
    an IK control."""
    return bool(
        _split_bones(chain.ik_bones) and _split_bones(chain.fk_bones) and chain.ik_ctrl
    )


def ikfk_has_complete_chains(arm):
    """Whether the model has at least one usable IK/FK chain."""
    snapper = arm.MustardUI_IKFKSnapperSettings
    return any(ikfk_chain_is_complete(c) for c in snapper.ikfk_chains)


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------
class MustardUI_IKFKChain(bpy.types.PropertyGroup):
    """Describes one auto-detected (or manually refined) IK/FK chain."""

    name: StringProperty(name="Chain Name", default="Chain")

    # IK chain bones (result/deform – read when snapping IK→FK)
    ik_bones: StringProperty(
        name="IK Bones",
        description="Comma-separated list of IK result bones, root→end",
    )

    # FK counterpart bones (same order as ik_bones)
    fk_bones: StringProperty(
        name="FK Bones",
        description="Comma-separated list of FK bones, root→end",
    )

    # IK controls
    ik_ctrl: StringProperty(
        name="IK Control",
        description="IK effector/target bone",
    )
    pole_ctrl: StringProperty(
        name="Pole Target",
        description="IK pole target bone (empty = none)",
    )
    pole_distance: FloatProperty(
        name="Pole Distance",
        description="Distance to place the pole from the mid joint",
        default=0.5,
        min=0.001,
        max=10.0,
    )

    # Bone collections (layers) shown per mode; toggled by the snap/switch ops
    ik_collection: StringProperty(
        name="IK Bone Collection",
        description="Bone collection (layer) shown in IK mode (empty = leave alone)",
    )
    fk_collection: StringProperty(
        name="FK Bone Collection",
        description="Bone collection (layer) shown in FK mode (empty = leave alone)",
    )

    # Marks chains that were produced by auto-detection vs hand-crafted
    auto_detected: BoolProperty(default=False, options={"HIDDEN"})


class MustardUI_IKFKSnapperSettings(bpy.types.PropertyGroup):
    ikfk_chains: CollectionProperty(type=MustardUI_IKFKChain)
    ikfk_chains_index: IntProperty(name="Active Chain", default=0)


# ---------------------------------------------------------------------------
# Auto-detection helpers
# ---------------------------------------------------------------------------

# Ordered substitution rules: (ik_token, fk_token).
# Applied left-to-right; first match wins.
_IK_FK_SUBS = [
    # Explicit IK → FK substitutions (highest priority)
    ("_ik.", "_fk."),
    ("_IK.", "_FK."),
    (".ik.", ".fk."),
    (".IK.", ".FK."),
    ("-ik.", "-fk."),
    ("-IK.", "-FK."),
    ("_ik_", "_fk_"),
    ("_IK_", "_FK_"),
    ("_ik", "_fk"),
    ("_IK", "_FK"),
    (".ik", ".fk"),
    (".IK", ".FK"),
    ("-ik", "-fk"),
    ("-IK", "-FK"),
    ("IK", "FK"),
    ("ik", "fk"),
    # Fallback: strip the IK suffix (FK bone might just be "L_Arm" not "L_Arm_FK")
    ("_ik", ""),
    ("_IK", ""),
    (".ik", ""),
    (".IK", ""),
    ("-ik", ""),
    ("-IK", ""),
]


def _fk_name_for(bone_name, pose_bones):
    """Try every substitution pattern to find a matching FK bone."""
    for ik_tok, fk_tok in _IK_FK_SUBS:
        if ik_tok in bone_name:
            candidate = bone_name.replace(ik_tok, fk_tok, 1)
            if candidate != bone_name and candidate in pose_bones:
                return candidate
    return None


# Delimited IK/FK tokens stripped from a chain's display name (e.g. R_Leg_IK → R_Leg).
_NAME_STRIP_TOKENS = [
    "_ik",
    "_IK",
    "ik_",
    "IK_",
    ".ik",
    ".IK",
    "ik.",
    "IK.",
    "-ik",
    "-IK",
    "ik-",
    "IK-",
    "_fk",
    "_FK",
    "fk_",
    "FK_",
    ".fk",
    ".FK",
    "fk.",
    "FK.",
    "-fk",
    "-FK",
    "fk-",
    "FK-",
]


def _clean_chain_name(name):
    """Make a readable chain name: strip IK/FK tokens and turn separators into
    spaces (e.g. R_Leg_IK → "R Leg")."""
    cleaned = name
    for tok in _NAME_STRIP_TOKENS:
        cleaned = cleaned.replace(tok, "")
    # Bare trailing IK/FK with no separator (e.g. "ArmIK").
    for tok in ("IK", "FK", "ik", "fk"):
        if cleaned.endswith(tok):
            cleaned = cleaned[: -len(tok)]
    cleaned = cleaned.strip(" _.-")
    if not cleaned:
        return name
    # Replace separators with spaces and collapse runs of whitespace.
    for sep in ("_", ".", "-"):
        cleaned = cleaned.replace(sep, " ")
    return " ".join(cleaned.split())


def _ik_chain_from_constraint(arm_obj, end_bone, constraint):
    """Return the list of pose bones [root … end] for one IK constraint."""
    count = constraint.chain_count  # 0 = unlimited (walk to root)
    chain = []
    b = end_bone
    steps = 0
    while b is not None:
        chain.append(b)
        steps += 1
        if count and steps >= count:
            break
        b = b.parent
    chain.reverse()
    return chain


def _bone_is_visible(arm_obj, bone_name):
    """Return True if the bone is not explicitly hidden (b.hide).
    Collection visibility is intentionally ignored because rigs toggle
    IK/FK collections based on mode, which would break detection."""
    b = arm_obj.data.bones.get(bone_name)
    return b is not None and not b.hide


def _all_collections(armature):
    """All bone collections of the armature, flattened (incl. nested)."""
    return getattr(armature, "collections_all", armature.collections)


def _collections_of(arm_obj, bone_names):
    """Ordered, de-duplicated collection names the given bones belong to."""
    names = []
    for bn in bone_names:
        b = arm_obj.data.bones.get(bn) if bn else None
        if b is None:
            continue
        for coll in b.collections:
            if coll.name not in names:
                names.append(coll.name)
    return names


def detect_chains(arm_obj):
    """
    Scan *arm_obj* for IK constraints and build chain descriptions.
    Returns a list of dicts ready to be stored in MustardUI_IKFKChain.

    Only chains whose IK control bone is visible are included, which
    filters out internal/mechanism bones and keeps the animator-facing limb chains.
    """
    pose_bones = arm_obj.pose.bones
    seen_ctrls = set()
    results = []

    for bone in pose_bones:
        for cns in bone.constraints:
            if cns.type != "IK":
                continue
            # Only care about IK targeting another bone on the same armature
            if cns.target is not arm_obj or not cns.subtarget:
                continue
            ik_ctrl = cns.subtarget
            if ik_ctrl in seen_ctrls:
                continue

            # Skip if the IK control bone itself is hidden – those are internal chains
            if not _bone_is_visible(arm_obj, ik_ctrl):
                continue

            # Skip chains shorter than 2 bones – usually single-joint correction IK
            chain_count = cns.chain_count
            if chain_count == 1:
                continue

            seen_ctrls.add(ik_ctrl)

            ik_chain = _ik_chain_from_constraint(arm_obj, bone, cns)
            pole_ctrl = cns.pole_subtarget if cns.pole_subtarget else ""

            # Try to find FK counterparts for every bone in the chain.
            # If none are found, reuse the IK chain bones (single-chain rig).
            fk_names = [_fk_name_for(b.name, pose_bones) for b in ik_chain]
            fk_count = sum(1 for n in fk_names if n)
            if not fk_count:
                fk_names = [b.name for b in ik_chain]

            # Pole distance: distance between mid and end IK bones as a reference
            pole_dist = 0.5
            if len(ik_chain) >= 2:
                mid = ik_chain[len(ik_chain) // 2]
                end = ik_chain[-1]
                pole_dist = (end.head - mid.head).length or 0.5

            # Bone collections (layers). Find the IK collection among the
            # collections the IK controls / chain bones belong to (preferring one
            # whose name marks it as IK), then derive the FK collection from that
            # name via the same IK→FK substitution (e.g. R_Arm_IK → R_Arm_FK).
            ik_candidates = _collections_of(
                arm_obj, [ik_ctrl, pole_ctrl] + [b.name for b in ik_chain]
            )
            ik_collection = next(
                (n for n in ik_candidates if "ik" in n.lower()), ""
            ) or (ik_candidates[0] if ik_candidates else "")

            coll_names = {c.name for c in _all_collections(arm_obj.data)}
            fk_collection = ""
            if ik_collection:
                fk_collection = _fk_name_for(ik_collection, coll_names) or ""
            if not fk_collection:
                # Fall back to a collection the FK counterpart bones live in.
                fk_candidates = _collections_of(arm_obj, [n for n in fk_names if n])
                fk_collection = next(
                    (n for n in fk_candidates if "fk" in n.lower()), ""
                )

            results.append(
                {
                    "name": _clean_chain_name(ik_ctrl),
                    "ik_bones": ",".join(b.name for b in ik_chain),
                    "fk_bones": ",".join(n or "" for n in fk_names),
                    "ik_ctrl": ik_ctrl,
                    "pole_ctrl": pole_ctrl,
                    "pole_distance": round(pole_dist, 4),
                    "ik_collection": ik_collection,
                    "fk_collection": fk_collection,
                    "fk_found": fk_count,
                }
            )

    return results


# ---------------------------------------------------------------------------
# Helpers used by operators
# ---------------------------------------------------------------------------


def _arm_obj(arm_data):
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE" and obj.data is arm_data:
            return obj
    return None


def _bone(arm_obj, name):
    if not name:
        return None
    return arm_obj.pose.bones.get(name)


def _split_bones(s):
    return [n.strip() for n in s.split(",") if n.strip()]


def _signed_angle(v_from, v_to, axis):
    """Signed angle (radians) rotating *v_from* onto *v_to* about *axis*.

    Both vectors are projected onto the plane perpendicular to *axis* first.
    Returns 0.0 if either projection is degenerate.
    """
    f = v_from - axis * v_from.dot(axis)
    t = v_to - axis * v_to.dot(axis)
    if f.length < 1e-9 or t.length < 1e-9:
        return 0.0
    f.normalize()
    t.normalize()
    ang = f.angle(t, 0.0)
    if axis.dot(f.cross(t)) < 0.0:
        ang = -ang
    return ang


def _set_world_matrix(bone, mat):
    bone.matrix = mat
    bpy.context.view_layer.update()


def _set_world_location(bone, loc):
    mat = bone.matrix.copy()
    mat.translation = loc
    bone.matrix = mat
    bpy.context.view_layer.update()


def _auto_key(bone, frame):
    if not bpy.context.scene.tool_settings.use_keyframe_insert_auto:
        return
    bone.keyframe_insert("location", frame=frame)
    rm = bone.rotation_mode
    if rm == "QUATERNION":
        bone.keyframe_insert("rotation_quaternion", frame=frame)
    elif rm == "AXIS_ANGLE":
        bone.keyframe_insert("rotation_axis_angle", frame=frame)
    else:
        bone.keyframe_insert("rotation_euler", frame=frame)
    bone.keyframe_insert("scale", frame=frame)


# ---------------------------------------------------------------------------
# Auto-detect operator
# ---------------------------------------------------------------------------


def populate_ikfk_chains(arm, arm_obj, clear_existing=False):
    """(Re)build auto-detected IK/FK chains on *arm* from *arm_obj*.

    Removes previously auto-detected chains (or all, when *clear_existing*) and
    adds freshly detected ones. Returns the list of detection result dicts.
    """
    snapper = arm.MustardUI_IKFKSnapperSettings

    if clear_existing:
        snapper.ikfk_chains.clear()
    else:
        # Remove only previously auto-detected chains
        to_remove = [i for i, c in enumerate(snapper.ikfk_chains) if c.auto_detected]
        for i in reversed(to_remove):
            snapper.ikfk_chains.remove(i)

    found = detect_chains(arm_obj)
    for data in found:
        item = snapper.ikfk_chains.add()
        item.name = data["name"]
        item.ik_bones = data["ik_bones"]
        item.fk_bones = data["fk_bones"]
        item.ik_ctrl = data["ik_ctrl"]
        item.pole_ctrl = data["pole_ctrl"]
        item.pole_distance = data["pole_distance"]
        item.ik_collection = data["ik_collection"]
        item.fk_collection = data["fk_collection"]
        item.auto_detected = True

    return found


class MUSTARDUI_OT_IKFKDetect(bpy.types.Operator):
    """Scan the armature for IK constraints and build snap chains automatically"""

    bl_idname = "mustardui.ikfk_detect"
    bl_label = "Auto-Detect IK/FK Chains"
    bl_options = {"REGISTER", "UNDO"}

    clear_existing: BoolProperty(
        name="Clear Existing",
        description="Remove manually added chains before detecting",
        default=False,
    )

    @classmethod
    def poll(cls, context):
        # Works in both normal mode (config=0) and configure mode (config=1)
        res, arm = mustardui_active_object(context, config=-1)
        return arm is not None

    def execute(self, context):
        res, arm = mustardui_active_object(context, config=-1)
        arm_obj = _arm_obj(arm)
        if arm_obj is None:
            self.report({"ERROR"}, "Cannot find armature object")
            return {"CANCELLED"}

        found = populate_ikfk_chains(arm, arm_obj, clear_existing=self.clear_existing)

        fk_missing = sum(1 for d in found if d["fk_found"] == 0)
        msg = f"Found {len(found)} IK chain(s)"
        if fk_missing:
            msg += (
                f"; {fk_missing} chain(s) have no FK counterparts "
                f"(IK→FK snap unavailable)"
            )
        self.report({"INFO"}, msg)
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# Snap operator
# ---------------------------------------------------------------------------


class MUSTARDUI_OT_IKFKSnap(bpy.types.Operator):
    """Snap between IK and FK for the selected chain"""

    bl_idname = "mustardui.ikfk_snap"
    bl_label = "IK/FK Snap"
    bl_options = {"REGISTER", "UNDO"}

    chain_index: IntProperty(default=0, options={"HIDDEN"})
    direction: EnumProperty(
        name="Direction",
        items=[
            ("FK_TO_IK", "FK → IK", "Snap IK controls to match current FK pose"),
            ("IK_TO_FK", "IK → FK", "Snap FK bones to match current IK pose"),
        ],
    )
    switch: BoolProperty(
        name="Switch Mode",
        description="Also flip the IK/FK switch after snapping",
        default=True,
    )

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        return res and arm is not None

    def execute(self, context):
        res, arm = mustardui_active_object(context, config=0)
        snapper = arm.MustardUI_IKFKSnapperSettings

        if self.chain_index >= len(snapper.ikfk_chains):
            self.report({"ERROR"}, "Invalid chain index")
            return {"CANCELLED"}

        chain = snapper.ikfk_chains[self.chain_index]
        arm_obj = _arm_obj(arm)
        if arm_obj is None:
            self.report({"ERROR"}, "Cannot find armature object")
            return {"CANCELLED"}

        frame = context.scene.frame_current

        if self.direction == "FK_TO_IK":
            ok = self._snap_fk_to_ik(arm_obj, chain, frame)
        else:
            ok = self._snap_ik_to_fk(arm_obj, chain, frame)

        if not ok:
            return {"CANCELLED"}

        if self.switch:
            apply_ikfk_switch(arm_obj, chain, self.direction, frame)

        return {"FINISHED"}

    # ------------------------------------------------------------------
    def _snap_fk_to_ik(self, arm_obj, chain, frame):
        ik_ctrl_bone = _bone(arm_obj, chain.ik_ctrl)
        if ik_ctrl_bone is None:
            self.report({"ERROR"}, f"IK control bone '{chain.ik_ctrl}' not found")
            return False

        # Use explicit FK bones if configured; otherwise fall back to the IK
        # chain bones themselves (single-chain rigs reuse the same bones for FK).
        fk_list = _split_bones(chain.fk_bones) or _split_bones(chain.ik_bones)
        if not fk_list:
            self.report({"ERROR"}, "No chain bones found")
            return False

        fk_end_bone = _bone(arm_obj, fk_list[-1])
        if fk_end_bone is None:
            self.report({"ERROR"}, f"FK end bone '{fk_list[-1]}' not found")
            return False

        # Read the TRUE FK pose even when we're currently in IK mode. Just
        # disabling the IK constraint isn't enough: any constraint that drives an
        # FK-side bone (or the pole) from the IK result still reports the IK pose,
        # so a second FK→IK click would read the IK-driven (bent) pose and the
        # pole would jump. Neutralize every link from the IK side — the IK
        # constraint plus every copy constraint pointing at the IK ctrl or an IK
        # chain bone — for the duration of the read; restored before returning.
        ik_list = _split_bones(chain.ik_bones)
        _ik_cns = None
        _was_ik_on = False
        _copy_types = {"COPY_ROTATION", "COPY_TRANSFORMS", "COPY_LOCATION"}
        _ik_side = set(ik_list)
        if chain.ik_ctrl:
            _ik_side.add(chain.ik_ctrl)

        if ik_list:
            end_ik_b = _bone(arm_obj, ik_list[-1])
            if end_ik_b:
                for cns in end_ik_b.constraints:
                    if cns.type == "IK" and cns.subtarget == chain.ik_ctrl:
                        _ik_cns = cns
                        _was_ik_on = cns.influence > 0.5
                        break

        _fk_read_saved = []
        for pb in arm_obj.pose.bones:
            for cns in pb.constraints:
                drives_from_ik = (
                    cns.type == "IK" and getattr(cns, "subtarget", "") == chain.ik_ctrl
                ) or (
                    cns.type in _copy_types
                    and getattr(cns, "subtarget", "") in _ik_side
                )
                if drives_from_ik and cns.influence != 0.0:
                    _fk_read_saved.append((cns, cns.influence))
                    cns.influence = 0.0
        if _fk_read_saved:
            bpy.context.view_layer.update()

        # Capture ALL FK positions before touching any bone.
        # Placing the IK ctrl triggers a scene update that can shift constraint-driven
        # FK bones, so pole geometry must be read from the unmodified FK pose.
        fk_tail = fk_end_bone.tail.copy()

        # For rotation: find the bone that Copy Rotation-s from the IK ctrl (e.g.
        # Hand.l → Copy Rotation → L_Arm_IK). In FK mode its rotation is the one
        # the IK ctrl needs to match so that the hand stays put after switching.
        # Fall back to the FK end bone if no such companion exists.
        rot_source = next(
            (
                pb
                for pb in arm_obj.pose.bones
                for cns in pb.constraints
                if cns.type in {"COPY_ROTATION", "COPY_TRANSFORMS"}
                and getattr(cns, "subtarget", "") == chain.ik_ctrl
            ),
            fk_end_bone,
        )
        rot_mat = rot_source.matrix.copy()

        # Capture pole geometry from clean FK state (before IK ctrl is placed).
        # Placing the IK ctrl triggers an update that can shift constraint-driven
        # bones, so everything the pole needs is read from the unmodified FK pose.
        pole_data = None
        if chain.pole_ctrl and len(fk_list) >= 2:
            pole_bone = _bone(arm_obj, chain.pole_ctrl)
            above = _bone(arm_obj, fk_list[0])  # thigh FK
            below = _bone(arm_obj, fk_list[1])  # shin FK
            if pole_bone and above and below:
                pole_data = (
                    pole_bone,
                    pole_bone.head.copy(),  # current pole world position
                    below.head.copy(),  # knee world position
                    above.head.copy(),  # hip world position (chain root)
                    fk_tail,  # ankle world position (chain tip / IK target)
                )

        # Place IK ctrl to match FK end position.
        rot_mat.translation = fk_tail
        _set_world_matrix(ik_ctrl_bone, rot_mat)
        _auto_key(ik_ctrl_bone, frame)

        # Place pole target using the FK geometry captured above.
        if pole_data:
            pole_bone, pole_p0, knee_pos, root_pos, end_pos = pole_data
            chain_axis = end_pos - root_pos
            limb_len = chain_axis.length

            if limb_len > 1e-8:
                chain_axis = chain_axis.normalized()
                t = (knee_pos - root_pos).dot(chain_axis)
                pivot = root_pos + chain_axis * t

                # True FK bend direction: the knee's offset from the hip→ankle
                # chord (perpendicular to the chain axis by construction).
                bend_dir = knee_pos - pivot

                # Skip when the limb is too straight to determine a reliable bend
                # direction (e.g. rest pose) — moving the pole then only adds error.
                if bend_dir.length > max(1e-5, 1e-3 * limb_len):
                    bend_dir.normalize()

                    # Preserve the pole's existing offset from the chain axis (its
                    # axial position and radial distance); only re-aim the radial
                    # direction. This makes the snap a no-op when the pole is
                    # already correct, so a clean FK→IK round-trip leaves the pole
                    # transform unchanged instead of jumping to a fixed distance.
                    rel = pole_p0 - pivot
                    axial = chain_axis * rel.dot(chain_axis)
                    radial_len = (rel - axial).length or chain.pole_distance
                    base = pivot + axial

                    # Place the pole so the solve reproduces the FK bend, handling
                    # the constraint's pole angle (and its per-side sign) by
                    # measuring the bend the solver induces and cancelling it —
                    # deterministic, so repeated clicks don't flip the side.
                    pole_pos = self._match_pole(
                        arm_obj,
                        chain,
                        ik_list,
                        pole_bone,
                        base,
                        chain_axis,
                        radial_len,
                        bend_dir,
                    )

                    _set_world_location(pole_bone, pole_pos)
                    _auto_key(pole_bone, frame)

        # Restore every constraint disabled for the FK read so the switch sees
        # the original state.
        for cns, influence in _fk_read_saved:
            cns.influence = influence
        if _fk_read_saved:
            bpy.context.view_layer.update()

        return True

    # ------------------------------------------------------------------
    @staticmethod
    def _match_pole(
        arm_obj, chain, ik_list, pole_bone, base, axis, radial_len, desired_dir
    ):
        """Place the pole so the IK solve reproduces the FK bend.

        Rotating the pole around the chain axis rotates the IK bend plane — and so
        the mid (knee/elbow) joint — by the same angle. So we aim the pole along
        the FK bend direction, solve once, measure how far the solver's pole angle
        rotated the resulting bend away from the FK direction, and cancel exactly
        that angle. A single measure-and-correct pass lands the joint on the FK
        position regardless of the constraint's pole_angle or its sign convention,
        and it is deterministic — repeated clicks compute the same pole, so the
        side never flips.

        ``base`` is the pole's anchor on the chain axis (pivot + the pole's own
        axial offset); the pole is kept at ``radial_len`` from it.
        """
        default = base + desired_dir * radial_len
        if not ik_list:
            return default
        mid_ik = _bone(arm_obj, ik_list[len(ik_list) // 2])
        if mid_ik is None:
            return default

        # Temporarily force a clean IK solve: enable the IK constraint and disable
        # any FK→IK copy constraints that would otherwise pin the IK bones to FK
        # (the same ones apply_ikfk_switch toggles when switching to IK).
        saved = []
        end_ik = _bone(arm_obj, ik_list[-1])
        if end_ik is not None:
            for cns in end_ik.constraints:
                if cns.type == "IK" and cns.subtarget == chain.ik_ctrl:
                    saved.append((cns, cns.influence))
                    cns.influence = 1.0
                    break

        fk_set = set(_split_bones(chain.fk_bones))
        _copy_types = {"COPY_ROTATION", "COPY_TRANSFORMS", "COPY_LOCATION"}
        for ik_name in ik_list:
            pb = _bone(arm_obj, ik_name)
            if pb is None:
                continue
            for cns in pb.constraints:
                if cns.type in _copy_types and getattr(cns, "subtarget", "") in fk_set:
                    saved.append((cns, cns.influence))
                    cns.influence = 0.0

        # Solve with the pole aimed along the FK bend direction and read the bend
        # the solver actually produced (mid joint offset from the axis).
        _set_world_location(pole_bone, default)  # triggers a view_layer update
        achieved = mid_ik.head - base
        achieved -= axis * achieved.dot(axis)

        result = default
        if achieved.length > 1e-7:
            # Rotate the pole back by the angle the solver introduced.
            err = _signed_angle(achieved, desired_dir, axis)
            corrected_dir = Quaternion(axis, err) @ desired_dir
            result = base + corrected_dir * radial_len

        # Restore every constraint influence we touched.
        for cns, influence in saved:
            cns.influence = influence
        bpy.context.view_layer.update()
        return result

    # ------------------------------------------------------------------
    def _snap_ik_to_fk(self, arm_obj, chain, frame):
        ik_list = _split_bones(chain.ik_bones)
        fk_list = _split_bones(chain.fk_bones)
        if not ik_list:
            return True

        # Single-chain rig: FK and IK are the SAME bones, so the solved pose lives
        # only in the IK constraint result, not in the bone basis. We must bake it
        # into the basis — otherwise switching IK off reverts to the old FK pose
        # and IK→FK appears to do nothing.
        single_chain = (not fk_list) or (ik_list == fk_list)
        if single_chain:
            fk_list = ik_list

        # Capture the solved IK world matrices before changing anything: writing a
        # bone triggers a view_layer update that re-evaluates the IK solve and can
        # shift the remaining matrices.
        pairs = []
        for ik_name, fk_name in zip(ik_list, fk_list):
            ik_b = _bone(arm_obj, ik_name)
            fk_b = _bone(arm_obj, fk_name)
            if ik_b is None or fk_b is None:
                continue
            pairs.append((fk_b, ik_b.matrix.copy()))

        if not pairs:
            self.report({"ERROR"}, "No valid IK/FK bone pairs found")
            return False

        # The tip/hand bone is not part of the IK chain: its rotation comes from a
        # companion Copy Rotation/Transforms that targets the IK ctrl. Capture that
        # IK-driven world matrix too, so we can bake it into the FK pose — otherwise
        # the tip snaps back to its old FK rotation when the switch disables the
        # companion.
        _companion_types = {"COPY_ROTATION", "COPY_TRANSFORMS", "COPY_LOCATION"}
        companions = []  # (pose_bone, world_matrix, [constraints])
        for pb in arm_obj.pose.bones:
            cnss = [
                c
                for c in pb.constraints
                if c.type in _companion_types
                and getattr(c, "subtarget", "") == chain.ik_ctrl
            ]
            if cnss:
                companions.append((pb, pb.matrix.copy(), cnss))

        # Disable everything that drives these bones from the IK side so the
        # matrices we write below bake into the basis instead of being overwritten:
        # the IK constraint (single-chain only — separate FK controls aren't driven
        # by it) and the tip's companion constraints.
        if single_chain:
            end_ik = _bone(arm_obj, ik_list[-1])
            if end_ik is not None:
                for cns in end_ik.constraints:
                    if cns.type == "IK" and cns.subtarget == chain.ik_ctrl:
                        _remove_driver_and_set(arm_obj, end_ik, cns, 0.0, frame)
                        break
        for pb, _mat, cnss in companions:
            for cns in cnss:
                _remove_driver_and_set(arm_obj, pb, cns, 0.0, frame)
        bpy.context.view_layer.update()

        # Bake the chain (root→tip) then the tip/companion bones.
        for fk_b, mat in pairs:
            _set_world_matrix(fk_b, mat)
            _auto_key(fk_b, frame)
        for pb, mat, _cnss in companions:
            _set_world_matrix(pb, mat)
            _auto_key(pb, frame)

        return True


# ---------------------------------------------------------------------------
# Shared switch logic
# ---------------------------------------------------------------------------


def _remove_driver_and_set(arm_obj, bone, cns, influence, frame):
    """Remove any driver on cns.influence, set the value, and optionally keyframe it."""
    data_path = f'pose.bones["{bone.name}"].constraints["{cns.name}"].influence'
    if arm_obj.animation_data:
        drv = arm_obj.animation_data.drivers.find(data_path)
        if drv:
            arm_obj.animation_data.drivers.remove(drv)
    cns.influence = influence
    if bpy.context.scene.tool_settings.use_keyframe_insert_auto:
        arm_obj.keyframe_insert(data_path, frame=frame)


def _find_bone_collection(armature, name):
    """Look up a bone collection by name (including nested ones)."""
    if not name:
        return None
    coll = None
    if hasattr(armature, "collections_all"):
        coll = armature.collections_all.get(name)
    if coll is None:
        coll = armature.collections.get(name)
    return coll


def _set_collection_visible(armature, coll_name, visible):
    """Show/hide a bone collection, removing any driver on its visibility first."""
    coll = _find_bone_collection(armature, coll_name)
    if coll is None:
        return
    # Drop drivers on the collection visibility so the explicit toggle sticks.
    # Collection visibility drivers live on the armature DATA's animation_data.
    ad = armature.animation_data
    if ad:
        needle = '"%s"' % coll_name
        for drv in list(ad.drivers):
            dp = drv.data_path
            if dp.endswith("is_visible") and needle in dp:
                ad.drivers.remove(drv)
    coll.is_visible = visible


def apply_ikfk_switch(arm_obj, chain, direction, frame):
    """Toggle the IK constraint and any companion constraints that target the IK ctrl.

    Companion constraints (e.g. Copy Rotation on the hand/foot bone that point at
    the IK ctrl) are toggled together with the main IK constraint so they stay
    in sync without needing drivers. The chain's IK/FK bone collections (layers)
    are shown/hidden to match the new mode.

    direction is 'FK_TO_IK' or 'IK_TO_FK'.
    """
    influence = 1.0 if direction == "FK_TO_IK" else 0.0

    # 1. Toggle the IK constraint on the chain end bone
    ik_list = _split_bones(chain.ik_bones)
    if not ik_list:
        return
    end_bone = _bone(arm_obj, ik_list[-1])
    if end_bone is not None:
        for cns in end_bone.constraints:
            if cns.type == "IK" and cns.subtarget == chain.ik_ctrl:
                _remove_driver_and_set(arm_obj, end_bone, cns, influence, frame)
                break

    _COMPANION_TYPES = {"COPY_ROTATION", "COPY_TRANSFORMS", "COPY_LOCATION"}

    # 2. Toggle companion constraints on ALL pose bones that target ik_ctrl.
    #    Covers e.g. Hand.l Copy Rotation → L_Arm_IK.
    for pb in arm_obj.pose.bones:
        for cns in pb.constraints:
            if cns.type not in _COMPANION_TYPES:
                continue
            if getattr(cns, "subtarget", "") != chain.ik_ctrl:
                continue
            _remove_driver_and_set(arm_obj, pb, cns, influence, frame)

    # 3. Toggle Copy constraints on IK chain bones that target FK chain bones.
    #    Many rigs use Copy Rotation/Transform from FK→IK in FK mode so the IK
    #    chain tracks the FK animation. When switching to IK, these must be
    #    disabled so the IK solver can freely rotate all chain bones (including
    #    the first one, which otherwise stays locked to the FK rotation).
    fk_set = set(_split_bones(chain.fk_bones))
    fk_influence = 0.0 if direction == "FK_TO_IK" else 1.0
    for ik_name in ik_list:
        ik_pb = _bone(arm_obj, ik_name)
        if not ik_pb:
            continue
        for cns in ik_pb.constraints:
            if cns.type in _COMPANION_TYPES and getattr(cns, "subtarget", "") in fk_set:
                _remove_driver_and_set(arm_obj, ik_pb, cns, fk_influence, frame)

    # 4. Show the bone collection for the new mode and hide the other one.
    show_ik = direction == "FK_TO_IK"
    _set_collection_visible(arm_obj.data, chain.ik_collection, show_ik)
    _set_collection_visible(arm_obj.data, chain.fk_collection, not show_ik)

    arm_obj.update_tag()
    bpy.context.view_layer.update()


# ---------------------------------------------------------------------------
# Simple switch operator (no snap)
# ---------------------------------------------------------------------------


class MUSTARDUI_OT_IKFKSwitch(bpy.types.Operator):
    """Switch between IK and FK without snapping bone positions"""

    bl_idname = "mustardui.ikfk_switch"
    bl_label = "IK/FK Switch"
    bl_options = {"REGISTER", "UNDO"}

    chain_index: IntProperty(default=0, options={"HIDDEN"})
    direction: EnumProperty(
        name="Direction",
        items=[
            ("TO_IK", "→ IK", "Switch to IK mode"),
            ("TO_FK", "→ FK", "Switch to FK mode"),
        ],
    )

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        return res and arm is not None

    def execute(self, context):
        res, arm = mustardui_active_object(context, config=0)
        snapper = arm.MustardUI_IKFKSnapperSettings

        if self.chain_index >= len(snapper.ikfk_chains):
            self.report({"ERROR"}, "Invalid chain index")
            return {"CANCELLED"}

        chain = snapper.ikfk_chains[self.chain_index]
        arm_obj = _arm_obj(arm)
        if arm_obj is None:
            self.report({"ERROR"}, "Cannot find armature object")
            return {"CANCELLED"}

        snap_direction = "FK_TO_IK" if self.direction == "TO_IK" else "IK_TO_FK"
        apply_ikfk_switch(arm_obj, chain, snap_direction, context.scene.frame_current)
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# Chain list operators (for manual editing in configure panel)
# ---------------------------------------------------------------------------


class MUSTARDUI_OT_IKFKChainAdd(bpy.types.Operator):
    """Add a blank IK/FK chain entry"""

    bl_idname = "mustardui.ikfk_chain_add"
    bl_label = "Add IK/FK Chain"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=1)
        return res and arm is not None

    def execute(self, context):
        res, arm = mustardui_active_object(context, config=1)
        snapper = arm.MustardUI_IKFKSnapperSettings
        item = snapper.ikfk_chains.add()
        item.name = "Chain " + str(len(snapper.ikfk_chains))
        snapper.ikfk_chains_index = len(snapper.ikfk_chains) - 1
        return {"FINISHED"}


class MUSTARDUI_OT_IKFKChainRemove(bpy.types.Operator):
    """Remove the selected IK/FK chain"""

    bl_idname = "mustardui.ikfk_chain_remove"
    bl_label = "Remove IK/FK Chain"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=1)
        if not res or arm is None:
            return False
        return len(arm.MustardUI_IKFKSnapperSettings.ikfk_chains) > 0

    def execute(self, context):
        res, arm = mustardui_active_object(context, config=1)
        snapper = arm.MustardUI_IKFKSnapperSettings
        idx = snapper.ikfk_chains_index
        if idx < len(snapper.ikfk_chains):
            snapper.ikfk_chains.remove(idx)
            snapper.ikfk_chains_index = max(0, idx - 1)
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# UIList
# ---------------------------------------------------------------------------


class MUSTARDUI_UL_IKFKChain_UIList(bpy.types.UIList):
    def draw_item(
        self,
        context,
        layout,
        _data,
        item,
        _icon,
        _active_data,
        _active_propname,
        _index,
    ):
        row = layout.row(align=True)
        icon = "CURVE_PATH" if item.auto_detected else "ARMATURE_DATA"
        row.label(text="", icon=icon)
        row.prop(item, "name", text="", emboss=False)
        # Warn if FK bones are missing
        fk_list = _split_bones(item.fk_bones)
        if not fk_list:
            row.label(text="", icon="ERROR")


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

_classes = [
    MustardUI_IKFKChain,
    MustardUI_IKFKSnapperSettings,
    MUSTARDUI_UL_IKFKChain_UIList,
    MUSTARDUI_OT_IKFKDetect,
    MUSTARDUI_OT_IKFKSnap,
    MUSTARDUI_OT_IKFKSwitch,
    MUSTARDUI_OT_IKFKChainAdd,
    MUSTARDUI_OT_IKFKChainRemove,
]


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.types.Armature.MustardUI_IKFKSnapperSettings = bpy.props.PointerProperty(
        type=MustardUI_IKFKSnapperSettings
    )


def unregister():
    del bpy.types.Armature.MustardUI_IKFKSnapperSettings
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
