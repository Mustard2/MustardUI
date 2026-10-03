import bpy
from helpers import BlenderTestCase, build_model, configure_model


class TestMorphs(BlenderTestCase):
    def setUp(self):
        super().setUp()
        self.model = build_model()
        configure_model(self.model)
        self.arm = self.model["armature"].data
        self.shape_keys = self.model["body"].data.shape_keys

        # Back to configuration mode, with a generic Blink section
        bpy.ops.mustardui.configuration()
        self.morphs_settings = self.arm.MustardUI_MorphsSettings
        self.morphs_settings.enable_ui = True
        self.morphs_settings.type = "GENERIC"
        bpy.ops.mustardui.morphs_section_add()
        section = self.morphs_settings.sections[0]
        section.name = "Eyes"
        section.string = "Blink"
        section.shape_keys = True
        section.custom_properties = False

    def morph_paths(self):
        return {m.path for m in self.morphs_settings.sections[0].morphs}

    # Check Morphs adds matching shape keys once
    def test_check_shape_keys(self):
        bpy.ops.mustardui.morphs_check()
        self.assertEqual(self.morph_paths(), {"Blink", "Blink.L", "Blink.R"})

        # Running the check again does not duplicate the morphs
        bpy.ops.mustardui.morphs_check()
        self.assertEqual(len(self.morphs_settings.sections[0].morphs), 3)

    # Check Morphs adds matching armature custom properties
    def test_check_custom_properties(self):
        self.model["armature"]["Blink Strength"] = 0.0
        section = self.morphs_settings.sections[0]
        section.custom_properties = True
        section.custom_properties_source = "ARMATURE_OBJ"
        bpy.ops.mustardui.morphs_check()
        self.assertIn("Blink Strength", self.morph_paths())

    # Empty entries match nothing, while spaces are part of the search strings
    def test_check_search_strings(self):
        section = self.morphs_settings.sections[0]
        for string, expected in (
            ("", set()),
            ("Blink,", {"Blink", "Blink.L", "Blink.R"}),
            ("Smile,,Blink.L", {"Smile", "Blink.L"}),
            ("Smile, Blink", {"Smile"}),
        ):
            with self.subTest(string):
                section.string = string
                section.morphs.clear()
                bpy.ops.mustardui.morphs_check()
                self.assertEqual(self.morph_paths(), expected)

    # Restore Default Values resets the morphs
    def test_default_values(self):
        bpy.ops.mustardui.morphs_check()
        bpy.ops.mustardui.configuration()
        self.shape_keys.key_blocks["Blink.L"].value = 0.7
        bpy.ops.mustardui.morphs_defaultvalues()
        self.assertEqual(self.shape_keys.key_blocks["Blink.L"].value, 0.0)
