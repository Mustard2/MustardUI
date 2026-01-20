import bpy
from bpy.props import *
from ..model_selection.active_object import *
from ..misc.set_bool import set_bool


class MustardUI_Morphs_Optimize(bpy.types.Operator):
    """Enable/disable morph optimization"""
    bl_idname = "mustardui.morphs_optimize"
    bl_label = "Morph Optimize"

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        morphs_settings = arm.MustardUI_MorphsSettings
        return res and morphs_settings.enable_ui

    def execute(self, context):
        poll, arm = mustardui_active_object(context, config=0)
        morphs_settings = arm.MustardUI_MorphsSettings
        rig_settings = arm.MustardUI_RigSettings

        obj = rig_settings.model_body
        enable = not morphs_settings.morphs_optimized
        sections = [x for x in morphs_settings.sections if x.freezable]

        # Body: Shape Keys and their drivers
        if obj is not None and obj.data and obj.data.shape_keys:

            if obj.data.shape_keys.key_blocks:
                key_block = obj.data.shape_keys.key_blocks
                for section in sections:
                    if enable:
                        section.collapse = True

                    for morph in section.morphs:
                        if (morph.path not in key_block or
                                "facs" in morph.path or
                                "jcm" in morph.path or
                                "body_cbs" in morph.path):
                            continue
                        if abs(key_block[morph.path].value) < 0.001:
                            set_bool(key_block[morph.path], "mute", enable)

            if obj.data.shape_keys.animation_data and obj.data.shape_keys.animation_data.drivers:
                for section in sections:
                    for morph in section.morphs:
                        for fcurve in obj.data.shape_keys.animation_data.drivers:
                            if (not fcurve.data_path == f'key_blocks["{morph.path}"].value' or
                                    "facs" in morph.path or
                                    "jcm" in morph.path or
                                    "body_cbs" in morph.path):
                                continue
                            set_bool(fcurve, "mute", enable)

        morphs_settings.morphs_optimized = enable

        self.report({'INFO'}, 'MustardUI - Morphs optimized.')

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_Morphs_Optimize)


def unregister():
    bpy.utils.unregister_class(MustardUI_Morphs_Optimize)
