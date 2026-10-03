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


def add_driver(owner, path, inputs, mute=False):
    """Driver summing the given (id, data_path) properties, plus optional bone rotation inputs."""
    fcurve = owner.driver_add(path)
    driver = fcurve.driver
    driver.type = "SUM"
    for target_id, data_path in inputs:
        var = driver.variables.new()
        if data_path is None:
            var.type = "TRANSFORMS"
            var.targets[0].id = target_id
            var.targets[0].bone_target = "head"
            var.targets[0].transform_type = "ROT_X"
        else:
            var.targets[0].id_type = target_id.id_type
            var.targets[0].id = target_id
            var.targets[0].data_path = data_path
    fcurve.mute = mute
    return fcurve


class TestDisableMorphs(BlenderTestCase):
    def setUp(self):
        super().setUp()
        self.model = build_model()
        configure_model(self.model)
        self.rig = self.model["armature"]
        self.arm = self.rig.data
        self.body = self.model["body"]
        self.key_blocks = self.body.data.shape_keys.key_blocks
        self.shirt = bpy.data.objects["Casual - Shirt"]
        self.shirt.shape_key_add(name="Basis")
        self.shirt.shape_key_add(name="Wide")

        # Wide drives the shape keys through a chain of drivers, as Diffeomorphic does
        self.rig["Wide"] = 0.0
        self.rig["Unrelated"] = 0.0
        self.arm["Wide(fin)"] = 0.0
        self.fin = add_driver(self.arm, '["Wide(fin)"]', [(self.rig, '["Wide"]')])
        self.smile = add_driver(self.key_blocks["Smile"], "value", [(self.arm, '["Wide(fin)"]')])
        self.wide = add_driver(
            self.shirt.data.shape_keys.key_blocks["Wide"], "value", [(self.rig, '["Wide"]')]
        )

        bpy.ops.mustardui.configuration()
        self.morphs_settings = self.arm.MustardUI_MorphsSettings
        self.morphs_settings.enable_ui = True
        self.morphs_settings.type = "GENERIC"
        for name, string, shape_keys in (("Eyes", "Blink", True), ("Body", "Wide", False)):
            bpy.ops.mustardui.morphs_section_add()
            section = self.morphs_settings.sections[-1]
            section.name = name
            section.string = string
            section.shape_keys = shape_keys
            section.custom_properties = not shape_keys
        bpy.ops.mustardui.morphs_check()
        bpy.ops.mustardui.configuration()

    def mutes(self):
        return {
            "fin": self.fin.mute,
            "smile_driver": self.smile.mute,
            "wide_driver": self.wide.mute,
            "wide": self.shirt.data.shape_keys.key_blocks["Wide"].mute,
            **{name: kb.mute for name, kb in self.key_blocks.items()},
        }

    def assert_muted(self, *names):
        mutes = self.mutes()
        self.assertEqual({x for x, mute in mutes.items() if mute}, set(names))

    # Shape key morphs and the drivers depending only on custom property morphs are muted
    def test_disable_all(self):
        initial = self.mutes()
        self.morphs_settings.diffeomorphic_enable = False
        self.assert_muted(
            "Blink", "Blink.L", "Blink.R", "fin", "smile_driver", "Smile", "wide_driver", "wide"
        )
        self.morphs_settings.diffeomorphic_enable = True
        self.assertEqual(self.mutes(), initial)

    # Muted drivers keep their value, so the model keeps its shape
    def test_disable_unused(self):
        self.rig["Wide"] = 0.5
        self.rig.update_tag()
        self.key_blocks["Blink.L"].value = 0.3
        bpy.context.evaluated_depsgraph_get().update()
        self.morphs_settings.mute_shape_keys = "UNUSED"
        self.morphs_settings.diffeomorphic_enable = False
        self.assert_muted("Blink", "Blink.R", "fin", "smile_driver", "wide_driver")

        self.rig["Wide"] = 1.0
        self.rig.update_tag()
        bpy.context.evaluated_depsgraph_get().update()
        self.assertAlmostEqual(self.key_blocks["Smile"].value, 0.5, places=5)

        self.morphs_settings.diffeomorphic_enable = True
        self.assert_muted()
        bpy.context.evaluated_depsgraph_get().update()
        self.assertAlmostEqual(self.key_blocks["Smile"].value, 1.0, places=5)

    # Drivers with inputs that are not disabled morphs stay active
    def test_mixed_inputs(self):
        self.key_blocks["Smile"].driver_remove("value")
        add_driver(
            self.key_blocks["Smile"], "value", [(self.arm, '["Wide(fin)"]'), (self.rig, None)]
        )
        unrelated = add_driver(
            self.key_blocks["Blink"], "slider_max", [(self.rig, '["Unrelated"]')]
        )
        self.morphs_settings.diffeomorphic_enable = False
        self.assertFalse(self.key_blocks["Smile"].mute)
        self.assertFalse(self.body.data.shape_keys.animation_data.drivers[-2].mute)
        self.assertFalse(unrelated.mute)
        self.assertTrue(self.fin.mute)

    # Morphs that can not be disabled stay active, with the drivers they affect
    def test_can_not_disable(self):
        self.morphs_settings.sections[1].can_disable = False
        self.morphs_settings.diffeomorphic_enable = False
        self.assert_muted("Blink", "Blink.L", "Blink.R")
        self.morphs_settings.diffeomorphic_enable = True
        self.assert_muted()

    # Muted drivers not related to the morphs are left untouched
    def test_unrelated_muted_driver(self):
        unrelated = add_driver(
            self.key_blocks["Blink"], "slider_max", [(self.rig, '["Unrelated"]')], mute=True
        )
        self.morphs_settings.diffeomorphic_enable = False
        self.morphs_settings.diffeomorphic_enable = True
        self.assertTrue(unrelated.mute)

    # Simplify disables the morphs, and enables them back
    def test_simplify(self):
        simplify = self.arm.MustardUI_SimplifySettings
        simplify.simplify_main_enable = True
        simplify.simplify_enable = True
        self.assertFalse(self.morphs_settings.diffeomorphic_enable)
        self.assertTrue(self.fin.mute)
        simplify.simplify_enable = False
        self.assertTrue(self.morphs_settings.diffeomorphic_enable)
        self.assertFalse(self.fin.mute)


