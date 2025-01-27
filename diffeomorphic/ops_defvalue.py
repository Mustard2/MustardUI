import bpy
from ..model_selection.active_object import *


class MustardUI_DazMorphs_DefaultValues(bpy.types.Operator):
    """Set the value of all morphs to the default value"""
    bl_idname = "mustardui.dazmorphs_defaultvalues"
    bl_label = "Restore Default Values"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings
        return res and rig_settings.diffeomorphic_support

    def execute(self, context):
        res, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings

        for morph in rig_settings.diffeomorphic_morphs_list:
            rig_settings.model_armature_object[morph.path] = 0.

        arm.update_tag()
        rig_settings.model_armature_object.update_tag()

        self.report({'INFO'}, 'MustardUI - Morphs values restored to default.')

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_DazMorphs_DefaultValues)


def unregister():
    bpy.utils.unregister_class(MustardUI_DazMorphs_DefaultValues)