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
