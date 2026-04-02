# SPDX-FileCopyrightText: 2016-2026, Thomas Larsson
#
# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
from .utils import *
from .layers import *

from ....menu import MainPanel
from ...external.mhx_defs import panel_poll


def needsMhxUpdate(layout, rig):
    if rig is None:
        return True
    if bpy.app.version >= (4,0,0) and "Layer 1" in rig.data.collections.keys():
        layout.operator("mhx.update_mhx_blender4")
        return True
    if not rig.data.get("MhaFeatures", 0) & F_IDPROPS:
        layout.operator("mhx.update_mhx")
        return True
    return False

#------------------------------------------------------------------------
#    Mhx Properties Panel
#------------------------------------------------------------------------

class MHX_PT_MustardUI_Properties(MainPanel, bpy.types.Panel):
    bl_label = "Properties"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MHX"
    bl_options = {'DEFAULT_CLOSED'}
    bl_parent_id = "PANEL_PT_MustardUI_Armature_External"

    @classmethod
    def poll(cls, context):
        ob = context.object
        return (ob and ob.get("MhxRig", False)) and panel_poll(cls, context)

    def draw(self, context):
        rig = context.object
        if needsMhxUpdate(self.layout, rig):
            return

        self.layout.label(text = "Gaze")
        self.layout.prop(rig, propRef("MhaGazeFollowsHead"), text="Gaze Follows Head")
        row = self.layout.row()
        row.prop(rig, propRef("MhaGaze_L"), text="Gaze Left")
        row.prop(rig, propRef("MhaGaze_R"), text="Gaze Right")
        if "MhaTongueIk" in rig.keys():
            self.layout.prop(rig, propRef("MhaTongueIk"), text="Tongue IK")

        self.layout.label(text = "Spine")
        if "MhaNeckFollowsSpine" in rig.keys():
            self.layout.prop(rig, propRef("MhaNeckFollowsSpine"), text="Neck Follows Spine")
        if "MhaSpineIk" in rig.keys():
            self.layout.prop(rig, propRef("MhaSpineIk"), text="Spine IK")
        row = self.layout.row()
        row.prop(rig, propRef("MhaSpineControl"), text="FK/IK Spine")
        row.prop(rig, propRef("MhaNeckControl"), text="FK/IK Neck")

        self.layout.label(text = "Hinge")
        row = self.layout.row()
        row.prop(rig, propRef("MhaArmHinge_L"), text="Arm Hinge Left")
        row.prop(rig, propRef("MhaArmHinge_R"), text="Arm Hinge Right")
        row = self.layout.row()
        row.prop(rig, propRef("MhaLegHinge_L"), text="Leg Hinge Left")
        row.prop(rig, propRef("MhaLegHinge_R"), text="Leg Hinge Right")
        row = self.layout.row()
        op = row.operator("mhx.unhinge", text="Unhinge Left Arm")
        op.limb = "Arm"
        op.suffix = "L"
        op = row.operator("mhx.unhinge", text="Unhinge Right Arm")
        op.limb = "Arm"
        op.suffix = "R"
        row = self.layout.row()
        op = row.operator("mhx.unhinge", text="Unhinge Left Leg")
        op.limb = "Leg"
        op.suffix = "L"
        op = row.operator("mhx.unhinge", text="Unhinge Right Leg")
        op.limb = "Leg"
        op.suffix = "R"

        self.layout.label(text = "Hands And Fingers")
        row = self.layout.row()
        row.prop(rig, propRef("MhaForearmFollow_L"), text="Forearm Follows Hand Left")
        row.prop(rig, propRef("MhaForearmFollow_R"), text="Forearm Follows Hand Right")
        row = self.layout.row()
        row.prop(rig, propRef("MhaFingerControl_L"), text="FK/IK Fingers Left")
        row.prop(rig, propRef("MhaFingerControl_R"), text="FK/IK Fingers Right")
        if "MhaFingerIk_L" in rig.keys():
            row = self.layout.row()
            row.prop(rig, propRef("MhaFingerIk_L"), text="Finger IK Left")
            row.prop(rig, propRef("MhaFingerIk_R"), text="Finger IK Right")

        self.layout.label(text = "Limits")
        row = self.layout.row()
        self.updateFunction(row, rig, "MhaLimitsOn", "mhx.toggle_limits")
        row.operator("mhx.enforce_limits")

        self.layout.label(text = "IK")
        row = self.layout.row()
        row.prop(rig, propRef("MhaArmIk_L"), text="Arm IK Left")
        row.prop(rig, propRef("MhaArmIk_R"), text="Arm IK Right")
        row = self.layout.row()
        row.prop(rig, propRef("MhaLegIk_L"), text="Leg IK Left")
        row.prop(rig, propRef("MhaLegIk_R"), text="Leg IK Left")
        if "foot.2.L" in rig.pose.bones.keys():
            row = self.layout.row()
            row.prop(rig, propRef("MhaLegIkToAnkle_L"), text="Ankle IK Left")
            row.prop(rig, propRef("MhaLegIkToAnkle_R"), text="Ankle IK Right")

        self.layout.label(text = "Stretchiness")
        row = self.layout.row()
        row.prop(rig, propRef("MhaArmStretch_L"), text="Arm Stretch Left")
        row.prop(rig, propRef("MhaArmStretch_R"), text="Arm Stretch Right")
        row = self.layout.row()
        row.prop(rig, propRef("MhaLegStretch_L"), text="Leg Stretch Left")
        row.prop(rig, propRef("MhaLegStretch_R"), text="Leg Stretch Right")

        self.layout.label(text = "Toes Tarsal Parents")
        row = self.layout.row()
        self.updateFunction(row, rig, "MhaToeTarsal_L", "mhx.toggle_left_toe_tarsal")
        self.updateFunction(row, rig, "MhaToeTarsal_R", "mhx.toggle_right_toe_tarsal")

        self.layout.separator()
        self.layout.operator("mhx.update_mhx")


    def updateFunction(self, layout, rig, prop, opname):
        icon = ('CHECKBOX_HLT' if rig[prop] else 'CHECKBOX_DEHLT')
        layout.operator(opname, icon=icon)

