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
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

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
        self.assertFalse(bpy.ops.mustardui.model_toolkit_sticky_liquid.poll())
        self.assertFalse(bpy.ops.mustardui.model_toolkit_hex_dissolve.poll())
        self.assertFalse(bpy.ops.mustardui.model_toolkit_cloth_tear.poll())
        self.assertFalse(bpy.ops.mustardui.model_toolkit_rope.poll())
        self.assertFalse(bpy.ops.mustardui.model_toolkit_tape.poll())
        self.assertFalse(bpy.ops.mustardui.model_toolkit_wet.poll())

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

    # Multires can't have modifiers above it
    def test_multires(self):
        self.grid.modifiers.clear()
        self.grid.modifiers.new("Multires", "MULTIRES")
        bpy.ops.mustardui.model_toolkit_ripple()
        self.assertEqual([m.type for m in self.grid.modifiers], ["MULTIRES", "NODES"])

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
class TestClothTear(BlenderTestCase):
    def setUp(self):
        super().setUp()
        configure_model(build_model())
        self.shirt = bpy.data.objects["Casual - Shirt"]
        self.pants = bpy.data.objects["Casual - Pants"]
        bm = bmesh.new()
        bm.from_mesh(self.shirt.data)
        bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=10, use_grid_fill=True)
        bm.to_mesh(self.shirt.data)
        bm.free()
        self.shirt.modifiers.new("Subdivision", "SUBSURF")
        for name in ("Left", "Right"):
            self.shirt.data.materials.append(bpy.data.materials.new(name))
        for face in self.shirt.data.polygons:
            face.material_index = face.center.x > 0.45
        set_active(self.shirt)
        self.pants.select_set(True)
        # On the shirt corner
        bpy.context.scene.cursor.location = (0.6, 0.6, 1.6)

    def controls(self, obj):
        modifier = obj.modifiers["Cloth Tear"]
        return list(effect.modifier_input(modifier, "Controls").value.objects)

    def threads(self, obj):
        """Thread roots and materials, in an instance next to the mesh"""
        depsgraph = bpy.context.evaluated_depsgraph_get()
        geometry = obj.evaluated_get(depsgraph).evaluated_geometry()
        references = geometry.instance_references()
        meshes = [x.mesh for x in references if x.mesh]
        if not meshes:
            return np.empty((0, 3)), set()
        mesh = meshes[0]
        co = np.empty(len(mesh.vertices) * 3)
        mesh.vertices.foreach_get("co", co)
        # Rings of 3 points along the 5 points of each thread
        roots = co.reshape(-1, 5, 3, 3)[:, 0].mean(axis=1)
        return roots, {mesh.materials[p.material_index].name for p in mesh.polygons}

    # The Control on the vertex closest to the 3D cursor, following its bone, grows to tear the
    # meshes, leaving threads with the materials of the meshes on the edge
    def test_cloth_tear(self):
        bpy.ops.mustardui.model_toolkit_cloth_tear(radius=0.2, duration=10)
        self.assertEqual([m.type for m in self.shirt.modifiers], ["ARMATURE", "NODES", "SUBSURF"])
        modifier = self.shirt.modifiers["Cloth Tear"]
        (control,) = self.controls(self.shirt)
        self.assertEqual(self.controls(self.pants), [control])
        self.assertEqual(control.MustardUI_tools_creators_type, "EFFECT_CLOTH_TEAR")
        self.assertEqual((control.parent_type, control.parent_bone), ("BONE", "spine"))
        # Only in the Controls collections, in the scene out of the outfit collections
        collections = {
            effect.modifier_input(x.modifiers["Cloth Tear"], "Controls").value
            for x in (self.shirt, self.pants)
        }
        self.assertEqual(set(control.users_collection), collections)
        self.assertLessEqual(collections, set(bpy.context.scene.collection.children))
        # Selected, to be moved or scaled right away
        self.assertEqual(bpy.context.selected_objects, [control])
        self.assertEqual(bpy.context.view_layer.objects.active, control)
        bpy.context.view_layer.update()
        np.testing.assert_allclose(control.matrix_world.translation, (0.55, 0.55, 1.55), atol=1e-5)
        # Starting from a quarter of the Radius
        self.assertAlmostEqual(control.scale.x, 0.05)

        scene = bpy.context.scene
        scene.frame_set(scene.frame_current + 10)
        self.assertAlmostEqual(control.scale.x, 0.2)
        # Nothing left inside the sphere, before the subdivision smoothing the edge
        self.shirt.modifiers["Subdivision"].show_viewport = False
        depsgraph = bpy.context.evaluated_depsgraph_get()
        data = self.shirt.evaluated_get(depsgraph).data
        co = np.empty(len(data.vertices) * 3)
        data.vertices.foreach_get("co", co)
        distance = np.linalg.norm(co.reshape(-1, 3) - (0.55, 0.55, 1.55), axis=1)
        self.assertGreater(distance.min(), 0.2 - 1e-5)
        self.assertLess(len(data.polygons), len(self.shirt.data.polygons))
        self.assertIn("cloth_tear_edge", data.attributes)
        tree = BVHTree.FromPolygons(co.reshape(-1, 3).tolist(), [p.vertices for p in data.polygons])
        roots, materials = self.threads(self.shirt)
        self.assertGreater(len(roots), 0)
        # The threads start on the edge of the tear
        for root in roots:
            self.assertLess(tree.find_nearest(root)[3], 1e-3)
            self.assertAlmostEqual(np.linalg.norm(root - (0.55, 0.55, 1.55)), 0.2, delta=0.2 * 0.6)
        self.assertEqual(materials, {"Left", "Right"})

        effect.modifier_input(modifier, "Density").value = 0.0
        # Changing the modifier inputs from Python does not tag the object
        self.shirt.update_tag()
        self.assertEqual(len(self.threads(self.shirt)[0]), 0)

    # No warnings, as from removing missing attributes, without and with physics
    def test_no_warnings(self):
        set_active(self.shirt)
        bpy.ops.mustardui.model_toolkit_cloth_tear()
        modifier = self.shirt.modifiers["Cloth Tear"]
        scene = bpy.context.scene
        for physics in (False, True):
            effect.modifier_input(modifier, "Physics").value = physics
            self.shirt.update_tag()
            for frame in range(scene.frame_current, scene.frame_current + 3):
                scene.frame_set(frame)
                bpy.context.evaluated_depsgraph_get()
                self.assertEqual([x.message for x in modifier.node_warnings], [])

    # Without a tear, as with the Control away from the mesh, there are no threads
    def test_no_tear(self):
        bpy.ops.mustardui.model_toolkit_cloth_tear()
        for control in self.controls(self.shirt):
            control.animation_data_clear()
            control.location.x += 5.0
        self.shirt.modifiers["Subdivision"].show_viewport = False
        depsgraph = bpy.context.evaluated_depsgraph_get()
        data = self.shirt.evaluated_get(depsgraph).data
        edge = np.empty(len(data.vertices))
        data.attributes["cloth_tear_edge"].data.foreach_get("value", edge)
        self.assertEqual(edge.max(), 0.0)
        self.assertEqual(len(self.threads(self.shirt)[0]), 0)

    # With physics, the torn pieces fall to the floor, colliding with the model body
    def test_physics(self):
        scene = bpy.context.scene
        # On the side of the shirt, 5 cm out of the body
        scene.cursor.location = (0.6, 0.0, 1.0)
        set_active(self.shirt)
        bpy.ops.mustardui.model_toolkit_cloth_tear(radius=0.2, duration=5, physics=True)
        modifier = self.shirt.modifiers["Cloth Tear"]
        self.assertTrue(effect.modifier_input(modifier, "Physics").value)
        self.assertEqual(effect.modifier_input(modifier, "Start Frame").value, scene.frame_current)
        body = bpy.data.objects["Tester Body"]
        # In a collection in the scene, for more colliders to be added
        colliders = effect.modifier_input(modifier, "Colliders").value
        self.assertEqual(list(colliders.objects), [body])
        self.assertIn(colliders, bpy.context.scene.collection.children[:])
        # The collider normals outwards, as on a real body
        bm = bmesh.new()
        bm.from_mesh(body.data)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(body.data)
        bm.free()
        self.shirt.modifiers["Subdivision"].show_viewport = False
        effect.modifier_input(modifier, "Rip Out").value = 1.0
        self.shirt.update_tag()

        depsgraph = bpy.context.evaluated_depsgraph_get()
        for frame in range(scene.frame_current, scene.frame_current + 30):
            scene.frame_set(frame)
        data = self.shirt.evaluated_get(depsgraph).data
        co = np.empty(len(data.vertices) * 3)
        data.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        self.assertTrue(np.isfinite(co).all())
        # Below the shirt, but not the floor
        self.assertLess(co[:, 2].min(), 0.4)
        self.assertGreater(co[:, 2].min(), 0.0)
        # Not inside the body
        inside = (np.abs(co[:, :2]) < 0.499).all(axis=1) & (np.abs(co[:, 2] - 1.0) < 0.499)
        self.assertFalse(inside.any())
        self.assertGreater(len(self.threads(self.shirt)[0]), 0)

        # Not sliding once resting on the floor
        floor = co[co[:, 2] < 0.01]
        self.assertGreater(len(floor), 0)
        for frame in range(scene.frame_current + 1, scene.frame_current + 4):
            scene.frame_set(frame)
        data = self.shirt.evaluated_get(depsgraph).data
        later = np.empty(len(data.vertices) * 3)
        data.vertices.foreach_get("co", later)
        later = later.reshape(-1, 3)
        kd = KDTree(len(later))
        for i, point in enumerate(later):
            kd.insert(point, i)
        kd.balance()
        self.assertLess(np.median([kd.find(point)[2] for point in floor]), 1e-5)

    def curtain(self):
        """Hanging sheet, from 0.75 to 1.25 high"""
        mesh = bpy.data.meshes.new("Curtain")
        bm = bmesh.new()
        bmesh.ops.create_grid(
            bm, x_segments=40, y_segments=40, size=0.25, matrix=Matrix.Rotation(1.5708, 4, "X")
        )
        bmesh.ops.translate(bm, verts=bm.verts, vec=(0.0, 0.0, 1.0))
        bm.to_mesh(mesh)
        bm.free()
        return new_object("Curtain", mesh)

    def tear(self, curtain, anchor="", release=0.0, across=True, rip_out=0.0, shape=0.5):
        """Curtain points, torn with physics across near its top, or in its middle"""
        set_active(curtain)
        scene = bpy.context.scene
        start = scene.frame_current
        scene.cursor.location = (-0.25, 0.0, 1.15) if across else (0.0, 0.0, 1.0)
        bpy.ops.mustardui.model_toolkit_cloth_tear(
            radius=0.04 if across else 0.08, duration=1, physics=True, anchor=anchor
        )
        modifier = curtain.modifiers["Cloth Tear"]
        effect.modifier_input(modifier, "Rip Out").value = rip_out
        effect.modifier_input(modifier, "Release").value = release
        effect.modifier_input(modifier, "Shape").value = shape
        # Not colliding with the model body around it
        effect.modifier_input(modifier, "Colliders").value = None
        # Changing the modifier inputs from Python does not tag the object
        curtain.update_tag()
        (control,) = self.controls(curtain)
        for frame, x in ((start, -0.3), (start + 10, 0.3)) if across else ():
            control.location.x = x
            control.keyframe_insert("location", frame=frame)

        depsgraph = bpy.context.evaluated_depsgraph_get()
        for frame in range(start, start + 40):
            scene.frame_set(frame)
        data = curtain.evaluated_get(depsgraph).data
        co = np.empty(len(data.vertices) * 3)
        data.vertices.foreach_get("co", co)
        return co.reshape(-1, 3)

    # With physics, the cloth cut off from the top of the mesh falls, the rest stays
    def test_physics_cut_off(self):
        curtain = self.curtain()
        z = self.tear(curtain)[:, 2]
        self.assertGreater((z > 1.2).sum(), 40)
        self.assertGreater((z < 0.05).sum(), len(curtain.data.vertices) / 2)

    # With an Anchor at the bottom, the cloth cut off above it falls instead
    def test_physics_anchor(self):
        curtain = self.curtain()
        curtain.vertex_groups.new(name="Hem").add(
            [v.index for v in curtain.data.vertices if v.co.z < 0.8], 1.0, "REPLACE"
        )
        z = self.tear(curtain, anchor="Hem")[:, 2]
        self.assertEqual((z > 1.2).sum(), 0)
        self.assertGreater(((z > 0.75) & (z < 1.1)).sum(), len(curtain.data.vertices) / 2)

    # With physics, the cloth around a hole sags when released, still without
    def test_physics_release(self):
        heights = []
        for release in (0.0, 0.1):
            curtain = self.curtain()
            # The pieces ripped out to the floor, the cloth below the hole left
            co = self.tear(curtain, release=release, across=False, rip_out=1.0)
            below = co[(np.abs(co[:, 0]) < 0.05) & (co[:, 2] > 0.6) & (co[:, 2] < 0.95)]
            heights.append(below[:, 2].max())
            bpy.data.objects.remove(curtain)
        self.assertLess(heights[1], heights[0] - 0.02)

    # The Shape holds the released cloth below the hole on the shape of the mesh, sagging less
    def test_physics_shape(self):
        heights = []
        for shape in (0.0, 1.0):
            curtain = self.curtain()
            co = self.tear(curtain, release=0.1, across=False, rip_out=1.0, shape=shape)
            below = co[(np.abs(co[:, 0]) < 0.05) & (co[:, 2] > 0.6) & (co[:, 2] < 0.95)]
            heights.append(below[:, 2].max())
            bpy.data.objects.remove(curtain)
        self.assertGreater(heights[1], heights[0] + 0.01)

    # A Pull grabs the cloth and moves away along its normal, ripping it and holding the ripped
    # part, or letting it fall, removed with the Cloth Tear
    def test_cloth_rip(self):
        held = []
        for in_hand in (True, False):
            curtain = self.curtain()
            set_active(curtain)
            scene = bpy.context.scene
            start = scene.frame_current
            scene.cursor.location = (0.0, 0.0, 1.0)
            bpy.ops.mustardui.model_toolkit_cloth_rip(radius=0.04, distance=0.2, duration=10)
            pull = bpy.context.view_layer.objects.active
            modifier = curtain.modifiers["Cloth Tear"]
            pulls = effect.modifier_input(modifier, "Pulls").value
            self.assertEqual(list(pulls.objects), [pull])
            self.assertTrue(effect.modifier_input(modifier, "Physics").value)
            effect.modifier_input(modifier, "Colliders").value = None
            effect.modifier_input(modifier, "In Hand").value = in_hand
            # Changing the modifier inputs from Python does not tag the object
            curtain.update_tag()

            depsgraph = bpy.context.evaluated_depsgraph_get()
            for frame in range(start, start + 40):
                scene.frame_set(frame)
            end = np.array(pull.matrix_world.translation)
            np.testing.assert_allclose(np.abs(end), (0.0, 0.2, 1.0), atol=1e-3)
            data = curtain.evaluated_get(depsgraph).data
            co = np.empty(len(data.vertices) * 3)
            data.vertices.foreach_get("co", co)
            co = co.reshape(-1, 3)
            # Ripped, no cloth stretched between the curtain, rumpled around the hole, and the Pull
            # anymore, above the floor
            gap = np.abs(co[co[:, 2] > 0.5, 1])
            self.assertEqual(((gap > 0.03) & (gap < 0.12)).sum(), 0)
            self.assertLess(len(data.polygons), len(curtain.data.polygons))
            held.append((np.linalg.norm(co - end, axis=1) < 0.06).sum())

            names = (pull.name, pulls.name)
            set_active(curtain)
            bpy.ops.mustardui.model_toolkit_remove_cloth_tear()
            self.assertNotIn(names[0], bpy.data.objects)
            self.assertNotIn(names[1], bpy.data.collections)
            bpy.data.objects.remove(curtain)
        self.assertGreater(held[0], 20)
        self.assertEqual(held[1], 0)

    # The Control is removed with the last Cloth Tear using it, with the Controls collections
    def test_remove(self):
        bpy.ops.mustardui.model_toolkit_cloth_tear()
        (control,) = self.controls(self.shirt)
        name = control.name
        collections = {
            effect.modifier_input(x.modifiers["Cloth Tear"], "Controls").value.name
            for x in (self.shirt, self.pants)
        }

        set_active(self.shirt)
        bpy.ops.mustardui.model_toolkit_remove_cloth_tear()
        self.assertNotIn("Cloth Tear", self.shirt.modifiers)
        self.assertIn(name, bpy.data.objects)

        set_active(self.pants)
        bpy.ops.mustardui.model_toolkit_remove_cloth_tear()
        self.assertNotIn("Cloth Tear", self.pants.modifiers)
        self.assertNotIn(name, bpy.data.objects)
        self.assertFalse(collections & set(bpy.data.collections.keys()))

    # Another tear on a mesh adds its Control to the same modifier, the simulation needing a
    # fixed mesh
    def test_controls(self):
        set_active(self.shirt)
        bpy.ops.mustardui.model_toolkit_cloth_tear(physics=True)
        bpy.context.scene.cursor.location = (-0.6, -0.6, 0.4)
        set_active(self.shirt)
        bpy.ops.mustardui.model_toolkit_cloth_tear(physics=True)
        self.assertEqual(
            [m.name for m in self.shirt.modifiers], ["Armature", "Cloth Tear", "Subdivision"]
        )
        controls = self.controls(self.shirt)
        self.assertEqual(len(controls), 2)

        # Torn at both Controls, without the loose pieces free to swing through them
        effect.modifier_input(self.shirt.modifiers["Cloth Tear"], "Physics").value = False
        self.shirt.update_tag()
        self.shirt.modifiers["Subdivision"].show_viewport = False
        scene = bpy.context.scene
        for frame in range(scene.frame_current, scene.frame_current + 30):
            scene.frame_set(frame)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        data = self.shirt.evaluated_get(depsgraph).data
        co = np.empty(len(data.vertices) * 3)
        data.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        for control in controls:
            distance = np.linalg.norm(co - control.matrix_world.translation, axis=1)
            self.assertGreater(distance.min(), control.matrix_world.to_scale().x * 0.99)

        names = [x.name for x in controls]
        set_active(self.shirt)
        bpy.ops.mustardui.model_toolkit_remove_cloth_tear()
        self.assertFalse(set(names) & set(bpy.data.objects.keys()))


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

    def balls(self, name, *xs, radius=0.05):
        mesh = bpy.data.meshes.new(name)
        bm = bmesh.new()
        for x in xs:
            matrix = Matrix.Translation((x, 0.0, 0.0))
            bmesh.ops.create_uvsphere(
                bm, u_segments=32, v_segments=16, radius=radius, matrix=matrix
            )
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

    # Hidden outside the frame range, placed on the Start Frame where the meshes are then
    def test_frame_range(self):
        for physics in (True, False):
            with self.subTest(physics=physics):
                lip = self.pull(physics=physics)
                modifier = lip.modifiers["Sticky Strands"]
                start = effect.modifier_input(modifier, "Start Frame").value
                self.assertEqual(start, self.scene.frame_start)
                effect.modifier_input(modifier, "Start Frame").value = start + 5
                effect.modifier_input(modifier, "End Frame").value = start + 8
                lip.update_tag()
                self.scene.frame_set(start)
                self.play(4)
                self.assertEqual(len(self.strands(lip)), 0)
                self.play(1)
                finger = bpy.data.objects["Finger"]
                self.assertAlmostEqual(
                    self.strands(lip)[:, 0].max(), finger.location.x - 0.05, delta=0.005
                )
                self.play(4)
                self.assertEqual(len(self.strands(lip)), 0)
                bpy.data.objects.remove(lip)
                bpy.data.objects.remove(finger)

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
    # Effects added later go before the strands, not to affect them
    def test_effect_order(self):
        lip = self.pull(physics=False)
        set_active(lip)
        bpy.ops.mustardui.model_toolkit_ripple()
        self.assertEqual([m.name for m in lip.modifiers], ["Ripple", "Sticky Strands"])

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

    # Broken strands swinging under the edge of an open mesh in the Colliders are not pushed
    # through it to its top
    def test_open_collider(self):
        lip = self.pull(physics=True)
        mesh = bpy.data.meshes.new("Floor")
        mesh.from_pydata(
            [(0, -0.1, 0), (0.2, -0.1, 0), (0.2, 0.1, 0), (0, 0.1, 0)], [], [(0, 1, 2, 3)]
        )
        colliders = bpy.data.collections.new("Colliders")
        new_object("Floor", mesh, colliders).location.z = -0.07
        effect.modifier_input(lip.modifiers["Sticky Strands"], "Colliders").value = colliders
        lip.update_tag()
        self.scene.frame_set(self.scene.frame_start)
        before = self.strands(lip)
        for _ in range(50):
            self.play(1)
            after = self.strands(lip)
            if len(after) == len(before):
                over = (after[:, 0] > 0.0) & (after[:, 0] < 0.2) & (np.abs(after[:, 1]) < 0.1)
                through = over & (before[:, 2] < -0.075) & (after[:, 2] > -0.065)
                self.assertFalse(through.any())
            before = after

    # Smoothing the strands straightens their sag between the fixed ends
    def test_smooth(self):
        for physics in (False, True):
            with self.subTest(physics=physics):
                lip = self.pull(physics=physics)
                self.play(10)
                modifier = lip.modifiers["Sticky Strands"]
                # Not pulled onto the surfaces, which would hide moved ends
                effect.modifier_input(modifier, "Sticky Ends").value = 0.0
                sags, ends = [], []
                for smooth in (0, 30):
                    effect.modifier_input(modifier, "Smooth").value = smooth
                    lip.update_tag()
                    self.scene.frame_set(self.scene.frame_current)
                    co = self.strands(lip)
                    sags.append(co[np.abs(co[:, 0] - 0.1) < 0.01][:, 2].min())
                    # Centers of the rings at the ends, turning with the strands next to them
                    factor = self.attributes(lip)["sticky_factor"]
                    ends.append(co[(factor < 0.001) | (factor > 0.999)].reshape(-1, 12, 3).mean(1))
                self.assertGreater(sags[1], sags[0])
                np.testing.assert_allclose(ends[1], ends[0], atol=1e-4)
                bpy.data.objects.remove(lip)
                bpy.data.objects.remove(bpy.data.objects["Finger"])

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

    # Faces larger than the strands, the flared ends staying on them and not pulled inside
    def test_large_spheres(self):
        lip = self.balls("Lip", 0.0, radius=1.0)
        set_active(self.balls("Finger", 2.0, radius=1.0))
        lip.select_set(True)

        bpy.ops.mustardui.model_toolkit_sticky_strands()
        self.scene.frame_set(self.scene.frame_start)
        co = self.strands(lip)
        self.assertGreater(len(co), 0)
        self.assertGreater(np.linalg.norm(co, axis=1).min(), 0.95)

    # The Control is removed with the Sticky Strands
    def test_remove(self):
        mouth = self.balls("Mouth", 0.0)
        set_active(mouth)
        bpy.ops.mustardui.model_toolkit_sticky_strands()
        name = effect.modifier_input(mouth.modifiers["Sticky Strands"], "Control").value.name

        bpy.ops.mustardui.model_toolkit_remove_sticky_strands()
        self.assertNotIn("Sticky Strands", mouth.modifiers)
        self.assertNotIn(name, bpy.data.objects)

    # Converted to a mesh with the shader attributes, as applying the modifier discards them
    def test_convert(self):
        lip = self.pull(physics=True)
        self.play(10)
        co = self.strands(lip)
        name = effect.modifier_input(lip.modifiers["Sticky Strands"], "Control").value.name

        bpy.ops.mustardui.model_toolkit_convert_sticky_strands()
        self.assertNotIn("Sticky Strands", lip.modifiers)
        self.assertNotIn(name, bpy.data.objects)
        strands = bpy.data.objects["Lip Sticky Strands"]
        self.assertEqual(strands.parent, lip)
        self.assertIn("sticky_factor", strands.data.attributes)
        self.assertEqual(strands.data.materials[0].name, "MustardUI Sticky Strands")
        converted = np.array([strands.matrix_world @ v.co for v in strands.data.vertices])
        np.testing.assert_allclose(converted, co, atol=1e-5)


