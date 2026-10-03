import importlib
import itertools
import os
import tempfile

import bpy
from fake_ui import Drawer, FakeLayout, FakeSelf, draw_all
from helpers import (
    ADDON,
    BlenderTestCase,
    build_model,
    configure_model,
    new_collection,
    new_mesh_object,
    new_object,
)

cp_misc = importlib.import_module(ADDON + ".custom_properties.misc")
export = importlib.import_module(ADDON + ".outfits.toolkit.ops_export_outfits")
storage = importlib.import_module(ADDON + ".text_storage.storage")


def plain(value):
    """ID properties as Python values, with IDs as names to compare across file loads."""
    if isinstance(value, bpy.types.ID):
        return value.name
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    elif hasattr(value, "to_list"):
        value = value.to_list()
    elif hasattr(value, "keys") and not isinstance(value, dict):
        value = {k: value[k] for k in value.keys()}
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    return value


def file_state():
    """Every datablock of the file with its add-on and custom properties."""
    state = {}
    for prop in bpy.data.bl_rna.properties:
        if prop.type != "COLLECTION" or prop.identifier in {"window_managers", "screens"}:
            continue
        for idb in getattr(bpy.data, prop.identifier):
            if isinstance(idb, bpy.types.ID):
                groups = (idb, storage.system_properties(idb))
                state[f"{type(idb).__name__}/{idb.name}"] = [plain(x or {}) for x in groups]
    return state


