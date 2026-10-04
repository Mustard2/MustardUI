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
        self.assertFalse(bpy.ops.mustardui.model_toolkit_fireball.poll())
        self.assertFalse(bpy.ops.mustardui.model_toolkit_hex_dissolve.poll())

    # The meshes are cut by the growing Control, and emit particles from the cut
    @unittest.skipUnless(effect.effects_available(), "Needs Blender 5.2")
    def test_disintegration(self):
        bpy.ops.mustardui.model_toolkit_disintegration(duration=10)
        self.assertEqual([m.type for m in self.shirt.modifiers], ["ARMATURE", "NODES", "SUBSURF"])
        modifier = self.shirt.modifiers["Disintegration"]
        control = effect.modifier_input(modifier, "Control").value
        self.assertEqual(control, effect.modifier_input(self.pants.modifiers[-1], "Control").value)
        self.assertEqual(control.MustardUI_tools_creators_type, "EFFECT_DISINTEGRATION")

        # The Control is at its value of the current frame, without changing frame
        depsgraph = bpy.context.evaluated_depsgraph_get()
        self.assertLess(control.scale.x, 0.01)
        self.assertGreater(len(self.shirt.evaluated_get(depsgraph).data.polygons), 0)

        scene = bpy.context.scene
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


@unittest.skipUnless(effect.effects_available(), "Needs Blender 5.2")
class TestFireball(BlenderTestCase):
    def setUp(self):
        super().setUp()
        configure_model(build_model())
        bpy.context.scene.cursor.location = (0.0, 0.0, 1.0)
        bpy.ops.mustardui.model_toolkit_fireball(radius=0.1)
        self.fireball = bpy.data.objects["Fireball"]
        self.control = effect.modifier_input(self.fireball.modifiers["Fireball"], "Control").value

    # The core follows the Control, and the flames trail behind it
    def test_fireball(self):
        self.assertEqual(self.control.MustardUI_tools_creators_type, "EFFECT_FIREBALL")
        self.assertEqual(bpy.context.active_object, self.control)
        collection = self.fireball.users_collection[0]
        self.assertIn(collection, bpy.context.scene.collection.children[:])
        self.assertEqual(set(collection.objects), {self.fireball, self.control})
        for lock in ("lock_location", "lock_rotation", "lock_scale"):
            self.assertTrue(all(getattr(self.fireball, lock)))

        scene = bpy.context.scene
        depsgraph = bpy.context.evaluated_depsgraph_get()
        for frame in range(scene.frame_start, scene.frame_start + 20):
            self.control.location.x = (frame - scene.frame_start) * 0.05
            scene.frame_set(frame)
        geometry = self.fireball.evaluated_get(depsgraph).evaluated_geometry()

        co = np.empty(len(geometry.mesh.vertices) * 3)
        geometry.mesh.vertices.foreach_get("co", co)
        np.testing.assert_allclose(co.reshape(-1, 3).mean(axis=0), self.control.location, atol=0.02)

        co = np.empty(len(geometry.pointcloud.points) * 3)
        geometry.pointcloud.points.foreach_get("co", co)
        x = co.reshape(-1, 3)[:, 0]
        self.assertGreater(len(x), 100)
        self.assertLess(x.min(), self.control.location.x - 0.3)
        self.assertIn("fireball_age", geometry.pointcloud.attributes)
        self.assertIn("fireball_brightness", geometry.mesh.attributes)

    # Removing from the Control removes the Fireball and its collection too
    def test_remove(self):
        names = {self.fireball.name, self.control.name}
        collection = self.fireball.users_collection[0].name
        bpy.ops.mustardui.model_toolkit_remove_fireball()
        self.assertFalse(names & set(bpy.data.objects.keys()))
        self.assertNotIn(collection, bpy.data.collections)
        self.assertFalse(bpy.ops.mustardui.model_toolkit_remove_fireball.poll())


@unittest.skipUnless(effect.effects_available(), "Needs Blender 5.2")
class TestHexDissolve(BlenderTestCase):
    def setUp(self):
        super().setUp()
        configure_model(build_model())
        self.shirt = bpy.data.objects["Casual - Shirt"]
        self.pants = bpy.data.objects["Casual - Pants"]
        self.dress = bpy.data.objects["Formal - Dress"]
        self.cloth = bpy.data.materials.new("Cloth")
        for obj in (self.shirt, self.pants, self.dress):
            obj.data.materials.append(self.cloth)
        self.leather = bpy.data.materials.new("Leather")
        self.pants.data.materials.append(self.leather)
        set_active(self.shirt)
        self.pants.select_set(True)

    def surface(self, material):
        nodes = material.node_tree.nodes
        return nodes["Material Output"].inputs["Surface"].links[0].from_node

    # The surface shaders are wrapped by the effect, bound to the growing Control
    def test_hex_dissolve(self):
        bpy.ops.mustardui.model_toolkit_hex_dissolve(duration=10)
        controls = set()
        for material in (self.cloth, self.leather):
            group = self.surface(material)
            self.assertEqual(group.node_tree.name, "MustardUI Hex Dissolve")
            self.assertEqual(group.inputs["Shader"].links[0].from_node.type, "BSDF_PRINCIPLED")
            controls.add(group.inputs["Control"].links[0].from_node.object)
        self.assertEqual(len(controls), 1)
        control = controls.pop()
        self.assertEqual(control.MustardUI_tools_creators_type, "EFFECT_HEX_DISSOLVE")
        self.assertLess(control.scale.x, 0.01)

        scene = bpy.context.scene
        start = scene.frame_current
        scene.frame_set(start)
        self.assertLess(control.scale.x, 0.01)
        scene.frame_set(start + 10)
        self.assertGreater(control.scale.x, 0.5)

    # Showing shrinks the Control instead
    def test_show(self):
        bpy.ops.mustardui.model_toolkit_hex_dissolve(duration=10, show=True)
        control = self.surface(self.cloth).inputs["Control"].links[0].from_node.object
        self.assertGreater(control.scale.x, 0.5)
        scene = bpy.context.scene
        start = scene.frame_current
        scene.frame_set(start)
        self.assertGreater(control.scale.x, 0.5)
        scene.frame_set(start + 10)
        self.assertLess(control.scale.x, 0.01)

    # Effects stack, and removing them restores the shaders and removes the Controls
    def test_remove(self):
        bpy.ops.mustardui.model_toolkit_hex_dissolve()
        set_active(self.dress)
        bpy.ops.mustardui.model_toolkit_hex_dissolve()
        nodes = len(self.leather.node_tree.nodes)

        bpy.ops.mustardui.model_toolkit_remove_hex_dissolve()
        self.assertEqual(self.surface(self.cloth).type, "BSDF_PRINCIPLED")
        self.assertEqual(self.surface(self.leather).node_tree.name, "MustardUI Hex Dissolve")
        self.assertEqual(len(self.leather.node_tree.nodes), nodes)
        controls = [x for x in bpy.data.objects if x.MustardUI_tools_creators_type]
        self.assertEqual(len(controls), 1)

        set_active(self.pants)
        bpy.ops.mustardui.model_toolkit_remove_hex_dissolve()
        self.assertEqual(self.surface(self.leather).type, "BSDF_PRINCIPLED")
        self.assertEqual(len(self.leather.node_tree.nodes), nodes - 2)
        self.assertFalse([x for x in bpy.data.objects if x.MustardUI_tools_creators_type])
        self.assertFalse(bpy.ops.mustardui.model_toolkit_remove_hex_dissolve.poll())
