from ...model_selection.active_object import ModelMode, mustardui_active_object

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
#    @classmethod
#    def poll(cls, context):
#        return panel_poll_mhx(cls, context)
#
# - Adjust classes at the end for register/unregister
# - Change the names of the operators substituting MHX_OT with MHX_OT_MustardUI_
# - Change the bl_idname of the operators substituting mhx. with mhx.mustardui_


def panel_poll(cls, context):
    res, arm = mustardui_active_object(context, config=ModelMode.USER)
    if not res or arm is None:
        return False

    rig_settings = arm.MustardUI_RigSettings
    armature_settings = arm.MustardUI_ArmatureSettings

    if not armature_settings.rig_specific_panel:
        return False

    rig = arm.MustardUI_RigSettings.model_armature_object

    if rig_settings.model_rig_type == "mhx":
        return rig.get("MhxRig", False)

    return False


def panel_poll_mhx(cls, context):
    poll = panel_poll(cls, context)

    res, arm = mustardui_active_object(context, config=ModelMode.USER)
    if not res or arm is None:
        return False

    ob = context.object
    return poll and ob.data == arm
