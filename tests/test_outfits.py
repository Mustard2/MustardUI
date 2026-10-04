import importlib
import os
import shutil
import tempfile

import bmesh
import bpy
import numpy as np
from fake_ui import Drawer, FakeLayout, FakeSelf
from helpers import (
    ADDON,
    BlenderTestCase,
    build_model,
    configure_model,
    new_collection,
    new_mesh_object,
    new_object,
    reset_scene,
)

add_outfit = importlib.import_module(ADDON + ".outfits.toolkit.ops_add_outfit")
squish = importlib.import_module(ADDON + ".model_toolkit.outfits.ops_squish")
export = importlib.import_module(ADDON + ".outfits.toolkit.ops_export_outfits")
cp_misc = importlib.import_module(ADDON + ".custom_properties.misc")


class TestOutfits(BlenderTestCase):
    def setUp(self):
        super().setUp()
        self.model = build_model()
        self.rig_settings = configure_model(self.model)

    def visible(self, name):
        obj = bpy.data.objects[name]
        return not obj.hide_viewport and not obj.hide_render

    # Switching outfit shows only its pieces, Nude hides all
    def test_switch_outfit(self):
        self.rig_settings.outfits_list = "Tester Casual"
        self.assertTrue(self.visible("Casual - Shirt"))
        self.assertTrue(self.visible("Casual - Pants"))
        self.assertFalse(self.visible("Formal - Dress"))

        self.rig_settings.outfits_list = "Tester Formal"
        self.assertFalse(self.visible("Casual - Shirt"))
        self.assertTrue(self.visible("Formal - Dress"))

        self.rig_settings.outfits_list = "Nude"
        for name in ("Casual - Shirt", "Casual - Pants", "Formal - Dress"):
            self.assertFalse(self.visible(name))

    # Body masks follow the outfit and the global mask switch
    def test_outfit_masks(self):
        mask = self.model["body"].modifiers["Formal - Dress"]
        self.rig_settings.outfits_list = "Tester Formal"
        self.assertTrue(mask.show_viewport)
        self.rig_settings.outfits_list = "Tester Casual"
        self.assertFalse(mask.show_viewport)

        self.rig_settings.outfits_global_mask = False
        self.rig_settings.outfits_list = "Tester Formal"
        self.assertFalse(mask.show_viewport)

    # Single piece visibility toggles only that piece
    def test_piece_visibility(self):
        self.rig_settings.outfits_list = "Tester Casual"
        bpy.ops.mustardui.object_visibility(obj="Casual - Shirt")
        self.assertFalse(self.visible("Casual - Shirt"))
        self.assertTrue(self.visible("Casual - Pants"))
        bpy.ops.mustardui.object_visibility(obj="Casual - Shirt")
        self.assertTrue(self.visible("Casual - Shirt"))

    # Toggling a piece toggles its body mask
    def test_piece_visibility_drives_mask(self):
        mask = self.model["body"].modifiers["Formal - Dress"]
        self.rig_settings.outfits_list = "Tester Formal"
        bpy.ops.mustardui.object_visibility(obj="Formal - Dress")
        self.assertFalse(mask.show_viewport)
        bpy.ops.mustardui.object_visibility(obj="Formal - Dress")
        self.assertTrue(mask.show_viewport)

    # Extras visibility can be toggled
    def test_extras_visibility(self):
        bpy.ops.mustardui.object_visibility(obj="Extras - Glasses")
        glasses = self.visible("Extras - Glasses")
        bpy.ops.mustardui.object_visibility(obj="Extras - Glasses")
        self.assertNotEqual(glasses, self.visible("Extras - Glasses"))

    # Outfit global switch toggles the Smooth Corrective modifiers
    def test_global_modifier_switch(self):
        shirt = bpy.data.objects["Casual - Shirt"]
        smooth = shirt.modifiers.new("Smooth", "CORRECTIVE_SMOOTH")
        self.rig_settings.outfits_enable_global_smoothcorrection = True
        self.rig_settings.outfits_global_smoothcorrection = False
        self.assertFalse(smooth.show_viewport)
        self.rig_settings.outfits_global_smoothcorrection = True
        self.assertTrue(smooth.show_viewport)

    # Deleting an outfit removes it and its objects
    def test_delete_outfit(self):
        bpy.ops.mustardui.configuration()
        bpy.context.scene.mustardui_outfits_uilist_index = 1
        bpy.ops.mustardui.delete_outfit(is_config=True)
        self.assertEqual(
            [x.collection.name for x in self.rig_settings.outfits_collections], ["Tester Casual"]
        )
        self.assertNotIn("Formal - Dress", bpy.data.objects)


