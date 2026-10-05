import ast
import math
import re
from itertools import zip_longest

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

from ..model_selection.active_object import (
    ModelMode,
    active_object_operator_poll,
    mustardui_active_object,
)

_COPY_TYPES = {"COPY_ROTATION", "COPY_TRANSFORMS", "COPY_LOCATION"}


def ikfk_snapper_available(arm):
    """Whether the IK/FK Snapper applies to the model (generic rigs only)"""
    rig_settings = arm.MustardUI_RigSettings
    if arm.MustardUI_created:
        return rig_settings.model_rig_type == "other"

    from ..configuration.definitions import mustardui_detect_rig_type

    arm_obj = _arm_obj(arm)
    if arm_obj is None:
        return False
    return mustardui_detect_rig_type(arm, arm_obj) == "other"


def ikfk_chain_is_complete(chain):
    """Whether the chain has its IK bones, FK bones and IK control"""
    return bool(_split_bones(chain.ik_bones) and _split_bones(chain.fk_bones) and chain.ik_ctrl)


def ikfk_has_complete_chains(arm):
    """Whether the model has at least one usable IK/FK chain."""
    snapper = arm.MustardUI_IKFKSnapperSettings
    return any(ikfk_chain_is_complete(c) for c in snapper.ikfk_chains)


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
    """Readable chain name without the IK/FK tokens (e.g. R_Leg_IK -> R Leg)"""
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
    """Whether the bone is not hidden, ignoring the collections visibility"""
    b = arm_obj.data.bones.get(bone_name)
    return b is not None and not b.hide


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
    """IK/FK chains of the armature with a visible IK control, as dicts"""
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
            ik_collection = next((n for n in ik_candidates if "ik" in n.lower()), "") or (
                ik_candidates[0] if ik_candidates else ""
            )

            coll_names = {c.name for c in arm_obj.data.collections_all}
            fk_collection = ""
            if ik_collection:
                fk_collection = _fk_name_for(ik_collection, coll_names) or ""
            if not fk_collection:
                # Fall back to a collection the FK counterpart bones live in.
                fk_candidates = _collections_of(arm_obj, [n for n in fk_names if n])
                fk_collection = next((n for n in fk_candidates if "fk" in n.lower()), "")

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


def _arm_obj(arm_data, context=None):
    """Armature object using the data, the active one first since the data can be shared"""
    active = context.active_object if context else None
    for obj in (
        active,
        active and active.parent,
        arm_data.MustardUI_RigSettings.model_armature_object,
    ):
        if obj is not None and obj.data == arm_data:
            return obj
    return next((x for x in bpy.data.objects if x.type == "ARMATURE" and x.data == arm_data), None)


def _bone(arm_obj, name):
    if not name:
        return None
    return arm_obj.pose.bones.get(name)


def _split_bones(s):
    return [n.strip() for n in s.split(",") if n.strip()]


def _ik_constraint(arm_obj, chain):
    """IK constraint of the chain end bone targeting the IK control"""
    ik_list = _split_bones(chain.ik_bones)
    end = _bone(arm_obj, ik_list[-1]) if ik_list else None
    if end is None:
        return None
    return next(
        (c for c in end.constraints if c.type == "IK" and c.subtarget == chain.ik_ctrl), None
    )


def _ik_solve_changes(arm_obj, chain, ik_list):
    """Influences forcing a clean IK solve: IK and companions on, FK copies off"""
    ik_cns = _ik_constraint(arm_obj, chain)
    changes = [(ik_cns, 1.0)] if ik_cns is not None else []
    for pb in arm_obj.pose.bones:
        for cns in pb.constraints:
            if cns.type in _COPY_TYPES and cns.subtarget == chain.ik_ctrl:
                changes.append((cns, 1.0))
    fk_set = set(_split_bones(chain.fk_bones))
    for ik_name in ik_list:
        pb = _bone(arm_obj, ik_name)
        for cns in pb.constraints if pb is not None else []:
            if cns.type in _COPY_TYPES and cns.subtarget in fk_set:
                changes.append((cns, 0.0))
    return changes