#------------------------------------------------------------------------
#    Mhx FK/IK switch panel
#------------------------------------------------------------------------

class MHX_PT_MustardUI_FKIKArmsLegs(MainPanel, bpy.types.Panel):
    bl_label = "FK/IK Arms Legs"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MHX"
    bl_options = {'DEFAULT_CLOSED'}
    bl_parent_id = "PANEL_PT_MustardUI_Armature_External"

    @classmethod
    def poll(cls, context):
        ob = context.object
        return (ob and ob.get("MhxRig", False)) and panel_poll(cls, context)

    def draw(self, context):
        rig = context.object
        scn = context.scene
        if needsMhxUpdate(self.layout, rig):
            return

        box = self.layout.box()
        box.label(text = "Arms")
        row = box.row()
        row.label(text = "Left")
        row.label(text = "Right")
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

        box = self.layout.box()
        box.label(text = "Legs")
        row = box.row()
        row.label(text = "Left")
        row.label(text = "Right")
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

        self.layout.separator()
        row = self.layout.row()
        row.operator("mhx.enforce_limits")
        row.operator("mhx.clear_ik_twist_bones")
        row = self.layout.row()
        row.operator("mhx.clear_fingers")
        row.operator("mhx.clear_feet")
        row = self.layout.row()
        row.operator("mhx.clear_tongue")
        row.operator("mhx.clear_face")
        row = self.layout.row()
        row.operator("mhx.set_fk_all")
        row.operator("mhx.set_ik_all")
        row = self.layout.row()
        row.operator("mhx.snap_fk_all")
        row.operator("mhx.snap_ik_all")
        self.layout.prop(scn, "MhxUseSwitch")
        self.layout.prop(scn, "MhxUseSnapRotation")


def toggleFKIK(row, value, op):
    if value > 0.5:
        row.operator(op, text="IK")
    else:
        row.operator(op, text="FK")


