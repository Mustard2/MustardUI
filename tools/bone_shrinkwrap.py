import bpy

from ..model_selection.active_object import mustardui_active_object

RIG_MAP = {
    "arp": {
        "type": "arp",
        "bones": {
            "corner": ["c_lips_smile.r", "c_lips_smile.l"],
            "all": [
                "c_lips_smile.r",
                "c_lips_top.r",
                "c_lips_top_01.r",
                "c_lips_top.x",
                "c_lips_top.l",
                "c_lips_top_01.l",
                "c_lips_smile.l",
                "c_lips_bot.r",
                "c_lips_bot_01.r",
                "c_lips_bot.x",
                "c_lips_bot.l",
                "c_lips_bot_01.l",
            ],
        },
    },
    "mhx": {
        "type": "mhx",
        # Naming patterns instead of hardcoded lists
        "pattern": {
            "corner": "Corner.{side}",
            "lower_outer": "LowerOuter.{side}",
            "lower_inner": "LowerInner.{side}",
            "lower_mid": "LowerMiddle",
            "upper_mid": "UpperMiddle",
            "upper_outer": "UpperOuter.{side}",
            "upper_inner": "UpperInner.{side}",
        },
        # Supported naming variants
        "variants": [
            {"prefix": "Lip", "corner": "LipCorner.l", "sides": ("l", "r")},
            {"prefix": "Lip", "corner": "LipCorner.L", "sides": ("L", "R")},
            {"prefix": "lip", "corner": "lipCorner.l", "sides": ("l", "r")},
            {"prefix": "lip", "corner": "lipCorner.L", "sides": ("L", "R")},
        ],
    },
}


def build_mhx_bones(variant, pattern):
    prefix = variant["prefix"]
    left, right = variant["sides"]

    def n(key, side=None):
        name = pattern[key]
        if "{side}" in name:
            name = name.format(side=side)
        return f"{prefix}{name}"

    return [
        n("corner", left),
        n("lower_outer", left),
        n("lower_inner", left),
        n("lower_mid"),
        n("lower_inner", right),
        n("lower_outer", right),
        n("corner", right),
        n("upper_mid"),
        n("upper_outer", left),
        n("upper_inner", left),
        n("upper_inner", right),
        n("upper_outer", right),
    ]


def get_lip_bones(rig_type, armature):
    rig = RIG_MAP.get(rig_type)
    if not rig:
        return []

    if rig_type == "arp":
        return rig["bones"]["all"]

    if rig_type == "mhx":
        variant = detect_rig_variant(armature, rig_type)
        if not variant:
            return []

        return build_mhx_bones(variant, rig["pattern"])

    return []


def get_corner_bones(rig_type, armature):
    rig = RIG_MAP.get(rig_type)
    if not rig:
        return []

    if rig_type == "arp":
        return rig["bones"]["corner"]

    if rig_type == "mhx":
        variant = detect_rig_variant(armature, rig_type)
        if not variant:
            return []

        prefix = variant["prefix"]
        left, right = variant["sides"]

        return [
            f"{prefix}Corner.{left}",
            f"{prefix}Corner.{right}",
        ]

    return []


def detect_rig_variant(armature, rig_type):
    names = {b.name for b in armature.data.bones}

    rig = RIG_MAP.get(rig_type)
    if not rig:
        return None

    if rig_type == "arp":
        return {"type": "arp"}

    for v in rig.get("variants", []):
        if v["corner"] in names:
            return v

    return None


