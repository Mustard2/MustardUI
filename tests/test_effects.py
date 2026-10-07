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
    new_mesh_object,
    new_object,
    set_active,
)
from mathutils import Matrix

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
        self.assertFalse(bpy.ops.mustardui.model_toolkit_rope.poll())
        self.assertFalse(bpy.ops.mustardui.model_toolkit_tape.poll())

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


@unittest.skipUnless(effect.effects_available(), "Needs Blender 5.2")
class TestWrap(BlenderTestCase):
    def setUp(self):
        super().setUp()
        configure_model(build_model())
        self.ball = self.new_balls("Ball", (0.0,))
        set_active(self.ball)

    def new_balls(self, name, xs):
        """Mesh of spheres along X at z = 3, with a Vertex Group for each"""
        mesh = bpy.data.meshes.new(name)
        bm = bmesh.new()
        for x in xs:
            bmesh.ops.create_uvsphere(
                bm, u_segments=64, v_segments=32, radius=0.1, matrix=Matrix.Translation((x, 0, 0))
            )
        bm.to_mesh(mesh)
        bm.free()
        obj = new_object(name, mesh)
        obj.location = (0.0, 0.0, 3.0)
        for i, x in enumerate(xs):
            group = obj.vertex_groups.new(name=f"Ball {i}")
            group.add([v.index for v in mesh.vertices if abs(v.co.x - x) < 0.11], 0.2, "REPLACE")
        bpy.context.scene.cursor.location = obj.location
        return obj

    def points(self, obj):
        # Changing the modifier inputs from Python does not tag the object
        obj.update_tag()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        mesh = obj.evaluated_get(depsgraph).to_mesh()
        return np.array([obj.matrix_world @ v.co for v in mesh.vertices]) - (0.0, 0.0, 3.0)

    def distances(self, obj):
        return np.linalg.norm(self.points(obj), axis=1)

    # A new loop around the cursor tightens on the ball, resting on its surface
    def test_rope(self):
        bpy.ops.mustardui.model_toolkit_rope(radius=0.2)
        rope = bpy.data.objects["Ball Rope"]
        self.assertEqual(rope.MustardUI_tools_creators_type, "EFFECT_ROPE")
        self.assertEqual(rope.parent, self.ball)
        modifier = rope.modifiers["Rope"]
        self.assertEqual(effect.modifier_input(modifier, "Target").value, self.ball)
        self.assertEqual(effect.modifier_input(modifier, "Material").value.name, "MustardUI Rope")

        radius = effect.modifier_input(modifier, "Radius").value
        distances = self.distances(rope)
        self.assertGreater(len(distances), 0)
        self.assertGreater(distances.min(), 0.0995)
        self.assertLess(distances.max(), 0.1 + 2 * radius + 0.001)

        effect.modifier_input(modifier, "Offset").value = 0.01
        self.assertGreater(self.distances(rope).min(), 0.1095)

    # The tape lies on the ball, as thick as set
    def test_tape(self):
        bpy.ops.mustardui.model_toolkit_tape(radius=0.2)
        tape = bpy.data.objects["Ball Tape"]
        self.assertEqual(tape.MustardUI_tools_creators_type, "EFFECT_TAPE")
        modifier = tape.modifiers["Tape"]
        self.assertEqual(effect.modifier_input(modifier, "Material").value.name, "MustardUI Tape")

        thickness = effect.modifier_input(modifier, "Thickness").value
        distances = self.distances(tape)
        self.assertGreater(len(distances), 0)
        self.assertGreater(distances.min(), 0.0995)
        self.assertLess(distances.max(), 0.1 + thickness + 0.001)
        # Across the tape, along the axis of the loop
        width = effect.modifier_input(modifier, "Width").value
        self.assertAlmostEqual(np.ptp(self.points(tape)[:, 2]), width, delta=0.005)

    # A Vertex Group as the Mask limits the targets, ignoring the rest
    def test_vertex_group(self):
        balls = self.new_balls("Balls", (-0.12, 0.12))
        set_active(balls)
        bpy.ops.mustardui.model_toolkit_rope(radius=0.3)
        rope = bpy.data.objects["Balls Rope"]
        self.assertGreater(self.points(rope)[:, 0].max(), 0.2)

        mask = effect.modifier_input(rope.modifiers["Rope"], "Mask")
        mask.type = "ATTRIBUTE"
        mask.attribute_name = "Ball 0"
        self.assertLess(self.points(rope)[:, 0].max(), 0.0)

    # Smoothing rounds the corners where the rope leaves the balls, keeping it out of them
    def test_smooth(self):
        balls = self.new_balls("Balls", (-0.12, 0.12))
        set_active(balls)
        bpy.ops.mustardui.model_toolkit_rope(radius=0.3)
        rope = bpy.data.objects["Balls Rope"]
        sharp = self.points(rope)

        effect.modifier_input(rope.modifiers["Rope"], "Smooth").value = 20
        smooth = self.points(rope)
        self.assertLess(len(smooth), len(sharp))
        for x in (-0.12, 0.12):
            self.assertGreater(np.linalg.norm(smooth - (x, 0, 0), axis=1).min(), 0.0995)

    # The Vertex Group set as the Mask when adding, here with a low weight
    def test_add_vertex_group(self):
        balls = self.new_balls("Balls", (-0.12, 0.12))
        set_active(balls)
        bpy.ops.mustardui.model_toolkit_tape(radius=0.3, vertex_group="Ball 1")
        tape = bpy.data.objects["Balls Tape"]
        mask = effect.modifier_input(tape.modifiers["Tape"], "Mask")
        self.assertEqual((mask.type, mask.attribute_name), ("ATTRIBUTE", "Ball 1"))
        self.assertGreater(self.points(tape)[:, 0].min(), 0.0)

    # Selected curves become ropes, kept when the Rope is removed
    def test_selected_curves(self):
        curve = bpy.data.curves.new("Lasso", "CURVE")
        curve.dimensions = "3D"
        spline = curve.splines.new("POLY")
        spline.points.add(3)
        for point, (x, y) in zip(spline.points, ((1, 0), (0, 1), (-1, 0), (0, -1)), strict=True):
            point.co = (0.15 * x, 0.15 * y, 3.0, 1.0)
        spline.use_cyclic_u = True
        lasso = new_object("Lasso", curve)
        lasso.select_set(True)
        objects = len(bpy.data.objects)

        bpy.ops.mustardui.model_toolkit_rope()
        self.assertEqual(len(bpy.data.objects), objects)
        self.assertIn("Rope", lasso.modifiers)
        self.assertLess(self.distances(lasso).max(), 0.12)

        bpy.ops.mustardui.model_toolkit_remove_rope()
        self.assertNotIn("Rope", lasso.modifiers)
        self.assertIn("Lasso", bpy.data.objects)

    # The loops added are removed with their effect only
    def test_remove(self):
        bpy.ops.mustardui.model_toolkit_rope()
        bpy.ops.mustardui.model_toolkit_tape()
        rope, tape = bpy.data.objects["Ball Rope"], bpy.data.objects["Ball Tape"]
        set_active(rope)
        tape.select_set(True)
        self.assertTrue(bpy.ops.mustardui.model_toolkit_remove_tape.poll())

        bpy.ops.mustardui.model_toolkit_remove_rope()
        self.assertNotIn("Ball Rope", bpy.data.objects)
        self.assertIn("Ball Tape", bpy.data.objects)
        self.assertFalse(bpy.ops.mustardui.model_toolkit_remove_rope.poll())

        bpy.ops.mustardui.model_toolkit_remove_tape()
        self.assertNotIn("Ball Tape", bpy.data.objects)