def _override_influences(arm_obj, changes):
    """Set constraint influences, muting their drivers, returning what to restore"""
    drivers = arm_obj.animation_data.drivers if arm_obj.animation_data else None
    saved = []
    for cns, influence in changes:
        fcu = drivers.find(cns.path_from_id("influence")) if drivers else None
        saved.append((cns, cns.influence, fcu, fcu is not None and fcu.mute))
        if fcu is not None:
            fcu.mute = True
        cns.influence = influence
    if saved:
        bpy.context.view_layer.update()
    return saved


def _restore_influences(saved):
    for cns, influence, fcu, mute in reversed(saved):
        cns.influence = influence
        if fcu is not None:
            fcu.mute = mute
    if saved:
        bpy.context.view_layer.update()


# Last element of a data path: an attribute or a quoted key
_PATH_END = re.compile(r'^(.*?)(?:\.(\w+)|\[("(?:[^"\\]|\\.)*")\])$')


def _set_path(id_data, path, value):
    head, attr, key = _PATH_END.match(path).groups()
    owner = id_data.path_resolve(head) if head else id_data
    if attr:
        setattr(owner, attr, value)
    else:
        owner[ast.literal_eval(key)] = value


def _drive(source, source_path, driven):
    """Set the property read by the drivers to the value giving the driven values"""
    try:
        old = source.path_resolve(source_path)
        if not isinstance(old, (bool, int, float)):
            return False
        for candidate in dict.fromkeys((old, type(old)(0), type(old)(1))):
            _set_path(source, source_path, candidate)
            source.update_tag()
            bpy.context.view_layer.update()
            if all(
                math.isclose(float(owner.path_resolve(path)), value, abs_tol=1e-4)
                for owner, path, value, *_ in driven
            ):
                return True
        _set_path(source, source_path, old)
        source.update_tag()
    except (AttributeError, TypeError, ValueError):
        pass
    return False


def _set_values(targets, frame):
    """Set (owner, data_path, value, key) targets, through the property their drivers read"""
    direct = []
    sources = {}
    for owner, path, value, key in targets:
        fcu = owner.animation_data.drivers.find(path) if owner.animation_data else None
        variables = fcu.driver.variables if fcu is not None and not fcu.mute else []
        target = variables[0].targets[0] if len(variables) == 1 else None
        if target is not None and variables[0].type == "SINGLE_PROP" and target.id is not None:
            sources.setdefault((target.id, target.data_path), []).append(
                (owner, path, value, key, fcu)
            )
        else:
            if fcu is not None:
                fcu.mute = True
            direct.append((owner, path, value, key))

    keys = []
    for (source, source_path), driven in sources.items():
        if _drive(source, source_path, driven):
            if any(x[3] for x in driven):
                keys.append((source, source_path))
            continue
        # Drivers the switch can not drive are muted, not removed
        for owner, path, value, key, fcu in driven:
            fcu.mute = True
            direct.append((owner, path, value, key))

    for owner, path, value, key in direct:
        _set_path(owner, path, value)
        if key:
            keys.append((owner, path))

    if bpy.context.scene.tool_settings.use_keyframe_insert_auto:
        for owner, path in keys:
            owner.keyframe_insert(path, frame=frame)


def _signed_angle(v_from, v_to, axis):
    """Signed angle rotating v_from onto v_to around the axis"""
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


def populate_ikfk_chains(arm, arm_obj, clear_existing=False):
    """Rebuild the auto-detected IK/FK chains, returning the detected ones"""
    snapper = arm.MustardUI_IKFKSnapperSettings

    if clear_existing:
        snapper.ikfk_chains.clear()
    else:
        # Remove only previously auto-detected chains
        to_remove = [i for i, c in enumerate(snapper.ikfk_chains) if c.auto_detected]
        for i in reversed(to_remove):
            snapper.ikfk_chains.remove(i)

    def _sort_key(d):
        name = d["name"].lower()
        if "arm" in name:
            return 0
        if "leg" in name:
            return 1
        return 2

    found = sorted(detect_chains(arm_obj), key=_sort_key)
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
        # Works in both user and configuration mode
        return active_object_operator_poll(context, config=ModelMode.ANY)

    def execute(self, context):
        res, arm = mustardui_active_object(context, config=ModelMode.ANY)
        arm_obj = _arm_obj(arm, context)
        if arm_obj is None:
            self.report({"ERROR"}, "Cannot find armature object")
            return {"CANCELLED"}

        found = populate_ikfk_chains(arm, arm_obj, clear_existing=self.clear_existing)

        fk_missing = sum(1 for d in found if d["fk_found"] == 0)
        msg = f"Found {len(found)} IK chain(s)"
        if fk_missing:
            msg += f"; {fk_missing} chain(s) have no FK counterparts (IK→FK snap unavailable)"
        self.report({"INFO"}, msg)
        return {"FINISHED"}


