import bpy

from ...model_selection.active_object import *
from ...warnings.ops_fix_old_UI import check_old_UI

# MHX porting guide
#
# - Copy files from the addon
# - Delete 'from .buildnumber import BUILD'
# - Add
# from ....menu import MainPanel
# from ...external.mhx_defs import panel_poll
#
# - Delete MHX_PT_Main
# - Delete MHX_PT_Layers
# - Extract needsMhxUpdate:
#       - needsMhxUpdate(self, rig) -> needsMhxUpdate(layout, rig)
#       - self.layout -> layout
# - Delete remaining MhxPanel
# - Rename the other panels adding MustardUI_ (to avoid issues with double definitions)
# - Add to each other panel
#       bl_parent_id = "PANEL_PT_MustardUI_Armature_External"
# - Add the poll function
# @classmethod
#    def poll(cls, context):
#        ob = context.object
#        return (ob and ob.get("MhxRig", False)) and panel_poll(cls, context)
#
# - Adjust classes at the end for register/unregister


def panel_poll(cls, context):
    if check_old_UI():
        return False

    res, arm = mustardui_active_object(context, config=0)
    if not res:
        return False

    rig_settings = arm.MustardUI_RigSettings
    armature_settings = arm.MustardUI_ArmatureSettings

    if not armature_settings.rig_specific_panel:
        return False

    rig = arm.MustardUI_RigSettings.model_armature_object

    if rig_settings.model_rig_type == "mhx":
        return all(name in rig for name in ("MhaArmIk_L", "MhaArmIk_R"))

    return False