@unittest.skipUnless(effect.effects_available(), "Needs Blender 5.2")
class TestStickyLiquid(BlenderTestCase):
    def setUp(self):
        super().setUp()
        configure_model(build_model())
        self.armature = bpy.data.objects["Tester Armature"]
        self.body = bpy.data.objects["Tester Body"]
        # Facing out, as the liquid sticks on the side the normals face
        self.body.data.flip_normals()
        self.scene = bpy.context.scene
        self.scene.cursor.location = (0.1, 0.0, 1.8)
        set_active(self.body)
        bpy.ops.mustardui.model_toolkit_sticky_liquid()
        self.liquid = bpy.data.objects["Sticky Liquid"]
        self.modifier = self.liquid.modifiers["Sticky Liquid"]
        self.control = effect.modifier_input(self.modifier, "Control").value

    def points(self):
        depsgraph = bpy.context.evaluated_depsgraph_get()
        geometry = self.liquid.evaluated_get(depsgraph).evaluated_geometry()
        co = np.empty(len(geometry.pointcloud.points) * 3)
        geometry.pointcloud.points.foreach_get("co", co)
        return co.reshape(-1, 3)

    # The liquid falls from the Control, sticks on the top of the body, and follows it as the
    # armature deforms it
    def test_sticky_liquid(self):
        self.assertEqual(self.control.MustardUI_tools_creators_type, "EFFECT_STICKY_LIQUID")
        self.assertEqual(bpy.context.active_object, self.control)
        targets = effect.modifier_input(self.modifier, "Targets").value
        self.assertEqual(set(targets.objects), {self.body})
        self.assertTrue(self.body.add_rest_position_attribute)
        self.assertTrue(all(self.liquid.lock_location))
        # The mesh bakeable frame by frame, besides the simulation
        self.assertEqual(
            {(b.node.bl_idname, b.bake_mode) for b in self.modifier.bakes},
            {("GeometryNodeSimulationOutput", "STILL"), ("GeometryNodeBake", "ANIMATION")},
        )

        # No liquid yet, and no warnings of the nodes making its mesh
        self.scene.frame_set(self.scene.frame_start)
        self.liquid.evaluated_get(bpy.context.evaluated_depsgraph_get())
        self.assertFalse(list(self.modifier.node_warnings))

        effect.modifier_input(self.modifier, "Mesh").value = False
        self.liquid.update_tag()
        bone = self.armature.pose.bones["spine"]
        start = self.scene.frame_start
        for frame, y in ((40, 0.0), (50, 0.2)):
            bone.location.y = y
            bone.keyframe_insert("location", frame=start + frame)
        for frame in range(start, start + 41):
            self.scene.frame_set(frame)
        co = self.points()
        self.assertGreater(len(co), 100)
        np.testing.assert_allclose(co[:, 2], 1.501, atol=0.001)
        self.assertLess(np.abs(co[:, :2]).max(), 0.5)

        for frame in range(start + 41, start + 51):
            self.scene.frame_set(frame)
        np.testing.assert_allclose(self.points()[:, 2], 1.701, atol=0.001)

        # The mesh of the liquid
        effect.modifier_input(self.modifier, "Mesh").value = True
        self.liquid.update_tag()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        mesh = self.liquid.evaluated_get(depsgraph).data
        self.assertGreater(len(mesh.vertices), 100)
        self.assertIn("liquid_color", mesh.attributes)

    # At half the Time Scale the liquid moves as at twice the frame rate, slower than at full speed
    def test_time_scale(self):
        self.control.location = (5.0, 0.0, 1.8)
        effect.modifier_input(self.modifier, "Mesh").value = False

        def points(time_scale, fps):
            effect.modifier_input(self.modifier, "Time Scale").value = time_scale
            self.scene.render.fps = fps
            self.liquid.update_tag()
            for frame in range(self.scene.frame_start, self.scene.frame_start + 20):
                self.scene.frame_set(frame)
            return self.points()

        half = points(0.5, 24)
        np.testing.assert_allclose(half, points(1.0, 48), atol=1e-5)
        self.assertLess(points(1.0, 24)[:, 2].mean(), half[:, 2].mean() - 0.3)

    # Poured on a ball, the liquid drips from under it on strings, none without String Length
    def test_strings(self):
        mesh = bpy.data.meshes.new("Ball")
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=0.15)
        bm.to_mesh(mesh)
        bm.free()
        ball = new_object("Ball", mesh)
        effect.modifier_input(self.modifier, "Targets").value.objects.link(ball)
        self.control.location = (0.03, 0.0, 0.45)
        effect.modifier_input(self.modifier, "Rate").value = 600.0
        effect.modifier_input(self.modifier, "Mesh").value = False

        def strings(length):
            """Most points of the particles and their strings, the liquid dripping off"""
            effect.modifier_input(self.modifier, "String Length").value = length
            self.liquid.update_tag()
            depsgraph = bpy.context.evaluated_depsgraph_get()
            points = 0
            for frame in range(self.scene.frame_start, self.scene.frame_start + 220):
                self.scene.frame_set(frame)
                geometry = self.liquid.evaluated_get(depsgraph).evaluated_geometry()
                if geometry.pointcloud:
                    points = max(points, len(geometry.pointcloud.points))
            self.assertLess(self.points()[:, 2].min(), -0.17)
            return points

        self.assertEqual(strings(0.0), 600)
        self.assertGreater(strings(0.1), 600)

    # Removing from the Control removes the liquid, the Control and the collections, keeping the
    # Targets
    def test_remove(self):
        collection = self.liquid.users_collection[0].name
        names = {self.liquid.name, self.control.name}
        bpy.ops.mustardui.model_toolkit_remove_sticky_liquid()
        self.assertFalse(names & set(bpy.data.objects.keys()))
        self.assertNotIn(collection, bpy.data.collections)
        self.assertNotIn("Sticky Liquid Targets", bpy.data.collections)
        self.assertIn(self.body.name, bpy.context.scene.objects)
        self.assertFalse(bpy.ops.mustardui.model_toolkit_remove_sticky_liquid.poll())

    # Converted to a mesh following the Target, with the shader attributes, removing the effect
    def test_convert(self):
        for frame in range(self.scene.frame_start, self.scene.frame_start + 30):
            self.scene.frame_set(frame)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated = self.liquid.evaluated_get(depsgraph).data
        co = np.array([v.co for v in evaluated.vertices])
        self.assertGreater(len(co), 100)
        collection = self.liquid.users_collection[0]
        names = {self.liquid.name, self.control.name}

        bpy.ops.mustardui.model_toolkit_convert_sticky_liquid()
        self.assertFalse(names & set(bpy.data.objects.keys()))
        self.assertNotIn("Sticky Liquid Targets", bpy.data.collections)
        liquid = bpy.data.objects["Sticky Liquid Mesh"]
        self.assertEqual(liquid.users_collection, (collection,))
        self.assertEqual(liquid.parent, self.body)
        self.assertFalse(liquid.modifiers)
        self.assertIn("liquid_color", liquid.data.attributes)
        self.assertIn("liquid_thin", liquid.data.attributes)
        self.assertEqual(
            list(liquid.data.materials), [bpy.data.materials["MustardUI Sticky Liquid"]]
        )
        self.assertEqual({p.material_index for p in liquid.data.polygons}, {0})
        converted = np.array([liquid.matrix_world @ v.co for v in liquid.data.vertices])
        np.testing.assert_allclose(converted, co, atol=1e-5)


