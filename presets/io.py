import json

import bpy
from bpy_extras.io_utils import ExportHelper, ImportHelper

from ..model_selection.active_object import mustardui_active_object
from .get_context import get_preset_context
from .misc import check_preset_type, check_preset_version, get_unique_preset_name
from .types import get_preset_definition, preset_type_items


def build_preset_filename(preset_type, arm, preset_name):
    definition = get_preset_definition(preset_type)

    model_name = getattr(arm, "name", "Model")

    return f"{definition['file_prefix']}_{model_name}_{preset_name}.json"


class MustardUI_PresetExport(bpy.types.Operator, ExportHelper):
    """Export Preset"""

    bl_idname = "mustardui.preset_export"
    bl_label = "Export Preset"
    bl_options = {"PRESET", "UNDO"}

    preset_type: bpy.props.EnumProperty(items=preset_type_items, options={"HIDDEN"})

    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(default="*.json", options={"HIDDEN"})

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        return res and arm is not None

    def invoke(self, context, event):
        res, arm = mustardui_active_object(context, config=0)

        settings, presets, preset, index, _ = get_preset_context(arm, self.preset_type)

        if not preset:
            self.report({"WARNING"}, "MustardUI - Select a Preset")
            return {"CANCELLED"}

        self.filepath = build_preset_filename(
            self.preset_type,
            arm,
            preset.name,
        )

        return super().invoke(context, event)

    def execute(self, context):
        res, arm = mustardui_active_object(context, config=0)

        _, _, preset, _, _ = get_preset_context(arm, self.preset_type)

        if not preset or not preset.data:
            self.report({"WARNING"}, "MustardUI - No preset data")
            return {"CANCELLED"}

        try:
            data = json.loads(preset.data)

            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

        except Exception as e:
            self.report({"ERROR"}, f"MustardUI - Export failed: {e}")
            return {"CANCELLED"}

        self.report({"INFO"}, f"MustardUI - {preset.name} exported")
        return {"FINISHED"}


class MustardUI_PresetImport(bpy.types.Operator, ImportHelper):
    """Import Preset"""

    bl_idname = "mustardui.preset_import"
    bl_label = "Import Preset"
    bl_options = {"PRESET", "UNDO"}

    preset_type: bpy.props.EnumProperty(items=preset_type_items, options={"HIDDEN"})

    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(default="*.json", options={"HIDDEN"})

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        return res and arm is not None

    def execute(self, context):
        res, arm = mustardui_active_object(context, config=0)

        _, presets, _, _, _ = get_preset_context(arm, self.preset_type)

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Check the preset version
            if not check_preset_version(data):
                self.report(
                    {"ERROR"},
                    "MustardUI - This Preset is not compatible with this MustardUI version",
                )
                return {"CANCELLED"}

            # Check the preset type
            definition = get_preset_definition(self.preset_type)
            err, msg = check_preset_type(self.preset_type, data, definition.get("name"))
            if err != "":
                self.report({err}, msg)
                return {"CANCELLED"}

            if isinstance(data, dict):
                data = [data]

            for i, preset_json in enumerate(data):
                new_name = get_unique_preset_name(presets, preset_json.get("name", f"Preset_{i}"))

                new_preset = presets.add()
                new_preset.name = new_name
                new_preset.data = json.dumps(preset_json, ensure_ascii=False, indent=4)

                # Post-import function
                post_import = definition.get("post_import_set")
                if post_import is not None:
                    post_import(new_preset, preset_json)

        except Exception as e:
            self.report({"ERROR"}, f"MustardUI - Import failed: {e}")
            return {"CANCELLED"}

        arm.update_tag()

        self.report({"INFO"}, "MustardUI - Preset(s) imported")
        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_PresetExport)
    bpy.utils.register_class(MustardUI_PresetImport)


def unregister():
    bpy.utils.unregister_class(MustardUI_PresetImport)
    bpy.utils.unregister_class(MustardUI_PresetExport)