class TestDisableDiffeomorphicMorphs(BlenderTestCase):
    def setUp(self):
        super().setUp()
        self.model = build_model()
        configure_model(self.model)
        rig = self.model["armature"]
        self.arm = rig.data
        self.key_blocks = self.model["body"].data.shape_keys.key_blocks
        self.model["body"].shape_key_add(name="body_bs_Wide")

        # Diffeomorphic morph: armature property, final property and shape key
        rig["body_bs_Wide"] = 0.0
        self.arm["body_bs_Wide(fin)"] = 0.0
        self.fin = add_driver(self.arm, '["body_bs_Wide(fin)"]', [(rig, '["body_bs_Wide"]')])
        self.sk = add_driver(
            self.key_blocks["body_bs_Wide"], "value", [(self.arm, '["body_bs_Wide(fin)"]')]
        )

        bpy.ops.mustardui.configuration()
        self.morphs_settings = self.arm.MustardUI_MorphsSettings
        self.morphs_settings.enable_ui = True
        self.morphs_settings.type = "DIFFEO_GENESIS_9"
        self.morphs_settings.diffeomorphic_body_morphs = True
        bpy.ops.mustardui.morphs_check()
        bpy.ops.mustardui.configuration()

    def mutes(self):
        return self.fin.mute, self.sk.mute, self.key_blocks["body_bs_Wide"].mute

    def test_disable(self):
        self.morphs_settings.diffeomorphic_enable = False
        self.assertEqual(self.mutes(), (True, True, True))
        self.morphs_settings.diffeomorphic_enable = True
        self.assertEqual(self.mutes(), (False, False, False))

    def test_can_not_disable(self):
        body = next(x for x in self.morphs_settings.sections if x.diffeomorphic_id == 4)
        self.assertEqual(len(body.morphs), 1)
        body.can_disable = False
        self.morphs_settings.diffeomorphic_enable = False
        self.assertEqual(self.mutes(), (False, False, False))