class TestAddOutfit(BlenderTestCase):
    def setUp(self):
        super().setUp()
        self.model = build_model()
        self.rig_settings = configure_model(self.model)
        settings = bpy.context.scene.MustardUI_Settings
        settings.viewport_model_selection = False
        settings.panel_model_selection_armature = self.model["armature"].data

        # Body Shape Key growing the body
        body = self.model["body"]
        grow = body.shape_key_add(name="Grow", from_mix=False)
        for d in grow.data:
            d.co *= 1.1

        # Pieces to add, one clipping through the body
        coll = new_collection("Import")
        self.top = new_mesh_object("GO Top Mesh", coll, size=0.52)
        self.belt = new_mesh_object("GO Belt Mesh", coll, size=0.49)
        bm = bmesh.new()
        bm.from_mesh(self.belt.data)
        bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=4, use_grid_fill=True)
        bm.to_mesh(self.belt.data)
        bm.free()
        self.select(self.top, self.belt)

    def select(self, *objs):
        bpy.context.view_layer.update()
        for obj in bpy.context.view_layer.objects:
            obj.select_set(obj in objs)
        bpy.context.view_layer.objects.active = objs[-1]

    def visible(self, name):
        obj = bpy.data.objects[name]
        return not obj.hide_viewport and not obj.hide_render

    def weights(self, obj, name):
        vg = obj.vertex_groups[name]
        return [g.weight for v in obj.data.vertices for g in v.groups if g.group == vg.index]

    # New outfit with renamed and bound pieces, weights and Shape Keys from the body
    def test_new_outfit(self):
        bpy.ops.mustardui.model_toolkit_add_outfit(outfit_name="Sporty", fit="NONE")

        coll = bpy.data.collections["Tester Sporty"]
        self.assertIn(coll, [x.collection for x in self.rig_settings.outfits_collections])
        self.assertEqual(self.rig_settings.outfits_list, "Tester Sporty")
        self.assertNotIn("Import", bpy.data.collections)
        self.assertEqual(
            sorted(o.name for o in coll.objects), ["Tester Sporty - Belt", "Tester Sporty - Top"]
        )
        self.assertEqual(self.top.data.name, "Tester Sporty - Top")

        arm = self.model["armature"]
        self.assertEqual(self.top.parent, arm)
        self.assertEqual(self.top.modifiers["Armature"].object, arm)

        np.testing.assert_allclose(self.weights(self.top, "spine"), 1.0)

        sks = self.top.data.shape_keys
        self.assertIn("Grow", sks.key_blocks)
        self.assertNotIn("Smile", sks.key_blocks)
        self.assertIsNotNone(sks.animation_data.drivers.find('key_blocks["Grow"].value'))

    # The pieces clipping through the body are pushed out, close to it
    def test_fit(self):
        # Outward normals, as the fit needs them to find the inside of the body
        mesh = self.model["body"].data
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(mesh)
        bm.free()

        bpy.ops.mustardui.model_toolkit_add_outfit(outfit_name="Sporty", fit="MESH")
        outside = self.belt_outside()
        self.assertGreater(outside.min(), 0.5)
        # The smoothing rounds the belt over the sharp edges of the box
        self.assertLess(outside.max(), 0.56)

    # Distance of the belt vertices from the body center, along the axis closest to its faces
    def belt_outside(self):
        co = np.array([v.co for v in self.belt.data.vertices]) - (0.0, 0.0, 1.0)
        return np.abs(co).max(axis=1)

    # Existing Vertex Groups and Shape Keys are kept, unless overwritten
    def test_overwrite(self):
        self.top.vertex_groups.new(name="spine").add(range(8), 0.3, "REPLACE")
        self.top.shape_key_add(name="Basis")
        self.top.shape_key_add(name="Grow", from_mix=False)

        bpy.ops.mustardui.model_toolkit_add_outfit(outfit_name="Sporty", fit="NONE")
        np.testing.assert_allclose(self.weights(self.top, "spine"), 0.3)
        # No second group for the same bone
        self.assertEqual([vg.name for vg in self.top.vertex_groups], ["spine"])
        grow = self.top.data.shape_keys.key_blocks["Grow"]
        self.assertEqual(grow.data[0].co, self.top.data.vertices[0].co)

        self.select(self.top)
        bpy.ops.mustardui.model_toolkit_add_outfit(
            destination="OUTFIT",
            outfit="Tester Sporty",
            fit="NONE",
            overwrite_weights=True,
            overwrite_shape_keys=True,
        )
        np.testing.assert_allclose(self.weights(self.top, "spine"), 1.0)
        self.assertNotEqual(grow.data[0].co, self.top.data.vertices[0].co)

    # Body Shape Keys driven by other outfits are not transferred
    def test_outfit_shape_keys(self):
        body = self.model["body"]
        shirt = bpy.data.objects["Casual - Shirt"]
        shirt.shape_key_add(name="Basis")
        shirt.shape_key_add(name="Tight", from_mix=False)
        fix = body.shape_key_add(name="Shirt Fix", from_mix=False)
        for d in fix.data:
            d.co *= 0.9
        var = fix.driver_add("value").driver.variables.new()
        var.targets[0].id_type = "KEY"
        var.targets[0].id = shirt.data.shape_keys
        var.targets[0].data_path = 'key_blocks["Tight"].value'

        bpy.ops.mustardui.model_toolkit_add_outfit(outfit_name="Sporty", fit="NONE")
        sks = self.top.data.shape_keys.key_blocks
        self.assertIn("Grow", sks)
        self.assertNotIn("Shirt Fix", sks)

    # The fit uses the default settings, not the ones changed in the Fit to Body tool
    def test_fit_default_settings(self):
        settings = bpy.context.window_manager.MustardUI_ModelToolkit_FitToBodySettings
        settings.stiffness = 7.0
        settings.self_collisions = False
        settings.fit_distance = 0.03
        used = {}

        class Solver(add_outfit.FitToBodySolver):
            def solve(self, context, settings):
                used.update(
                    stiffness=settings.stiffness,
                    collisions=settings.self_collisions,
                    pull=settings.fit_distance,
                    smooth=settings.smooth_distance,
                )
                return super().solve(context, settings)

        original = add_outfit.FitToBodySolver
        add_outfit.FitToBodySolver = Solver
        try:
            bpy.ops.mustardui.model_toolkit_add_outfit(
                outfit_name="Sporty", fit="MESH", fit_smooth=0.03
            )
        finally:
            add_outfit.FitToBodySolver = original

        self.assertAlmostEqual(used["stiffness"], 1.0)
        self.assertTrue(used["collisions"])
        self.assertAlmostEqual(used["pull"], 0.01)
        self.assertAlmostEqual(used["smooth"], 0.03)
        # The Fit to Body settings are kept
        self.assertAlmostEqual(settings.stiffness, 7.0)
        self.assertFalse(settings.self_collisions)
        self.assertAlmostEqual(settings.fit_distance, 0.03)

    # Corrective Smooth and Shrinkwrap are added after the Armature only if requested
    def test_modifiers(self):
        self.top.modifiers.new("Subsurf", "SUBSURF")
        self.belt.modifiers.new("Existing", "SHRINKWRAP")
        bpy.ops.mustardui.model_toolkit_add_outfit(outfit_name="Sporty", fit="NONE")
        self.assertEqual([m.type for m in self.top.modifiers], ["ARMATURE", "SUBSURF"])

        self.select(self.top, self.belt)
        bpy.ops.mustardui.model_toolkit_add_outfit(
            destination="OUTFIT",
            outfit="Tester Sporty",
            fit="NONE",
            add_smooth=True,
            add_shrinkwrap=True,
        )
        self.assertEqual(
            [m.type for m in self.top.modifiers],
            ["ARMATURE", "CORRECTIVE_SMOOTH", "SHRINKWRAP", "SUBSURF"],
        )
        shrinkwrap = self.top.modifiers["Shrinkwrap"]
        self.assertEqual(shrinkwrap.target, self.model["body"])
        self.assertEqual(shrinkwrap.wrap_mode, "OUTSIDE")
        # The existing Shrinkwrap is not duplicated
        self.assertEqual([m.type for m in self.belt.modifiers].count("SHRINKWRAP"), 1)

    # Meshes parented to a piece follow it, and are named after it
    def test_children(self):
        button = new_mesh_object("GO Top Button", self.top.users_collection[0], size=0.02)
        button.parent = self.top
        self.select(self.top, button, self.belt)

        bpy.ops.mustardui.model_toolkit_add_outfit(outfit_name="Sporty", fit="MESH")
        self.assertEqual(button.name, "Tester Sporty - Top Button")
        self.assertEqual(button.parent, self.top)
        self.assertIn(button, bpy.data.collections["Tester Sporty"].objects[:])
        self.assertFalse([m for m in button.modifiers if m.type == "ARMATURE"])
        self.assertEqual(len(button.vertex_groups), 0)
        self.assertIsNone(button.data.shape_keys)

    # The dialog lists are not saved in the file, and the pieces one is emptied at the end
    def test_dialog_lists_not_saved(self):
        add_outfit.add_outfit_fill_lists(bpy.context)
        bpy.ops.mustardui.model_toolkit_add_outfit(outfit_name="Sporty", fit="NONE")
        wm = bpy.context.window_manager
        self.assertEqual(len(wm.MustardUI_ModelToolkit_AddOutfit_Items), 0)
        self.assertGreater(len(wm.MustardUI_ModelToolkit_AddOutfit_ShapeKeys), 0)
        scene = bpy.context.scene
        self.assertFalse(hasattr(scene, "MustardUI_ModelToolkit_AddOutfit_Items"))
        self.assertFalse(hasattr(scene, "MustardUI_ModelToolkit_AddOutfit_ShapeKeys"))
        self.assertFalse(hasattr(scene, "MustardUI_ModelToolkit_TransferShapeKeys_Items"))
        self.assertFalse(hasattr(scene, "MustardUI_ModelToolkit_TransferVertexGroups_Items"))

    # Emptied collections used by MustardUI are kept, the others removed
    def test_emptied_collections(self):
        casual = self.model["outfits"][0].name
        hair = self.model["hair"].name
        self.select(
            self.top, self.belt, *self.model["outfits"][0].objects, *self.model["hair"].objects
        )

        bpy.ops.mustardui.model_toolkit_add_outfit(outfit_name="Sporty", fit="NONE")

        self.assertNotIn("Import", bpy.data.collections)
        self.assertIn(casual, bpy.data.collections)
        self.assertIn(hair, bpy.data.collections)
        self.assertEqual(self.rig_settings.outfits_collections[0].collection.name, casual)
        self.assertEqual(self.rig_settings.hair_collection.name, hair)

    # Cancelling restores the pieces, their children and their meshes
    def test_backup_restore(self):
        button = new_mesh_object("GO Top Button", self.top.users_collection[0], size=0.02)
        button.parent = self.top
        mesh_name = self.top.data.name
        co = [v.co.copy() for v in self.top.data.vertices]
        counts = (len(bpy.data.meshes), len(bpy.data.shape_keys))

        backup = add_outfit.PiecesBackup([self.top, self.belt])
        arm = self.model["armature"]
        add_outfit.bind_to_armature(self.top, arm)
        add_outfit.transfer_weights(bpy.context, self.model["body"], arm, self.top, False)
        self.top.shape_key_add(name="Basis")
        self.top.data.vertices[0].co.x += 1.0
        button.shape_key_add(name="Basis")
        backup.restore()

        self.assertIsNone(self.top.parent)
        self.assertEqual(len(self.top.modifiers), 0)
        self.assertEqual(len(self.top.vertex_groups), 0)
        self.assertIsNone(self.top.data.shape_keys)
        self.assertIsNone(button.data.shape_keys)
        self.assertEqual(self.top.data.name, mesh_name)
        self.assertEqual([v.co for v in self.top.data.vertices], co)
        self.assertEqual((len(bpy.data.meshes), len(bpy.data.shape_keys)), counts)

        # Discarded after a completed run, without leftovers
        add_outfit.PiecesBackup([self.top, self.belt]).discard()
        self.assertEqual(len(bpy.data.meshes), counts[0])

    # A failing step restores the pieces, like cancelling
    def test_failure_restores(self):
        settings = bpy.context.window_manager.MustardUI_ModelToolkit_FitToBodySettings
        settings.stiffness = 7.0
        meshes = len(bpy.data.meshes)

        class Solver(add_outfit.FitToBodySolver):
            def solve(self, context, settings):
                raise ValueError("Test failure")

        original = add_outfit.FitToBodySolver
        add_outfit.FitToBodySolver = Solver
        try:
            with self.assertRaises(RuntimeError):
                bpy.ops.mustardui.model_toolkit_add_outfit(outfit_name="Sporty", fit="MESH")
        finally:
            add_outfit.FitToBodySolver = original
        # The expected error is printed
        self._stderr.buffer.seek(0)
        self._stderr.buffer.truncate()

        self.assertIsNone(self.top.parent)
        self.assertEqual(len(self.top.modifiers), 0)
        self.assertEqual(len(self.top.vertex_groups), 0)
        self.assertIsNone(self.top.data.shape_keys)
        self.assertEqual(len(bpy.data.meshes), meshes)
        self.assertAlmostEqual(settings.stiffness, 7.0)

    # The model is Nude while adding, then the previous Outfit is restored for the Extras
    def test_nude_while_adding(self):
        self.rig_settings.outfits_list = "Tester Casual"
        shown = []

        class Solver(add_outfit.FitToBodySolver):
            def solve(solver, context, settings):
                shown.append((self.rig_settings.outfits_list, self.visible("Casual - Shirt")))
                return super().solve(context, settings)

        original = add_outfit.FitToBodySolver
        add_outfit.FitToBodySolver = Solver
        try:
            bpy.ops.mustardui.model_toolkit_add_outfit(destination="EXTRAS", fit="MESH")
        finally:
            add_outfit.FitToBodySolver = original

        self.assertEqual(shown[0], ("Nude", False))
        self.assertEqual(self.rig_settings.outfits_list, "Tester Casual")
        self.assertTrue(self.visible("Casual - Shirt"))

    # Pieces can be added to the Extras
    def test_extras(self):
        bpy.ops.mustardui.model_toolkit_add_outfit(destination="EXTRAS", fit="NONE")
        self.assertIn(self.top, self.model["extras"].objects[:])
        self.assertEqual(self.top.name, "Tester Extras - Top")
        self.assertEqual(len(self.rig_settings.outfits_collections), 2)

    # A new outfit with the name of an existing collection gets a number suffix
    def test_existing_name(self):
        # The emptied collection of the pieces frees its name
        self.top.users_collection[0].name = "Tester Casual.001"
        bpy.ops.mustardui.model_toolkit_add_outfit(outfit_name="Casual", fit="NONE")
        self.assertEqual(self.top.users_collection[0].name, "Tester Casual.001")
        self.assertEqual(self.top.name, "Tester Casual.001 - Top")
        self.assertEqual(len(self.model["outfits"][0].objects), 2)

    # The dialog lists the pieces and the body Shape Keys, and draws valid properties
    def test_dialog(self):
        coll_name = add_outfit.add_outfit_fill_lists(bpy.context)
        self.assertEqual(coll_name, "Import")

        wm = bpy.context.window_manager
        pieces = {i.object_name: i.name for i in wm.MustardUI_ModelToolkit_AddOutfit_Items}
        self.assertEqual(pieces, {"GO Top Mesh": "Top", "GO Belt Mesh": "Belt"})
        keys = [i.name for i in wm.MustardUI_ModelToolkit_AddOutfit_ShapeKeys]
        self.assertEqual(keys, ["Smile", "Blink", "Blink.L", "Blink.R", "Grow"])

        cls = bpy.types.MUSTARDUI_OT_model_toolkit_add_outfit
        drawer = Drawer()
        for destination in ("NEW", "OUTFIT", "EXTRAS"):
            op = FakeSelf(
                cls,
                FakeLayout(drawer),
                bl_rna=bpy.ops.mustardui.model_toolkit_add_outfit.get_rna_type(),
                destination=destination,
                split=False,
                fit="MESH",
                transfer_weights=True,
                transfer_shape_keys=True,
            )
            drawer.run("draw", cls.draw, op, bpy.context)

        cls = bpy.types.MUSTARDUI_OT_model_toolkit_add_outfit_from_file
        op = FakeSelf(
            cls,
            FakeLayout(drawer),
            bl_rna=bpy.ops.mustardui.model_toolkit_add_outfit_from_file.get_rna_type(),
            destination="NEW",
            split=False,
            fit="NONE",
            transfer_weights=True,
            transfer_shape_keys=True,
        )
        drawer.run("draw", cls.draw, op, bpy.context)
        self.assertEqual(drawer.errors, [])

    # With One Outfit per Collection, each collection of the pieces becomes an Outfit
    def test_split(self):
        self.belt.users_collection[0].objects.unlink(self.belt)
        new_collection("Beach").objects.link(self.belt)
        bpy.ops.mustardui.model_toolkit_add_outfit(split=True, fit="NONE")

        names = {x.collection.name for x in self.rig_settings.outfits_collections}
        self.assertEqual(names, {"Tester Casual", "Tester Formal", "Tester Import", "Tester Beach"})
        self.assertEqual(self.top.name, "Tester Import - Top")
        self.assertEqual(self.belt.name, "Tester Beach - Belt")
        self.assertNotIn("Import", bpy.data.collections)
        self.assertNotIn("Beach", bpy.data.collections)

    # Source file with two outfits bound to their own, hidden armature
    def write_source(self):
        rig = new_object("Source Rig", bpy.data.armatures.new("Source Rig"))
        colls = [new_collection("Other Sporty"), new_collection("Other Beach")]
        for coll, name in zip(colls, ("Shorts", "Hat"), strict=True):
            obj = new_mesh_object(f"{coll.name} - {name}", coll, size=0.52)
            obj.parent = rig
            obj.modifiers.new("Armature", "ARMATURE").object = rig
            obj.hide_viewport = True
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        path = os.path.join(folder, "source.blend")
        bpy.data.libraries.write(path, set(colls))
        objs = [o for c in colls for o in c.objects]
        bpy.data.batch_remove([*objs, *(o.data for o in objs), rig, rig.data, *colls])
        return path

    # Collections appended from another file are added bound to the model armature
    def test_from_file(self):
        path = self.write_source()
        bpy.ops.mustardui.model_toolkit_add_outfit_from_file(
            directory=os.path.join(path, "Collection", ""),
            files=[{"name": "Other Sporty"}, {"name": "Other Beach"}],
            split=True,
            fit="NONE",
        )
        arm = self.model["armature"]
        shorts = bpy.data.objects["Tester Other Sporty - Shorts"]
        self.assertNotIn("Source Rig", bpy.data.objects)
        self.assertNotIn("Source Rig", bpy.data.armatures)
        self.assertEqual(shorts.parent, arm)
        self.assertEqual(shorts.modifiers["Armature"].object, arm)
        self.assertTrue(shorts.visible_get())
        self.assertIn(shorts, bpy.data.collections["Tester Other Sporty"].objects[:])
        self.assertIn(
            "Tester Other Beach - Hat", bpy.data.collections["Tester Other Beach"].objects
        )
        self.assertNotIn("Other Sporty", bpy.data.collections)
        # The pieces of the scene are not changed
        self.assertIsNone(self.top.parent)

    # Appended piece with drivers to the source body and armature, returning its drivers
    def append_driven(self):
        rig = new_object("Source Rig", bpy.data.armatures.new("Source Rig"))
        rig.data["Outfit Sporty"] = 1.0
        body = new_mesh_object("Source Body", size=0.5)
        for name in ("Basis", "Blink", "Missing"):
            body.shape_key_add(name=name, from_mix=False)
        rig.data.MustardUI_RigSettings.model_body = body
        coll = new_collection("Other Sporty")
        shorts = new_mesh_object("Other Sporty - Shorts", coll, size=0.52)
        shorts.modifiers.new("Armature", "ARMATURE").object = rig
        shorts.shape_key_add(name="Basis")
        for name, id_type, id_data, path in (
            ("Blink", "KEY", body.data.shape_keys, 'key_blocks["Blink"].value'),
            ("Missing", "KEY", body.data.shape_keys, 'key_blocks["Missing"].value'),
            ("Outfit", "ARMATURE", rig.data, '["Outfit Sporty"]'),
        ):
            sk = shorts.shape_key_add(name=name, from_mix=False)
            var = sk.driver_add("value").driver.variables.new()
            var.targets[0].id_type = id_type
            var.targets[0].id = id_data
            var.targets[0].data_path = path
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        path = os.path.join(folder, "source.blend")
        bpy.data.libraries.write(path, {coll})
        bpy.data.batch_remove([shorts, shorts.data, body, body.data, rig, rig.data, coll])

        bpy.ops.mustardui.model_toolkit_add_outfit_from_file(
            directory=os.path.join(path, "Collection", ""),
            files=[{"name": "Other Sporty"}],
            fit="NONE",
            transfer_shape_keys=False,
        )
        shorts = bpy.data.objects["Tester Other Sporty - Shorts"]
        return {
            fc.data_path: fc.driver.variables[0].targets[0].id
            for fc in shorts.data.shape_keys.animation_data.drivers
        }

    # Drivers using something missing in this file are removed
    def test_from_file_broken_drivers(self):
        drivers = self.append_driven()
        self.assertEqual(drivers, {'key_blocks["Blink"].value': self.model["body"].data.shape_keys})

    # Appended MustardUI model with Outfit custom properties, returning the model ones added
    def append_custom_properties(self):
        cp_misc = importlib.import_module(ADDON + ".custom_properties.misc")
        rig = new_object("Source Rig", bpy.data.armatures.new("Source Rig"))
        body = new_mesh_object("Source Body", size=0.5)
        for name in ("Basis", "Fix"):
            body.shape_key_add(name=name, from_mix=False)
        rig.data.MustardUI_RigSettings.model_body = body
        coll = new_collection("Other Sporty")
        shorts = new_mesh_object("Other Sporty - Shorts", coll, size=0.52)
        shorts.modifiers.new("Armature", "ARMATURE").object = rig
        for name in ("Basis", "Tight", "Loose"):
            shorts.shape_key_add(name=name, from_mix=False)

        # Piece property with a pointer, Outfit one without, and one driving the body
        for name, key, piece, pointer in (
            ("Tight", shorts.data.shape_keys, shorts, True),
            ("Loose", shorts.data.shape_keys, None, False),
            ("Fix", body.data.shape_keys, shorts, True),
        ):
            rna = f'bpy.data.shape_keys["{key.name}"].key_blocks["{name}"]'
            rig.data[name] = 0.7
            cp_misc.mustardui_add_driver(rig.data, rna, "value", name, 0)
            cp = rig.data.MustardUI_CustomPropertiesOutfit.add()
            cp.name, cp.prop_name, cp.rna, cp.path = name, name, rna, "value"
            cp.type, cp.is_animatable, cp.cp_type = "FLOAT", True, "OUTFIT"
            cp.outfit, cp.outfit_piece = coll, piece
            if pointer:
                cp.ptr_type, cp.ptr_key = "SHAPEKEY", key

        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        path = os.path.join(folder, "source.blend")
        bpy.data.libraries.write(path, {coll})
        bpy.data.batch_remove([shorts, shorts.data, body, body.data, rig, rig.data, coll])

        arm = self.model["armature"].data
        # Name taken by a property of the model
        arm["Tight"] = 0.5
        start = len(arm.MustardUI_CustomPropertiesOutfit)
        bpy.ops.mustardui.model_toolkit_add_outfit_from_file(
            directory=os.path.join(path, "Collection", ""),
            files=[{"name": "Other Sporty"}],
            fit="NONE",
            transfer_shape_keys=False,
        )
        return {cp.name: cp for cp in list(arm.MustardUI_CustomPropertiesOutfit)[start:]}

    # The Outfit custom properties of the appended pieces are added to the model
    def test_from_file_custom_properties(self):
        cps = self.append_custom_properties()
        arm = self.model["armature"].data
        shorts = bpy.data.objects["Tester Other Sporty - Shorts"]
        outfit = bpy.data.collections["Tester Other Sporty"]
        self.assertEqual(set(cps), {"Tight", "Loose"})
        self.assertNotIn("Other Sporty", bpy.data.collections)

        tight = cps["Tight"]
        self.assertEqual((tight.outfit, tight.outfit_piece), (outfit, shorts))
        self.assertEqual(tight.prop_name, "Tight 2")
        self.assertIn(f'bpy.data.shape_keys["{shorts.data.shape_keys.name}"]', tight.rna)
        self.assertAlmostEqual(arm["Tight 2"], 0.7)
        self.assertAlmostEqual(arm["Tight"], 0.5)
        drivers = shorts.data.shape_keys.animation_data.drivers
        target = drivers.find('key_blocks["Tight"].value').driver.variables[0].targets[0]
        self.assertEqual((target.id, target.data_path), (arm, '["Tight 2"]'))
        # The imported property drives the Shape Key
        arm["Tight 2"] = 0.2
        arm.update_tag()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        depsgraph.update()
        key = shorts.data.shape_keys.evaluated_get(depsgraph)
        self.assertAlmostEqual(key.key_blocks["Tight"].value, 0.2, places=5)

        loose = cps["Loose"]
        self.assertEqual((loose.outfit, loose.outfit_piece), (outfit, None))
        self.assertEqual(loose.prop_name, "Loose")
        self.assertIsNotNone(drivers.find('key_blocks["Loose"].value'))
        self.assertNotIn("Fix", arm.keys())

    # Outfit custom properties follow the pieces, with the paths updated after the renaming
    def test_custom_properties_follow_pieces(self):
        arm = self.model["armature"].data
        self.top.shape_key_add(name="Basis")
        self.top.shape_key_add(name="Tight", from_mix=False)
        rna = f'bpy.data.objects["{self.top.name}"].data.shape_keys.key_blocks["Tight"]'
        for name, piece in (("Tight", self.top), ("Loose", None)):
            cp = arm.MustardUI_CustomPropertiesOutfit.add()
            cp.name, cp.rna, cp.path = name, rna, "value"
            cp.outfit, cp.outfit_piece = self.top.users_collection[0], piece

        bpy.ops.mustardui.model_toolkit_add_outfit(outfit_name="Sporty", fit="NONE")
        outfit = bpy.data.collections["Tester Sporty"]
        cps = {cp.name: cp for cp in arm.MustardUI_CustomPropertiesOutfit}
        self.assertEqual(cps["Tight"].outfit, outfit)
        self.assertEqual(cps["Loose"].outfit, outfit)
        self.assertTrue(cps["Tight"].rna.startswith('bpy.data.objects["Tester Sporty - Top"]'))
        self.assertNotIn("Import", bpy.data.collections)

    # Surface Deform and Corrective Smooth modifiers are bound again, in rest pose
    def test_rebind_modifiers(self):
        deform = self.top.modifiers.new("SurfaceDeform", "SURFACE_DEFORM")
        deform.target = self.model["body"]
        smooth = self.top.modifiers.new("CorrectiveSmooth", "CORRECTIVE_SMOOTH")
        smooth.rest_source = "BIND"
        self.assertFalse(deform.is_bound or smooth.is_bind)
        arm = self.model["armature"].data
        arm.pose_position = "POSE"

        bpy.ops.mustardui.model_toolkit_add_outfit(outfit_name="Sporty", fit="NONE")
        self.assertTrue(deform.is_bound)
        self.assertTrue(smooth.is_bind)
        self.assertEqual(arm.pose_position, "POSE")

        # Bound ones are bound again
        self.select(self.top)
        bpy.ops.mustardui.model_toolkit_add_outfit(
            destination="OUTFIT", outfit="Tester Sporty", fit="NONE"
        )
        self.assertTrue(deform.is_bound and smooth.is_bind)

    # The own armature of a piece is moved with it, the model one is not
    def test_own_armature(self):
        coll = self.belt.users_collection[0]
        rig = new_object("GO Wing Rig", bpy.data.armatures.new("GO Wing Rig"), coll)
        self.belt.parent = rig
        self.top.parent = self.model["armature"]
        bpy.ops.mustardui.model_toolkit_add_outfit(outfit_name="Sporty", fit="NONE")

        outfit = bpy.data.collections["Tester Sporty"]
        self.assertEqual(list(rig.users_collection), [outfit])
        self.assertEqual(self.belt.parent, rig)
        self.assertNotIn(outfit, self.model["armature"].users_collection)
        self.assertNotIn("Import", bpy.data.collections)


