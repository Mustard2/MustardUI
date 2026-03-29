import bpy
from ....model_selection.active_object import *
from .diffeomorphic_ikfk import *


def toggleFKIK(row, value, op):
    if value > 0.5:
        row.operator(op, text="IK")
    else:
        row.operator(op, text="FK")


def diffeomorphic_ikfk_panel_poll(context):
    res, arm = mustardui_active_object(context, config=0)
    rig = arm.MustardUI_RigSettings.model_armature_object
    return all(name in rig for name in ("MhaArmIk_L", "MhaArmIk_R"))


def diffeomorphic_ikfk_panel(layout, context):
    res, arm = mustardui_active_object(context, config=0)
    rig = arm.MustardUI_RigSettings.model_armature_object
    scn = context.scene

    box = layout.box()
    box.label(text="Arms")
    row = box.row()
    row.label(text="Left")
    row.label(text="Right")
    row = box.row()
    toggleFKIK(row, rig["MhaArmIk_L"], "mhx.toggle_fkik_left_arm")
    toggleFKIK(row, rig["MhaArmIk_R"], "mhx.toggle_fkik_right_arm")
    row = box.row()
    row.prop(rig, propRef("MhaArmIk_L"), text="Arm IK Left")
    row.prop(rig, propRef("MhaArmIk_R"), text="Arm IK Right")
    row = box.row()
    row.operator("mhx.snap_fk_left_arm")
    row.operator("mhx.snap_fk_right_arm")
    row = box.row()
    row.operator("mhx.snap_ik_left_arm")
    row.operator("mhx.snap_ik_right_arm")

    box = layout.box()
    box.label(text="Legs")
    row = box.row()
    row.label(text="Left")
    row.label(text="Right")
    row = box.row()
    toggleFKIK(row, rig["MhaLegIk_L"], "mhx.toggle_fkik_left_leg")
    toggleFKIK(row, rig["MhaLegIk_R"], "mhx.toggle_fkik_right_leg")
    row = box.row()
    row.prop(rig, propRef("MhaLegIk_L"), text="Leg IK Left")
    row.prop(rig, propRef("MhaLegIk_R"), text="Leg IK Right")
    row = box.row()
    row.operator("mhx.snap_fk_left_leg")
    row.operator("mhx.snap_fk_right_leg")
    row = box.row()
    row.operator("mhx.snap_ik_left_leg")
    row.operator("mhx.snap_ik_right_leg")

    layout.separator()
    row = layout.row()
    row.operator("mhx.enforce_limits")
    row.operator("mhx.clear_ik_twist_bones")
    row = layout.row()
    row.operator("mhx.clear_fingers")
    row.operator("mhx.clear_feet")
    row = layout.row()
    row.operator("mhx.clear_tongue")
    row.operator("mhx.clear_face")
    row = layout.row()
    row.operator("mhx.set_fk_all")
    row.operator("mhx.set_ik_all")
    row = layout.row()
    row.operator("mhx.snap_fk_all")
    row.operator("mhx.snap_ik_all")
    layout.prop(scn, "MhxUseSwitch")
    layout.prop(scn, "MhxUseSnapRotation")
