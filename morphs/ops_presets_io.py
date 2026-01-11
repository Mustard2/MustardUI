import bpy
from ..model_selection.active_object import *
from bpy_extras.io_utils import ExportHelper, ImportHelper
from bpy.props import *
from bpy.utils import register_class
import json
from .. import __package__ as base_package


class MustardUI_Morphs_PresetExport(bpy.types.Operator, ExportHelper):
    """Export Morph Presets to JSON"""
    bl_idname = "mustardui.morphs_preset_export"
    bl_label = "Export Morph Presets"
    bl_options = {'PRESET', 'UNDO'}

    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})

    preset_id: bpy.props.IntProperty(default=-1)

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        return res if arm is not None else False

    # Set a default file name
    def invoke(self, context, event):
        res, arm = mustardui_active_object(context, config=0)

        if res:
            morphs_settings = arm.MustardUI_MorphsSettings
            if morphs_settings.presets:
                preset_name = morphs_settings.presets[0].name
            else:
                preset_name = "Preset"

            model_name = getattr(arm, "name", "Model")
            # Safe filename: replace spaces or invalid characters
            safe_model_name = model_name.replace(" ", "_")
            safe_preset_name = preset_name.replace(" ", "_")
            self.filepath = f"{safe_model_name}_{safe_preset_name}.json"

        return super().invoke(context, event)

    def execute(self, context):
        res, arm = mustardui_active_object(context, config=0)
        morphs_settings = arm.MustardUI_MorphsSettings

        if len(morphs_settings.presets) < 1 or self.preset_id < 0:
            self.report({'WARNING'}, "No morph presets to export.")
            return {'FINISHED'}

        presets = morphs_settings.presets
        preset = presets[self.preset_id]

        data = []
        preset_data = {"name": preset.name, "morphs": []}
        for morph in preset.morphs:
            preset_data["morphs"].append({
                "name": morph.name,
                "path": morph.path,
                "shape_key": morph.shape_key,
                "custom_property": morph.custom_property,
                "custom_property_source": morph.custom_property_source,
                "value": morph.value
            })
        data.append(preset_data)

        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        self.report({'INFO'}, f"Morph presets exported: {len(morphs_settings.presets)} presets.")

        return {'FINISHED'}

    def draw(self, context):
        pass


class MustardUI_Morphs_PresetImport(bpy.types.Operator, ImportHelper):
    """Import Morph Presets from JSON"""
    bl_idname = "mustardui.morphs_preset_import"
    bl_label = "Import Morph Presets"
    bl_options = {'PRESET', 'UNDO'}

    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        return res

    def execute(self, context):
        res, arm = mustardui_active_object(context, config=0)
        morphs_settings = arm.MustardUI_MorphsSettings

        presets = morphs_settings.presets
        preset_names = [x.name for x in presets]

        n_import = 0
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                presets_data = json.load(f)
                for preset_json in presets_data:
                    preset = morphs_settings.presets.add()

                    # Assign a unique name
                    imported_name = preset_json.get("name", f"Preset_{n_import}")
                    unique_name = imported_name
                    counter = 1
                    while unique_name in preset_names:
                        unique_name = f"{imported_name}_{counter}"
                        counter += 1
                    preset.name = unique_name

                    for morph_json in preset_json.get("morphs", []):
                        morph = preset.morphs.add()
                        morph.name = morph_json.get("name", "")
                        morph.path = morph_json.get("path", "")
                        morph.shape_key = morph_json.get("shape_key", False)
                        morph.custom_property = morph_json.get("custom_property", True)
                        morph.custom_property_source = morph_json.get("custom_property_source", "ARMATURE_OBJ")
                        morph.value = morph_json.get("value", 0.0)
                    n_import += 1

        except Exception as e:
            self.report({'ERROR'}, f"Failed to import morph presets: {e}")
            return {'CANCELLED'}

        arm.update_tag()

        self.report({'INFO'}, f"Preset imported.")

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_Morphs_PresetExport)
    bpy.utils.register_class(MustardUI_Morphs_PresetImport)


def unregister():
    bpy.utils.unregister_class(MustardUI_Morphs_PresetImport)
    bpy.utils.unregister_class(MustardUI_Morphs_PresetExport)