@unittest.skipUnless(effect.effects_available(), "Needs Blender 5.2")
class TestStickyStrands(BlenderTestCase):
    def setUp(self):
        super().setUp()
        configure_model(build_model())
        self.scene = bpy.context.scene
        self.scene.cursor.location = (0.055, 0.0, 0.0)

    def balls(self, name, *xs):
        mesh = bpy.data.meshes.new(name)
        bm = bmesh.new()
        for x in xs:
            matrix = Matrix.Translation((x, 0.0, 0.0))
            bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=0.05, matrix=matrix)
        bm.to_mesh(mesh)
        bm.free()
        return new_object(name, mesh)

    def strands(self, obj):
        """World positions of the strand vertices, an instance next to the mesh"""
        depsgraph = bpy.context.evaluated_depsgraph_get()
        geometry = obj.evaluated_get(depsgraph).evaluated_geometry()
        references = geometry.instance_references()
        meshes = [x.mesh for x in references if x.mesh]
        co = np.empty(sum(len(x.vertices) for x in meshes) * 3)
        if meshes:
            meshes[0].vertices.foreach_get("co", co)
        return co.reshape(-1, 3) + np.array(obj.location)

    def pull(self, physics, moves=((0, 0.11), (10, 0.2), (30, 0.5))):
        """Strands from a lip to a finger pulled away, stretching until frame 10, breaking after"""
        lip = self.balls("Lip", 0.0)
        finger = self.balls("Finger", 0.0)
        start = self.scene.frame_start
        for frame, x in moves:
            finger.location.x = x
            finger.keyframe_insert("location", frame=start + frame)
        self.scene.frame_set(start)
        set_active(finger)
        lip.select_set(True)

        # With two meshes, the Control is on the mesh where it is closest to the other one
        self.scene.cursor.location = (1.0, 1.0, 1.0)
        bpy.ops.mustardui.model_toolkit_sticky_strands(radius=0.03)
        self.assertFalse(finger.modifiers)
        self.assertTrue(finger.add_rest_position_attribute)
        modifier = lip.modifiers["Sticky Strands"]
        self.assertEqual(effect.modifier_input(modifier, "Target").value, finger)
        control = effect.modifier_input(modifier, "Control").value
        self.assertEqual(control.MustardUI_tools_creators_type, "EFFECT_STICKY_STRANDS")
        bpy.context.view_layer.update()
        np.testing.assert_allclose(control.matrix_world.translation, (0.05, 0.0, 0.0), atol=0.001)
        effect.modifier_input(modifier, "Break Length").value = 0.15
        effect.modifier_input(modifier, "Elasticity").value = 0.0
        effect.modifier_input(modifier, "Physics").value = physics
        # Changing the modifier inputs from Python does not tag the object
        lip.update_tag()
        self.scene.frame_set(start)
        return lip

    def play(self, frames):
        start = self.scene.frame_current + 1
        for frame in range(start, start + frames):
            self.scene.frame_set(frame)

    # Strands stretch between the meshes, then break and dangle
    def test_sticky_strands(self):
        lip = self.pull(physics=True)
        self.play(10)
        co = self.strands(lip)
        self.assertTrue(np.any(np.abs(co[:, 0] - 0.1) < 0.01))

        self.play(40)
        co = self.strands(lip)
        self.assertGreater(len(co), 0)
        self.assertFalse(np.any(np.abs(co[:, 0] - 0.25) < 0.05))
        self.assertLess(co[:, 2].min(), -0.05)

    def attributes(self, obj):
        """The strand attributes for the shader, by name"""
        geometry = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).evaluated_geometry()
        references = geometry.instance_references()
        mesh = next(x.mesh for x in references if x.mesh)
        self.assertNotIn("strand_length", mesh.attributes)
        values = {}
        for name in ("sticky_length", "sticky_factor", "sticky_length_normalized"):
            values[name] = np.empty(len(mesh.vertices))
            mesh.attributes[name].data.foreach_get("value", values[name])
        return values

    # The length, the factor along and the closeness to breaking are kept for the shader
    def test_shader_attributes(self):
        lip = self.pull(physics=True)
        self.play(10)
        values = self.attributes(lip)
        self.assertGreater(values["sticky_length"].min(), 0.09)
        self.assertAlmostEqual(values["sticky_factor"].min(), 0.0, places=3)
        self.assertAlmostEqual(values["sticky_factor"].max(), 1.0, places=3)
        self.assertGreater(values["sticky_length_normalized"].min(), 0.5)
        self.assertLessEqual(values["sticky_length_normalized"].max(), 1.0)

        # Never close to breaking without Break Length
        effect.modifier_input(lip.modifiers["Sticky Strands"], "Break Length").value = 0.0
        lip.update_tag()
        self.scene.frame_set(self.scene.frame_current)
        self.assertFalse(self.attributes(lip)["sticky_length_normalized"].any())

    # The factor is along the whole strands, 0 and 1 only at the ends on the meshes
    def test_shader_factor_broken(self):
        lip = self.pull(physics=True)
        self.play(40)
        factor = self.attributes(lip)["sticky_factor"]
        co = self.strands(lip)
        ends = co[(factor < 0.02) | (factor > 0.98)]
        finger = bpy.data.objects["Finger"].location
        distance = np.minimum(np.linalg.norm(ends, axis=1), np.linalg.norm(ends - finger, axis=1))
        self.assertLess(distance.max(), 0.07)
        self.assertLess(co[:, 2].min(), -0.05)
        # Not close to breaking anymore once broken
        self.assertFalse(self.attributes(lip)["sticky_length_normalized"].any())

    # Broken strands are not close to breaking anymore, also when placed already broken
    def test_shader_broken_tension(self):
        lip = self.pull(physics=True, moves=((0, 0.3),))
        self.play(10)
        self.assertFalse(self.attributes(lip)["sticky_length_normalized"].any())

    # Without physics, the strands get closer to breaking as they stretch too
    def test_static_tension(self):
        lip = self.pull(physics=False)
        self.play(10)
        self.assertGreater(self.attributes(lip)["sticky_length_normalized"].min(), 0.5)

    # The break length, and the other strand options, apply while simulating
    def test_live_options(self):
        lip = self.pull(physics=True)
        self.play(5)
        effect.modifier_input(lip.modifiers["Sticky Strands"], "Break Length").value = 0.0
        lip.update_tag()
        self.play(45)
        self.assertTrue(np.any(np.abs(self.strands(lip)[:, 0] - 0.25) < 0.05))

    # Broken strands are replaced by new ones when the meshes touch again
    def test_contact(self):
        lip = self.pull(physics=True, moves=((0, 0.1), (10, 0.5), (30, 0.1), (40, 0.18)))
        effect.modifier_input(
            lip.modifiers["Sticky Strands"], "New Strands on Contact"
        ).value = True
        lip.update_tag()
        self.scene.frame_set(self.scene.frame_start)
        self.play(40)
        self.assertTrue(np.any(np.abs(self.strands(lip)[:, 0] - 0.09) < 0.01))

    # Meshes far apart are connected too, never breaking without Break Length
    def test_far(self):
        lip = self.pull(physics=True, moves=((0, 1.0),))
        effect.modifier_input(lip.modifiers["Sticky Strands"], "Break Length").value = 0.0
        lip.update_tag()
        self.scene.frame_set(self.scene.frame_start)
        self.play(10)
        self.assertTrue(np.any(np.abs(self.strands(lip)[:, 0] - 0.5) < 0.01))

    # Without physics, the strands hang between the meshes, and are removed when broken
    def test_static(self):
        lip = self.pull(physics=False)
        self.play(10)
        co = self.strands(lip)
        self.assertTrue(np.any(np.abs(co[:, 0] - 0.1) < 0.01))

        self.play(40)
        self.assertEqual(len(self.strands(lip)), 0)

    # Not on a selected collider, for physics colliding with it not to make a dependency cycle
    def test_collider(self):
        lip = self.balls("Lip", 0.0)
        finger = self.balls("Finger", 0.11)
        lip.modifiers.new("Collision", "COLLISION")
        set_active(finger)
        lip.select_set(True)
        bpy.ops.mustardui.model_toolkit_sticky_strands()
        self.assertNotIn("Sticky Strands", lip.modifiers)
        modifier = finger.modifiers["Sticky Strands"]
        self.assertEqual(effect.modifier_input(modifier, "Target").value, lip)

    # The Control follows the mesh, for its strands not to disappear when it moves
    def test_follow(self):
        lip = self.pull(physics=False, moves=((0, 0.11),))
        effect.modifier_input(lip.modifiers["Sticky Strands"], "Break Length").value = 0.0
        lip.location.x = -0.5
        lip.update_tag()
        self.scene.frame_set(self.scene.frame_start)
        self.assertGreater(len(self.strands(lip)), 0)

    # Smoothing the strands straightens their sag between the fixed ends
    def test_smooth(self):
        lip = self.pull(physics=False)
        self.play(10)
        modifier = lip.modifiers["Sticky Strands"]
        sags = []
        for smooth in (0, 30):
            effect.modifier_input(modifier, "Smooth").value = smooth
            lip.update_tag()
            self.scene.frame_set(self.scene.frame_current)
            co = self.strands(lip)
            sags.append(co[np.abs(co[:, 0] - 0.1) < 0.01][:, 2].min())
        self.assertGreater(sags[1], sags[0])

    # Without physics, the options change the strands on any frame, without a simulation cache
    def test_static_options(self):
        lip = self.pull(physics=False)
        effect.modifier_input(lip.modifiers["Sticky Strands"], "Break Length").value = 0.0
        lip.update_tag()
        self.play(5)
        count = len(self.strands(lip))
        effect.modifier_input(lip.modifiers["Sticky Strands"], "Count").value = 3
        lip.update_tag()
        self.scene.frame_set(self.scene.frame_current)
        self.assertEqual(len(self.strands(lip)), count // 4)

    # Without Target, the strands connect the mesh to itself, between the Vertex Groups
    def test_self(self):
        mouth = self.balls("Mouth", 0.0, 0.11)
        for name, side in (("Upper", -1), ("Lower", 1)):
            group = mouth.vertex_groups.new(name=name)
            group.add(
                [v.index for v in mouth.data.vertices if (v.co.x - 0.055) * side > 0],
                1.0,
                "REPLACE",
            )
        set_active(mouth)

        bpy.ops.mustardui.model_toolkit_sticky_strands(radius=0.03)
        modifier = mouth.modifiers["Sticky Strands"]
        self.assertIsNone(effect.modifier_input(modifier, "Target").value)
        for name, group in (("Start Vertex Group", "Upper"), ("End Vertex Group", "Lower")):
            mask = effect.modifier_input(modifier, name)
            mask.type = "ATTRIBUTE"
            mask.attribute_name = group

        # Changing the modifier inputs from Python does not tag the object
        mouth.update_tag()
        self.scene.frame_set(self.scene.frame_start)
        co = self.strands(mouth)
        self.assertGreater(len(co), 0)
        self.assertTrue(np.any(np.abs(co[:, 0] - 0.055) < 0.005))

    # Faces larger than the Control, its sphere on a vertex holding no face center
    def test_large_faces(self):
        for name, z in (("Lip", 0.0), ("Finger", 0.02)):
            mesh = bpy.data.meshes.new(name)
            bm = bmesh.new()
            matrix = Matrix.Translation((0.0, 0.0, z))
            bmesh.ops.create_grid(bm, x_segments=2, y_segments=2, size=0.5, matrix=matrix)
            bm.to_mesh(mesh)
            bm.free()
            set_active(new_object(name, mesh))
        bpy.data.objects["Lip"].select_set(True)

        bpy.ops.mustardui.model_toolkit_sticky_strands()
        self.scene.frame_set(self.scene.frame_start)
        self.assertGreater(len(self.strands(bpy.data.objects["Lip"])), 0)

    # The Control is removed with the Sticky Strands
    def test_remove(self):
        mouth = self.balls("Mouth", 0.0)
        set_active(mouth)
        bpy.ops.mustardui.model_toolkit_sticky_strands()
        name = effect.modifier_input(mouth.modifiers["Sticky Strands"], "Control").value.name

        bpy.ops.mustardui.model_toolkit_remove_sticky_strands()
        self.assertNotIn("Sticky Strands", mouth.modifiers)
        self.assertNotIn(name, bpy.data.objects)


@unittest.skipUnless(effect.effects_available(), "Needs Blender 5.2")
class TestWithoutModel(BlenderTestCase):
    # The effects work on any mesh, without a MustardUI model
    def test_ripple(self):
        cube = new_mesh_object("Cube")
        set_active(cube)
        bpy.ops.mustardui.model_toolkit_ripple()
        self.assertIn("Ripple", cube.modifiers)

        bpy.ops.mustardui.model_toolkit_remove_ripple()
        self.assertNotIn("Ripple", cube.modifiers)
