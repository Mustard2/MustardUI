import importlib

import bpy
from helpers import (
    ADDON,
    BlenderTestCase,
    build_model,
    configure_model,
    set_active,
    set_active_collection,
)

storage = importlib.import_module(ADDON + ".text_storage.storage")


class TestConfiguration(BlenderTestCase):
    # Configuration enables the model and stores outfits and hair
    def test_configuration_enables_model(self):
        model = build_model()
        arm = model["armature"].data
        rig_settings = configure_model(model)

        self.assertTrue(arm.MustardUI_created)
        self.assertTrue(arm.MustardUI_enable)
        self.assertEqual(rig_settings.model_armature_object, model["armature"])
        self.assertEqual(len(rig_settings.outfits_collections), 2)
        self.assertNotEqual(rig_settings.hair_list, "")

    # Configuration fails without a body mesh
    def test_configuration_requires_body(self):
        model = build_model()
        arm = model["armature"].data
        arm.MustardUI_RigSettings.model_name = "Tester"
        set_active(model["armature"])
        with self.assertRaisesRegex(RuntimeError, "body mesh"):
            bpy.ops.mustardui.configuration()
        self.assertFalse(arm.MustardUI_enable)
        self.assertFalse(arm.MustardUI_created)

    # Configuration mode can be re-entered and closed again
    def test_configuration_toggle_back(self):
        model = build_model()
        arm = model["armature"].data
        configure_model(model)
        bpy.ops.mustardui.configuration()
        self.assertFalse(arm.MustardUI_enable)
        self.assertTrue(arm.MustardUI_created)
        bpy.ops.mustardui.configuration()
        self.assertTrue(arm.MustardUI_enable)

    # Adding the same outfit collection twice is rejected
    def test_add_outfit_twice_is_rejected(self):
        model = build_model()
        configure_model(model)
        bpy.ops.mustardui.configuration()
        set_active_collection(model["outfits"][0])
        with self.assertRaisesRegex(RuntimeError, "already added"):
            bpy.ops.mustardui.add_collection()
        rig_settings = model["armature"].data.MustardUI_RigSettings
        self.assertEqual(len(rig_settings.outfits_collections), 2)

    # Quick Setup scans outfits, extras and hair and configures the model
    def test_quick_setup(self):
        model = build_model()
        arm = model["armature"].data
        rig_settings = arm.MustardUI_RigSettings
        rig_settings.model_name = "Tester"
        rig_settings.model_body = model["body"]
        set_active(model["armature"])

        bpy.ops.mustardui.quick_setup_smart_check()
        found = {x.collection.name for x in rig_settings.quick_setup_outfit_collections}
        self.assertTrue({c.name for c in model["outfits"]} <= found)
        self.assertEqual(rig_settings.extras_collection, model["extras"])

        for item in rig_settings.quick_setup_outfit_collections:
            item.enabled = item.collection in model["outfits"]
        bpy.ops.mustardui.quick_setup()

        self.assertTrue(arm.MustardUI_created)
        self.assertTrue(arm.MustardUI_enable)
        self.assertEqual(
            {x.collection for x in rig_settings.outfits_collections}, set(model["outfits"])
        )
        self.assertIsNotNone(rig_settings.hair_collection)
        self.assertEqual(
            {o.name for o in rig_settings.hair_collection.objects}, {"Hair Short", "Hair Long"}
        )

    # Remove UI with Delete Settings keeps the objects
    def test_remove_ui_settings(self):
        model = build_model()
        arm = model["armature"].data
        configure_model(model)
        bpy.ops.mustardui.remove(delete_settings=True)
        self.assertEqual(len(arm.MustardUI_RigSettings.outfits_collections), 0)
        self.assertIn("Casual - Shirt", bpy.data.objects)

    # Remove UI with Delete Settings removes the stored settings, not only the outfits
    def test_remove_ui_settings_stored(self):
        model = build_model()
        arm = model["armature"].data
        configure_model(model)
        bpy.ops.mustardui.remove(delete_settings=True)
        props = storage.system_properties(arm)
        self.assertNotIn("MustardUI_RigSettings", props or {})

    # Remove UI with Delete Objects deletes the model objects
    def test_remove_ui_objects(self):
        model = build_model()
        configure_model(model)
        bpy.ops.mustardui.remove(delete_objects=True)
        for name in ("Casual - Shirt", "Hair Long", "Extras - Glasses", "Tester Body"):
            self.assertNotIn(name, bpy.data.objects)
