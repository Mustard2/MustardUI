import importlib

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
)

add_outfit = importlib.import_module(ADDON + ".model_toolkit.model.ops_add_outfit")
squish = importlib.import_module(ADDON + ".model_toolkit.mesh.ops_squish")


class TestOutfits(BlenderTestCase):
    def setUp(self):
        super().setUp()
        self.model = build_model()
        self.rig_settings = configure_model(self.model)

    def visible(self, name):
        obj = bpy.data.objects[name]
        return not obj.hide_viewport and not obj.hide_render

    # Outfit list has Nude plus the outfit collections
    def test_outfit_list(self):
        items = [x[0] for x in self.rig_settings.outfits_list_make(bpy.context)]
        self.assertEqual(items, ["Nude", "Tester Casual", "Tester Formal"])

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

    def weights(self, obj, name):
        vg = obj.vertex_groups[name]
        return [g.weight for v in obj.data.vertices for g in v.groups if g.group == vg.index]

    # New outfit with renamed and bound pieces, weights and Shape Keys from the body
    def test_new_outfit(self):
        bpy.ops.mustardui.tools_creators_add_outfit(outfit_name="Sporty", fit="NONE")

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

        bpy.ops.mustardui.tools_creators_add_outfit(outfit_name="Sporty", fit="MESH")
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

        bpy.ops.mustardui.tools_creators_add_outfit(outfit_name="Sporty", fit="NONE")
        np.testing.assert_allclose(self.weights(self.top, "spine"), 0.3)
        # No second group for the same bone
        self.assertEqual([vg.name for vg in self.top.vertex_groups], ["spine"])
        grow = self.top.data.shape_keys.key_blocks["Grow"]
        self.assertEqual(grow.data[0].co, self.top.data.vertices[0].co)

        self.select(self.top)
        bpy.ops.mustardui.tools_creators_add_outfit(
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

        bpy.ops.mustardui.tools_creators_add_outfit(outfit_name="Sporty", fit="NONE")
        sks = self.top.data.shape_keys.key_blocks
        self.assertIn("Grow", sks)
        self.assertNotIn("Shirt Fix", sks)

    # The fit uses the default settings, not the ones changed in the Fit to Body tool
    def test_fit_default_settings(self):
        settings = bpy.context.window_manager.MustardUI_ToolsCreators_FitToBodySettings
        settings.relax_iterations = 7
        settings.refit_auto = False
        settings.fit_distance = 0.03
        used = {}

        class Solver(add_outfit.FitToBodySolver):
            def solve(self, context, settings):
                used.update(
                    relax=settings.relax_iterations,
                    auto=settings.refit_auto,
                    pull=settings.fit_distance,
                    smooth=settings.smooth_distance,
                )
                return super().solve(context, settings)

        original = add_outfit.FitToBodySolver
        add_outfit.FitToBodySolver = Solver
        try:
            bpy.ops.mustardui.tools_creators_add_outfit(
                outfit_name="Sporty", fit="MESH", fit_smooth=0.03
            )
        finally:
            add_outfit.FitToBodySolver = original

        self.assertEqual(used["relax"], 0)
        self.assertTrue(used["auto"])
        self.assertAlmostEqual(used["pull"], 0.01)
        self.assertAlmostEqual(used["smooth"], 0.03)
        # The Fit to Body settings are kept
        self.assertEqual(settings.relax_iterations, 7)
        self.assertFalse(settings.refit_auto)
        self.assertAlmostEqual(settings.fit_distance, 0.03)

    # Corrective Smooth and Shrinkwrap are added after the Armature only if requested
    def test_modifiers(self):
        self.top.modifiers.new("Subsurf", "SUBSURF")
        self.belt.modifiers.new("Existing", "SHRINKWRAP")
        bpy.ops.mustardui.tools_creators_add_outfit(outfit_name="Sporty", fit="NONE")
        self.assertEqual([m.type for m in self.top.modifiers], ["ARMATURE", "SUBSURF"])

        self.select(self.top, self.belt)
        bpy.ops.mustardui.tools_creators_add_outfit(
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

        bpy.ops.mustardui.tools_creators_add_outfit(outfit_name="Sporty", fit="MESH")
        self.assertEqual(button.name, "Tester Sporty - Top Button")
        self.assertEqual(button.parent, self.top)
        self.assertIn(button, bpy.data.collections["Tester Sporty"].objects[:])
        self.assertFalse([m for m in button.modifiers if m.type == "ARMATURE"])
        self.assertEqual(len(button.vertex_groups), 0)
        self.assertIsNone(button.data.shape_keys)

    # The dialog lists are not saved in the file, and the pieces one is emptied at the end
    def test_dialog_lists_not_saved(self):
        add_outfit.add_outfit_fill_lists(bpy.context)
        bpy.ops.mustardui.tools_creators_add_outfit(outfit_name="Sporty", fit="NONE")
        wm = bpy.context.window_manager
        self.assertEqual(len(wm.MustardUI_ToolsCreators_AddOutfit_Items), 0)
        self.assertGreater(len(wm.MustardUI_ToolsCreators_AddOutfit_ShapeKeys), 0)
        scene = bpy.context.scene
        self.assertFalse(hasattr(scene, "MustardUI_ToolsCreators_AddOutfit_Items"))
        self.assertFalse(hasattr(scene, "MustardUI_ToolsCreators_AddOutfit_ShapeKeys"))
        self.assertFalse(hasattr(scene, "MustardUI_ToolsCreators_TransferShapeKeys_Items"))
        self.assertFalse(hasattr(scene, "MustardUI_ToolsCreators_TransferVertexGroups_Items"))

    # Pieces can be added to the Extras
    def test_extras(self):
        bpy.ops.mustardui.tools_creators_add_outfit(destination="EXTRAS", fit="NONE")
        self.assertIn(self.top, self.model["extras"].objects[:])
        self.assertEqual(self.top.name, "Tester Extras - Top")
        self.assertEqual(len(self.rig_settings.outfits_collections), 2)

    # A new outfit can not reuse an existing collection
    def test_existing_name(self):
        with self.assertRaises(RuntimeError):
            bpy.ops.mustardui.tools_creators_add_outfit(outfit_name="Casual", fit="NONE")
        self.assertIsNone(self.top.parent)

    # The dialog lists the pieces and the body Shape Keys, and draws valid properties
    def test_dialog(self):
        coll_name = add_outfit.add_outfit_fill_lists(bpy.context)
        self.assertEqual(coll_name, "Import")

        wm = bpy.context.window_manager
        pieces = {i.object_name: i.name for i in wm.MustardUI_ToolsCreators_AddOutfit_Items}
        self.assertEqual(pieces, {"GO Top Mesh": "Top", "GO Belt Mesh": "Belt"})
        keys = [i.name for i in wm.MustardUI_ToolsCreators_AddOutfit_ShapeKeys]
        self.assertEqual(keys, ["Smile", "Blink", "Blink.L", "Blink.R", "Grow"])

        cls = bpy.types.MUSTARDUI_OT_tools_creators_add_outfit
        drawer = Drawer()
        for destination in ("NEW", "OUTFIT", "EXTRAS"):
            op = FakeSelf(
                cls,
                FakeLayout(drawer),
                bl_rna=bpy.ops.mustardui.tools_creators_add_outfit.get_rna_type(),
                destination=destination,
                fit="MESH",
                transfer_weights=True,
                transfer_shape_keys=True,
            )
            drawer.run("draw", cls.draw, op, bpy.context)
        self.assertEqual(drawer.errors, [])


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

        settings = bpy.context.window_manager.MustardUI_ToolsCreators_SquishSettings
        for name in ("outfit_property", "shape_key_name"):
            self.addCleanup(setattr, settings, name, getattr(settings, name))
        settings.outfit_property = True
        settings.shape_key_name = "Squish Shirt"

    def squish(self, squisher):
        for obj in bpy.context.view_layer.objects:
            obj.select_set(obj in (self.body, squisher))
        bpy.context.view_layer.objects.active = self.body
        self.assertEqual(bpy.ops.mustardui.tools_creators_squish(), {"FINISHED"})

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
