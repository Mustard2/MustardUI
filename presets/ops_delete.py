import bpy

from ..model_selection.active_object import mustardui_active_object
from .get_context import mustardui_get_preset_context
from .types import mustardui_preset_type_items


class MustardUI_PresetDelete(bpy.types.Operator):
    """Delete preset"""

    bl_idname = "mustardui.preset_delete"
    bl_label = "Delete Preset"
    bl_options = {"UNDO"}

    preset_type: bpy.props.EnumProperty(
        items=mustardui_preset_type_items,
    )

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        return res if arm is not None else False

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=0)

        try:
            settings, presets, preset, index, index_prop = mustardui_get_preset_context(
                arm, self.preset_type
            )
        except ValueError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}

        if preset is None:
            return {"FINISHED"}

        preset_name = preset.name

        presets.remove(index)

        new_index = min(max(0, index - 1), len(presets) - 1)
        setattr(arm, index_prop, new_index)

        self.report({"INFO"}, f"MustardUI - Preset '{preset_name}' deleted")

        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_PresetDelete)


def unregister():
    bpy.utils.unregister_class(MustardUI_PresetDelete)
