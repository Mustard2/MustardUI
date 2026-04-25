import json

import bpy

from ..model_selection.active_object import mustardui_active_object
from .get_context import get_preset_context
from .misc import get_unique_preset_name
from .types import get_preset_definition, preset_type_items


def make_json_serializable(value):
    # Handle Blender math types (Vector, Color, Euler, etc.)
    if hasattr(value, "to_tuple"):
        return list(value.to_tuple())

    # Handle generic iterables (but not strings)
    elif hasattr(value, "__iter__") and not isinstance(value, (str, bytes)):
        return [make_json_serializable(v) for v in value]

    # Handle basic types
    elif isinstance(value, (int, float, str, bool)) or value is None:
        return value

    # Fallback (last resort)
    else:
        return str(value)


class MustardUI_PresetCreate(bpy.types.Operator):
    """Create preset"""

    bl_idname = "mustardui.preset_create"
    bl_label = "Create Preset"
    bl_options = {"UNDO"}

    preset_type: bpy.props.EnumProperty(
        items=preset_type_items,
    )

    new_preset_name: bpy.props.StringProperty()

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        return arm is not None and res

    def execute(self, context):

        new_preset_name = self.new_preset_name

        if not new_preset_name.strip():
            self.report({"ERROR"}, "MustardUI - Invalid preset name")
            return {"CANCELLED"}

        res, arm = mustardui_active_object(context, config=0)

        settings, presets, _, _, _ = get_preset_context(arm, self.preset_type)

        definition = get_preset_definition(self.preset_type)

        # Check the poll function
        poll = definition.get("poll")
        if poll is not None:
            error_type, msg = poll(arm, settings)
            if error_type != "":
                self.report({error_type}, f"MustardUI - {msg}")
                return {"CANCELLED"}

        # Find the builder function used to create the json string from data
        builder = definition.get("builder")
        if not builder:
            self.report({"ERROR"}, "MustardUI - No builder function defined")
            return {"CANCELLED"}

        # Resolve settings and object depending on preset type
        if self.preset_type == "MORPHS":
            obj = None
        elif self.preset_type == "PHYSICS":
            obj = settings.items[arm.mustardui_physics_items_uilist_index].object
        else:
            self.report({"ERROR"}, "MustardUI - Invalid preset type")
            return {"CANCELLED"}

        # Build data
        if self.preset_type == "PHYSICS":
            preset_data = builder(obj, new_preset_name)
        else:
            preset_data = builder(settings, arm.MustardUI_RigSettings, new_preset_name)

        if not preset_data:
            self.report({"WARNING"}, "MustardUI - No data to save")
            return {"FINISHED"}

        # Emit warnings if the necessary function is set for the preset type
        warnings = definition.get("warnings")
        if warnings is not None:
            error_type, msg = warnings(obj)
            if error_type != "":
                self.report({error_type}, f"MustardUI - {msg}")
                return {"CANCELLED"}

        # Unique name (shared)
        new_name = get_unique_preset_name(presets, new_preset_name.strip())

        # Create preset
        new_preset = presets.add()
        new_preset.name = new_name

        new_preset.data = json.dumps(
            preset_data, ensure_ascii=False, indent=4, default=make_json_serializable
        )

        # Set some additional preset properties
        preset_set = get_preset_definition(self.preset_type).get("preset_set")
        if preset_set is not None:
            preset_set(obj, new_preset)

        self.report({"INFO"}, f"MustardUI - Preset '{new_preset.name}' created")

        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_PresetCreate)


def unregister():
    bpy.utils.unregister_class(MustardUI_PresetCreate)
