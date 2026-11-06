import importlib
from datetime import datetime
from types import SimpleNamespace

import bpy
from fake_ui import Drawer, FakeLayout
from helpers import (
    ADDON,
    BlenderTestCase,
    build_model,
    checked_items,
    configure_model,
    new_mesh_object,
    set_active,
    set_active_collection,
)

storage = importlib.import_module(ADDON + ".text_storage.storage")
smartcheck = importlib.import_module(ADDON + ".configuration.ops_smartcheck")
cleanmodel = importlib.import_module(ADDON + ".configuration.ops_cleanmodel")


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

    # The version date follows the date vector in every format, and 0,0,0 means today
    def test_version_date(self):
        model = build_model()
        rig_settings = configure_model(model)
        rig_settings.model_version_date_enable = True
        cases = [
            ("DMY", (13, 4, 2023), "13/04/2023"),
            ("MDY2", (4, 13, 2023), "04/13/2023"),
            ("MDY", (4, 13, 2023), "April 13, 2023"),
            ("DMY", (0, 0, 0), datetime.today().strftime("%d/%m/%Y")),
        ]
        for date_format, vector, expected in cases:
            with self.subTest(date_format=date_format, vector=vector):
                bpy.ops.mustardui.configuration()
                rig_settings.model_version_date_format = date_format
                rig_settings.model_version_date_vector = vector
                bpy.ops.mustardui.configuration()
                self.assertEqual(rig_settings.model_version_date, expected)

    # The Today button fills the date vector in the order of the chosen format
    def test_version_date_today(self):
        model = build_model()
        rig_settings = configure_model(model)
        bpy.ops.mustardui.configuration()
        today = datetime.today()
        for date_format, expected in [
            ("DMY", (today.day, today.month, today.year)),
            ("MDY2", (today.month, today.day, today.year)),
        ]:
            with self.subTest(date_format=date_format):
                rig_settings.model_version_date_format = date_format
                bpy.ops.mustardui.version_date_today()
                self.assertEqual(tuple(rig_settings.model_version_date_vector), expected)

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

    # Smart Check finds the collections named after the model, without warnings when no
    # body vertex group is named after an outfit piece
    def test_smartcheck(self):
        model = build_model()
        rig_settings = model["armature"].data.MustardUI_RigSettings
        rig_settings.model_name = "Tester"
        rig_settings.model_body = model["body"]
        set_active(model["armature"])

        bpy.ops.mustardui.configuration_smartcheck()
        self.assertEqual(
            {x.collection for x in rig_settings.outfits_collections}, set(model["outfits"])
        )
        self.assertEqual(rig_settings.extras_collection, model["extras"])
        self.assertEqual(rig_settings.hair_collection, model["hair"])
        self.assertNotIn("MustardUI - Mask", model["body"].vertex_groups)
        options = SimpleNamespace(smartcheck_body_mask_optimize=True)
        self.assertEqual(
            smartcheck.smartcheck_body_mask_from_vg(options, bpy.context, rig_settings), 0
        )

    # Smart Check turns the Mask of a vertex group named after an outfit piece into a
    # Vertex Weight Mix on the shared mask
    def test_smartcheck_body_mask(self):
        model = build_model()
        body = model["body"]
        body.vertex_groups.new(name="Formal - Dress")
        body.modifiers["Formal - Dress"].vertex_group = "Formal - Dress"
        rig_settings = model["armature"].data.MustardUI_RigSettings
        rig_settings.model_name = "Tester"
        rig_settings.model_body = body
        set_active(model["armature"])

        bpy.ops.mustardui.configuration_smartcheck()
        mix = body.modifiers["Formal - Dress"]
        self.assertEqual(mix.type, "VERTEX_WEIGHT_MIX")
        self.assertEqual(mix.vertex_group_a, "MustardUI - Mask")
        self.assertIn("MustardUI - Mask", body.vertex_groups)
        self.assertEqual(body.modifiers["MustardUI - Mask"].type, "MASK")

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


class CleanModelDialog:
    """Clean Model instance stand-in, on the last properties of the operator"""

    def __init__(self):
        self.drawer = Drawer()
        self.layout = FakeLayout(self.drawer)
        self.properties = bpy.context.window_manager.operator_properties_last(
            "mustardui.cleanmodel"
        )

    def __getattr__(self, name):
        if hasattr(self.properties, name):
            return getattr(self.properties, name)
        return getattr(cleanmodel.MustardUI_CleanModel, name).__get__(self)


class TestCleanModel(BlenderTestCase):
    def setUp(self):
        super().setUp()
        self.model = build_model()
        self.rig_settings = configure_model(self.model)
        lens = new_mesh_object("Extras - Lens", self.model["extras"], size=0.1)
        lens.parent = bpy.data.objects["Extras - Glasses"]
        new_mesh_object("Extras - Hat", self.model["extras"]).hide_viewport = True

    # The lists show the pieces and hair, and Check Not In Use checks all but the ones shown
    def test_lists(self):
        self.rig_settings.outfits_list = "Tester Casual"
        self.rig_settings.hair_list = "Hair Short"
        bpy.data.objects["Formal - Dress"].MustardUI_outfit_lock = True
        dialog = CleanModelDialog()
        dialog.update_lists(self.rig_settings)

        names = {
            kind: [x.name for x in getattr(dialog, f"{kind}_to_remove")]
            for kind in ("outfits", "extras", "hair")
        }
        self.assertEqual(names["outfits"], ["Tester Casual", "Tester Formal"])
        self.assertEqual(names["extras"], ["Extras - Glasses", "Extras - Hat"])
        self.assertEqual(sorted(names["hair"]), ["Hair Long", "Hair Short"])

        self.assertFalse(dialog.check(bpy.context))
        for kind in names:
            setattr(dialog.properties, f"check_{kind}_not_in_use", True)
            setattr(dialog.properties, f"remove_{kind}", True)
        self.assertTrue(dialog.check(bpy.context))
        checked = {
            kind: [x.name for x in getattr(dialog, f"{kind}_to_remove") if x.remove]
            for kind in names
        }
        self.assertEqual(
            checked, {"outfits": [], "extras": ["Extras - Hat"], "hair": ["Hair Long"]}
        )

        cleanmodel.MustardUI_CleanModel.draw(dialog, bpy.context)
        self.assertEqual(dialog.drawer.errors, [])

    # Only the checked pieces are deleted, with their children and Physics Items
    def test_checked_extras(self):
        items = self.model["armature"].data.MustardUI_PhysicsSettings.items
        item = items.add()
        item.object = new_mesh_object("Glasses Cage")
        item.outfit_enable = True
        item.outfit_collection = self.model["extras"]
        item.outfit_object = bpy.data.objects["Extras - Glasses"]

        bpy.ops.mustardui.cleanmodel(remove_extras=True)
        self.assertIn("Extras - Glasses", bpy.data.objects)

        bpy.ops.mustardui.cleanmodel(
            remove_extras=True, extras_to_remove=checked_items("Extras - Glasses")
        )
        self.assertEqual([o.name for o in self.model["extras"].objects], ["Extras - Hat"])
        self.assertNotIn("Extras - Lens", bpy.data.objects)
        self.assertNotIn("Glasses Cage", bpy.data.objects)
        self.assertEqual(len(items), 0)

    # Deleting all the pieces deletes the Extras collection
    def test_all_extras(self):
        bpy.ops.mustardui.cleanmodel(
            remove_extras=True,
            extras_to_remove=checked_items("Extras - Glasses", "Extras - Hat"),
        )
        self.assertIsNone(self.rig_settings.extras_collection)