class MHX_PT_MustardUI_FKIKFingers(MainPanel, bpy.types.Panel):
    bl_label = "FK/IK Spine Fingers Tongue Shaft"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MHX"
    bl_options = {'DEFAULT_CLOSED'}
    bl_parent_id = "PANEL_PT_MustardUI_Armature_External"

    @classmethod
    def poll(cls, context):
        ob = context.object
        return (ob and ob.get("MhxRig", False)) and panel_poll(cls, context)

    def draw(self, context):
        rig = context.object
        scn = context.scene
        if needsMhxUpdate(self.layout, rig):
            return

        box = self.layout.box()
        box.label(text = "Spine")
        row = box.row()
        row.prop(rig, propRef("MhaSpineControl"), text="Spine FK/IK")
        row.prop(rig, propRef("MhaNeckControl"), text="Neck FK/IK")
        if "MhaSpineIk" in rig.keys():
            box.prop(rig, propRef("MhaSpineIk"), text="Spine IK")
            row = box.row()
            op = row.operator("mhx.snap_reverse", text="Snap FK")
            op.prop = "MhaSpineIk"
            op.value = 0.0
            op.bonename = "back"
            op.revname = "REV-ik_back"
            op.fk = op.ik = L_MAIN
            op = row.operator("mhx.snap_reverse", text="Snap IK")
            op.prop = "MhaSpineIk"
            op.value = 1.0
            op.bonename = "ik_back"
            op.revname = "REV-back"
            op.fk = op.ik = L_MAIN

        row = box.row()
        row.operator("mhx.snap_spine")

        box = self.layout.box()
        box.label(text = "Fingers")
        row = box.row()
        row.label(text = "Left")
        row.label(text = "Right")
        row = box.row()
        row.prop(rig, propRef("MhaFingerControl_L"), text="Fingers FK/IK Left")
        row.prop(rig, propRef("MhaFingerControl_R"), text="Fingers FK/IK Right")
        if "MhaFingerIk_L" in rig.keys():
            row = box.row()
            row.prop(rig, propRef("MhaFingerIk_L"), text="IK Influence")
            row.prop(rig, propRef("MhaFingerIk_R"), text="IK Influence")
        row = box.row()
        for suffix in ["L", "R"]:
            op = row.operator("mhx.snap_fingers")
            op.suffix = suffix

        if "MhaTongueControl" in rig.keys():
            box = self.layout.box()
            box.prop(rig, propRef("MhaTongueControl"), text="Tongue FK/IK")
            if "MhaTongueIk" in rig.keys():
                box.prop(rig, propRef("MhaTongueIk"), text="Tongue IK")
                parprops = [prop for prop in rig.keys() if prop.startswith("MhaTongue_")]
                for parprop in parprops:
                    text = "%s Parent" % parprop[10:].capitalize()
                    box.prop(rig, propRef(parprop), text=text)
            box.operator("mhx.snap_tongue")

        if "MhaShaftControl" in rig.keys():
            box = self.layout.box()
            box.prop(rig, propRef("MhaShaftControl"), text="Shaft FK/IK")
            if "MhaShaftIk" in rig.keys():
                box.prop(rig, propRef("MhaShaftIk"), text="Shaft IK")
                parprops = [prop for prop in rig.keys() if prop.startswith("MhaShaft_")]
                for parprop in parprops:
                    text = "%s Parent" % parprop[9:].capitalize()
                    box.prop(rig, propRef(parprop), text=text)
            box.operator("mhx.snap_shaft")

        self.layout.operator("mhx.enforce_limits")

#------------------------------------------------------------------------
#    Mhx Animation Panel
#------------------------------------------------------------------------

class MHX_PT_MustardUI_Animation(MainPanel, bpy.types.Panel):
    bl_label = "Animation"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MHX"
    bl_options = {'DEFAULT_CLOSED'}
    bl_parent_id = "PANEL_PT_MustardUI_Armature_External"

    @classmethod
    def poll(cls, context):
        ob = context.object
        return (ob and ob.get("MhxRig", False)) and panel_poll(cls, context)

    def draw(self, context):
        rig = context.object
        scn = context.scene
        if needsMhxUpdate(self.layout, rig):
            return
        self.layout.operator("mhx.remove_unused_fcurves")
        self.layout.operator("mhx.clear_animation")
        self.layout.operator("mhx.constrain_feet")
        self.layout.operator("mhx.enforce_all_limits")
        self.layout.separator()
        self.layout.operator("mhx.limbs_bend_positive")
        self.layout.operator("mhx.shift_animation")
        self.layout.operator("mhx.floor_fk_feet")
        self.layout.separator()
        self.layout.operator("mhx.transfer_to_ik")
        self.layout.operator("mhx.transfer_to_fk")
        self.layout.operator("mhx.transfer_to_links")
        self.layout.operator("mhx.floor_ik_feet")
        self.layout.separator()
        self.layout.operator("mhx.update_mhx_animation")

#-------------------------------------------------------------
#   Initialize
#-------------------------------------------------------------

classes = [
    MHX_PT_MustardUI_Properties,
    MHX_PT_MustardUI_FKIKArmsLegs,
    MHX_PT_MustardUI_FKIKFingers,
    MHX_PT_MustardUI_Animation,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)