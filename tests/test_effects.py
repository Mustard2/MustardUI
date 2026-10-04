import importlib
import unittest

import bmesh
import bpy
import numpy as np
from helpers import (
    ADDON,
    BlenderTestCase,
    build_model,
    configure_model,
    new_object,
    set_active,
)

effect = importlib.import_module(ADDON + ".model_toolkit.effects.effect")


class TestDisintegration(BlenderTestCase):
    def setUp(self):
        super().setUp()
        configure_model(build_model())
        self.shirt = bpy.data.objects["Casual - Shirt"]
        self.pants = bpy.data.objects["Casual - Pants"]
        self.shirt.modifiers.new("Subdivision", "SUBSURF")
        set_active(self.shirt)
        self.pants.select_set(True)

    @unittest.skipIf(bpy.app.version >= (5, 2, 0), "Blender 5.2 supports the effects")
    def test_unavailable(self):
        self.assertFalse(bpy.ops.mustardui.model_toolkit_disintegration.poll())
        self.assertFalse(bpy.ops.mustardui.model_toolkit_ripple.poll())

    # The meshes are cut by the growing Control, and emit particles from the cut
    @unittest.skipUnless(effect.effects_available(), "Needs Blender 5.2")
    def test_disintegration(self):
        bpy.ops.mustardui.model_toolkit_disintegration(duration=10)
        self.assertEqual([m.type for m in self.shirt.modifiers], ["ARMATURE", "NODES", "SUBSURF"])
        modifier = self.shirt.modifiers["Disintegration"]
        control = effect.modifier_input(modifier, "Control").value
        self.assertEqual(control, effect.modifier_input(self.pants.modifiers[-1], "Control").value)
        self.assertEqual(control.MustardUI_tools_creators_type, "EFFECT_DISINTEGRATION")

        scene = bpy.context.scene
        depsgraph = bpy.context.evaluated_depsgraph_get()
        faces, points = [], []
        for frame in range(scene.frame_start, 13):
            scene.frame_set(frame)
            geometry = self.shirt.evaluated_get(depsgraph).evaluated_geometry()
            faces.append(len(geometry.mesh.polygons) if geometry.mesh else 0)
            points.append(len(geometry.pointcloud.points) if geometry.pointcloud else 0)
        self.assertGreater(faces[0], 0)
        self.assertEqual(faces[-1], 0)
        self.assertGreater(max(points), 0)
        self.assertIn("disintegration_age", geometry.pointcloud.attributes)

    # On open meshes, the faces of the cutter inside the mesh are not kept
    @unittest.skipUnless(effect.effects_available(), "Needs Blender 5.2")
    def test_open_mesh(self):
        mesh = bpy.data.meshes.new("Cup")
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=0.4)
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z > 0.2], context="VERTS")
        bm.to_mesh(mesh)
        bm.free()
        cup = new_object("Cup", mesh)
        set_active(cup)
        bpy.ops.mustardui.model_toolkit_disintegration(duration=10)

        scene = bpy.context.scene
        depsgraph = bpy.context.evaluated_depsgraph_get()
        for frame in range(scene.frame_start, 13):
            scene.frame_set(frame)
            data = cup.evaluated_get(depsgraph).data
            co = np.empty(len(data.vertices) * 3)
            data.vertices.foreach_get("co", co)
            distance = np.linalg.norm(co.reshape(-1, 3), axis=1)
            self.assertGreater(distance.min(initial=0.4), 0.39, f"frame {frame}")

    # The Control is removed with the last Disintegration using it
    @unittest.skipUnless(effect.effects_available(), "Needs Blender 5.2")
    def test_remove(self):
        bpy.ops.mustardui.model_toolkit_disintegration()
        control = effect.modifier_input(self.shirt.modifiers["Disintegration"], "Control").value
        name = control.name

        set_active(self.shirt)
        bpy.ops.mustardui.model_toolkit_remove_disintegration()
        self.assertNotIn("Disintegration", self.shirt.modifiers)
        self.assertIn(name, bpy.data.objects)

        set_active(self.pants)
        bpy.ops.mustardui.model_toolkit_remove_disintegration()
        self.assertNotIn("Disintegration", self.pants.modifiers)
        self.assertNotIn(name, bpy.data.objects)