class ConstraintManager:
    def __init__(self, owner_tag="MUSTARDUI"):
        self.tag = owner_tag

    # -----------------------------
    # Internal Helpers
    # -----------------------------
    def _tag_name(self, name):
        return f"{self.tag}_{name}"

    def get(self, pbone, name):
        return pbone.constraints.get(self._tag_name(name))

    def ensure(self, pbone, name, ctype):
        cname = self._tag_name(name)
        c = pbone.constraints.get(cname)

        if not c:
            c = pbone.constraints.new(ctype)
            c.name = cname

        return c

    def remove(self, pbone, name):
        cname = self._tag_name(name)
        c = pbone.constraints.get(cname)
        if c:
            pbone.constraints.remove(c)

    def remove_all_tagged(self, pbone):
        for c in list(pbone.constraints):
            if c.name.startswith(self.tag):
                pbone.constraints.remove(c)

    def set_enabled(self, pbone, name, state: bool):
        c = self.get(pbone, name)
        if c:
            c.influence = 1.0 if state else 0.0

    def exists(self, pbone, name):
        return self._tag_name(name) in pbone.constraints


def apply_lips_shrinkwrap(props, armature, rig_type):
    cm = ConstraintManager(props.bone_shrinkwrap_constraint_tag)

    bones = get_lip_bones(rig_type, armature)
    corners = set(get_corner_bones(rig_type, armature))

    for name in bones:
        pbone = armature.pose.bones.get(name)
        if not pbone:
            continue

        # -------------------------
        # SHRINKWRAP
        # -------------------------
        c = cm.ensure(pbone, "shrinkwrap", "SHRINKWRAP")

        c.target = props.bone_shrinkwrap_target
        c.wrap_mode = "OUTSIDE"

        dist = props.bone_shrinkwrap_distance
        if name in corners:
            dist *= props.bone_shrinkwrap_corner_correction

        c.distance = dist

        # NON-DESTRUCTIVE TOGGLE
        c.influence = 1.0 if props.bone_shrinkwrap_enable else 0.0

        # -------------------------
        # FRICTION
        # -------------------------
        cf = cm.ensure(pbone, "friction", "CHILD_OF")

        cf.target = (
            props.bone_shrinkwrap_target_friction or props.bone_shrinkwrap_target
        )

        if props.bone_shrinkwrap_target_friction_subtarget:
            cf.subtarget = props.bone_shrinkwrap_target_friction_subtarget

        cf.use_scale_x = False
        cf.use_scale_y = False
        cf.use_scale_z = False

        cf.influence = (
            props.bone_shrinkwrap_friction_influence
            if (props.bone_shrinkwrap_enable and props.bone_shrinkwrap_enable_friction)
            else 0.0
        )


class MUSTARDUI_OT_constraint_apply(bpy.types.Operator):
    """Add Bone Shrinkwrap on the lips"""

    bl_idname = "mustardui.constraints_apply"
    bl_label = "Apply Constraint System"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)

        if arm is None:
            return False

        tools_settings = arm.MustardUI_ToolsSettings
        target = tools_settings.bone_shrinkwrap_target

        return res if target is not None else False

    def execute(self, context):
        res, arm = mustardui_active_object(context, config=0)
        tools_settings = arm.MustardUI_ToolsSettings
        rig_settings = arm.MustardUI_RigSettings

        armature = rig_settings.model_armature_object

        if not armature:
            self.report({"ERROR"}, "No armature set")
            return {"CANCELLED"}

        rig_type = rig_settings.model_rig_type

        # Plug modules here
        apply_lips_shrinkwrap(tools_settings, armature, rig_type)

        return {"FINISHED"}


class MUSTARDUI_OT_constraints_clear(bpy.types.Operator):
    """Clear Bone Shrinkwrap on the lips, removing all constraints and settings"""

    bl_idname = "mustardui.constraints_clear"
    bl_label = "Clear Managed Constraints"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        return res if arm is not None else False

    def execute(self, context):
        res, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings

        armature = rig_settings.model_armature_object

        cm = ConstraintManager("MUSTARDUI_LIPS")

        for pb in armature.pose.bones:
            cm.remove_all_tagged(pb)

        return {"FINISHED"}


def register():
    bpy.utils.register_class(MUSTARDUI_OT_constraint_apply)
    bpy.utils.register_class(MUSTARDUI_OT_constraints_clear)


def unregister():
    bpy.utils.unregister_class(MUSTARDUI_OT_constraints_clear)
    bpy.utils.unregister_class(MUSTARDUI_OT_constraint_apply)
