import json

import bpy

from ..model_selection.active_object import mustardui_active_object
from .get_context import get_preset_context
from .misc import check_preset_type
from .types import get_preset_definition, preset_type_items


class MustardUI_PresetApply(bpy.types.Operator):
    """Apply preset"""

    bl_idname = "mustardui.preset_apply"
    bl_label = "Apply Preset"
    bl_options = {"UNDO"}

    preset_type: bpy.props.EnumProperty(items=preset_type_items)

    force_modifiers_creation: bpy.props.BoolProperty(default=False)

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        return res and arm is not None

    def execute(self, context):
        res, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings

        settings, presets, preset, index, index_prop = get_preset_context(
            arm, self.preset_type
        )

        if not preset:
            self.report({"ERROR"}, "MustardUI - Select a valid Preset")
            return {"CANCELLED"}

        definition = get_preset_definition(self.preset_type)

        # Load the data inside the preset in Json format
        try:
            data = json.loads(preset.data)
        except Exception:
            self.report({"ERROR"}, "MustardUI - Preset data not valid")
            return {"CANCELLED"}

        # Check the preset type
        err, msg = check_preset_type(self.preset_type, data, definition.get("name"))
        if err != "":
            self.report({err}, msg)
            return {"CANCELLED"}

        # Check the poll function
        poll = definition.get("poll")
        if poll is not None:
            error_type, msg = poll(arm, settings, type="APPLY")
            if error_type != "":
                self.report({error_type}, f"MustardUI - {msg}")
                return {"CANCELLED"}

        applier = definition.get("applier")

        if not applier:
            self.report({"ERROR"}, "MustardUI - No applier function defined")
            return {"CANCELLED"}

        errors = applier(
            context=context,
            arm=arm,
            settings=settings,
            data=data,
            force=self.force_modifiers_creation,
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

        if errors == 0:
            self.report({"INFO"}, f"MustardUI - {preset.name} applied")
        else:
            self.report(
                {"WARNING"}, f"MustardUI - {preset.name} applied with {errors} issues"
            )

        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_PresetApply)


def unregister():
    bpy.utils.unregister_class(MustardUI_PresetApply)
