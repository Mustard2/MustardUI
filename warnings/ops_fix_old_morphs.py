import bpy
from bpy.props import *
from ..model_selection.active_object import *


class MustardUI_Warnings_FixOldMorphs(bpy.types.Operator):
    """Update the Morphs to the latest version"""
    bl_idname = "mustardui.warnings_fix_old_morphs"
    bl_label = "Update Morphs"
    bl_options = {'UNDO'}

    ignore: bpy.props.BoolProperty(default=False)

    @classmethod
    def poll(cls, context):
        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings

        return (poll and rig_settings.diffeomorphic_support and rig_settings.diffeomorphic_morphs_number > 0) \
            if obj is not None else False

    def execute(self, context):
        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings
        morphs_settings = obj.MustardUI_MorphsSettings

        if self.ignore:
            rig_settings.diffeomorphic_support = False
            return {'FINISHED'}

        try:
            morphs_settings.type = "DIFFEO_GENESIS_8"
            morphs_settings.enable_ui = True

            # Retrieve settings from the old Morphs implementation
            morphs_settings.diffeomorphic_emotions = rig_settings.diffeomorphic_emotions
            morphs_settings.diffeomorphic_emotions_custom = rig_settings.diffeomorphic_emotions_custom
            morphs_settings.diffeomorphic_facs_emotions = rig_settings.diffeomorphic_facs_emotions
            morphs_settings.diffeomorphic_emotions_units = rig_settings.diffeomorphic_emotions_units
            morphs_settings.diffeomorphic_facs_emotions_units = rig_settings.diffeomorphic_facs_emotions_units
            morphs_settings.diffeomorphic_body_morphs = rig_settings.diffeomorphic_body_morphs
            morphs_settings.diffeomorphic_body_morphs_custom = rig_settings.diffeomorphic_body_morphs_custom

            # To use the morphs_check operator we need to be in Configuration mode
            bpy.ops.mustardui.configuration()
            bpy.ops.mustardui.morphs_check()

            # Switch back to normal mode
            bpy.ops.mustardui.configuration()

            # Flag the error as solved
            rig_settings.diffeomorphic_support = False
        except:
            # Disable the Morphs panel if an error occurs
            morphs_settings.enable_ui = False

            # Switch out of configuration mode if needed
            if not obj.MustardUI_enable:
                bpy.ops.mustardui.configuration()

            self.report({'ERROR'}, 'MustardUI - An error occurred while updating the model.')
            return {'FINISHED'}

        self.report({'INFO'}, 'MustardUI - Morphs udpated.')
        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_Warnings_FixOldMorphs)


def unregister():
    bpy.utils.unregister_class(MustardUI_Warnings_FixOldMorphs)