def _chain_and_object(operator, context):
    """Chain of the operator and armature object of the model, or None if missing"""
    res, arm = mustardui_active_object(context, config=ModelMode.USER)
    chains = arm.MustardUI_IKFKSnapperSettings.ikfk_chains
    if operator.chain_index >= len(chains):
        operator.report({"ERROR"}, "Invalid chain index")
        return None, None
    arm_obj = _arm_obj(arm, context)
    if arm_obj is None:
        operator.report({"ERROR"}, "Cannot find armature object")
        return None, None
    return chains[operator.chain_index], arm_obj


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
        return active_object_operator_poll(context, config=ModelMode.USER)

    def execute(self, context):
        chain, arm_obj = _chain_and_object(self, context)
        if chain is None:
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

    def _snap_fk_to_ik(self, arm_obj, chain, frame):
        ik_ctrl_bone = _bone(arm_obj, chain.ik_ctrl)
        if ik_ctrl_bone is None:
            self.report({"ERROR"}, f"IK control bone '{chain.ik_ctrl}' not found")
            return False

        # FK bones keep their position in the chain: a missing one uses the IK bone,
        # as do single-chain rigs, which reuse the same bones for FK
        ik_list = _split_bones(chain.ik_bones)
        fk_slots = [x.strip() for x in chain.fk_bones.split(",")]
        fk_list = [fk or ik for ik, fk in zip_longest(ik_list, fk_slots, fillvalue="") if fk or ik]
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
        ik_side = set(ik_list) | {chain.ik_ctrl}
        changes = [
            (cns, 0.0)
            for pb in arm_obj.pose.bones
            for cns in pb.constraints
            if cns.influence != 0.0
            and (
                (cns.type == "IK" and cns.subtarget == chain.ik_ctrl)
                or (cns.type in _COPY_TYPES and cns.subtarget in ik_side)
            )
        ]
        saved = _override_influences(arm_obj, changes)
        try:
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
                    and cns.subtarget == chain.ik_ctrl
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
        finally:
            _restore_influences(saved)

        return True

    @staticmethod
    def _match_pole(arm_obj, chain, ik_list, pole_bone, base, axis, radial_len, desired_dir):
        """Place the pole so that the IK solve reproduces the FK bend"""
        default = base + desired_dir * radial_len
        if not ik_list:
            return default
        mid_ik = _bone(arm_obj, ik_list[len(ik_list) // 2])
        if mid_ik is None:
            return default

        # Temporarily force a clean IK solve, unpinning the IK bones from FK
        saved = _override_influences(arm_obj, _ik_solve_changes(arm_obj, chain, ik_list))
        try:
            # Solve with the pole aimed along the FK bend direction and read the bend
            # the solver actually produced (mid joint offset from the axis).
            _set_world_location(pole_bone, default)  # triggers a view_layer update
            achieved = mid_ik.head - base
            achieved -= axis * achieved.dot(axis)
        finally:
            _restore_influences(saved)

        if achieved.length > 1e-7:
            # Rotate the pole back by the angle the solver introduced.
            err = _signed_angle(achieved, desired_dir, axis)
            return base + Quaternion(axis, err) @ desired_dir * radial_len
        return default

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
            fk_pairing = ik_list
        else:
            # Preserve empty positions: a partial FK mapping stores "" for bones
            # with no FK counterpart, and dropping them would shift every later FK
            # bone one slot left and mis-pair the chain. Skip the empty pairs below.
            fk_pairing = [n.strip() for n in chain.fk_bones.split(",")]

        # The IK pose only exists when the IK constraint is solving. If we're in FK
        # mode it is off and the chain tracks FK instead, so reading it now would
        # make IK→FK a no-op (you'd have to switch to IK first). Force a clean IK
        # solve while we read, then restore the constraints.
        saved = _override_influences(arm_obj, _ik_solve_changes(arm_obj, chain, ik_list))
        try:
            # Capture the solved IK world matrices before changing anything: writing
            # a bone triggers a view_layer update that re-evaluates the IK solve and
            # can shift the remaining matrices.
            pairs = []
            for ik_name, fk_name in zip(ik_list, fk_pairing, strict=False):
                ik_b = _bone(arm_obj, ik_name)
                fk_b = _bone(arm_obj, fk_name)
                if ik_b is None or fk_b is None:
                    continue
                pairs.append((fk_b, ik_b.matrix.copy()))

            # The tip/hand bone is not part of the IK chain: its rotation comes from
            # a companion Copy Rotation/Transforms that targets the IK ctrl. Capture
            # that IK-driven world matrix too, so we can bake it into the FK pose —
            # otherwise the tip snaps back to its old FK rotation when the switch
            # disables the companion.
            companions = []  # (pose_bone, world_matrix, [constraints])
            for pb in arm_obj.pose.bones:
                cnss = [
                    c
                    for c in pb.constraints
                    if c.type in _COPY_TYPES and c.subtarget == chain.ik_ctrl
                ]
                if cnss:
                    companions.append((pb, pb.matrix.copy(), cnss))
        finally:
            _restore_influences(saved)

        if not pairs:
            self.report({"ERROR"}, "No valid IK/FK bone pairs found")
            return False

        # Disable everything that drives these bones from the IK side so the
        # matrices we write below bake into the basis instead of being overwritten:
        # the IK constraint (single-chain only — separate FK controls aren't driven
        # by it) and the tip's companion constraints.
        off = [cns for _pb, _mat, cnss in companions for cns in cnss]
        ik_cns = _ik_constraint(arm_obj, chain) if single_chain else None
        if ik_cns is not None:
            off.insert(0, ik_cns)
        _set_values([(arm_obj, x.path_from_id("influence"), 0.0, True) for x in off], frame)
        bpy.context.view_layer.update()

        # Bake the chain (root→tip) then the tip/companion bones.
        for fk_b, mat in pairs:
            _set_world_matrix(fk_b, mat)
            _auto_key(fk_b, frame)
        for pb, mat, _cnss in companions:
            _set_world_matrix(pb, mat)
            _auto_key(pb, frame)

        return True


def _visibility_path(armature, coll):
    """Data path of the collection visibility, the one with a driver if any"""
    name = bpy.utils.escape_identifier(coll.name)
    paths = (coll.path_from_id("is_visible"), f'collections["{name}"].is_visible')
    ad = armature.animation_data
    return next((x for x in paths if ad and ad.drivers.find(x)), paths[0])


def apply_ikfk_switch(arm_obj, chain, direction, frame):
    """Switch the IK constraints of the chain and the visibility of its collections"""
    ik_list = _split_bones(chain.ik_bones)
    if not ik_list:
        return
    to_ik = direction == "FK_TO_IK"
    influences = []

    # 1. The IK constraint on the chain end bone
    ik_cns = _ik_constraint(arm_obj, chain)
    if ik_cns is not None:
        influences.append((ik_cns, to_ik))

    # 2. Companion constraints on ALL pose bones that target ik_ctrl.
    #    Covers e.g. Hand.l Copy Rotation → L_Arm_IK.
    for pb in arm_obj.pose.bones:
        for cns in pb.constraints:
            if cns.type in _COPY_TYPES and cns.subtarget == chain.ik_ctrl:
                influences.append((cns, to_ik))

    # 3. Copy constraints on IK chain bones that target FK chain bones.
    #    Many rigs use Copy Rotation/Transform from FK→IK in FK mode so the IK
    #    chain tracks the FK animation. When switching to IK, these must be
    #    disabled so the IK solver can freely rotate all chain bones (including
    #    the first one, which otherwise stays locked to the FK rotation).
    fk_set = set(_split_bones(chain.fk_bones))
    for ik_name in ik_list:
        pb = _bone(arm_obj, ik_name)
        for cns in pb.constraints if pb is not None else []:
            if cns.type in _COPY_TYPES and cns.subtarget in fk_set:
                influences.append((cns, not to_ik))

    targets = [(arm_obj, c.path_from_id("influence"), float(v), True) for c, v in influences]

    # 4. Show the bone collection for the new mode and hide the other one.
    armature = arm_obj.data
    for name, visible in ((chain.ik_collection, to_ik), (chain.fk_collection, not to_ik)):
        coll = armature.collections_all.get(name) if name else None
        if coll is not None:
            targets.append((armature, _visibility_path(armature, coll), visible, False))

    _set_values(targets, frame)
    arm_obj.update_tag()
    bpy.context.view_layer.update()


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
        return active_object_operator_poll(context, config=ModelMode.USER)

    def execute(self, context):
        chain, arm_obj = _chain_and_object(self, context)
        if chain is None:
            return {"CANCELLED"}

        snap_direction = "FK_TO_IK" if self.direction == "TO_IK" else "IK_TO_FK"
        apply_ikfk_switch(arm_obj, chain, snap_direction, context.scene.frame_current)
        return {"FINISHED"}


class MUSTARDUI_OT_IKFKChainAdd(bpy.types.Operator):
    """Add a blank IK/FK chain entry"""

    bl_idname = "mustardui.ikfk_chain_add"
    bl_label = "Add IK/FK Chain"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        return active_object_operator_poll(context, config=ModelMode.CONFIG)

    def execute(self, context):
        res, arm = mustardui_active_object(context, config=ModelMode.CONFIG)
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
        res, arm = mustardui_active_object(context, config=ModelMode.CONFIG)
        if not res or arm is None:
            return False
        return len(arm.MustardUI_IKFKSnapperSettings.ikfk_chains) > 0

    def execute(self, context):
        res, arm = mustardui_active_object(context, config=ModelMode.CONFIG)
        snapper = arm.MustardUI_IKFKSnapperSettings
        idx = snapper.ikfk_chains_index
        if idx < len(snapper.ikfk_chains):
            snapper.ikfk_chains.remove(idx)
            snapper.ikfk_chains_index = max(0, idx - 1)
        return {"FINISHED"}


class MUSTARDUI_OT_IKFKChainSwitch(bpy.types.Operator):
    """Move the selected IK/FK chain in the list"""

    bl_idname = "mustardui.ikfk_chain_switch"
    bl_label = "Move IK/FK Chain"

    direction: bpy.props.EnumProperty(
        items=(
            ("UP", "Up", ""),
            ("DOWN", "Down", ""),
        )
    )

    @classmethod
    def poll(cls, context):
        return active_object_operator_poll(context, config=ModelMode.CONFIG)

    def execute(self, context):
        res, arm = mustardui_active_object(context, config=ModelMode.CONFIG)
        snapper = arm.MustardUI_IKFKSnapperSettings
        chains = snapper.ikfk_chains
        index = snapper.ikfk_chains_index

        if len(chains) <= index:
            return {"FINISHED"}

        if self.direction == "UP" and index == 0:
            return {"FINISHED"}
        if self.direction == "DOWN" and index >= len(chains) - 1:
            return {"FINISHED"}
        neighbour = index + (-1 if self.direction == "UP" else 1)
        chains.move(neighbour, index)

        list_length = len(chains) - 1
        new_index = index + (-1 if self.direction == "UP" else 1)
        snapper.ikfk_chains_index = max(0, min(new_index, list_length))

        return {"FINISHED"}


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


_classes = [
    MustardUI_IKFKChain,
    MustardUI_IKFKSnapperSettings,
    MUSTARDUI_UL_IKFKChain_UIList,
    MUSTARDUI_OT_IKFKDetect,
    MUSTARDUI_OT_IKFKSnap,
    MUSTARDUI_OT_IKFKSwitch,
    MUSTARDUI_OT_IKFKChainAdd,
    MUSTARDUI_OT_IKFKChainRemove,
    MUSTARDUI_OT_IKFKChainSwitch,
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
