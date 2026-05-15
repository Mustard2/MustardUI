import bpy

from ..model_selection.active_object import mustardui_active_object
from .misc import get_cp_source


class MustardUI_DazMorphs_DefaultValues(bpy.types.Operator):
    """Set the value of all morphs to the default value"""

    bl_idname = "mustardui.morphs_defaultvalues"
    bl_label = "Restore Default Values"
    bl_options = {"UNDO"}

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
                if cp_source and morph.custom_property and morph.path in cp_source:
                    val = cp_source.get(morph.path)
                    if val is None:
                        continue

                    if isinstance(val, float):
                        cp_source[morph.path] = 0.0
                    if isinstance(val, int):
                        cp_source[morph.path] = 0
                    elif isinstance(val, bool):
                        cp_source[morph.path] = True
                elif morph.shape_key:
                    kb = rig_settings.data.shape_keys.key_blocks.get(morph.path)
                    if kb is not None:
                        kb.value = 0.0

        # Check if a preset is default
        preset_default = -1
        preset_name = ""
        for i, preset in enumerate(morphs_settings.presets):
            if preset.default:
                preset_default = i
                preset_name = preset.name
                break
        # Apply the preset
        if preset_default > -1:
            # Override the selected preset
            arm.mustardui_morphs_preset_uilist_index = preset_default
            # Set the preset
            bpy.ops.mustardui.preset_apply(
                preset_type="MORPHS", force_modifiers_creation=False
            )

        # Update everything
        if arm:
            arm.update_tag()
        if rig_settings.model_armature_object:
            rig_settings.model_armature_object.update_tag()
        if rig_settings.model_body:
            rig_settings.model_body.update_tag()
            if rig_settings.model_body.data:
                rig_settings.model_body.data.update_tag()
                rig_settings.model_body.data.update()
        bpy.context.view_layer.update()

        if preset_default < 0:
            self.report({"INFO"}, "MustardUI - Morphs values restored to default.")
        else:
            self.report(
                {"INFO"},
                f"MustardUI - Morphs values restored to preset '{preset_name}'.",
            )

        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_DazMorphs_DefaultValues)


def unregister():
    bpy.utils.unregister_class(MustardUI_DazMorphs_DefaultValues)
