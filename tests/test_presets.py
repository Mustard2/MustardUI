import json
import os
import tempfile

import bpy
from helpers import BlenderTestCase, build_model, configure_model, setup_generic_morphs


class TestMorphPresets(BlenderTestCase):
    def setUp(self):
        super().setUp()
        self.model = build_model()
        configure_model(self.model)
        self.morphs_settings = setup_generic_morphs(self.model)
        self.keys = self.model["body"].data.shape_keys.key_blocks

    # Morphs from array or text custom properties are not stored in the preset
    def test_create_with_non_numeric_morphs(self):
        arm = self.model["armature"]
        arm["Blink Color"] = [1.0, 0.0, 0.0]
        arm["Blink Label"] = "text"
        bpy.ops.mustardui.configuration()
        section = self.morphs_settings.sections[0]
        section.custom_properties = True
        section.custom_properties_source = "ARMATURE_OBJ"
        bpy.ops.mustardui.morphs_check()
        bpy.ops.mustardui.configuration()

        self.keys["Blink.L"].value = 1.0
        bpy.ops.mustardui.preset_create(preset_type="MORPHS", new_preset_name="Wink")
        data = json.loads(self.morphs_settings.presets[0].data)
        self.assertEqual([m["path"] for m in data["morphs"]], ["Blink.L"])

    # Morph preset stores and restores the morph values
    def test_create_and_apply(self):
        self.keys["Blink.L"].value = 1.0
        bpy.ops.mustardui.preset_create(preset_type="MORPHS", new_preset_name="Wink")
        self.assertEqual([p.name for p in self.morphs_settings.presets], ["Wink"])

        bpy.ops.mustardui.morphs_defaultvalues()
        self.assertEqual(self.keys["Blink.L"].value, 0.0)

        bpy.ops.mustardui.preset_apply(preset_type="MORPHS")
        self.assertAlmostEqual(self.keys["Blink.L"].value, 1.0)
        self.assertAlmostEqual(self.keys["Blink.R"].value, 0.0)

    # Morph preset survives export, delete and import
    def test_export_import(self):
        self.keys["Blink.R"].value = 0.5
        bpy.ops.mustardui.preset_create(preset_type="MORPHS", new_preset_name="Half")
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "preset.json")
            bpy.ops.mustardui.preset_export(preset_type="MORPHS", filepath=path)
            self.assertTrue(os.path.isfile(path))

            bpy.ops.mustardui.preset_delete(preset_type="MORPHS")
            self.assertEqual(len(self.morphs_settings.presets), 0)

            bpy.ops.mustardui.preset_import(preset_type="MORPHS", filepath=path)
        self.assertEqual([p.name for p in self.morphs_settings.presets], ["Half"])

        self.keys["Blink.R"].value = 0.0
        bpy.ops.mustardui.preset_apply(preset_type="MORPHS")
        self.assertAlmostEqual(self.keys["Blink.R"].value, 0.5)

    # A file with several presets imports all of them, or none if one is not valid
    def test_import_several(self):
        bpy.ops.mustardui.preset_create(preset_type="MORPHS", new_preset_name="One")
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "preset.json")
            bpy.ops.mustardui.preset_export(preset_type="MORPHS", filepath=path)
            with open(path) as f:
                preset = json.load(f)
            bpy.ops.mustardui.preset_delete(preset_type="MORPHS")

            with open(path, "w") as f:
                json.dump([preset, dict(preset, name="Two")], f)
            bpy.ops.mustardui.preset_import(preset_type="MORPHS", filepath=path)
            self.assertEqual([p.name for p in self.morphs_settings.presets], ["One", "Two"])

            with open(path, "w") as f:
                json.dump([dict(preset, name="Three"), dict(preset, type="PHYSICS")], f)
            with self.assertRaises(RuntimeError):
                bpy.ops.mustardui.preset_import(preset_type="MORPHS", filepath=path)
            self.assertEqual([p.name for p in self.morphs_settings.presets], ["One", "Two"])
