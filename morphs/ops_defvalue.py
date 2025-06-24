import bpy
from ..model_selection.active_object import *
from .misc import get_cp_source


class MustardUI_DazMorphs_DefaultValues(bpy.types.Operator):
    """Set the value of all morphs to the default value"""
    bl_idname = "mustardui.morphs_defaultvalues"
    bl_label = "Restore Default Values"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        morphs_settings = arm.MustardUI_MorphsSettings
        return res and morphs_settings.enable_ui

    def execute(self, context):
        res, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings
        morphs_settings = arm.MustardUI_MorphsSettings

        for section in morphs_settings.sections:
            for morph in section.morphs:
                cp_source = get_cp_source(morph.custom_property_source, rig_settings)
                if cp_source and morph.custom_property and hasattr(cp_source,
                                                          f'["{bpy.utils.escape_identifier(morph.path)}"]'):
                    val = cp_source[morph.path]
                    if isinstance(val, float):
                        cp_source[morph.path] = 0.
                    elif isinstance(val, bool):
                        cp_source[morph.path] = True
                elif morph.shape_key:
                    rig_settings.data.shape_keys.key_blocks[morph.path].value = 0.

        if arm:
            arm.update_tag()
        if rig_settings.model_armature_object:
            rig_settings.model_armature_object.update_tag()
        if rig_settings.model_body:
            rig_settings.model_body.update_tag()
            if rig_settings.model_body.data:
                rig_settings.model_body.data.update_tag()

        bpy.context.view_layer.update()

        self.report({'INFO'}, 'MustardUI - Morphs values restored to default.')

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_DazMorphs_DefaultValues)


def unregister():
    bpy.utils.unregister_class(MustardUI_DazMorphs_DefaultValues)