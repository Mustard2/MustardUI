import bpy
from mathutils import Vector
from ..model_selection.active_object import *
from bpy_extras.io_utils import ExportHelper, ImportHelper
from bpy.props import *
import json


class MustardUI_Physics_PresetExport(bpy.types.Operator, ExportHelper):
    """Export Physics Preset JSON from internal data to a file"""
    bl_idname = "mustardui.physics_preset_export"
    bl_label = "Export Physics Preset"
    bl_options = {'PRESET', 'UNDO'}

    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})
    preset_id: IntProperty(default=-1)

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        if not res or arm is None:
            return False
        physics_settings = arm.MustardUI_PhysicsSettings
        if arm.mustardui_physics_items_uilist_index < 0 or len(physics_settings.items) < 1:
            return False
        obj = physics_settings.items[arm.mustardui_physics_items_uilist_index].object
        return obj and obj.type == "MESH"

    def invoke(self, context, event):
        res, arm = mustardui_active_object(context, config=0)

        if res:
            physics_settings = arm.MustardUI_PhysicsSettings
            preset_name = physics_settings.presets[0].name if physics_settings.presets else "Preset"
            model_name = getattr(arm, "name", "Model")
            safe_model_name = model_name.replace(" ", "_")
            safe_preset_name = preset_name.replace(" ", "_")
            self.filepath = f"MustardUI_PhysicsPreset_{safe_model_name}_{safe_preset_name}.json"
        return super().invoke(context, event)

    def execute(self, context):
        res, arm = mustardui_active_object(context, config=0)
        physics_settings = arm.MustardUI_PhysicsSettings

        if len(physics_settings.presets) < 1 or self.preset_id < 0:
            self.report({'WARNING'}, "No presets to export.")
            return {'FINISHED'}

        preset = physics_settings.presets[self.preset_id]

        if not preset.data:
            self.report({'WARNING'}, f"Preset '{preset.name}' has no internal data.")
            return {'FINISHED'}

        try:
            # Load preset.data (string) into Python object
            preset_json = json.loads(preset.data)

            # Write proper JSON to file
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(preset_json, f, ensure_ascii=False, indent=4)

        except Exception as e:
            self.report({'ERROR'}, f"Failed to export preset: {e}")
            return {'CANCELLED'}

        self.report({'INFO'}, f"Preset '{preset.name}' exported to '{self.filepath}'")
        return {'FINISHED'}


class MustardUI_Physics_PresetImport(bpy.types.Operator, ImportHelper):
    """Import Physics Presets from JSON file"""
    bl_idname = "mustardui.physics_preset_import"
    bl_label = "Import Physics Presets"
    bl_options = {'PRESET', 'UNDO'}

    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        return res

    def execute(self, context):
        res, arm = mustardui_active_object(context, config=0)
        if not res or not arm:
            self.report({'ERROR'}, "No active MustardUI rig found.")
            return {'CANCELLED'}

        physics_settings = arm.MustardUI_PhysicsSettings
        presets = physics_settings.presets
        preset_names = [p.name for p in presets]

        n_import = 0
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                presets_data = json.load(f)
                if isinstance(presets_data, dict):
                    presets_data = [presets_data]

                for preset_json in presets_data:
                    preset = physics_settings.presets.add()

                    # Assign a unique name
                    imported_name = preset_json.get("name", f"Preset_{n_import}")
                    unique_name = imported_name
                    counter = 1
                    while unique_name in preset_names:
                        unique_name = f"{imported_name}_{counter}"
                        counter += 1
                    preset.name = unique_name
                    preset_names.append(unique_name)

                    # Store JSON string internally
                    preset.data = json.dumps(preset_json, ensure_ascii=False, indent=4)

                    # Populate flags based on keys
                    preset.has_cloth = "cloth" in preset_json and bool(preset_json["cloth"])
                    preset.has_soft_body = "soft_body" in preset_json and bool(preset_json["soft_body"])
                    preset.has_collision = "object_collision" in preset_json and bool(preset_json["object_collision"])

                    n_import += 1

        except Exception as e:
            self.report({'ERROR'}, f"Failed to import physics presets: {e}")
            return {'CANCELLED'}

        arm.update_tag()
        self.report({'INFO'}, f"{n_import} physics preset(s) imported from file.")
        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_Physics_PresetExport)
    bpy.utils.register_class(MustardUI_Physics_PresetImport)


def unregister():
    bpy.utils.unregister_class(MustardUI_Physics_PresetImport)
    bpy.utils.unregister_class(MustardUI_Physics_PresetExport)
