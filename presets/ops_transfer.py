import bpy

from ..model_selection.active_object import (
    active_object_operator_poll,
    mustardui_active_object,
)
from .get_context import get_preset_context
from .types import preset_type_items


def mustardui_get_characters(self, context):
    res, arm = mustardui_active_object(context, config=0)

    items = []

    if arm is None:
        return items

    for obj in [x for x in context.scene.objects if x.type == "ARMATURE"]:
        try:
            # Check if object is a valid MustardUI armature
            if (
                hasattr(obj.data, "MustardUI_created")
                and obj.data.MustardUI_created
                and obj.data != arm
            ):
                items.append((obj.name, obj.data.MustardUI_RigSettings.model_name, ""))
        except Exception:
            pass

    return items


class MustardUI_PresetTransfer(bpy.types.Operator):
    """Transfer the preset to another character in the scene"""

    bl_idname = "mustardui.preset_transfer"
    bl_label = "Transfer Preset"
    bl_options = {"UNDO"}

    target_character: bpy.props.EnumProperty(
        name="Target Character",
        description="Select the character to receive the preset",
        items=mustardui_get_characters,
    )

    preset_type: bpy.props.EnumProperty(
        items=preset_type_items,
    )

    @classmethod
    def poll(cls, context):
        return (
            active_object_operator_poll(context, config=0)
            and len(mustardui_get_characters(None, context)) > 0
        )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.layout.prop(self, "target_character")

    def execute(self, context):
        res, source_arm = mustardui_active_object(context, config=0)

        target_obj = context.scene.objects.get(self.target_character)
        if not target_obj or not target_obj.data:
            self.report({"ERROR"}, "MustardUI - Target character not found")
            return {"CANCELLED"}

        target_arm = target_obj.data

        try:
            _, _, src_preset, _, _ = get_preset_context(source_arm, self.preset_type)
        except ValueError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}

        if src_preset is None:
            self.report({"ERROR"}, "MustardUI - Invalid preset index")
            return {"CANCELLED"}

        # Morphs
        if self.preset_type == "MORPHS":
            trg_settings = target_arm.MustardUI_MorphsSettings

            new_preset = trg_settings.presets.add()
            new_preset.name = src_preset.name

            new_preset.data = src_preset.data

        # Physics
        elif self.preset_type == "PHYSICS":
            if not hasattr(target_arm, "MustardUI_PhysicsSettings"):
                self.report({"ERROR"}, "MustardUI - Physics settings not found")
                return {"CANCELLED"}

            trg_settings = target_arm.MustardUI_PhysicsSettings

            new_preset = trg_settings.presets.add()
            new_preset.name = src_preset.name

            new_preset.data = src_preset.data
            new_preset.has_cloth = src_preset.has_cloth
            new_preset.has_soft_body = src_preset.has_soft_body
            new_preset.has_collision = src_preset.has_collision

        target_name = target_arm.MustardUI_RigSettings.model_name
        self.report(
            {"INFO"},
            f"MustardUI - Preset '{src_preset.name}' transferred to {target_name}",
        )

        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_PresetTransfer)


def unregister():
    bpy.utils.unregister_class(MustardUI_PresetTransfer)
