import bpy
from ..model_selection.active_object import *


# =========================================================
# UNIVERSAL LIP DETECTION
# =========================================================

def detect_lip_map(armature):
    names = {b.name for b in armature.data.bones}

    # New MHX
    new_mhx = [
        'lipuppermiddle', 'lipupper.L', 'lipupper.R',
        'lipcorner.L', 'liplower.L', 'liplowermiddle',
        'liplower.R', 'lipcorner.R'
    ]

    if all(b in names for b in new_mhx):
        return {
            "corners": ["lipcorner.L", "lipcorner.R"],
            "lower": ["liplower.L", "liplowermiddle", "liplower.R"],
            "upper": ["lipuppermiddle", "lipupper.L", "lipupper.R"],
            "all": new_mhx
        }

    # Old MHX
    old_mhx_variants = [
        ("Lip", "L", "R"),
        ("Lip", "l", "r"),
        ("lip", "L", "R"),
        ("lip", "l", "r"),
    ]

    for prefix, L, R in old_mhx_variants:
        test = f"{prefix}Corner.{L}"
        if test in names:
            def n(x): return f"{prefix}{x}"

            return {
                "corners": [n(f"Corner.{L}"), n(f"Corner.{R}")],
                "lower": [
                    n(f"LowerOuter.{L}"),
                    n("LowerMiddle"),
                    n(f"LowerOuter.{R}")
                ],
                "upper": [
                    n("UpperMiddle"),
                    n(f"UpperOuter.{L}"),
                    n(f"UpperOuter.{R}")
                ],
                "all": [
                    n(f"Corner.{L}"),
                    n(f"LowerOuter.{L}"),
                    n(f"LowerInner.{L}"),
                    n("LowerMiddle"),
                    n(f"LowerInner.{R}"),
                    n(f"LowerOuter.{R}"),
                    n(f"Corner.{R}"),
                    n("UpperMiddle"),
                    n(f"UpperOuter.{L}"),
                    n(f"UpperInner.{L}"),
                    n(f"UpperInner.{R}"),
                    n(f"UpperOuter.{R}"),
                ]
            }

    # ARP
    arp_test = "c_lips_smile.l"
    if arp_test in names:
        return {
            "corners": ["c_lips_smile.r", "c_lips_smile.l"],
            "lower": [
                "c_lips_bot.r",
                "c_lips_bot.x",
                "c_lips_bot.l"
            ],
            "upper": [
                "c_lips_top.x",
                "c_lips_top.r",
                "c_lips_top.l"
            ],
            "all": [
                'c_lips_smile.r', 'c_lips_top.r', 'c_lips_top_01.r', 'c_lips_top.x',
                'c_lips_top.l', 'c_lips_top_01.l', 'c_lips_smile.l',
                'c_lips_bot.r', 'c_lips_bot_01.r', 'c_lips_bot.x',
                'c_lips_bot.l', 'c_lips_bot_01.l'
            ]
        }

    return None


class ConstraintManager:
    def __init__(self, owner_tag="MUSTARDUI"):
        self.tag = owner_tag

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


def apply_lips_shrinkwrap(props, armature):
    lip_map = detect_lip_map(armature)

    if not lip_map:
        return

    cm = ConstraintManager(props.bone_shrinkwrap_constraint_tag)

    corners = set(lip_map["corners"])
    lowers = set(lip_map["lower"])
    uppers = set(lip_map["upper"])

    for name in lip_map["all"]:
        pbone = armature.pose.bones.get(name)
        if not pbone:
            continue

        # Shrinkwrap
        c = cm.ensure(pbone, "shrinkwrap", 'SHRINKWRAP')

        c.target = props.bone_shrinkwrap_target
        c.wrap_mode = 'OUTSIDE'

        dist = props.bone_shrinkwrap_distance
        if name in corners:
            dist *= props.bone_shrinkwrap_corner_correction

        c.distance = dist
        c.influence = 1.0 if props.bone_shrinkwrap_enable else 0.0

        if props.bone_shrinkwrap_rotation_correction:
            if name in uppers:
                c.use_track_normal = True
                c.track_axis = 'TRACK_NEGATIVE_Z'
            elif name in lowers:
                c.use_track_normal = True
                c.track_axis = 'TRACK_Z'
        else:
            c.use_track_normal = False

        # Friction
        cf = cm.ensure(pbone, "friction", 'CHILD_OF')

        cf.target = (
            props.bone_shrinkwrap_target_friction
            or props.bone_shrinkwrap_target
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
    bl_idname = "mustardui.constraints_apply"
    bl_label = "Apply Constraint System"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)

        if arm is None:
            return False

        target = arm.MustardUI_ToolsSettings.bone_shrinkwrap_target
        return res if target is not None else False

    def execute(self, context):
        res, arm = mustardui_active_object(context, config=0)

        armature = arm.MustardUI_RigSettings.model_armature_object

        if not armature:
            self.report({'ERROR'}, "No armature set")
            return {'CANCELLED'}

        apply_lips_shrinkwrap(arm.MustardUI_ToolsSettings, armature)

        return {'FINISHED'}


class MUSTARDUI_OT_constraints_clear(bpy.types.Operator):
    bl_idname = "mustardui.constraints_clear"
    bl_label = "Clear Managed Constraints"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        return res if arm is not None else False

    def execute(self, context):
        res, arm = mustardui_active_object(context, config=0)

        armature = arm.MustardUI_RigSettings.model_armature_object
        cm = ConstraintManager("MUSTARDUI_LIPS")

        for pb in armature.pose.bones:
            cm.remove_all_tagged(pb)

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MUSTARDUI_OT_constraint_apply)
    bpy.utils.register_class(MUSTARDUI_OT_constraints_clear)


def unregister():
    bpy.utils.unregister_class(MUSTARDUI_OT_constraints_clear)
    bpy.utils.unregister_class(MUSTARDUI_OT_constraint_apply)