@unittest.skipUnless(effect.effects_available(), "Needs Blender 5.2")
class TestWet(BlenderTestCase):
    def setUp(self):
        super().setUp()
        configure_model(build_model())
        self.body = bpy.data.objects["Tester Body"]
        self.shirt = bpy.data.objects["Casual - Shirt"]
        bm = bmesh.new()
        bm.from_mesh(self.body.data)
        bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=8, use_grid_fill=True)
        bm.to_mesh(self.body.data)
        bm.free()
        self.body.modifiers.new("Subdivision", "SUBSURF")
        self.skin = bpy.data.materials.new("Skin")
        for obj in (self.body, self.shirt):
            obj.data.materials.append(self.skin)
        set_active(self.body)

    def add(self, obj, density=200.0):
        set_active(obj)
        bpy.ops.mustardui.model_toolkit_wet()
        modifier = obj.modifiers[-2 if obj == self.body else -1]
        effect.modifier_input(modifier, "Density").value = density
        obj.update_tag()
        return modifier

    def drops(self, obj):
        """World positions of the drops, in their order"""
        depsgraph = bpy.context.evaluated_depsgraph_get()
        return np.array(
            [
                x.matrix_world.to_translation()
                for x in depsgraph.object_instances
                if x.is_instance and x.parent and x.parent.original == obj
            ]
        ).reshape(-1, 3)

    def wetness(self, obj):
        data = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
        values = np.empty(len(data.vertices))
        data.attributes["wetness"].data.foreach_get("value", values)
        return values

    # The Control covers the meshes following their bone, wetting them with drops on the surface
    # and the film on their materials
    def test_wet(self):
        modifier = self.add(self.body)
        self.assertEqual([m.type for m in self.body.modifiers][-2:], ["NODES", "SUBSURF"])
        control = effect.modifier_input(modifier, "Control").value
        self.assertEqual(control.MustardUI_tools_creators_type, "EFFECT_WET")
        self.assertEqual((control.parent_type, control.parent_bone), ("BONE", "spine"))
        self.assertEqual(control.users_collection, (bpy.context.scene.collection,))
        self.assertGreater(self.wetness(self.body).min(), 0.7)
        # Read by the film, with the rest position, in a single attribute for EEVEE
        data = self.body.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
        self.assertEqual(data.attributes["wet"].data_type, "FLOAT_COLOR")

        output = self.skin.node_tree.nodes["Material Output"].inputs["Surface"].links[0].from_node
        self.assertEqual(output.node_tree.name, "MustardUI Wet Film")
        self.assertEqual(output.inputs["Shader"].links[0].from_node.type, "BSDF_PRINCIPLED")

        drops = self.drops(self.body)
        # Area of the cube times the density, fewer in the drier patches and between clusters
        self.assertGreater(len(drops), 6 * 200 * 0.4)
        self.assertLess(len(drops), 6 * 200)
        np.testing.assert_allclose(np.abs(drops - (0, 0, 1)).max(axis=1), 0.5, atol=1e-5)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        geometry = self.body.evaluated_get(depsgraph).evaluated_geometry()
        references = geometry.instance_references()
        (mesh,) = [x.mesh for x in references if x.mesh]
        materials = {mesh.materials[p.material_index].name for p in mesh.polygons}
        self.assertEqual(materials, {"MustardUI Wet Drops"})
        self.assertEqual([x.message for x in modifier.node_warnings], [])

    # The drops follow the deformed mesh
    def test_follow(self):
        self.add(self.body)
        before = self.drops(self.body)
        armature = self.body.parent
        bone = armature.pose.bones["spine"]
        bone.rotation_mode = "XYZ"
        bone.rotation_euler = (0.3, 0.2, 0.0)
        bpy.context.view_layer.update()
        matrix = armature.matrix_world @ bone.matrix @ bone.bone.matrix_local.inverted()
        moved = np.array([matrix @ Vector(x) for x in before])
        np.testing.assert_allclose(self.drops(self.body), moved, atol=1e-5)

    # Drying or shrinking the Control removes drops, the others staying in place
    def test_dry(self):
        modifier = self.add(self.body)
        drops = {tuple(x) for x in self.drops(self.body).round(6)}
        effect.modifier_input(modifier, "Wetness").value = 0.5
        self.body.update_tag()
        half = {tuple(x) for x in self.drops(self.body).round(6)}
        self.assertLess(len(half), len(drops) * 0.7)
        self.assertLessEqual(half, drops)

        control = effect.modifier_input(modifier, "Control").value
        control.scale = (0.5, 0.5, 0.5)
        bpy.context.view_layer.update()
        self.assertLess(self.wetness(self.body).min(), 0.01)
        self.assertLessEqual({tuple(x) for x in self.drops(self.body).round(6)}, half)

        effect.modifier_input(modifier, "Wetness").value = 0.0
        self.body.update_tag()
        self.assertEqual(len(self.drops(self.body)), 0)
        self.assertEqual(self.wetness(self.body).max(), 0.0)

    # A second Wet keeps the wetness of the first, adding drops only where it is wetter
    def test_stack(self):
        first = self.add(self.body)
        effect.modifier_input(first, "Control").value.scale = (0.5, 0.5, 0.5)
        bpy.context.view_layer.update()
        drops = {tuple(x) for x in self.drops(self.body).round(6)}
        self.add(self.body)
        stacked = self.drops(self.body).round(6)
        self.assertEqual(len({tuple(x) for x in stacked}), len(stacked))
        self.assertLess(drops, {tuple(x) for x in stacked})
        self.assertGreater(self.wetness(self.body).min(), 0.7)

    # With physics the large drops run down from the Start Frame, leaving lines of water
    def test_physics(self):
        modifier = self.add(self.body)
        scene = bpy.context.scene
        start = scene.frame_current
        static = self.drops(self.body)
        scene.frame_set(start + 1)
        np.testing.assert_allclose(self.drops(self.body), static)

        effect.modifier_input(modifier, "Physics").value = True
        effect.modifier_input(modifier, "Start Frame").value = start
        # Most of the large drops running right away
        effect.modifier_input(modifier, "Run Rate").value = 20.0
        self.body.update_tag()
        counts, heights, lines = [], [], []
        for frame in range(start, start + 14):
            scene.frame_set(frame)
            depsgraph = bpy.context.evaluated_depsgraph_get()
            geometry = self.body.evaluated_get(depsgraph).evaluated_geometry()
            points = geometry.instances_pointcloud()
            ids = np.zeros(len(points.points), dtype=np.int32)
            if ".wet_id" in points.attributes:
                points.attributes[".wet_id"].data.foreach_get("value", ids)
            references = geometry.instance_references()
            lines.append(sum(len(x.mesh.vertices) for x in references if x.mesh))
            drops = self.drops(self.body)
            counts.append(len(drops))
            # Height of each running drop
            transforms = np.zeros(len(points.points) * 16)
            points.attributes["instance_transform"].data.foreach_get("value", transforms)
            z = transforms.reshape(-1, 4, 4)[:, 3, 2]
            heights.append({i: x for i, x in zip(ids, z, strict=True) if i})
        self.assertFalse(heights[0])
        # Lower than they started, those still on the mesh
        common = heights[3].keys() & heights[-1].keys()
        self.assertGreater(len(common), 5)
        self.assertLess(np.mean([heights[-1][i] - heights[3][i] for i in common]), -0.01)
        # The drop mesh only, then with the lines growing
        self.assertGreater(lines[2], lines[0])
        self.assertGreater(lines[-1], lines[2])
        # The drops not growing in number, only swept away
        self.assertLess(max(counts), counts[0] * 1.05)
        self.assertEqual([x.message for x in modifier.node_warnings], [])

    # With dripping, the running drops grow on the wet surface and drip from below, splashing on
    # the floor
    def test_dripping(self):
        mesh = bpy.data.meshes.new("Ball")
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=0.15)
        bm.to_mesh(mesh)
        bm.free()
        ball = new_object("Ball", mesh)
        ball.data.materials.append(self.skin)
        modifier = self.add(ball, density=3000.0)
        scene = bpy.context.scene
        start = scene.frame_current
        for name, value in (
            ("Physics", True),
            ("Dripping", True),
            ("Floor", -0.3),
            ("Run Rate", 20.0),
            ("Drip Radius", 0.0012),
        ):
            effect.modifier_input(modifier, name).value = value
        effect.modifier_input(modifier, "Start Frame").value = start
        ball.update_tag()
        falling = 0
        for frame in range(start, start + 80):
            scene.frame_set(frame)
            depsgraph = bpy.context.evaluated_depsgraph_get()
            geometry = ball.evaluated_get(depsgraph).evaluated_geometry()
            points = geometry.instances_pointcloud()
            landed = np.zeros(len(points.points))
            velocity = np.zeros(len(points.points) * 3)
            if ".wet_landed" in points.attributes:
                points.attributes[".wet_landed"].data.foreach_get("value", landed)
                points.attributes[".wet_velocity"].data.foreach_get("vector", velocity)
            moving = np.linalg.norm(velocity.reshape(-1, 3), axis=1) > 0
            falling = max(falling, int((moving & (landed < 0.5)).sum()))
        self.assertGreater(falling, 0)
        self.assertGreater((landed > 0.5).sum(), 0)
        self.assertEqual([x.message for x in modifier.node_warnings], [])

    # The film gets the normal of the material, from its normal image outside the node groups
    def test_normal(self):
        nodes, links = self.skin.node_tree.nodes, self.skin.node_tree.links
        image = nodes.new("ShaderNodeTexImage")
        image.image = bpy.data.images.new("Normal", 4, 4)
        normal_map = nodes.new("ShaderNodeNormalMap")
        links.new(image.outputs["Color"], normal_map.inputs["Color"])
        links.new(normal_map.outputs["Normal"], nodes["Principled BSDF"].inputs["Normal"])
        # In a node group, as from importers
        layered = bpy.data.materials.new("Layered")
        self.shirt.data.materials.clear()
        self.shirt.data.materials.append(layered)
        group = bpy.data.node_groups.new("Skin Shader", "ShaderNodeTree")
        group.interface.new_socket("Normal Image", in_out="INPUT", socket_type="NodeSocketColor")
        group.interface.new_socket("BSDF", in_out="OUTPUT", socket_type="NodeSocketShader")
        inner = group.nodes.new("ShaderNodeNormalMap")
        bsdf = group.nodes.new("ShaderNodeBsdfPrincipled")
        group.links.new(group.nodes.new("NodeGroupInput").outputs[0], inner.inputs["Color"])
        group.links.new(inner.outputs["Normal"], bsdf.inputs["Normal"])
        group.links.new(bsdf.outputs[0], group.nodes.new("NodeGroupOutput").inputs[0])
        nodes = layered.node_tree.nodes
        skin = nodes.new("ShaderNodeGroup")
        skin.node_tree = group
        outer = nodes.new("ShaderNodeTexImage")
        outer.image = image.image
        layered.node_tree.links.new(outer.outputs["Color"], skin.inputs[0])
        layered.node_tree.links.new(skin.outputs[0], nodes["Material Output"].inputs["Surface"])

        self.add(self.body)
        self.add(self.shirt)
        film = self.skin.node_tree.nodes["Material Output"].inputs["Surface"].links[0].from_node
        self.assertEqual(film.inputs["Normal"].links[0].from_node, normal_map)
        film = nodes["Material Output"].inputs["Surface"].links[0].from_node
        copy = film.inputs["Normal"].links[0].from_node
        self.assertEqual(copy.type, "NORMAL_MAP")
        self.assertEqual(copy.inputs["Color"].links[0].from_node, outer)

        set_active(self.shirt)
        bpy.ops.mustardui.model_toolkit_remove_wet()
        self.assertFalse([n for n in nodes if n.type == "NORMAL_MAP"])
        set_active(self.body)
        bpy.ops.mustardui.model_toolkit_remove_wet()
        self.assertIn(normal_map, list(self.skin.node_tree.nodes))

    # The film stays on the materials of the other wet meshes, and the Controls are removed
    def test_remove(self):
        self.add(self.body)
        self.add(self.shirt)
        films = [n for n in self.skin.node_tree.nodes if n.type == "GROUP"]
        self.assertEqual(len(films), 1)

        set_active(self.body)
        bpy.ops.mustardui.model_toolkit_remove_wet()
        self.assertNotIn("Wet", self.body.modifiers)
        self.assertEqual([n for n in self.skin.node_tree.nodes if n.type == "GROUP"], films)
        controls = [x for x in bpy.data.objects if x.MustardUI_tools_creators_type]
        self.assertEqual(len(controls), 1)

        set_active(self.shirt)
        bpy.ops.mustardui.model_toolkit_remove_wet()
        surface = self.skin.node_tree.nodes["Material Output"].inputs["Surface"]
        self.assertEqual(surface.links[0].from_node.type, "BSDF_PRINCIPLED")
        self.assertFalse([n for n in self.skin.node_tree.nodes if n.type == "GROUP"])
        self.assertFalse([x for x in bpy.data.objects if x.MustardUI_tools_creators_type])
        self.assertFalse(bpy.ops.mustardui.model_toolkit_remove_wet.poll())


