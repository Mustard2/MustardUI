import importlib
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
simplify = importlib.import_module(ADDON + ".tools.simplify")
storage = importlib.import_module(ADDON + ".text_storage.storage")


def system_props(id_data, create=False):
    """Storage of the add-on properties, apart from custom properties in Blender 5.0+."""
    if bpy.app.version >= (5, 0):
        return id_data.bl_system_properties_get(do_create=create)
    return id_data


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
                groups = (system_props(idb), idb) if bpy.app.version >= (5, 0) else (idb,)
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
        props = system_props(id_data) or {}
        return {
            k: plain(props[k])
            for k in props.keys()
            if k.lower().startswith("mustardui") and k != "MustardUI_data"
        }

    def depsgraph_materials(self):
        depsgraph = bpy.context.evaluated_depsgraph_get()
        return {x.original for x in depsgraph.ids if isinstance(x, bpy.types.Material)}

    # Switching moves the settings to a Text and back, keeping all their values
    def test_round_trip(self):
        settings = self.snapshot(self.arm)

        self.set_enabled(True)
        text = self.arm.MustardUI_data
        self.assertIsNotNone(text)
        self.assertNotIn("MustardUI_RigSettings", bpy.types.Armature.bl_rna.properties)
        self.assertEqual(self.arm.MustardUI_RigSettings.id_data, text)
        on_text = self.snapshot(text)
        self.assertIn("MustardUI_CustomPropertiesOutfit", on_text)
        self.assertEqual(on_text, {k: v for k, v in settings.items() if k in on_text})
        self.assertFalse(set(on_text) & set(self.snapshot(self.arm)))

        self.set_enabled(False)
        self.assertIsNone(self.arm.MustardUI_data)
        self.assertNotIn(text, bpy.data.texts.values())
        self.assertEqual(self.arm.MustardUI_RigSettings.id_data, self.arm)
        self.assertEqual(self.snapshot(self.arm), settings)

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
        self.assertNotIn("MustardUI_data", system_props(self.arm) or {})

    # Empty pointers stored by reading MustardUI_data are removed with Armature storage
    def test_empty_pointer_removed(self):
        system_props(self.arm, create=True)["MustardUI_data"] = {}
        bpy.context.view_layer.update()
        self.assertNotIn("MustardUI_data", system_props(self.arm))

    # Blender starts with Armature storage, unless disabled in the preferences
    def test_startup(self):
        prefs = bpy.context.preferences.addons[ADDON].preferences
        self.set_enabled(True)
        storage._startup()
        self.assertEqual(prefs.settings_storage, "ARMATURE")
        self.assertNotIn("MustardUI_data", system_props(self.arm))

        self.set_enabled(True)
        prefs.settings_storage_startup = False
        storage._startup()
        self.assertEqual(prefs.settings_storage, "TEXT")
        self.assertIn("MustardUI_data", system_props(self.arm))

    # Text storage is active only with Experimental Features enabled
    def test_experimental(self):
        self.set_enabled(True)
        bpy.context.preferences.addons[ADDON].preferences.experimental = False
        self.assertIsNone(self.arm.MustardUI_data)
        self.assertEqual(self.arm.MustardUI_RigSettings.id_data, self.arm)

    # The materials of hidden outfits leave the depsgraph
    def test_hidden_outfit_materials(self):
        self.assertIn(self.dress_material, self.depsgraph_materials())
        self.set_enabled(True)
        self.assertNotIn(self.dress_material, self.depsgraph_materials())

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

    # Remove UI deletes the Text with the settings
    def test_remove_ui(self):
        self.set_enabled(True)
        text = self.arm.MustardUI_data
        bpy.ops.mustardui.remove(delete_settings=True)
        self.assertNotIn(text, bpy.data.texts.values())
        self.assertEqual(len(self.arm.MustardUI_RigSettings.outfits_collections), 0)

    # The Text has no fake user, so it goes away with its armature
    def test_text_removed_with_armature(self):
        self.set_enabled(True)
        text = self.arm.MustardUI_data
        self.assertFalse(text.use_fake_user)
        bpy.data.objects.remove(self.model["armature"])
        bpy.data.armatures.remove(self.arm)
        self.assertEqual(text.users, 0)

    # Settings left on an armature move to its Text on first access
    def test_first_access(self):
        self.set_enabled(True)
        arm = bpy.data.armatures.new("Appended")
        system_props(arm, create=True)["MustardUI_RigSettings"] = {"model_name": "Appended"}
        self.assertEqual(arm.MustardUI_RigSettings.model_name, "Appended")
        self.assertNotIn("MustardUI_RigSettings", system_props(arm))

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
        self.assertIsNone(arm.MustardUI_data)
        self.assertEqual(arm.MustardUI_RigSettings.model_name, "Tester")
        self.assertFalse([x for x in bpy.data.texts if x.name.startswith(".MustardUI")])

    # Armatures sharing a Text all get the settings back
    def test_shared_text(self):
        self.set_enabled(True)
        copy = self.arm.copy()
        self.assertEqual(copy.MustardUI_data, self.arm.MustardUI_data)
        self.set_enabled(False)
        for arm in (self.arm, copy):
            self.assertIsNone(arm.MustardUI_data)
            self.assertEqual(arm.MustardUI_RigSettings.model_body, self.model["body"])

    # Simplify skips the extras of settings without an armature
    def test_simplify_orphan_settings(self):
        self.set_enabled(True)
        text = bpy.data.texts.new("Orphan")
        text.MustardUI_RigSettings.extras_collection = self.model["extras"]
        simplify.simplify_extras(text.MustardUI_RigSettings, True)
        self.assertFalse(bpy.data.objects["Extras - Glasses"].hide_viewport)

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
            text = rig.data.MustardUI_data
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

        texts = [x.MustardUI_data for x in bpy.data.armatures]
        self.assertNotIn(None, texts)
        self.assertEqual(len(set(texts)), len(texts))
        self.assertEqual(
            bpy.data.armatures["Tester Armature.001"].MustardUI_RigSettings.model_body.name,
            "Tester Body",
        )

    # Files are converted to the active storage when loaded
    def test_load(self):
        settings = self.snapshot(self.arm)
        self.set_enabled(True)
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "model.blend")
            bpy.ops.wm.save_as_mainfile(filepath=path)
            self.set_enabled(False)
            bpy.ops.wm.open_mainfile(filepath=path)

        self.arm = bpy.data.armatures["Tester Armature"]
        self.assertIsNone(self.arm.MustardUI_data)
        self.assertEqual(self.snapshot(self.arm), settings)