@unittest.skipUnless(effect.effects_available(), "Needs Blender 5.2")
class TestRipple(BlenderTestCase):
    def setUp(self):
        super().setUp()
        configure_model(build_model())
        mesh = bpy.data.meshes.new("Grid")
        bm = bmesh.new()
        bmesh.ops.create_grid(bm, x_segments=100, y_segments=100, size=0.5)
        bm.to_mesh(mesh)
        bm.free()
        self.grid = new_object("Grid", mesh)
        self.grid.modifiers.new("Subdivision", "SUBSURF")
        set_active(self.grid)

    def displacement(self):
        # Changing the modifier inputs from Python does not tag the object
        self.grid.update_tag()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        co = np.empty(len(self.grid.data.vertices) * 3)
        self.grid.evaluated_get(depsgraph).data.vertices.foreach_get("co", co)
        return co.reshape(-1, 3)

    # The grid bulges along its normals only where the disc of the Control cuts it
    def test_ripple(self):
        bpy.ops.mustardui.model_toolkit_ripple()
        self.assertEqual([m.type for m in self.grid.modifiers], ["NODES", "SUBSURF"])
        control = effect.modifier_input(self.grid.modifiers["Ripple"], "Control").value
        self.assertEqual(control.MustardUI_tools_creators_type, "EFFECT_RIPPLE")

        self.grid.modifiers["Subdivision"].show_viewport = False
        for y in (0.0, 0.2):
            control.location.y = y
            co = self.displacement()
            moved = co[co[:, 2] > 1e-6]
            self.assertAlmostEqual(co[:, 2].max(), 0.02, delta=0.002)
            self.assertTrue(np.all(np.abs(moved[:, 1] - y) < control.scale.z))
            self.assertTrue(np.all(np.abs(moved[:, 0]) < control.scale.x))

        effect.modifier_input(self.grid.modifiers["Ripple"], "Strength").value = 0.5
        self.assertAlmostEqual(self.displacement()[:, 2].max(), 0.01, delta=0.001)

        # Smoothing spreads the ripple, lowering its peak
        sharp = self.displacement()[:, 2]
        effect.modifier_input(self.grid.modifiers["Ripple"], "Smooth").value = 5
        smooth = self.displacement()[:, 2]
        self.assertLess(smooth.max(), sharp.max())
        self.assertGreater((smooth > 1e-6).sum(), (sharp > 1e-6).sum())

    # Only the vertices in the Vertex Group ripple
    def test_vertex_group(self):
        group = self.grid.vertex_groups.new(name="Soft")
        group.add([v.index for v in self.grid.data.vertices if v.co.x < 0], 1.0, "REPLACE")
        bpy.ops.mustardui.model_toolkit_ripple()
        mask = effect.modifier_input(self.grid.modifiers["Ripple"], "Mask")
        mask.type = "ATTRIBUTE"
        mask.attribute_name = "Soft"

        self.grid.modifiers["Subdivision"].show_viewport = False
        co = self.displacement()
        moved = co[co[:, 2] > 1e-6]
        self.assertGreater(len(moved), 0)
        self.assertTrue(np.all(moved[:, 0] < 0))

    # The Control is removed with the Ripple
    def test_remove(self):
        bpy.ops.mustardui.model_toolkit_ripple()
        name = effect.modifier_input(self.grid.modifiers["Ripple"], "Control").value.name

        bpy.ops.mustardui.model_toolkit_remove_ripple()
        self.assertNotIn("Ripple", self.grid.modifiers)
        self.assertNotIn(name, bpy.data.objects)