@unittest.skipUnless(effect.effects_available(), "Needs Blender 5.2")
class TestMarks(BlenderTestCase):
    def setUp(self):
        super().setUp()
        configure_model(build_model())
        self.body = bpy.data.objects["Tester Body"]
        self.shirt = bpy.data.objects["Casual - Shirt"]
        # Points 5 cm apart
        bm = bmesh.new()
        bm.from_mesh(self.body.data)
        bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=19, use_grid_fill=True)
        bm.to_mesh(self.body.data)
        bm.free()
        self.body.modifiers.new("Subdivision", "SUBSURF")
        self.skin = self.body.data.materials[0]
        self.shirt.data.materials.append(self.skin)
        # On the front of the body
        bpy.context.scene.cursor.location = (0.1, -0.6, 1.0)

    def add(self, obj, **settings):
        set_active(obj)
        bpy.ops.mustardui.model_toolkit_marks(radius=0.15, **settings)
        return [m for m in obj.modifiers if effect.is_effect(m, "MustardUI Marks")][-1]

    def marks(self, obj):
        """World positions of the evaluated points, their edge distance, amount and shape"""
        data = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
        mark, color = (np.empty(len(data.vertices) * 4) for _ in range(2))
        data.attributes["mark"].data.foreach_get("color", mark)
        data.attributes["mark_color"].data.foreach_get("color", color)
        mark, color = mark.reshape(-1, 4), color.reshape(-1, 4)
        co = np.array([obj.matrix_world @ v.co for v in data.vertices])
        return co, mark[:, 2], 1.0 - mark[:, 3], color[:, 3]

    # The Control on the vertex closest to the 3D cursor, facing out of the mesh and following its
    # bone, marks the points inside its sphere, tinting the base color of the materials
    def test_marks(self):
        bsdf = self.skin.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value = (0.9, 0.7, 0.6, 1.0)
        modifier = self.add(self.body)
        self.assertEqual([m.type for m in self.body.modifiers][-2:], ["NODES", "SUBSURF"])
        control = effect.modifier_input(modifier, "Control").value
        self.assertEqual(control.MustardUI_tools_creators_type, "EFFECT_MARKS")
        self.assertEqual((control.parent_type, control.parent_bone), ("BONE", "spine"))
        self.assertEqual(control.users_collection, (bpy.context.scene.collection,))
        matrix = control.matrix_world
        np.testing.assert_allclose(matrix.to_translation(), (0.1, -0.5, 1.0), atol=1e-5)
        # Along the normal, inward on the test cube
        np.testing.assert_allclose(matrix.to_3x3().col[2], (0.0, 0.15, 0.0), atol=1e-5)
        np.testing.assert_allclose(matrix.to_3x3().col[1], (0.0, 0.0, 0.15), atol=1e-5)
        data = self.body.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
        for name in ("mark", "mark_color"):
            self.assertEqual(data.attributes[name].data_type, "FLOAT_COLOR")

        # On the points of the mesh, not smoothed
        self.body.modifiers["Subdivision"].show_viewport = False
        co, edge, amount, shape = self.marks(self.body)
        distance = np.linalg.norm(co - (0.1, -0.5, 1.0), axis=1)
        np.testing.assert_allclose(edge, distance / 0.15 - 1.0, atol=1e-5)
        self.assertGreater(amount[distance < 0.15].min(), 0.2)
        self.assertLessEqual(amount.max(), 0.6 + 1e-6)
        np.testing.assert_allclose(shape, 1.0)

        tint = bsdf.inputs["Base Color"].links[0].from_node
        self.assertEqual(tint.node_tree.name, "MustardUI Marks Tint")
        np.testing.assert_allclose(tint.inputs["Color"].default_value, (0.9, 0.7, 0.6, 1.0))
        self.assertEqual([x.message for x in modifier.node_warnings], [])

    # A left hand print mirrors the Control, inside the palm and not above the fingers
    def test_hand(self):
        modifier = self.add(self.body, kind="HAND", left=True)
        control = effect.modifier_input(modifier, "Control").value
        self.assertLess(control.matrix_world.determinant(), 0.0)
        co, edge, amount, shape = self.marks(self.body)
        np.testing.assert_allclose(shape, -0.1)
        for local, inside in (((0.0, -0.42, 0.0), True), ((0.0, 1.0, 0.0), False)):
            nearest = np.linalg.norm(co - control.matrix_world @ Vector(local), axis=1).argmin()
            self.assertEqual(edge[nearest] < 0.0, inside)
            self.assertGreater(amount[nearest], 0.0)
        self.assertEqual([x.message for x in modifier.node_warnings], [])

    # Lasting marks stay where the Control was, painting along its path, and fade
    def test_lasting(self):
        modifier = self.add(self.body)
        scene = bpy.context.scene
        start = scene.frame_current
        effect.modifier_input(modifier, "Lasting").value = True
        effect.modifier_input(modifier, "Strength").value = 1.0
        control = effect.modifier_input(modifier, "Control").value
        control.keyframe_insert("location", frame=start)
        location = control.location.copy()
        # Sideways on the surface, then away from it (into the test cube, its normals inward)
        control.location = location + control.matrix_basis.col[0].xyz.normalized() * 0.3
        control.keyframe_insert("location", frame=start + 5)
        control.location = location + control.matrix_basis.col[2].xyz.normalized() * 2.0
        control.keyframe_insert("location", frame=start + 6)
        self.body.update_tag()
        for frame in range(start, start + 9):
            scene.frame_set(frame)
        co, edge, amount, _ = self.marks(self.body)
        side = control.matrix_world.col[0].xyz.normalized()
        for x in (0.0, 0.15, 0.3):
            nearest = np.linalg.norm(co - Vector((0.1, -0.5, 1.0)) - side * x, axis=1).argmin()
            self.assertLess(edge[nearest], -0.5)
            self.assertGreater(amount[nearest], 0.2)
        self.assertEqual([x.message for x in modifier.node_warnings], [])

        effect.modifier_input(modifier, "Lasting").value = False
        self.body.update_tag()
        self.assertGreater(self.marks(self.body)[1].min(), 0.0)

        effect.modifier_input(modifier, "Lasting").value = True
        effect.modifier_input(modifier, "Fade").value = 0.1
        self.body.update_tag()
        for frame in range(start, start + 12):
            scene.frame_set(frame)
        _, edge, amount, _ = self.marks(self.body)
        self.assertLess(amount[edge < 0.0].max(), 1e-6)

    # A second mark keeps the first one, each with its own color
    def test_stack(self):
        self.add(self.body)
        bpy.context.scene.cursor.location = (-0.2, -0.6, 1.2)
        modifier = self.add(self.body, kind="BRUISE")
        effect.modifier_input(modifier, "Color").value = (0.0, 0.0, 1.0, 1.0)
        self.body.update_tag()
        co, edge, _, shape = self.marks(self.body)
        data = self.body.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
        color = np.empty(len(data.vertices) * 4)
        data.attributes["mark_color"].data.foreach_get("color", color)
        color = color.reshape(-1, 4)
        for center, blue, falloff in (((0.1, -0.5, 1.0), 0.45, 1.0), ((-0.2, -0.5, 1.2), 1.0, 0.7)):
            nearest = np.linalg.norm(co - center, axis=1).argmin()
            self.assertLess(edge[nearest], -0.5)
            self.assertAlmostEqual(color[nearest, 2], blue, places=5)
            self.assertAlmostEqual(shape[nearest], falloff, places=5)

    # The tint goes before the base color of the shaders, also behind mix shaders and in groups
    def test_materials(self):
        layered = bpy.data.materials.new("Layered")
        nodes, links = layered.node_tree.nodes, layered.node_tree.links
        bsdf = nodes["Principled BSDF"]
        image = nodes.new("ShaderNodeTexImage")
        links.new(image.outputs["Color"], bsdf.inputs["Base Color"])
        group = bpy.data.node_groups.new("Skin Shader", "ShaderNodeTree")
        group.interface.new_socket("Color", in_out="INPUT", socket_type="NodeSocketColor")
        group.interface.new_socket("BSDF", in_out="OUTPUT", socket_type="NodeSocketShader")
        skin = nodes.new("ShaderNodeGroup")
        skin.node_tree = group
        mix = nodes.new("ShaderNodeMixShader")
        links.new(bsdf.outputs[0], mix.inputs[1])
        links.new(skin.outputs[0], mix.inputs[2])
        # Under a group wrapping the shader, with a color of its own
        wrapper = bpy.data.node_groups.new("Glow", "ShaderNodeTree")
        for name, socket_type in (("Shader", "NodeSocketShader"), ("Color", "NodeSocketColor")):
            wrapper.interface.new_socket(name, in_out="INPUT", socket_type=socket_type)
        wrapper.interface.new_socket("Shader", in_out="OUTPUT", socket_type="NodeSocketShader")
        glow = nodes.new("ShaderNodeGroup")
        glow.node_tree = wrapper
        links.new(mix.outputs[0], glow.inputs["Shader"])
        links.new(glow.outputs[0], nodes["Material Output"].inputs["Surface"])
        self.shirt.data.materials.clear()
        self.shirt.data.materials.append(layered)

        self.add(self.shirt)
        tint = bsdf.inputs["Base Color"].links[0].from_node
        self.assertEqual(tint.inputs["Color"].links[0].from_node, image)
        self.assertEqual(skin.inputs["Color"].links[0].from_node.node_tree, tint.node_tree)
        self.assertFalse(glow.inputs["Color"].is_linked)

        set_active(self.shirt)
        bpy.ops.mustardui.model_toolkit_remove_marks()
        self.assertEqual(bsdf.inputs["Base Color"].links[0].from_node, image)
        self.assertFalse(skin.inputs["Color"].is_linked)
        self.assertEqual(len(nodes), 6)

    # The tint stays on the materials of the other marked meshes, and the Controls are removed
    def test_remove(self):
        self.add(self.body)
        self.add(self.shirt)
        set_active(self.body)
        bpy.ops.mustardui.model_toolkit_remove_marks()
        self.assertFalse([m for m in self.body.modifiers if m.type == "NODES"])
        bsdf = self.skin.node_tree.nodes["Principled BSDF"]
        self.assertEqual(bsdf.inputs["Base Color"].links[0].from_node.type, "GROUP")
        controls = [x for x in bpy.data.objects if x.MustardUI_tools_creators_type]
        self.assertEqual(len(controls), 1)

        set_active(self.shirt)
        bpy.ops.mustardui.model_toolkit_remove_marks()
        self.assertFalse(bsdf.inputs["Base Color"].is_linked)
        self.assertFalse([n for n in self.skin.node_tree.nodes if n.type == "GROUP"])
        self.assertFalse([x for x in bpy.data.objects if x.MustardUI_tools_creators_type])
        self.assertFalse(bpy.ops.mustardui.model_toolkit_remove_marks.poll())


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
