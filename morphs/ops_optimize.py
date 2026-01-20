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
            has_key_blocks = True if obj.data.shape_keys.key_blocks else False
            has_animation_data = True if obj.data.shape_keys.animation_data and obj.data.shape_keys.animation_data.drivers else False
            key_block = None
            if has_key_blocks:
                key_block = obj.data.shape_keys.key_blocks

            for section in sections:
                # Collapse Frozen sections to avoid UI clutter
                if enable:
                    section.collapse = True

                for morph in section.morphs:

                    # Skip Diffeomorphic emotion units and correctives
                    if "facs" in morph.path or "jcm" in morph.path or "body_cbs" in morph.path:
                        continue

                    # Shape Keys
                    if has_key_blocks:
                        if morph.path not in key_block:
                            continue
                        if abs(key_block[morph.path].value) < 0.001:
                            set_bool(key_block[morph.path], "mute", enable)

                    # Drivers
                    if has_animation_data:
                        for fcurve in obj.data.shape_keys.animation_data.drivers:
                            if not fcurve.data_path == f'key_blocks["{morph.path}"].value':
                                continue
                            if (has_key_blocks and abs(key_block[morph.path].value) < 0.001) or (not has_key_blocks):
                                set_bool(fcurve, "mute", enable)

        morphs_settings.morphs_optimized = enable

        if enable:
            self.report({'INFO'}, 'MustardUI - Morphs optimized.')
        else:
            self.report({'INFO'}, 'MustardUI - Morphs optimization disabled.')

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_Morphs_Optimize)


def unregister():
    bpy.utils.unregister_class(MustardUI_Morphs_Optimize)