def outward_normals(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()


class TestSquishOutfitProperty(BlenderTestCase):
    def setUp(self):
        super().setUp()
        self.model = build_model()
        self.rig_settings = configure_model(self.model)
        self.rig_settings.outfits_list = "Tester Casual"
        self.body = self.model["body"]
        # The shirt inside the body, squishing it
        self.shirt = bpy.data.objects["Casual - Shirt"]
        for v in self.shirt.data.vertices:
            v.co = (v.co.x * 0.88, v.co.y * 0.88, 1.0 + (v.co.z - 1.0) * 0.88)
        for obj in (self.body, self.shirt):
            outward_normals(obj)

        settings = bpy.context.window_manager.MustardUI_ModelToolkit_SquishSettings
        for name in ("outfit_property", "shape_key_name"):
            self.addCleanup(setattr, settings, name, getattr(settings, name))
        settings.outfit_property = True
        settings.shape_key_name = "Squish Shirt"

    def squish(self, squisher):
        for obj in bpy.context.view_layer.objects:
            obj.select_set(obj in (self.body, squisher))
        bpy.context.view_layer.objects.active = self.body
        self.assertEqual(bpy.ops.mustardui.model_toolkit_squish(), {"FINISHED"})

    def outfit_property(self):
        arm = self.model["armature"].data
        return next((cp for cp in arm.MustardUI_CustomPropertiesOutfit if cp.path == "value"), None)

    # The squish is driven by a hidden property of the Outfit piece, switched with it
    def test_outfit_property(self):
        self.squish(self.shirt)

        cp = self.outfit_property()
        self.assertIsNotNone(cp)
        self.assertTrue(cp.hidden)
        self.assertEqual(cp.outfit, self.model["outfits"][0])
        self.assertEqual(cp.outfit_piece, self.shirt)
        self.assertTrue(cp.outfit_enable_on_switch and cp.outfit_disable_on_switch)
        drivers = self.body.data.shape_keys.animation_data.drivers
        self.assertIsNotNone(drivers.find('key_blocks["Squish Shirt"].value'))

        arm = self.model["armature"].data
        self.assertEqual(arm[cp.prop_name], 1.0)
        self.rig_settings.outfits_list = "Tester Formal"
        self.assertEqual(arm[cp.prop_name], 0.0)
        self.rig_settings.outfits_list = "Tester Casual"
        self.assertEqual(arm[cp.prop_name], 1.0)

    # Squishers not in an Outfit of the model do not get the property
    def test_not_outfit(self):
        other = new_mesh_object("Other", size=0.484)
        outward_normals(other)
        self.assertEqual(squish.squish_outfit(self.body, [other]), (None, None))
        self.assertEqual(squish.squish_outfit(self.body, [other, self.shirt]), (None, None))

        self.squish(other)
        self.assertIn("Squish Shirt", self.body.data.shape_keys.key_blocks)
        self.assertIsNone(self.outfit_property())


def select_model(model):
    settings = bpy.context.scene.MustardUI_Settings
    settings.viewport_model_selection = False
    settings.panel_model_selection_armature = model["armature"].data


def add_outfit_custom_property(arm, name, rna, path, piece, key=None):
    """Outfit custom property of the piece, driving the property at rna.path"""

    arm[name] = 0.7
    cp_misc.mustardui_add_driver(arm, rna, path, name, 0)
    cp = arm.MustardUI_CustomPropertiesOutfit.add()
    cp.name, cp.prop_name, cp.rna, cp.path = name, name, rna, path
    cp.type, cp.is_animatable, cp.cp_type = "FLOAT", True, "OUTFIT"
    cp.outfit, cp.outfit_piece = piece.users_collection[0], piece
    if key is not None:
        cp.ptr_type, cp.ptr_key = "SHAPEKEY", key


class TestExportOutfits(BlenderTestCase):
    def setUp(self):
        super().setUp()
        self.model = build_model()
        configure_model(self.model)
        select_model(self.model)
        arm = self.model["armature"].data
        body_keys = self.model["body"].data.shape_keys
        shirt = bpy.data.objects["Casual - Shirt"]

        # Shape Key of the shirt, linked to the body one
        shirt.shape_key_add(name="Basis")
        keys = shirt.data.shape_keys
        for name in ("Tight", "Smile"):
            shirt.shape_key_add(name=name, from_mix=False)
        link = keys.key_blocks["Smile"].driver_add("value").driver.variables.new()
        link.targets[0].id = self.model["body"]
        link.targets[0].data_path = 'data.shape_keys.key_blocks["Smile"].value'

        material = bpy.data.materials.new("Shirt Material")
        material.use_nodes = True
        shirt.data.materials.append(material)

        # Custom properties of the shirt, of the body and of the material
        rna = f'bpy.data.shape_keys["{keys.name}"].key_blocks["Tight"]'
        add_outfit_custom_property(arm, "Tight", rna, "value", shirt, keys)
        rna = f'bpy.data.shape_keys["{body_keys.name}"].key_blocks["Blink"]'
        add_outfit_custom_property(arm, "Blink Fix", rna, "value", shirt, body_keys)
        rna = 'bpy.data.materials["Shirt Material"].node_tree.nodes["Principled BSDF"]'
        rna += '.inputs["Roughness"]'
        add_outfit_custom_property(arm, "Rough", rna, "default_value", shirt)

        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        self.path = os.path.join(folder, "outfits.blend")

    def export(self, *names, extras=(), **settings):
        export.export_fill_items(bpy.context)
        wm = bpy.context.window_manager
        for item in wm.MustardUI_ModelToolkit_ExportOutfits_Items:
            item.use = item.name in names
        for item in wm.MustardUI_ModelToolkit_ExportOutfits_Extras:
            item.use = item.name in extras
        return bpy.ops.mustardui.model_toolkit_export_outfits(filepath=self.path, **settings)

    # Only the chosen Outfits are written, with stand-ins of the armature and body
    def test_export(self):
        counts = {
            a: len(getattr(bpy.data, a))
            for a in (
                "objects",
                "meshes",
                "materials",
                "collections",
                "armatures",
                "shape_keys",
                "scenes",
            )
        }
        names = sorted(o.name for o in bpy.data.objects)
        self.assertEqual(self.export("Tester Casual"), {"FINISHED"})

        with bpy.data.libraries.load(self.path) as (source, _):
            self.assertEqual(set(source.collections), {"Tester Casual"})
            self.assertEqual(
                set(source.objects),
                {"Casual - Shirt", "Casual - Pants", "Tester Armature", "Tester Body"},
            )
            self.assertEqual(list(source.armatures), ["Tester Armature"])
            self.assertIn("Shirt Material", source.materials)
            self.assertNotIn("Tester Skin", source.materials)

        # The model is not changed
        after = {a: len(getattr(bpy.data, a)) for a in counts}
        self.assertEqual(after, counts)
        self.assertEqual(sorted(o.name for o in bpy.data.objects), names)
        shirt = bpy.data.objects["Casual - Shirt"]
        self.assertEqual(shirt.modifiers["Armature"].object, self.model["armature"])
        self.assertEqual(shirt.data.materials[0], bpy.data.materials["Shirt Material"])
        target = shirt.data.shape_keys.animation_data.drivers[0].driver.variables[0].targets[0]
        self.assertIn(target.id, (self.model["body"], self.model["armature"].data))

        # The stand-in armature has the custom properties and the stand-in body
        with bpy.data.libraries.load(self.path) as (_, target):
            target.objects = ["Tester Armature"]
        data = target.objects[0].data
        self.assertEqual(len(data.MustardUI_CustomPropertiesOutfit), 3)
        self.assertEqual(len(data.MustardUI_RigSettings.model_body.data.vertices), 0)

    # With Delete Exported, the exported Outfits and Extras pieces are deleted from the model
    def test_export_delete(self):
        rig_settings = self.model["armature"].data.MustardUI_RigSettings
        extras = self.model["extras"]
        lens = new_mesh_object("Extras - Lens", extras, size=0.1)
        lens.parent = bpy.data.objects["Extras - Glasses"]
        new_mesh_object("Extras - Hat", extras, armature=self.model["armature"])
        self.export("Tester Casual", "Tester Formal", extras=["Extras - Glasses"])
        self.assertEqual(len(rig_settings.outfits_collections), 2)

        self.export(
            "Tester Casual", "Tester Formal", extras=["Extras - Glasses"], delete_outfits=True
        )
        with bpy.data.libraries.load(self.path) as (source, _):
            self.assertIn("Casual - Shirt", source.objects)
            self.assertIn("Extras - Lens", source.objects)
        self.assertEqual(len(rig_settings.outfits_collections), 0)
        self.assertNotIn("Tester Casual", bpy.data.collections)
        self.assertNotIn("Casual - Shirt", bpy.data.objects)
        self.assertNotIn("Extras - Glasses", bpy.data.objects)
        self.assertNotIn("Extras - Lens", bpy.data.objects)
        self.assertIn("Extras - Hat", bpy.data.objects)
        self.assertEqual(rig_settings.extras_collection, extras)
        self.assertEqual(len(self.model["armature"].data.MustardUI_CustomPropertiesOutfit), 0)

    # Images of the Outfits are packed in the file, not in the model
    def test_export_pack_images(self):
        image = bpy.data.images.new("Shirt Texture", 4, 4)
        image.filepath_raw = os.path.join(os.path.dirname(self.path), "shirt.png")
        image.file_format = "PNG"
        image.save()
        image.source = "FILE"
        missing = bpy.data.images.new("missing.png", 4, 4)
        missing.source = "FILE"
        missing.filepath = os.path.join(os.path.dirname(self.path), "missing.png")
        nodes = bpy.data.materials["Shirt Material"].node_tree.nodes
        for img in (image, missing):
            nodes.new("ShaderNodeTexImage").image = img

        self.export("Tester Casual")
        self.assertIsNone(image.packed_file)
        with bpy.data.libraries.load(self.path) as (_, target):
            target.images = ["Shirt Texture", "missing.png"]
        exported, exported_missing = target.images
        self.assertIsNotNone(exported.packed_file)
        self.assertIsNone(exported_missing.packed_file)

        # Not packed if not requested
        export.export_fill_items(bpy.context)
        for item in bpy.context.window_manager.MustardUI_ModelToolkit_ExportOutfits_Items:
            item.use = item.name == "Tester Casual"
        bpy.ops.mustardui.model_toolkit_export_outfits(filepath=self.path, pack_images=False)
        with bpy.data.libraries.load(self.path) as (_, target):
            target.images = ["Shirt Texture"]
        self.assertIsNone(target.images[0].packed_file)

    # Outfits and Extras pieces are listed, with the shown Outfit chosen
    def test_export_items(self):
        self.model["armature"].data.MustardUI_RigSettings.outfits_list = "Tester Formal"
        export.export_fill_items(bpy.context)
        wm = bpy.context.window_manager
        items = {i.name: i.use for i in wm.MustardUI_ModelToolkit_ExportOutfits_Items}
        self.assertEqual(items, {"Tester Casual": False, "Tester Formal": True})
        extras = {i.name: i.use for i in wm.MustardUI_ModelToolkit_ExportOutfits_Extras}
        self.assertEqual(extras, {"Extras - Glasses": False})

        bpy.ops.mustardui.model_toolkit_export_outfits_select(use=True, extras=True)
        self.assertTrue(wm.MustardUI_ModelToolkit_ExportOutfits_Extras[0].use)
        self.assertFalse(wm.MustardUI_ModelToolkit_ExportOutfits_Items[0].use)

        cls = bpy.types.MUSTARDUI_OT_model_toolkit_export_outfits
        drawer = Drawer()
        op = FakeSelf(
            cls,
            FakeLayout(drawer),
            bl_rna=bpy.ops.mustardui.model_toolkit_export_outfits.get_rna_type(),
        )
        drawer.run("draw", cls.draw, op, bpy.context)
        self.assertEqual(drawer.errors, [])

    # Only the chosen Extras pieces are written, with the objects parented to them
    def test_export_extras(self):
        extras = self.model["extras"]
        glasses = bpy.data.objects["Extras - Glasses"]
        lens = new_mesh_object("Extras - Lens", extras, size=0.1)
        lens.parent = glasses
        new_mesh_object("Extras - Hat", extras, armature=self.model["armature"])

        self.assertEqual(self.export("Tester Casual", extras=["Extras - Glasses"]), {"FINISHED"})
        with bpy.data.libraries.load(self.path) as (source, _):
            self.assertEqual(set(source.collections), {"Tester Casual", "Tester Extras"})
            self.assertIn("Extras - Lens", source.objects)
            self.assertNotIn("Extras - Hat", source.objects)
        with bpy.data.libraries.load(self.path) as (_, target):
            target.collections = ["Tester Extras"]
        # Loaded next to the originals, so with a suffix
        names = {o.name.removesuffix(".001") for o in target.collections[0].objects}
        self.assertEqual(names, {"Extras - Glasses", "Extras - Lens", "Tester Armature"})

        # Only Extras
        self.assertEqual(self.export(extras=["Extras - Hat"]), {"FINISHED"})
        with bpy.data.libraries.load(self.path) as (source, _):
            self.assertEqual(list(source.collections), ["Tester Extras"])
            self.assertNotIn("Extras - Glasses", source.objects)

    # Each Outfit and Extras piece can be written in its own file, named after it
    def test_export_separate_files(self):
        new_mesh_object("Extras - Hat", self.model["extras"], armature=self.model["armature"])
        self.export(
            "Tester Casual", extras=["Extras - Glasses", "Extras - Hat"], separate_files=True
        )
        self.assertFalse(os.path.exists(self.path))
        folder = os.path.dirname(self.path)
        for name, coll, piece in (
            ("Casual", "Tester Casual", "Casual - Shirt"),
            ("Extras - Glasses", "Tester Extras", "Extras - Glasses"),
            ("Extras - Hat", "Tester Extras", "Extras - Hat"),
        ):
            path = os.path.join(folder, f"outfits - {name}.blend")
            with bpy.data.libraries.load(path) as (source, _):
                self.assertEqual(list(source.collections), [coll])
                self.assertEqual(list(source.armatures), ["Tester Armature"])
                self.assertIn(piece, source.objects)
                self.assertEqual(len(source.objects), 3 if piece.startswith("Extras") else 4)

    # The exported Outfit is added to another model with its custom properties
    def test_round_trip(self):
        pants = bpy.data.objects["Casual - Pants"]
        pants.modifiers.new("SurfaceDeform", "SURFACE_DEFORM").target = self.model["body"]
        self.export("Tester Casual")
        reset_scene()
        model = build_model("Other")
        configure_model(model, "Other")
        select_model(model)
        arm = model["armature"].data

        bpy.ops.mustardui.model_toolkit_add_outfit_from_file(
            directory=os.path.join(self.path, "Collection", ""),
            files=[{"name": "Tester Casual"}],
            fit="NONE",
            transfer_shape_keys=False,
        )
        outfit = bpy.data.collections["Other Casual.001"]
        shirt = bpy.data.objects["Other Casual.001 - Shirt"]
        self.assertEqual(shirt.parent, model["armature"])
        self.assertNotIn("Tester Armature", bpy.data.armatures)
        self.assertNotIn("Tester Body", bpy.data.objects)

        cps = {cp.name: cp for cp in arm.MustardUI_CustomPropertiesOutfit}
        self.assertEqual(set(cps), {"Tight", "Blink Fix", "Rough"})
        self.assertEqual({cps[n].outfit for n in cps}, {outfit})

        # The custom properties drive the outfit, its material and the body
        for name in cps:
            arm[name] = 0.25
        arm.update_tag()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        depsgraph.update()
        key = shirt.data.shape_keys.evaluated_get(depsgraph)
        self.assertAlmostEqual(key.key_blocks["Tight"].value, 0.25, places=5)
        body_key = model["body"].data.shape_keys.evaluated_get(depsgraph)
        self.assertAlmostEqual(body_key.key_blocks["Blink"].value, 0.25, places=5)
        material = shirt.data.materials[0].evaluated_get(depsgraph)
        roughness = material.node_tree.nodes["Principled BSDF"].inputs["Roughness"]
        self.assertAlmostEqual(roughness.default_value, 0.25, places=5)
        link = shirt.data.shape_keys.animation_data.drivers.find('key_blocks["Smile"].value')
        self.assertEqual(link.driver.variables[0].targets[0].id, model["body"])
        # Bound to the new body
        deform = bpy.data.objects["Other Casual.001 - Pants"].modifiers["SurfaceDeform"]
        self.assertEqual(deform.target, model["body"])
        self.assertTrue(deform.is_bound)

    # Pieces keep their transform relative to the model armature
    def test_round_trip_transform(self):
        self.model["armature"].scale = (0.01,) * 3
        shirt = bpy.data.objects["Casual - Shirt"]
        shirt.location, shirt.scale = (0.2, 0, 0), (0.5,) * 3
        bpy.context.view_layer.update()
        relative = self.model["armature"].matrix_world.inverted() @ shirt.matrix_world
        self.export("Tester Casual")
        reset_scene()
        model = build_model("Other")
        configure_model(model, "Other")
        select_model(model)
        model["armature"].location = (1, 0, 0)

        bpy.ops.mustardui.model_toolkit_add_outfit_from_file(
            directory=os.path.join(self.path, "Collection", ""),
            files=[{"name": "Tester Casual"}],
            fit="NONE",
            transfer_shape_keys=False,
        )
        shirt = bpy.data.objects["Other Casual.001 - Shirt"]
        bpy.context.view_layer.update()
        matrix = model["armature"].matrix_world.inverted() @ shirt.matrix_world
        self.assertLess(max(abs(v) for row in matrix - relative for v in row), 1e-5)

    # The armature of an Outfit is kept, the one of the model replaced
    def test_round_trip_own_armature(self):
        formal = self.model["outfits"][1]
        rig = new_object("Formal - Wing Rig", bpy.data.armatures.new("Wing Rig"), formal)
        dress = bpy.data.objects["Formal - Dress"]
        dress.parent = rig
        dress.modifiers["Armature"].object = rig
        self.export("Tester Formal")
        reset_scene()
        model = build_model("Other")
        configure_model(model, "Other")
        select_model(model)

        bpy.ops.mustardui.model_toolkit_add_outfit_from_file(
            directory=os.path.join(self.path, "Collection", ""),
            files=[{"name": "Tester Formal"}],
            fit="NONE",
            transfer_shape_keys=False,
        )
        outfit = bpy.data.collections["Other Formal.001"]
        rig = bpy.data.objects["Formal - Wing Rig"]
        dress = bpy.data.objects["Other Formal.001 - Dress"]
        self.assertEqual(list(rig.users_collection), [outfit])
        self.assertEqual((dress.parent, dress.modifiers["Armature"].object), (rig, rig))
        self.assertEqual(
            {o for o in bpy.data.objects if o.type == "ARMATURE"}, {model["armature"], rig}
        )