class TestTextStorage(BlenderTestCase):
    def setUp(self):
        super().setUp()
        self.model = build_model()
        configure_model(self.model)
        self.arm = self.model["armature"].data
        self.dress_material = bpy.data.materials.new("Dress")
        bpy.data.objects["Formal - Dress"].data.materials.append(self.dress_material)
        self.arm.MustardUI_RigSettings.outfits_list = "Tester Casual"

        # Outfit custom property, to have pointers in the custom properties lists
        shirt = bpy.data.objects["Casual - Shirt"]
        cp = self.arm.MustardUI_CustomPropertiesOutfit.add()
        cp.name, cp.prop_name, cp.cp_type = "Sleeves", "Sleeves", "OUTFIT"
        cp.outfit, cp.outfit_piece = shirt.users_collection[0], shirt

    def tearDown(self):
        self.set_enabled(False)
        super().tearDown()

    def set_enabled(self, value):
        prefs = bpy.context.preferences.addons[ADDON].preferences
        prefs.experimental = value
        prefs.settings_storage = "TEXT" if value else "ARMATURE"

    def snapshot(self, id_data):
        """All the MustardUI settings stored on id_data."""
        props = storage.system_properties(id_data) or {}
        return {
            k: plain(props[k])
            for k in props.keys()
            if k.lower().startswith("mustardui") and k != "MustardUI_data"
        }

    def count_conversions(self):
        """Storage conversions made from now on."""
        calls, convert = [], storage._convert
        storage._convert = lambda enable: calls.append(enable) or convert(enable)
        self.addCleanup(setattr, storage, "_convert", convert)
        return calls

    def depsgraph_materials(self):
        depsgraph = bpy.context.evaluated_depsgraph_get()
        return {x.original for x in depsgraph.ids if isinstance(x, bpy.types.Material)}

    # Switching moves the settings to a Text and back, keeping all their values
    def test_round_trip(self):
        state = file_state()
        settings = self.snapshot(self.arm)

        self.set_enabled(True)
        text = storage.text_of(self.arm)
        self.assertIsNotNone(text)
        # Without the fake user the Text is removed with the armature
        self.assertFalse(text.use_fake_user)
        self.assertNotIn("MustardUI_RigSettings", bpy.types.Armature.bl_rna.properties)
        self.assertEqual(self.arm.MustardUI_RigSettings.id_data, text)
        on_text = self.snapshot(text)
        self.assertIn("MustardUI_CustomPropertiesOutfit", on_text)
        self.assertEqual(on_text, {k: v for k, v in settings.items() if k in on_text})
        self.assertFalse(set(on_text) & set(self.snapshot(self.arm)))

        self.set_enabled(False)
        self.assertNotIn(text, bpy.data.texts.values())
        self.assertEqual(file_state(), state)

    def save_reopen(self, directory):
        path = os.path.join(directory, "model.blend")
        bpy.ops.wm.save_as_mainfile(filepath=path)
        bpy.ops.wm.open_mainfile(filepath=path)
        self.arm = bpy.data.armatures["Tester Armature"]

    # Saving with Text storage, reopening and switching back leaves the file as before
    def test_text_save_reopen_armature(self):
        state = file_state()
        with tempfile.TemporaryDirectory() as directory:
            self.set_enabled(True)
            self.save_reopen(directory)
            self.assertIn(".MustardUI Tester Armature", bpy.data.texts)
            self.set_enabled(False)
            self.assertEqual(file_state(), state)
            self.save_reopen(directory)
        self.assertEqual(file_state(), state)

    # Saving with Armature storage leaves no trace of the Text storage
    def test_armature_save(self):
        state = file_state()
        bpy.context.scene.frame_set(2)
        bpy.context.view_layer.update()
        with tempfile.TemporaryDirectory() as directory:
            self.save_reopen(directory)
        self.assertEqual(file_state(), state)

    # Blender starts with Armature storage, unless disabled in the preferences
    def test_startup(self):
        prefs = bpy.context.preferences.addons[ADDON].preferences
        self.set_enabled(True)
        calls = self.count_conversions()
        storage._startup()
        self.assertEqual(prefs.settings_storage, "ARMATURE")
        self.assertNotIn("MustardUI_data", storage.system_properties(self.arm))
        self.assertEqual(calls, [False])

        self.set_enabled(True)
        prefs.settings_storage_startup = False
        storage._startup()
        self.assertEqual(prefs.settings_storage, "TEXT")
        self.assertIn("MustardUI_data", storage.system_properties(self.arm))

    # Text storage is active only with Experimental Features enabled
    def test_experimental(self):
        self.set_enabled(True)
        bpy.context.preferences.addons[ADDON].preferences.experimental = False
        self.assertIsNone(storage.text_of(self.arm))
        self.assertEqual(self.arm.MustardUI_RigSettings.id_data, self.arm)

    # The materials of hidden outfits leave the depsgraph
    def test_hidden_outfit_materials(self):
        self.assertIn(self.dress_material, self.depsgraph_materials())
        self.set_enabled(True)
        self.assertNotIn(self.dress_material, self.depsgraph_materials())

    # Custom properties edited with Text storage are kept and drive their targets in both
    def test_custom_properties(self):
        keys = self.model["body"].data.shape_keys
        self.set_enabled(True)
        rna = f'bpy.data.shape_keys["{keys.name}"].key_blocks["Smile"]'
        self.arm["Smile Amount"] = 0.0
        cp_misc.mustardui_add_driver(self.arm, rna, "value", "Smile Amount", 0)
        cp = self.arm.MustardUI_CustomProperties.add()
        cp.name, cp.prop_name, cp.rna, cp.path = "Smile Amount", "Smile Amount", rna, "value"
        cp.type, cp.is_animatable = "FLOAT", True
        self.arm.MustardUI_CustomPropertiesOutfit["Sleeves"].name = "Long Sleeves"

        for enable in (True, False):
            self.set_enabled(enable)
            outfit_cps = self.arm.MustardUI_CustomPropertiesOutfit
            self.assertEqual([x.name for x in outfit_cps], ["Long Sleeves"])
            self.assertEqual(self.arm.MustardUI_CustomProperties["Smile Amount"].rna, rna)
            for value in (0.25, 0.75):
                self.arm["Smile Amount"] = value
                self.arm.update_tag()
                depsgraph = bpy.context.evaluated_depsgraph_get()
                depsgraph.update()
                smile = keys.evaluated_get(depsgraph).key_blocks["Smile"].value
                self.assertAlmostEqual(smile, value, places=5)

    # Outfits still switch through the settings on the Text
    def test_switch_outfit(self):
        self.set_enabled(True)
        dress = bpy.data.objects["Formal - Dress"]
        self.arm.MustardUI_RigSettings.outfits_list = "Tester Formal"
        self.assertFalse(dress.hide_render)
        self.arm.MustardUI_RigSettings.outfits_list = "Tester Casual"
        self.assertTrue(dress.hide_render)

    # Configuration and user panels draw with the settings on the Text
    def test_draw(self):
        self.set_enabled(True)
        bpy.context.preferences.addons[ADDON].preferences.developer = True
        for panel in ("PANEL_PT_MustardUI_Outfits", "PANEL_PT_MustardUI_InitPanel_Outfit"):
            drawer = draw_all(bpy.context)
            self.assertIn(panel, drawer.drawn)
            self.assertEqual(drawer.errors, [], "\n" + "\n".join(drawer.errors))
            bpy.ops.mustardui.configuration()

    # The preferences draw the notice of each storage
    def test_draw_preferences(self):
        prefs = bpy.context.preferences.addons[ADDON].preferences
        drawer = Drawer()
        for value in (False, True):
            self.set_enabled(value)
            values = {x.identifier: getattr(prefs, x.identifier) for x in prefs.bl_rna.properties}
            fake = FakeSelf(type(prefs), FakeLayout(drawer), **values)
            drawer.run("preferences", type(prefs).draw, fake, bpy.context)
        self.assertEqual(drawer.errors, [], "\n" + "\n".join(drawer.errors))

    # Remove UI replaces the Text with the settings by an empty one
    def test_remove_ui(self):
        self.set_enabled(True)
        text = storage.text_of(self.arm)
        bpy.ops.mustardui.remove(delete_settings=True)
        bpy.context.view_layer.update()
        self.assertNotIn(text, bpy.data.texts.values())
        self.assertIsNotNone(storage.text_of(self.arm))
        self.assertEqual(len(self.arm.MustardUI_RigSettings.outfits_collections), 0)

    # Settings left on an armature move to its Text on first access
    def test_first_access(self):
        self.set_enabled(True)
        arm = bpy.data.armatures.new("Appended")
        props = storage.system_properties(arm, create=True)
        props["MustardUI_RigSettings"] = {"model_name": "Appended"}
        self.assertEqual(arm.MustardUI_RigSettings.model_name, "Appended")
        self.assertNotIn("MustardUI_RigSettings", storage.system_properties(arm))

    # Armatures appended in Armature mode get their settings back from the Text
    def test_append_armature_mode(self):
        self.set_enabled(True)
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "model.blend")
            bpy.ops.wm.save_as_mainfile(filepath=path, copy=True)
            self.set_enabled(False)
            bpy.ops.wm.read_homefile(use_empty=True)
            with bpy.data.libraries.load(path) as (data_from, data_to):
                data_to.objects = ["Tester Armature"]
        bpy.context.scene.collection.objects.link(data_to.objects[0])
        bpy.context.view_layer.update()

        arm = data_to.objects[0].data
        self.assertIsNone(storage.text_of(arm))
        self.assertEqual(arm.MustardUI_RigSettings.model_name, "Tester")
        self.assertFalse([x for x in bpy.data.texts if x.name.startswith(".MustardUI")])

    # Linked and overridden armatures are converted before drawing, which can not create the Text
    def test_linked_armatures(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = {}
            for saved in (False, True):
                self.set_enabled(saved)
                paths[saved] = os.path.join(directory, f"model_{saved}.blend")
                bpy.ops.wm.save_as_mainfile(filepath=paths[saved], copy=True)
            for saved, enabled in itertools.product((False, True), repeat=2):
                with self.subTest(saved=saved, enabled=enabled):
                    bpy.ops.wm.read_homefile(use_empty=True)
                    self.set_enabled(enabled)
                    with bpy.data.libraries.load(paths[saved], link=True) as (data_from, data_to):
                        data_to.objects = ["Tester Armature"]
                    linked = data_to.objects[0]
                    override = linked.override_create()
                    override.data = linked.data.override_create()
                    bpy.context.scene.collection.objects.link(override)
                    bpy.context.view_layer.update()

                    for arm in (linked.data, override.data):
                        self.assertEqual(storage.text_of(arm) is not None, enabled)
                        self.assertEqual(arm.MustardUI_RigSettings.model_name, "Tester")

    # Armatures sharing a Text all get the settings back
    def test_shared_text(self):
        self.set_enabled(True)
        copy = self.arm.copy()
        self.assertEqual(storage.text_of(copy), storage.text_of(self.arm))
        self.set_enabled(False)
        for arm in (self.arm, copy):
            self.assertIsNone(storage.text_of(arm))
            self.assertEqual(arm.MustardUI_RigSettings.model_body, self.model["body"])

    # Outfits are exported with Armature storage, leaving no Text in either file
    def test_export(self):
        settings = bpy.context.scene.MustardUI_Settings
        settings.viewport_model_selection = False
        settings.panel_model_selection_armature = self.arm
        # Outfit with its own rig, written as it is
        rig = new_object("Skirt Rig", bpy.data.armatures.new("Skirt Rig"), self.model["outfits"][0])
        self.set_enabled(True)
        texts = {x.name for x in bpy.data.texts}
        export.export_fill_items(bpy.context)
        for item in bpy.context.window_manager.MustardUI_ModelToolkit_ExportOutfits_Items:
            item.use = item.name == "Tester Casual"
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "outfits.blend")
            result = bpy.ops.mustardui.model_toolkit_export_outfits(filepath=path)
            self.assertEqual(result, {"FINISHED"})
            self.assertEqual({x.name for x in bpy.data.texts}, texts)
            self.assertIsNotNone(storage.text_of(rig.data))

            # Also an export stopped by an error leaves no Text
            original = export.OutfitCopier.run
            export.OutfitCopier.run = lambda self: 1 / 0
            try:
                with self.assertRaises(RuntimeError):
                    bpy.ops.mustardui.model_toolkit_export_outfits(filepath=path + "2")
            finally:
                export.OutfitCopier.run = original
            # The expected error is printed
            self._stderr.buffer.seek(0)
            self._stderr.buffer.truncate()
            self.assertEqual({x.name for x in bpy.data.texts}, texts)

            with bpy.data.libraries.load(path) as (data_from, data_to):
                self.assertEqual(list(data_from.texts), [])
                data_to.armatures = ["Tester Armature", "Skirt Rig"]

        for arm in data_to.armatures:
            self.assertNotIn("MustardUI_data", storage.system_properties(arm) or {})
        props = storage.system_properties(data_to.armatures[0])
        self.assertEqual(plain(props["MustardUI_RigSettings"])["model_name"], "Tester")

    # The storage is converted when armatures change, not when posing
    def test_depsgraph_update(self):
        self.set_enabled(True)
        calls = self.count_conversions()
        rig = self.model["armature"]
        rig.pose.bones["spine"].rotation_quaternion[1] = 0.1
        rig.location.x = 0.5
        bpy.context.view_layer.update()
        self.assertEqual(calls, [])

        # A deleted Text is replaced, e.g. after Make Local of a linked armature
        bpy.data.texts.remove(storage.text_of(self.arm))
        bpy.context.view_layer.update()
        self.assertEqual(calls, [True])
        self.assertIsNotNone(storage.text_of(self.arm))

    # Outfit custom properties of a model saved with source_text storage, added with the other
    def append_outfit(self, source_text):
        settings = bpy.context.scene.MustardUI_Settings
        settings.viewport_model_selection = False
        settings.panel_model_selection_armature = self.arm

        self.set_enabled(source_text)
        rig = new_object("Source Rig", bpy.data.armatures.new("Source Rig"))
        body = new_mesh_object("Source Body")
        rig.data.MustardUI_RigSettings.model_body = body
        coll = new_collection("Sporty")
        shorts = new_mesh_object("Sporty - Shorts", coll, size=0.52)
        shorts.modifiers.new("Armature", "ARMATURE").object = rig
        for name in ("Basis", "Tight"):
            shorts.shape_key_add(name=name, from_mix=False)
        rna = f'bpy.data.shape_keys["{shorts.data.shape_keys.name}"].key_blocks["Tight"]'
        rig.data["Tight"] = 0.7
        cp_misc.mustardui_add_driver(rig.data, rna, "value", "Tight", 0)
        cp = rig.data.MustardUI_CustomPropertiesOutfit.add()
        cp.name, cp.prop_name, cp.rna, cp.path = "Tight", "Tight", rna, "value"
        cp.type, cp.is_animatable, cp.cp_type = "FLOAT", True, "OUTFIT"
        cp.outfit, cp.outfit_piece = coll, shorts

        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "source.blend")
            bpy.data.libraries.write(path, {coll})
            text = storage.text_of(rig.data)
            removed = [shorts, shorts.data, body, body.data, rig, rig.data, coll]
            bpy.data.batch_remove(removed + ([text] if text else []))

            self.set_enabled(not source_text)
            bpy.ops.mustardui.model_toolkit_add_outfit_from_file(
                directory=os.path.join(path, "Collection", ""),
                files=[{"name": "Sporty"}],
                fit="NONE",
                transfer_shape_keys=False,
            )
        return [x.name for x in self.arm.MustardUI_CustomPropertiesOutfit]

    def test_add_outfit_from_armature_file(self):
        self.assertIn("Tight", self.append_outfit(source_text=False))

    def test_add_outfit_from_text_file(self):
        self.assertIn("Tight", self.append_outfit(source_text=True))

    # New and duplicated armatures get their own Text
    def test_new_armatures(self):
        self.set_enabled(True)
        new_object("New", bpy.data.armatures.new("New"))
        new_object("Copy", self.arm.copy())
        bpy.context.view_layer.update()

        texts = [storage.text_of(x) for x in bpy.data.armatures]
        self.assertNotIn(None, texts)
        self.assertEqual(len(set(texts)), len(texts))
        self.assertEqual(
            bpy.data.armatures["Tester Armature.001"].MustardUI_RigSettings.model_body.name,
            "Tester Body",
        )

    # Files are converted to the active storage when loaded
    def test_load(self):
        state = file_state()
        self.set_enabled(True)
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "model.blend")
            bpy.ops.wm.save_as_mainfile(filepath=path)
            self.set_enabled(False)
            bpy.ops.wm.open_mainfile(filepath=path)

        self.assertEqual(file_state(), state)
