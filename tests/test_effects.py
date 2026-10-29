import importlib
import os
import tempfile
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
        self.assertFalse(bpy.ops.mustardui.model_toolkit_shatter.poll())
        self.assertFalse(bpy.ops.mustardui.model_toolkit_wet.poll())
        self.assertFalse(bpy.ops.mustardui.model_toolkit_imprints.poll())
        self.assertFalse(bpy.ops.mustardui.model_toolkit_dust_puff.poll())
        self.assertFalse(bpy.ops.mustardui.model_toolkit_dust_motes.poll())
        self.assertFalse(bpy.ops.mustardui.model_toolkit_crush.poll())
        self.assertFalse(bpy.ops.mustardui.model_toolkit_aura.poll())

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
        controls, groups = set(), set()
        for material in (self.cloth, self.leather):
            group = self.surface(material)
            groups.add(group.node_tree)
            self.assertEqual(group.inputs["Shader"].links[0].from_node.type, "BSDF_PRINCIPLED")
            controls.add(group.inputs["Control"].links[0].from_node.object)
        self.assertEqual(len(controls), 1)
        # The materials share the settings, held by the effect node in their group
        (group,) = groups
        self.assertEqual(group.name, "MustardUI Hex Dissolve Settings")
        settings = group.nodes[effect.SETTINGS]
        self.assertEqual(settings.node_tree.name, "MustardUI Hex Dissolve")
        self.assertTrue(settings.inputs["Control"].is_linked)
        self.assertFalse(settings.inputs["Edge Width"].is_linked)
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
        self.assertEqual(
            self.surface(self.leather).node_tree.name, "MustardUI Hex Dissolve Settings"
        )
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
        for frame in range(start, start + 30):
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

    # With physics, the cloth around a hole sags when released, still without, the Shape holding
    # it on the shape of the mesh, sagging less
    def test_physics_release(self):
        heights = []
        for release, shape in ((0.0, 0.0), (0.1, 0.0), (0.1, 1.0)):
            curtain = self.curtain()
            # The pieces ripped out to the floor, the cloth below the hole left
            co = self.tear(curtain, release=release, across=False, rip_out=1.0, shape=shape)
            below = co[(np.abs(co[:, 0]) < 0.05) & (co[:, 2] > 0.6) & (co[:, 2] < 0.95)]
            heights.append(below[:, 2].max())
            bpy.data.objects.remove(curtain)
        self.assertLess(heights[1], heights[0] - 0.02)
        self.assertGreater(heights[2], heights[1] + 0.01)

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
            for frame in range(start, start + 30):
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
        self.assertEqual(output.node_tree.name, "MustardUI Wet Film Settings")
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
class TestFoam(BlenderTestCase):
    def setUp(self):
        super().setUp()
        configure_model(build_model())
        self.body = bpy.data.objects["Tester Body"]
        # Points 5 cm apart
        bm = bmesh.new()
        bm.from_mesh(self.body.data)
        bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=19, use_grid_fill=True)
        bm.to_mesh(self.body.data)
        bm.free()
        self.body.modifiers.new("Subdivision", "SUBSURF")
        # Normals out, unlike the test cube
        mesh = bpy.data.meshes.new("Ball")
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=32, radius=0.15)
        bm.to_mesh(mesh)
        bm.free()
        self.ball = new_object("Ball", mesh)

    def add(self, obj, cursor, **settings):
        bpy.context.scene.cursor.location = cursor
        set_active(obj)
        bpy.ops.mustardui.model_toolkit_foam(radius=0.1, **settings)
        return [m for m in obj.modifiers if effect.is_effect(m, "MustardUI Foam")][-1]

    def foam(self, obj):
        """World positions of the foam points and of the bubbles, and the foam meshes"""
        shell, bubbles, meshes = [], [], []
        for x in bpy.context.evaluated_depsgraph_get().object_instances:
            if not (x.is_instance and x.parent and x.parent.original == obj):
                continue
            if "foam" in x.object.data.attributes:
                meshes.append(x.object.data)
                shell += [x.matrix_world @ v.co for v in x.object.data.vertices]
            else:
                bubbles.append(x.matrix_world.to_translation())
        return np.array(shell).reshape(-1, 3), np.array(bubbles).reshape(-1, 3), meshes

    def films(self, obj):
        """Film thickness of each bubble, random for each one"""
        depsgraph = bpy.context.evaluated_depsgraph_get()
        geometry = obj.evaluated_get(depsgraph).evaluated_geometry()
        points = geometry.instances_pointcloud()
        values = np.zeros(len(points.points))
        if "foam_film" in points.attributes:
            points.attributes["foam_film"].data.foreach_get("value", values)
        return set(values.round(3))

    # The Control on the vertex closest to the 3D cursor, in the Controls collection, follows its
    # bone, the foam and the bubbles inside its sphere
    def test_foam(self):
        modifier = self.add(self.body, (0.1, -0.6, 1.0))
        self.assertEqual([m.type for m in self.body.modifiers][-2:], ["NODES", "SUBSURF"])
        controls = effect.modifier_input(modifier, "Controls").value
        self.assertIn(controls, bpy.context.scene.collection.children_recursive)
        (control,) = controls.objects
        self.assertEqual(control.MustardUI_tools_creators_type, "EFFECT_FOAM")
        self.assertEqual((control.parent_type, control.parent_bone), ("BONE", "spine"))
        self.assertEqual(control.users_collection, (controls,))
        self.assertEqual(bpy.context.view_layer.objects.active, control)
        np.testing.assert_allclose(
            control.matrix_world.to_translation(), (0.1, -0.5, 1.0), atol=1e-5
        )
        np.testing.assert_allclose(control.matrix_world.to_scale(), (0.1, 0.1, 0.1), atol=1e-5)

        shell, bubbles, (mesh,) = self.foam(self.body)
        self.assertGreater(len(shell), 100)
        self.assertGreater(len(bubbles), 20)
        # Within the ragged border of the sphere
        for points in (shell, bubbles):
            self.assertLess(np.linalg.norm(points - (0.1, -0.5, 1.0), axis=1).max(), 0.13)
        materials = {mesh.materials[p.material_index].name for p in mesh.polygons}
        self.assertEqual(materials, {"MustardUI Foam"})
        for name, data_type in (
            ("foam", "FLOAT_COLOR"),
            ("foam_color", "FLOAT_COLOR"),
            ("foam_bubbles", "FLOAT_VECTOR"),
        ):
            self.assertEqual(mesh.attributes[name].data_type, data_type)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        geometry = self.body.evaluated_get(depsgraph).evaluated_geometry()
        materials = {
            x.mesh.materials[p.material_index].name
            for x in geometry.instance_references()
            if x.mesh and "foam" not in x.mesh.attributes
            for p in x.mesh.polygons
        }
        self.assertEqual(materials, {"MustardUI Foam Bubbles"})
        self.assertEqual([x.message for x in modifier.node_warnings], [])

    # Puffy over the mesh up to the Thickness, the bubbles sitting on it
    def test_height(self):
        modifier = self.add(self.ball, (0.0, -0.2, 0.0))
        thickness = effect.modifier_input(modifier, "Thickness").value
        size = effect.modifier_input(modifier, "Bubble Size").value
        radius = effect.modifier_input(modifier, "Max Radius").value
        shell, bubbles, _ = self.foam(self.ball)
        mesh = self.ball.data
        bvh = BVHTree.FromPolygons(
            [v.co for v in mesh.vertices], [p.vertices for p in mesh.polygons]
        )

        def height(points):
            """Signed distance over the faces of the ball"""
            return np.array(
                [(Vector(x) - hit).dot(n) for x in points for hit, n, *_ in [bvh.find_nearest(x)]]
            )

        self.assertGreater(height(shell).min(), 0.0)
        self.assertGreater(height(shell).max(), 0.6 * thickness)
        self.assertLess(height(shell).max(), thickness + size + 0.001)
        self.assertGreater(height(bubbles).min(), 0.0)
        self.assertLess(height(bubbles).max(), thickness + size + radius)
        self.assertEqual([x.message for x in modifier.node_warnings], [])

    # The foam and the bubbles follow the deformed mesh
    def test_follow(self):
        self.add(self.body, (0.1, -0.6, 1.0))
        shell, bubbles, _ = self.foam(self.body)
        armature = self.body.parent
        bone = armature.pose.bones["spine"]
        bone.rotation_mode = "XYZ"
        bone.rotation_euler = (0.3, 0.2, 0.0)
        bpy.context.view_layer.update()
        matrix = armature.matrix_world @ bone.matrix @ bone.bone.matrix_local.inverted()
        moved, moved_bubbles, _ = self.foam(self.body)
        np.testing.assert_allclose(moved, [matrix @ Vector(x) for x in shell], atol=1e-5)
        np.testing.assert_allclose(moved_bubbles, [matrix @ Vector(x) for x in bubbles], atol=1e-5)

    # Less Amount washes the foam away from its border, keeping the other bubbles
    def test_amount(self):
        modifier = self.add(self.ball, (0.0, -0.2, 0.0))
        shell, _, _ = self.foam(self.ball)
        films = self.films(self.ball)
        effect.modifier_input(modifier, "Amount").value = 0.5
        self.ball.update_tag()
        half, _, _ = self.foam(self.ball)
        self.assertLess(len(half), len(shell) * 0.7)
        self.assertLess(len(self.films(self.ball)), len(films) * 0.7)
        self.assertLessEqual(self.films(self.ball), films)

        effect.modifier_input(modifier, "Amount").value = 0.0
        self.ball.update_tag()
        shell, bubbles, meshes = self.foam(self.ball)
        self.assertEqual((len(shell), len(bubbles)), (0, 0))
        self.assertEqual([x.message for x in modifier.node_warnings], [])

    # The bubbles pop at random from the Start Frame, the others staying
    def test_pop(self):
        modifier = self.add(self.ball, (0.0, -0.2, 0.0))
        scene = bpy.context.scene
        start = scene.frame_current
        effect.modifier_input(modifier, "Pop Rate").value = 1.0
        self.ball.update_tag()
        films = self.films(self.ball)
        scene.frame_set(start + scene.render.fps)
        popped = self.films(self.ball)
        # About exp(-1) of them left after a second
        self.assertLess(len(popped), len(films) * 0.5)
        self.assertGreater(len(popped), len(films) * 0.2)
        self.assertLessEqual(popped, films)
        scene.frame_set(start)
        self.assertEqual(self.films(self.ball), films)

    # Adding Foam again adds a Control to the Foam of the mesh, the foam inside both spheres
    def test_controls(self):
        modifier = self.add(self.ball, (0.0, -0.2, 0.0))
        self.add(self.ball, (0.0, 0.2, 0.0))
        self.assertEqual([m.type for m in self.ball.modifiers], ["NODES"])
        self.assertEqual(len(effect.modifier_input(modifier, "Controls").value.objects), 2)
        shell, _, meshes = self.foam(self.ball)
        self.assertEqual(len(meshes), 1)
        self.assertGreater(shell[:, 1].max(), 0.1)
        self.assertLess(shell[:, 1].min(), -0.1)
        self.assertEqual([x.message for x in modifier.node_warnings], [])

    # With Sliding the foam and its bubbles slide down the side of the mesh from the Start Frame
    def test_slide(self):
        modifier = self.add(self.ball, (-0.2, 0.0, 0.03))
        scene = bpy.context.scene
        start = scene.frame_current
        still, still_bubbles, _ = self.foam(self.ball)
        # Past the frames simulated next, as the simulation keeps the frames it cached
        scene.frame_set(start + 40)
        moved, moved_bubbles, _ = self.foam(self.ball)
        np.testing.assert_allclose(moved, still)

        effect.modifier_input(modifier, "Sliding").value = True
        effect.modifier_input(modifier, "Speed").value = 0.05
        self.ball.update_tag()
        for frame in range(start, start + 25):
            scene.frame_set(frame)
        moved, moved_bubbles, _ = self.foam(self.ball)
        # About a second at half to one and a half the Speed on the vertical side
        for before, after in ((still, moved), (still_bubbles, moved_bubbles)):
            drop = before[:, 2].mean() - after[:, 2].mean()
            self.assertGreater(drop, 0.01)
            self.assertLess(drop, 0.08)
        # Leaving a thin trail up to where it started, gone without Trail
        self.assertGreater(moved[:, 2].max(), still[:, 2].max() - 0.01)
        effect.modifier_input(modifier, "Trail").value = 0.0
        self.ball.update_tag()
        moved, _, _ = self.foam(self.ball)
        self.assertLess(moved[:, 2].max(), still[:, 2].max() - 0.01)
        self.assertEqual([x.message for x in modifier.node_warnings], [])

    # The Controls and their collections not used anymore are removed
    def test_remove(self):
        self.add(self.ball, (0.0, -0.2, 0.0))
        self.add(self.body, (0.1, -0.6, 1.0))
        set_active(self.ball)
        bpy.ops.mustardui.model_toolkit_remove_foam()
        self.assertFalse([m for m in self.ball.modifiers if m.type == "NODES"])
        controls = [x for x in bpy.data.objects if x.MustardUI_tools_creators_type]
        self.assertEqual(len(controls), 1)
        self.assertEqual(
            [x.name for x in bpy.data.collections if "Foam" in x.name], ["Tester Body Foam"]
        )
        set_active(self.body)
        bpy.ops.mustardui.model_toolkit_remove_foam()
        self.assertFalse([x for x in bpy.data.objects if x.MustardUI_tools_creators_type])
        self.assertFalse([x for x in bpy.data.collections if "Foam" in x.name])
        self.assertFalse(bpy.ops.mustardui.model_toolkit_remove_foam.poll())


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


def small_islands(mesh, size):
    """Whether each vertex is in a loose part of at most that many vertices"""
    parent = list(range(len(mesh.vertices)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for edge in mesh.edges:
        a, b = find(edge.vertices[0]), find(edge.vertices[1])
        parent[a] = b
    roots = np.array([find(i) for i in range(len(parent))])
    _, inverse, counts = np.unique(roots, return_inverse=True, return_counts=True)
    return counts[inverse] <= size


@unittest.skipUnless(effect.effects_available(), "Needs Blender 5.2")
class TestImprints(BlenderTestCase):
    def setUp(self):
        super().setUp()
        configure_model(build_model())
        self.body = bpy.data.objects["Tester Body"]
        # A 2 m ground the body cube sinks 3 cm into
        mesh = bpy.data.meshes.new("Ground")
        mesh.from_pydata([(x, y, 0.0) for y in (-1, 1) for x in (-1, 1)], [], [(0, 1, 3, 2)])
        self.ground = new_object("Ground", mesh)
        self.ground.location.z = 0.53
        self.snow = bpy.data.materials.new("Snow")
        mesh.materials.append(self.snow)

    def add(self, **settings):
        bpy.ops.mustardui.model_toolkit_imprints(**settings)
        modifier = self.ground.modifiers["Imprints"]
        for name in ("Noise", "Smooth"):
            effect.modifier_input(modifier, name).value = 0
        self.ground.update_tag()
        return modifier

    def heights(self):
        """World positions of the evaluated points, their height off the ground and tint amount"""
        data = self.ground.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
        co = np.empty(len(data.vertices) * 3)
        data.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3) @ np.array(self.ground.matrix_world.to_3x3()).T
        co += self.ground.matrix_world.translation
        imprint = np.empty(len(data.vertices) * 4)
        data.attributes["imprint"].data.foreach_get("color", imprint)
        return co, co[:, 2] - 0.53, 1.0 - imprint.reshape(-1, 4)[:, 3]

    # The model body sinks into the ground, which is pushed up around it, tinting its material
    def test_imprints(self):
        set_active(self.ground)
        modifier = self.add(kind="SNOW")
        colliders = effect.modifier_input(modifier, "Colliders").value
        self.assertEqual(list(colliders.objects), [self.body])
        self.assertIn(colliders, list(bpy.context.scene.collection.children))
        # Subdivided to about 1 cm
        self.assertEqual(effect.modifier_input(modifier, "Subdivisions").value, 8)

        co, height, amount = self.heights()
        side = np.abs(co[:, :2]).max(axis=1)
        np.testing.assert_allclose(height[side < 0.45], -0.03, atol=1e-4)
        rim = height[(side > 0.5) & (side < 0.53)]
        self.assertGreater(rim.min(), 0.0)
        self.assertGreater(rim.max(), 0.003)
        np.testing.assert_allclose(height[side > 0.7], 0.0, atol=1e-6)
        # Fully tinted from 40% of the Depth
        np.testing.assert_allclose(amount[side < 0.45], 0.03 / (0.08 * 0.4), atol=1e-5)
        np.testing.assert_allclose(amount[side > 0.7], 0.0, atol=1e-6)

        bsdf = self.snow.node_tree.nodes["Principled BSDF"]
        tint = bsdf.inputs["Base Color"].links[0].from_node
        self.assertEqual(tint.node_tree.name, "MustardUI Imprints Tint")
        self.assertEqual([x.message for x in modifier.node_warnings], [])

    # The other selected meshes are imprinted instead of the body, in world space
    def test_colliders(self):
        stone = new_mesh_object("Stone", size=0.1, z=0.6)
        self.ground.scale = (2.0, 2.0, 0.5)
        self.ground.rotation_euler.z = 0.3
        set_active(stone)
        self.ground.select_set(True)
        bpy.context.view_layer.objects.active = self.ground
        modifier = self.add(kind="SAND")
        effect.modifier_input(modifier, "Rim").value = 0.0
        colliders = effect.modifier_input(modifier, "Colliders").value
        self.assertEqual(list(colliders.objects), [stone])

        co, height, _ = self.heights()
        side = np.abs(co[:, :2]).max(axis=1)
        np.testing.assert_allclose(height[side < 0.09], -0.03, atol=1e-4)
        np.testing.assert_allclose(height[side > 0.15], 0.0, atol=1e-6)

    # A slab thinner than the reach of the rays is imprinted only where the body presses it
    def test_slab(self):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Diagonal((2.0, 2.0, 0.1, 1.0)))
        bm.to_mesh(self.ground.data)
        bm.free()
        self.ground.location.z = 0.48
        set_active(self.ground)
        self.add(kind="SNOW")
        co, _, _ = self.heights()
        data = self.ground.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
        normal = np.empty(len(data.vertices) * 3)
        data.vertices.foreach_get("normal", normal)
        side = np.abs(co[:, :2]).max(axis=1)
        top = (normal[2::3] > 0.9) & (side < 0.45)
        bottom = (normal[2::3] < -0.9) & (side < 0.95)
        np.testing.assert_allclose(co[top, 2], 0.5, atol=1e-4)
        np.testing.assert_allclose(co[bottom, 2], 0.43, atol=1e-6)

    # Soft imprints keep the pressed points on the body, and sink the surface around them
    def test_soft(self):
        set_active(self.ground)
        modifier = self.add(kind="CUSHION")
        self.assertGreater(effect.modifier_input(modifier, "Softness").value, 0.0)
        co, height, _ = self.heights()
        side = np.abs(co[:, :2]).max(axis=1)
        np.testing.assert_allclose(height[side < 0.45], -0.03, atol=1e-4)
        self.assertLess(height[(side > 0.51) & (side < 0.53)].max(), -0.003)
        self.assertLess(height.max(), 1e-6)
        # Fading away, untouched past the Softness from the box around the body
        self.assertLess(np.abs(height[side > 0.8]).max(), 0.001)
        np.testing.assert_allclose(height[side > 0.9], 0.0, atol=1e-6)
        self.assertEqual([x.message for x in modifier.node_warnings], [])

        # Bulging around the body with a Rim, the pressed points as deep
        effect.modifier_input(modifier, "Rim").value = 0.5
        self.ground.update_tag()
        bulged = self.heights()[1]
        np.testing.assert_allclose(bulged[side < 0.45], -0.03, atol=1e-4)
        self.assertGreater((bulged - height)[(side > 0.5) & (side < 0.6)].max(), 0.003)
        effect.modifier_input(modifier, "Rim").value = 0.0

        # Crisp without Softness, the surface around left as it is, less subdivided around
        effect.modifier_input(modifier, "Softness").value = 0.0
        self.ground.update_tag()
        co, height, _ = self.heights()
        np.testing.assert_allclose(height[np.abs(co[:, :2]).max(axis=1) > 0.51], 0.0, atol=1e-6)

    # A single point the rays pass by through a gap of the Colliders is imprinted as its neighbors
    def test_gap(self):
        cuts = (-0.1, -0.001, 0.001, 0.1)
        verts = [(x, y, 0.5) for y in cuts for x in cuts]
        faces = [
            (i + 4 * j, i + 1 + 4 * j, i + 5 + 4 * j, i + 4 + 4 * j)
            for j in range(3)
            for i in range(3)
        ]
        # With a lid above the ground, covering it
        verts += [(x, y, 0.7) for y in cuts[::3] for x in cuts[::3]]
        faces = [f for f in faces if f[0] != 5] + [(16, 17, 19, 18)]
        mesh = bpy.data.meshes.new("Plate")
        mesh.from_pydata(verts, [], faces)
        plate = new_object("Plate", mesh)
        set_active(plate)
        self.ground.select_set(True)
        bpy.context.view_layer.objects.active = self.ground
        self.add()
        co, height, _ = self.heights()
        center = np.linalg.norm(co[:, :2], axis=1).argmin()
        self.assertLess(np.linalg.norm(co[center, :2]), 1e-6)
        self.assertAlmostEqual(height[center], -0.03, places=4)

    # Lasting imprints stay after the body leaves, filling back in the Recovery
    def test_lasting(self):
        set_active(self.ground)
        modifier = self.add(kind="MUD")
        scene = bpy.context.scene
        start = scene.frame_current
        self.body.keyframe_insert("location", frame=start + 2)
        self.body.location.z += 0.5
        self.body.keyframe_insert("location", frame=start + 4)
        for frame in range(start, start + 8):
            scene.frame_set(frame)
        co, height, _ = self.heights()
        side = np.abs(co[:, :2]).max(axis=1)
        np.testing.assert_allclose(height[side < 0.45], -0.03, atol=1e-4)

        effect.modifier_input(modifier, "Lasting").value = False
        self.ground.update_tag()
        np.testing.assert_allclose(self.heights()[1], 0.0, atol=1e-6)

        effect.modifier_input(modifier, "Lasting").value = True
        effect.modifier_input(modifier, "Recovery").value = 0.1
        self.ground.update_tag()
        for frame in range(start, start + 12):
            scene.frame_set(frame)
        np.testing.assert_allclose(self.heights()[1], 0.0, atol=1e-6)
        self.assertEqual([x.message for x in modifier.node_warnings], [])

    # Subdivided only near the body, the far parts of the ground left as they are
    def test_subdivided_near(self):
        set_active(self.ground)
        self.add(kind="SNOW")
        co, _, _ = self.heights()
        data = self.ground.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
        self.assertLess(len(data.polygons), 4**8 * 3 // 4)
        side = np.abs(co[:, :2]).max(axis=1)
        # About 8 mm apart near the body, the corners far from it
        self.assertGreater((side < 0.6).sum(), 15000)
        self.assertLess((side > 0.9).sum(), 500)

    # Cracks spread from the imprints up to their length, grooved and drawn by the shader attribute,
    # and the surface around them breaks into slabs tilted by the rim, sharp apart
    def test_cracks(self):
        set_active(self.ground)
        modifier = self.add(kind="ASPHALT")
        effect.modifier_input(modifier, "Debris").value = False
        self.ground.update_tag()
        co, height, _ = self.heights()
        data = self.ground.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
        crack = np.empty(len(data.vertices) * 4)
        data.attributes["imprint_crack"].data.foreach_get("color", crack)
        crack = crack.reshape(-1, 4)
        # On the cracks, within the unit vector to them
        cracked = (crack[:, 3] < 0.5) & (np.linalg.norm(crack[:, :3], axis=1) < 1.0)
        side = np.abs(co[:, :2]).max(axis=1)
        outside = side > 0.52
        self.assertGreater((cracked & outside).sum(), 100)
        self.assertLess(height[outside].min(), -0.002)
        slab = np.empty(len(data.vertices) * 4)
        data.attributes["imprint_slab"].data.foreach_get("color", slab)
        self.assertGreater((slab.reshape(-1, 4)[:, 3] < 1.0)[outside].sum(), 100)
        self.assertGreater(height[outside].max(), 0.01)
        sharp = np.zeros(len(data.edges), dtype=bool)
        data.attributes["sharp_edge"].data.foreach_get("value", sharp)
        self.assertGreater(sharp.sum(), 100)
        # Not past the Crack Length and the slabs
        reach = sum(
            effect.modifier_input(modifier, x).value
            for x in ("Crack Length", "Slab Size", "Rim Width", "Rim Width")
        )
        far = side > 0.5 + reach
        np.testing.assert_allclose(height[far], 0.0, atol=1e-6)
        self.assertFalse(cracked[far].any())
        self.assertEqual([x.message for x in modifier.node_warnings], [])

        effect.modifier_input(modifier, "Cracks").value = False
        effect.modifier_input(modifier, "Rim").value = 0.0
        self.ground.update_tag()
        co, height, _ = self.heights()
        side = np.abs(co[:, :2]).max(axis=1)
        np.testing.assert_allclose(height[side > 0.52], 0.0, atol=1e-6)
        data = self.ground.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
        for name in ("imprint_crack", "imprint_slab"):
            values = np.empty(len(data.vertices) * 4)
            data.attributes[name].data.foreach_get("color", values)
            np.testing.assert_allclose(values.reshape(-1, 4)[:, 3], 1.0)

    # With Chunks the slabs are separate thick pieces, the surface sunk under them
    def test_chunks(self):
        set_active(self.ground)
        modifier = self.add(kind="ASPHALT")
        effect.modifier_input(modifier, "Debris").value = False
        self.ground.update_tag()
        data = self.ground.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
        # Out of the ground, the largest part
        self.assertGreater(small_islands(data, len(data.vertices) // 2).sum(), 100)
        sharp = np.zeros(len(data.polygons), dtype=bool)
        data.attributes["sharp_face"].data.foreach_get("value", sharp)
        self.assertTrue(sharp.any())
        co = np.empty(len(data.vertices) * 3)
        data.vertices.foreach_get("co", co)
        thickness = effect.modifier_input(modifier, "Thickness").value
        # The sunk surface under them, out of the imprints
        self.assertLess(co[2::3].min(), -0.03 - thickness * 0.9)
        self.assertEqual([x.message for x in modifier.node_warnings], [])

        effect.modifier_input(modifier, "Chunks").value = False
        self.ground.update_tag()
        data = self.ground.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
        self.assertFalse(small_islands(data, len(data.vertices) - 1).any())

    # The imprints tinted with the uneven color, none without Tint
    def test_tint(self):
        set_active(self.ground)
        modifier = self.add(kind="MUD")
        co, height, amount = self.heights()
        self.assertGreater(amount.max(), 0.99)
        data = self.ground.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
        detail = np.empty(len(data.vertices) * 3)
        data.attributes["imprint_detail"].data.foreach_get("vector", detail)
        np.testing.assert_allclose(detail.reshape(-1, 3)[:, 0], 0.5, atol=1e-6)
        np.testing.assert_allclose(detail.reshape(-1, 3)[:, 1], 80.0, atol=1e-4)

        effect.modifier_input(modifier, "Tint").value = False
        self.ground.update_tag()
        np.testing.assert_allclose(self.heights()[2], 0.0, atol=1e-6)
        data = self.ground.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
        data.attributes["imprint_detail"].data.foreach_get("vector", detail)
        np.testing.assert_allclose(detail.reshape(-1, 3)[:, 0], 0.0)

    # Chunks stick to the body leaving the imprints, then fall back into them, tinted as them
    def test_debris(self):
        set_active(self.ground)
        modifier = self.add(kind="ASPHALT")
        effect.modifier_input(modifier, "Debris Amount").value = 1000.0
        effect.modifier_input(modifier, "Chunks").value = False
        self.ground.update_tag()
        scene = bpy.context.scene
        start = scene.frame_current
        self.body.keyframe_insert("location", frame=start + 2)
        self.body.location.z += 0.5
        self.body.keyframe_insert("location", frame=start + 6)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        lifted = 0.0
        for frame in range(start, start + 40):
            scene.frame_set(frame)
            if frame not in (start + 5, start + 39):
                continue
            data = self.ground.evaluated_get(depsgraph).data
            co = np.empty(len(data.vertices) * 3)
            data.vertices.foreach_get("co", co)
            chunks = small_islands(data, 12)
            # Local to the ground, moved but not turned or scaled
            height = co.reshape(-1, 3)[chunks, 2]
            lifted = max(lifted, height.max(initial=0.0))
        self.assertGreater(chunks.sum(), 100)
        self.assertGreater(lifted, 0.1)
        # Resting in the imprints and their grooves, not falling through
        self.assertGreater(height.min(), -0.08)
        self.assertLess(height.max(), 0.0)
        material = np.empty(len(data.polygons), dtype=np.int32)
        data.polygons.foreach_get("material_index", material)
        self.assertFalse(material.any())
        imprint = np.empty(len(data.vertices) * 4)
        data.attributes["imprint"].data.foreach_get("color", imprint)
        np.testing.assert_allclose(imprint.reshape(-1, 4)[chunks, 3], 0.0)
        self.assertEqual([x.message for x in modifier.node_warnings], [])

        # As many chunks however far apart the points of the ground
        effect.modifier_input(modifier, "Subdivisions").value = 6
        self.ground.update_tag()
        for frame in range(start, start + 8):
            scene.frame_set(frame)
        coarse = small_islands(self.ground.evaluated_get(depsgraph).data, 12).sum()
        self.assertGreater(coarse, chunks.sum() * 0.6)
        self.assertLess(coarse, chunks.sum() * 1.6)

    # The Colliders collection goes with the effect, keeping the objects only in it in the scene
    def test_remove(self):
        set_active(self.ground)
        modifier = self.add()
        colliders = effect.modifier_input(modifier, "Colliders").value
        name = colliders.name
        stone = new_mesh_object("Stone", colliders)
        bpy.ops.mustardui.model_toolkit_remove_imprints()
        self.assertNotIn("Imprints", self.ground.modifiers)
        self.assertNotIn(name, bpy.data.collections)
        self.assertIn(self.body, list(bpy.context.scene.objects))
        self.assertEqual(stone.users_collection, (bpy.context.scene.collection,))
        self.assertFalse(self.snow.node_tree.nodes["Principled BSDF"].inputs[0].is_linked)
        self.assertFalse(bpy.ops.mustardui.model_toolkit_remove_imprints.poll())


@unittest.skipUnless(effect.effects_available(), "Needs Blender 5.2")
class TestDustPuff(BlenderTestCase):
    def setUp(self):
        super().setUp()
        configure_model(build_model())
        self.scene = bpy.context.scene
        # A 4 m ground away from the model
        mesh = bpy.data.meshes.new("Ground")
        mesh.from_pydata([(x, y, 0.0) for y in (2, 6) for x in (-2, 2)], [], [(0, 1, 3, 2)])
        self.dirt = bpy.data.materials.new("Dirt")
        mesh.materials.append(self.dirt)
        mesh.color_attributes.new("tint", "FLOAT_COLOR", "POINT")
        self.ground = new_object("Ground", mesh)
        # A 20 cm block falling at 2 m/s, landing at frame 10
        self.block = new_mesh_object("Block", size=0.1, z=0.0)
        for frame in range(1, 31):
            self.block.location = (0.0, 4.0, 0.1 + max(10 - frame, 0) * 2.0 / 24)
            self.block.keyframe_insert("location", frame=frame)
        self.scene.frame_set(1)

    def add(self, **settings):
        set_active(self.block)
        self.ground.select_set(True)
        bpy.context.view_layer.objects.active = self.ground
        bpy.ops.mustardui.model_toolkit_dust_puff(**settings)
        return self.ground.modifiers["Dust Puff"]

    def evaluate(self, end):
        """Evaluated geometry at the end frame, simulated from the first"""
        for frame in range(1, end + 1):
            self.scene.frame_set(frame)
        return self.ground.evaluated_get(bpy.context.evaluated_depsgraph_get()).evaluated_geometry()

    def grains(self, geometry):
        """Geometry of the grains instance, None without grains"""
        references = geometry.instance_references()
        return references[0] if references else None

    # Dust and grains are kicked up where the block lands, the grains resting on the ground
    def test_dust_puff(self):
        modifier = self.add(kind="SAND")
        colliders = effect.modifier_input(modifier, "Colliders").value
        self.assertEqual(list(colliders.objects), [self.block])
        self.assertEqual(self.ground.modifiers[-1], modifier)
        self.assertEqual(effect.modifier_input(modifier, "Start Frame").value, 1)
        dust = effect.modifier_input(modifier, "Dust Material").value
        self.assertEqual(dust.name, "MustardUI Dust Puff Dust")

        geometry = self.evaluate(9)
        self.assertIsNone(self.grains(geometry))
        self.assertIsNone(geometry.volume)

        geometry = self.evaluate(30)
        self.assertIsNotNone(geometry.volume)
        self.assertEqual(len(geometry.mesh.polygons), 1)
        grains = self.grains(geometry)
        mesh = grains.mesh
        self.assertGreater(len(mesh.polygons), 20 * 20)
        # Chips of 20 faces with the material of the ground, without its attributes
        self.assertEqual([x and x.original for x in mesh.materials], [self.dirt, None])
        index = np.empty(len(mesh.polygons), dtype=np.int32)
        mesh.polygons.foreach_get("material_index", index)
        self.assertEqual(index.max(), 0)
        self.assertNotIn("tint", mesh.attributes)
        co = np.array([v.co[:] for v in mesh.vertices])
        self.assertGreater(co[:, 2].min(), -0.002)
        self.assertLess(co[:, 2].max(), 0.01)
        self.assertGreater(np.linalg.norm(co[:, :2] - [0.0, 4.0], axis=1).max(), 0.12)
        # The dust around the block, not growing every frame
        volume = next(
            x.object
            for x in bpy.context.evaluated_depsgraph_get().object_instances
            if x.object.type == "VOLUME" and x.object.original == self.ground
        )
        corners = np.array([x[:] for x in volume.bound_box])
        self.assertLess((corners.max(0) - corners.min(0)).max(), 2.0)
        self.assertEqual([x.message for x in modifier.node_warnings], [])

        # Grains only when enabled
        effect.modifier_input(modifier, "Grains").value = False
        self.ground.update_tag()
        geometry = self.evaluate(30)
        self.assertIsNone(self.grains(geometry))

    # In a Ring the dust is blown out flat and further, instead of billowing around the block
    def test_ring(self):
        modifier = self.add(kind="DUST")
        spread = {}
        for ring in (0.0, 1.0):
            effect.modifier_input(modifier, "Ring").value = ring
            self.ground.update_tag()
            self.evaluate(20)
            volume = next(
                x.object
                for x in bpy.context.evaluated_depsgraph_get().object_instances
                if x.object.type == "VOLUME" and x.object.original == self.ground
            )
            corners = np.array([x[:] for x in volume.bound_box])
            spread[ring] = (corners.max(0) - corners.min(0))[:2].min()
        self.assertGreater(spread[1.0], spread[0.0] * 1.15)

    # A block resting on the ground, or touching it slower than the Min Speed, kicks nothing
    def test_resting(self):
        modifier = self.add(kind="DUST")
        effect.modifier_input(modifier, "Min Speed").value = 3.0
        self.ground.update_tag()
        geometry = self.evaluate(20)
        self.assertIsNone(self.grains(geometry))
        self.assertIsNone(geometry.volume)

    # A giant Collider gets dust as large as it, lasting longer, with as many puffs per hit
    def test_giant(self):
        modifier = self.add(kind="DUST")
        self.assertAlmostEqual(effect.modifier_input(modifier, "Size").value, 0.06)
        self.assertAlmostEqual(effect.modifier_input(modifier, "Amount").value, 3000.0)
        bpy.ops.mustardui.model_toolkit_remove_dust_puff()
        # Two blocks far apart are not one giant
        other = new_mesh_object("Other Block", size=0.1, z=0.0)
        other.location.x = 30.0
        bpy.context.view_layer.update()
        set_active(other)
        self.block.select_set(True)
        self.ground.select_set(True)
        bpy.context.view_layer.objects.active = self.ground
        bpy.ops.mustardui.model_toolkit_dust_puff(kind="DUST")
        modifier = self.ground.modifiers["Dust Puff"]
        self.assertAlmostEqual(effect.modifier_input(modifier, "Size").value, 0.06)
        bpy.ops.mustardui.model_toolkit_remove_dust_puff()
        bpy.data.objects.remove(other)
        # 34 m, 20 times a person
        self.block.scale = (170.0,) * 3
        bpy.context.view_layer.update()
        modifier = self.add(kind="DUST")
        inputs = {
            k: effect.modifier_input(modifier, k).value
            for k in ("Size", "Contact", "Min Speed", "Lifetime", "Amount")
        }
        expected = {
            "Size": 0.06 * 20,
            "Contact": 0.01 * 20,
            "Min Speed": 0.15 * 20**0.5,
            "Lifetime": 1.5 * 20**0.5,
            "Amount": 3000.0 * 20**-2.5,
        }
        for name, value in expected.items():
            self.assertAlmostEqual(inputs[name], value, places=4, msg=name)

    # Large dust is thinner per meter, not to render solid
    def test_thin(self):
        import openvdb

        modifier = self.add(kind="DUST")
        peaks = {}
        for size in (0.06, 0.4):
            effect.modifier_input(modifier, "Size").value = size
            self.ground.update_tag()
            path = os.path.join(tempfile.mkdtemp(), "dust.vdb")
            geometry = self.evaluate(14)
            geometry.volume.grids.save(path)
            peaks[size] = openvdb.read(path, "density").evalMinMax()[1]
        # By the square root of the size past 10 cm
        self.assertGreater(peaks[0.06], 0.6)
        self.assertLessEqual(peaks[0.4], 0.5 + 1e-4)

    # Without other selected meshes the model body is the Collider
    def test_body(self):
        set_active(self.ground)
        bpy.ops.mustardui.model_toolkit_dust_puff()
        colliders = effect.modifier_input(self.ground.modifiers["Dust Puff"], "Colliders").value
        self.assertEqual(list(colliders.objects), [bpy.data.objects["Tester Body"]])

    # Imprints added after it go before it, the grains not tinted by them
    def test_with_imprints(self):
        modifier = self.add(kind="SAND")
        bpy.ops.mustardui.model_toolkit_imprints(kind="SAND")
        self.assertEqual([m.name for m in self.ground.modifiers], ["Imprints", "Dust Puff"])
        effect.modifier_input(self.ground.modifiers["Imprints"], "Subdivisions").value = 4
        self.ground.update_tag()
        geometry = self.evaluate(20)
        # Subdivided near the body, the grains not part of the mesh
        self.assertGreater(len(geometry.mesh.polygons), 16)
        self.assertLessEqual(len(geometry.mesh.polygons), 256)
        grains = self.grains(geometry)
        self.assertNotIn("imprint", grains.mesh.attributes)
        self.assertIsNotNone(geometry.volume)
        self.assertEqual([x.message for x in modifier.node_warnings], [])

    # The Colliders collection goes with the effect, keeping its objects in the scene
    def test_remove(self):
        modifier = self.add()
        name = effect.modifier_input(modifier, "Colliders").value.name
        bpy.ops.mustardui.model_toolkit_remove_dust_puff()
        self.assertNotIn("Dust Puff", self.ground.modifiers)
        self.assertNotIn(name, bpy.data.collections)
        self.assertEqual(self.block.users_collection, (bpy.context.scene.collection,))
        self.assertFalse(bpy.ops.mustardui.model_toolkit_remove_dust_puff.poll())


@unittest.skipUnless(effect.effects_available(), "Needs Blender 5.2")
class TestShatter(BlenderTestCase):
    def setUp(self):
        super().setUp()
        configure_model(build_model())
        self.scene = bpy.context.scene
        # A 2 x 0.2 x 2 m wall standing on the ground, away from the model
        mesh = bpy.data.meshes.new("Wall")
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=(2.0, 0.2, 2.0), verts=bm.verts)
        bm.to_mesh(mesh)
        bm.free()
        self.brick = bpy.data.materials.new("Brick")
        mesh.materials.append(self.brick)
        self.wall = new_object("Wall", mesh)
        self.wall.location = (3.0, 0.0, 1.0)
        # A ball thrown through it at 3 m/s, hitting it at frame 12
        self.ball = self.sphere("Ball", 0.15)
        for frame, y in ((25, 1.5), (1, -1.5)):
            self.ball.location = (3.1, y, 1.1)
            self.ball.keyframe_insert("location", frame=frame)
        self.scene.frame_set(1)

    def sphere(self, name, radius):
        mesh = bpy.data.meshes.new(name)
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=radius)
        bm.to_mesh(mesh)
        bm.free()
        return new_object(name, mesh)

    def box(self, name, size, location):
        mesh = bpy.data.meshes.new(name)
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=size, verts=bm.verts)
        bm.to_mesh(mesh)
        bm.free()
        obj = new_object(name, mesh)
        obj.location = location
        return obj

    def add(self, obj, extras=False, **settings):
        """Shatter of the object, without Debris and Smoke unless asked"""
        set_active(obj)
        if obj == self.wall:
            self.ball.select_set(True)
        bpy.ops.mustardui.model_toolkit_shatter(**settings)
        modifier = obj.modifiers["Shatter"]
        if not extras:
            for name in ("Breakup", "Debris", "Smoke"):
                effect.modifier_input(modifier, name).value = False
            obj.update_tag()
        return modifier

    def evaluate(self, obj):
        """World positions of the evaluated vertices, faces, materials and volume"""
        data = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
        co = np.empty(len(data.vertices) * 3)
        data.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3) + np.array(obj.matrix_world.translation)
        bm = bmesh.new()
        bm.from_mesh(data)
        volume = bm.calc_volume(signed=True)
        bm.free()
        return co, len(data.polygons), [x and x.original for x in data.materials], volume

    # The ball breaks a hole in the wall, the pieces around it falling on the floor and resting
    # there, the others staying, all the pieces together keeping the volume of the wall, and
    # with Breakup large pieces hit hard break again, once
    def test_shatter(self):
        modifier = self.add(self.wall, kind="STONE")
        colliders = effect.modifier_input(modifier, "Colliders").value
        self.assertEqual(list(colliders.objects), [self.ball])
        self.assertEqual(effect.modifier_input(modifier, "Floor").value, 0.0)

        faces = []
        for frame in range(1, 81):
            self.scene.frame_set(frame)
            co, count, materials, volume = self.evaluate(self.wall)
            faces.append(count)
            self.assertTrue(np.isfinite(co).all(), f"frame {frame}")
            self.assertAlmostEqual(volume, 0.8, delta=1e-3, msg=f"frame {frame}")
            if frame == 13:
                top = co[co[:, 2] > 1.9]
            if frame == 79:
                before = co
        self.assertEqual(faces[:10], [6] * 10)
        self.assertGreater(faces[-1], 100)
        self.assertEqual(materials, [self.brick, None])
        self.assertGreater(co[:, 2].min(), -0.003)
        np.testing.assert_allclose(co, before, atol=1e-4)
        # The top of the wall, far from the hole, staying: the ball may break the pieces under it
        # again, still cut where they are
        self.assertAlmostEqual(co[:, 2].max(), 2.0, delta=1e-4)
        self.assertTrue(np.isin(top.round(4), co[co[:, 2] > 1.9].round(4)).all())
        # Some pieces passed through the wall
        self.assertGreater(co[:, 1].max(), 0.3)
        self.assertEqual([x.message for x in modifier.node_warnings], [])

        effect.modifier_input(modifier, "Breakup").value = True
        effect.modifier_input(modifier, "Breakup Chance").value = 1.0
        effect.modifier_input(modifier, "Breakup Size").value = 0.1
        self.wall.update_tag()
        for frame in range(1, 41):
            self.scene.frame_set(frame)
            co, count, _, volume = self.evaluate(self.wall)
            self.assertAlmostEqual(volume, 0.8, delta=1e-3, msg=f"frame {frame}")
        self.assertGreater(count, faces[-1] * 1.2)
        self.assertGreater(co[:, 2].min(), -0.003)
        self.assertEqual([x.message for x in modifier.node_warnings], [])

    # An open mesh, as a window pane, breaks keeping its area
    def test_open_mesh(self):
        mesh = bpy.data.meshes.new("Pane")
        mesh.from_pydata([(x, 0.0, z) for z in (0.5, 1.5) for x in (2.5, 3.5)], [], [(0, 1, 3, 2)])
        pane = new_object("Pane", mesh)
        set_active(pane)
        self.ball.select_set(True)
        bpy.ops.mustardui.model_toolkit_shatter(kind="GLASS")
        effect.modifier_input(pane.modifiers["Shatter"], "Debris").value = False
        pane.update_tag()
        for frame in range(1, 40):
            self.scene.frame_set(frame)
            data = pane.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
            area = sum(x.area for x in data.polygons)
            self.assertAlmostEqual(area, 1.0, delta=1e-3, msg=f"frame {frame}")
        self.assertGreater(len(data.polygons), 20)

    # Too weak a hit leaves the wall whole
    def test_strength(self):
        effect.modifier_input(self.add(self.wall), "Strength").value = 10.0
        self.wall.update_tag()
        for frame in range(1, 30):
            self.scene.frame_set(frame)
        self.assertEqual(self.evaluate(self.wall)[1], 6)

    # A giant foot sweeping through a 60 m wall and planted on the floor throws the pieces less,
    # all of them staying finite and none made out of nothing at the origin
    def test_giant(self):
        bpy.ops.object.select_all(action="DESELECT")
        wall = self.box("Giant Wall", (60.0, 6.0, 60.0), (90.0, 0.0, 30.0))
        foot = self.box("Foot", (15.0, 36.0, 9.0), (96.0, -45.0, 15.0))
        for frame in range(1, 121):
            u = min((frame - 1) / 108, 1.0)
            foot.location = (96.0, -45.0 + 90.0 * u, 15.0 - 10.5 * u)
            foot.keyframe_insert("location", frame=frame)
        self.scene.frame_set(1)
        set_active(wall)
        foot.select_set(True)
        bpy.ops.mustardui.model_toolkit_shatter(kind="STONE")
        modifier = wall.modifiers["Shatter"]
        throw = (36.0 / effect.PERSON_SIZE) ** -0.25
        self.assertAlmostEqual(effect.modifier_input(modifier, "Push").value, 0.6 * throw, 4)
        self.assertAlmostEqual(effect.modifier_input(modifier, "Scatter").value, 0.2 * throw, 4)
        for frame in range(1, 121):
            self.scene.frame_set(frame)
            co = self.evaluate(wall)[0]
            self.assertTrue(np.isfinite(co).all(), f"frame {frame}")
            self.assertGreater(np.linalg.norm(co, axis=1).min(), 1.0, f"frame {frame}")
        self.assertEqual([x.message for x in modifier.node_warnings], [])

    # Without other selected meshes, the model body breaks it, and the floor: a closed glass
    # dropped on the ground breaks into pieces scattered around and resting there, overlapping
    # each other less with Piece Collisions
    def test_drop(self):
        glass = self.sphere("Glass", 0.1)
        bpy.ops.object.select_all(action="DESELECT")
        for frame, z in ((21, -1.0), (1, 1.0)):
            glass.location = (-3.0, 0.0, z)
            glass.keyframe_insert("location", frame=frame)
        modifier = self.add(glass, kind="GLASS")
        colliders = effect.modifier_input(modifier, "Colliders").value
        self.assertEqual(list(colliders.objects), [bpy.data.objects["Tester Body"]])
        self.assertFalse(effect.modifier_input(modifier, "Piece Collisions").value)

        whole = self.evaluate(glass)[3]
        overlaps = []
        for enabled in (False, True):
            effect.modifier_input(modifier, "Piece Collisions").value = enabled
            glass.update_tag()
            for frame in range(1, 41):
                self.scene.frame_set(frame)
                co, count, _, volume = self.evaluate(glass)
                self.assertAlmostEqual(volume, whole, delta=whole * 1e-3, msg=f"frame {frame}")
            self.assertGreater(count, 200)
            self.assertGreater(co[:, 2].min(), -0.003)

            data = glass.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
            bm = bmesh.new()
            bm.from_mesh(data)
            trees = []
            seen = set()
            for face in bm.faces:
                if face in seen:
                    continue
                # The faces of the piece
                piece, stack = {face}, [face]
                while stack:
                    for edge in stack.pop().edges:
                        for other in edge.link_faces:
                            if other not in piece:
                                piece.add(other)
                                stack.append(other)
                seen |= piece
                verts = list({v for f in piece for v in f.verts})
                index = {v: i for i, v in enumerate(verts)}
                trees.append(
                    BVHTree.FromPolygons(
                        [v.co.copy() for v in verts], [[index[v] for v in f.verts] for f in piece]
                    )
                )
            bm.free()
            overlaps.append(
                sum(bool(a.overlap(b)) for i, a in enumerate(trees) for b in trees[i + 1 :])
            )
        self.assertLess(overlaps[1] * 2, overlaps[0])
        # Scattered, not only where it landed
        self.assertGreater(np.abs(co[:, :2] - (-3.0, 0.0)).max(), 0.2)

    # With Floor Support, the pieces standing on the floor of a tower all broken loose stay,
    # those not resting on them falling; without, all of them move
    def test_floor_support(self):
        # A 0.6 x 0.4 x 3 m tower
        self.wall.data.transform(Matrix.Diagonal((0.3, 2.0, 1.5, 1.0)))
        self.wall.location = (3.0, 0.0, 1.5)
        # In few pieces, the ball hits the ones anchored too, thrown faster
        for support, pieces in ((True, 60), (False, 60), (True, 4)):
            with self.subTest(support=support, pieces=pieces):
                if pieces < 60:
                    self.ball.animation_data_clear()
                    for frame, y in ((9, 1.5), (1, -1.5)):
                        self.ball.location = (3.1, y, 1.1)
                        self.ball.keyframe_insert("location", frame=frame)
                self.scene.frame_set(1)
                modifier = self.add(self.wall, kind="STONE")
                effect.modifier_input(modifier, "Pieces").value = pieces
                effect.modifier_input(modifier, "Break Radius").value = 10.0
                effect.modifier_input(modifier, "Floor Support").value = support
                self.wall.update_tag()
                base = self.evaluate(self.wall)[0]
                base = base[base[:, 2] < 0.01]
                for frame in range(1, 61):
                    self.scene.frame_set(frame)
                co, count = self.evaluate(self.wall)[:2]
                # Broken
                self.assertGreater(count, 6)
                low = co[co[:, 2] < 0.01]
                # The bottom face of the tower, unmoved
                still = len(low) >= len(base) and np.isin(base.round(4), low.round(4)).all()
                self.assertEqual(still, support)
                self.assertGreater(co[:, 2].min(), -0.003)
                self.assertLess(co[:, 2].max(), 2.9)
                self.wall.modifiers.remove(modifier)

    # With floors, a 6 x 6 x 9 m tower rammed through its ground floor breaks in pieces of a
    # single floor keeping its volume, the floors over it coming down on its rubble; without, the
    # pieces span the floors. The floors also from the faces of boxes stacked as floors of 4, 3, 2 m
    def test_floors(self):
        bpy.ops.object.select_all(action="DESELECT")
        ram = self.box("Ram", (3.0, 8.0, 2.3), (3.0, 0.0, 1.45))
        bm = bmesh.new()
        bm.from_mesh(ram.data)
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=8, use_grid_fill=True)
        bm.to_mesh(ram.data)
        bm.free()
        for frame in range(1, 26):
            ram.location.x = 3.0 + 0.75 * (frame - 1)
            ram.keyframe_insert("location", frame=frame)
        for heights, floor_height, faces in (
            ((9,), 3.0, False),
            ((9,), 0.0, False),
            ((4, 3, 2), 0.0, True),
        ):
            with self.subTest(floor_height=floor_height, faces=faces):
                self.scene.frame_set(1)
                mesh = bpy.data.meshes.new("Tower")
                bm = bmesh.new()
                for bottom, height in zip(np.cumsum((0,) + heights), heights, strict=False):
                    verts = bmesh.ops.create_cube(bm, size=1.0)["verts"]
                    bmesh.ops.scale(bm, vec=(6.0, 6.0, height), verts=verts)
                    bmesh.ops.translate(bm, vec=(12.0, 0.0, bottom + height / 2), verts=verts)
                bm.to_mesh(mesh)
                bm.free()
                tower = new_object("Tower", mesh)
                set_active(tower)
                ram.select_set(True)
                bpy.ops.mustardui.model_toolkit_shatter(kind="STONE")
                modifier = tower.modifiers["Shatter"]
                for name in ("Breakup", "Debris", "Smoke"):
                    effect.modifier_input(modifier, name).value = False
                effect.modifier_input(modifier, "Floor Support").value = True
                # For the floors over the broken one to land on its rubble
                effect.modifier_input(modifier, "Piece Collisions").value = True
                effect.modifier_input(modifier, "Floor Height").value = floor_height
                effect.modifier_input(modifier, "Floors from Faces").value = faces
                tower.update_tag()
                levels = np.array((3.0, 6.0) if floor_height else (4.0, 7.0))
                for frame in range(1, 31):
                    self.scene.frame_set(frame)
                    co, count, _, volume = self.evaluate(tower)
                    self.assertAlmostEqual(volume, 324.0, delta=0.01, msg=f"frame {frame}")
                    if frame == 8:
                        self.assertGreater(count, 30)
                        # How far the pieces reach into another floor, the loose ones moving a bit
                        bm = bmesh.new()
                        bm.from_mesh(
                            tower.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
                        )
                        across, seen = 0.0, set()
                        for face in bm.faces:
                            if face in seen:
                                continue
                            piece, stack = {face}, [face]
                            while stack:
                                for edge in stack.pop().edges:
                                    stack += [f for f in edge.link_faces if f not in piece]
                                    piece.update(edge.link_faces)
                            seen |= piece
                            z = [v.co.z for f in piece for v in f.verts]
                            reach = np.minimum(max(z) - levels, levels - min(z)).max()
                            across = max(across, reach)
                        bm.free()
                        self.assertEqual(across < 0.5, bool(floor_height or faces))
                # With floors the ones over it let go, landing on its rubble, else held by it
                if floor_height or faces:
                    self.assertLess(co[:, 2].max(), 9.0 - 0.05)
                else:
                    self.assertAlmostEqual(co[:, 2].max(), 9.0, delta=1e-3)
                self.assertEqual([x.message for x in modifier.node_warnings], [])
                bpy.data.objects.remove(tower)

    # Pieces getting loose after the break, hit or not held anymore, throw debris too, and the
    # ones anchored on the floor stay even when hit
    def test_late_loose(self):
        # A 0.6 x 0.4 x 3 m tower in a few pieces, few loose at the break
        self.wall.data.transform(Matrix.Diagonal((0.3, 2.0, 1.5, 1.0)))
        self.wall.location = (3.0, 0.0, 1.5)
        # The ball hitting it high
        for frame, y in ((25, 1.5), (1, -1.5)):
            self.ball.location = (3.1, y, 2.2)
            self.ball.keyframe_insert("location", frame=frame)
        modifier = self.add(self.wall, kind="STONE")
        effect.modifier_input(modifier, "Pieces").value = 12
        effect.modifier_input(modifier, "Break Radius").value = 0.05
        faces = {}
        for enabled in (True, False):
            effect.modifier_input(modifier, "Debris").value = enabled
            self.wall.update_tag()
            self.scene.frame_set(1)
            base = self.evaluate(self.wall)[0]
            base = base[base[:, 2] < 0.01]
            for frame in range(1, 31):
                self.scene.frame_set(frame)
            co, faces[enabled] = self.evaluate(self.wall)[:2]
            low = co[co[:, 2] < 0.01]
            # The bottom face of the tower, unmoved
            self.assertTrue(np.isin(base.round(4), low.round(4)).all())
        self.assertGreater(faces[True] - faces[False], 20 * 10)
        self.assertEqual([x.message for x in modifier.node_warnings], [])

    # A second hit breaks the still pieces again where it hits, also the ones anchored on the
    # floor when all the others got loose at the first, the base staying
    def test_second_hit(self):
        # A 0.6 x 0.4 x 3 m tower, hit high then low
        self.wall.data.transform(Matrix.Diagonal((0.3, 2.0, 1.5, 1.0)))
        self.wall.location = (3.0, 0.0, 1.5)
        self.ball.animation_data_clear()
        for frame, y, z in ((1, -1.5, 2.2), (9, 1.5, 2.2), (30, 1.5, 0.4), (38, -1.5, 0.4)):
            self.ball.location = (3.1, y, z)
            self.ball.keyframe_insert("location", frame=frame)
        for kind in ("STONE", "GLASS"):
            with self.subTest(kind=kind):
                self.scene.frame_set(1)
                modifier = self.add(self.wall, kind=kind)
                effect.modifier_input(modifier, "Pieces").value = 12
                effect.modifier_input(modifier, "Floor Support").value = True
                self.wall.update_tag()
                base = self.evaluate(self.wall)[0]
                base = base[base[:, 2] < 0.01]
                faces = {}
                for frame in range(1, 46):
                    self.scene.frame_set(frame)
                    co, faces[frame] = self.evaluate(self.wall)[:2]
                self.assertGreater(faces[45], faces[29])
                # The bottom face of the tower, unmoved
                self.assertTrue(np.isin(base.round(4), co[co[:, 2] < 0.01].round(4)).all())
                self.assertEqual([x.message for x in modifier.node_warnings], [])
                self.wall.modifiers.remove(modifier)

    # Debris chips are thrown from the cuts and rest on the floor, and dust billows as a volume
    def test_debris_smoke(self):
        modifier = self.add(self.wall, extras=True, kind="STONE")
        self.assertTrue(effect.modifier_input(modifier, "Debris").value)
        self.assertTrue(effect.modifier_input(modifier, "Smoke").value)
        dust = effect.modifier_input(modifier, "Smoke Material").value
        self.assertEqual(dust.name, "MustardUI Shatter Dust")

        for frame in range(1, 41):
            self.scene.frame_set(frame)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        self.assertIsNotNone(self.wall.evaluated_get(depsgraph).evaluated_geometry().volume)
        # Around the wall and the debris trailing dust, the grid not growing every frame
        volume = next(
            x.object
            for x in depsgraph.object_instances
            if x.object.type == "VOLUME" and x.object.original == self.wall
        )
        corners = np.array([x[:] for x in volume.bound_box])
        self.assertLess((corners.max(0) - corners.min(0)).max(), 12.0)
        co, faces, materials, _ = self.evaluate(self.wall)
        self.assertGreater(co[:, 2].min(), -0.003)
        self.assertEqual(materials, [self.brick, None])
        self.assertEqual([x.message for x in modifier.node_warnings], [])

        effect.modifier_input(modifier, "Debris").value = False
        effect.modifier_input(modifier, "Smoke").value = False
        self.wall.update_tag()
        for frame in range(1, 41):
            self.scene.frame_set(frame)
        geometry = self.wall.evaluated_get(
            bpy.context.evaluated_depsgraph_get()
        ).evaluated_geometry()
        self.assertIsNone(geometry.volume)
        # Chips of 20 faces, from the pieces loose around the hole
        self.assertGreater(faces - len(geometry.mesh.polygons), 20 * 50)

    # The inner faces have the Material, else the one of the closest outer face
    def test_inner_faces(self):
        modifier = self.add(self.wall)
        stone = bpy.data.materials.new("Stone")
        effect.modifier_input(modifier, "Inner Faces").value = True
        effect.modifier_input(modifier, "Material").value = stone
        self.wall.update_tag()
        for frame in range(1, 14):
            self.scene.frame_set(frame)
        data = self.wall.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
        used = {data.materials[x.material_index].original for x in data.polygons}
        self.assertEqual(used, {self.brick, stone})

    # The Colliders collection is removed with the effect, keeping its objects in the scene
    def test_remove(self):
        name = effect.modifier_input(self.add(self.wall), "Colliders").value.name
        bpy.ops.mustardui.model_toolkit_remove_shatter()
        self.assertNotIn("Shatter", self.wall.modifiers)
        self.assertNotIn(name, bpy.data.collections)
        self.assertIn(self.ball, list(self.scene.collection.objects))


@unittest.skipUnless(effect.effects_available(), "Needs Blender 5.2")
class TestCrush(BlenderTestCase):
    def setUp(self):
        super().setUp()
        configure_model(build_model())
        self.scene = bpy.context.scene
        # A 2 x 1 x 1 m box on the ground, away from the model
        mesh = bpy.data.meshes.new("Box")
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Diagonal((2.0, 1.0, 1.0, 1.0)))
        bm.to_mesh(mesh)
        bm.free()
        self.box = new_object("Box", mesh)
        self.box.location = (3.0, 0.0, 0.5)
        # A 40 cm block pressing it down to 30 cm at frame 10, then lifted off by frame 20
        self.block = new_mesh_object("Block", size=0.2, z=0.0)
        for frame, z in ((1, 1.7), (10, 0.5), (14, 0.5), (20, 1.7)):
            self.block.location = (3.0, 0.0, z)
            self.block.keyframe_insert("location", frame=frame)
        self.scene.frame_set(1)

    def add(self, **settings):
        """Crush of the box by the block, without Bulge, Crumple and Buckle"""
        set_active(self.block)
        self.box.select_set(True)
        bpy.context.view_layer.objects.active = self.box
        bpy.ops.mustardui.model_toolkit_crush(**settings)
        modifier = self.box.modifiers["Crush"]
        effect.modifier_input(modifier, "Subdivisions").value = 5
        for name in ("Bulge", "Crumple", "Buckle"):
            effect.modifier_input(modifier, name).value = 0.0
        self.box.update_tag()
        return modifier

    def evaluate(self, end):
        """World positions of the evaluated vertices at the end frame, simulated from the first"""
        for frame in range(1, end + 1):
            self.scene.frame_set(frame)
        data = self.box.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
        co = np.empty(len(data.vertices) * 3)
        data.vertices.foreach_get("co", co)
        return co.reshape(-1, 3) @ np.array(self.box.matrix_world.to_3x3()).T + np.array(
            self.box.matrix_world.translation
        )

    # The top under the block is pressed down to it and stays there after the block leaves, the
    # top around bent down less and less, the bottom on the ground untouched
    def test_crush(self):
        modifier = self.add(kind="METAL")
        colliders = effect.modifier_input(modifier, "Colliders").value
        self.assertEqual(list(colliders.objects), [self.block])
        self.assertEqual(effect.modifier_input(modifier, "Start Frame").value, 1)
        self.assertAlmostEqual(effect.modifier_input(modifier, "Flat Height").value, 0.1, 6)

        rest = self.evaluate(1)
        top = rest[:, 2] > 0.999
        under = top & (np.abs(rest[:, 0] - 3.0) < 0.15) & (np.abs(rest[:, 1]) < 0.15)
        co = self.evaluate(12)
        np.testing.assert_allclose(co[under, 2], 0.3, atol=1e-3)
        self.assertTrue((co[:, 2] <= rest[:, 2] + 1e-6).all())
        np.testing.assert_allclose(co[rest[:, 2] < 1e-6, 2], 0.0, atol=1e-6)
        np.testing.assert_allclose(co[:, :2], rest[:, :2], atol=1e-6)
        # Rising at most as steeply as the slope around the block
        side = np.abs(rest[:, 0] - 3.0)
        aside = top & (np.abs(rest[:, 1]) < 0.15)
        heights = []
        for distance in (0.3125, 0.5):
            near = aside & (np.abs(side - distance) < 0.01)
            heights.append(co[near, 2].mean())
            self.assertLess(co[near, 2].max(), 0.3 + distance - 0.2 + 0.02)
            self.assertGreater(co[near, 2].min(), 0.3)
        self.assertLess(heights[0], heights[1])
        np.testing.assert_allclose(self.evaluate(30), co, atol=1e-6)
        self.assertEqual([x.message for x in modifier.node_warnings], [])

    # Without Lasting the box gets back as it was once the block leaves
    def test_not_lasting(self):
        modifier = self.add()
        effect.modifier_input(modifier, "Lasting").value = False
        self.box.update_tag()
        rest = self.evaluate(1)
        self.assertLess(self.evaluate(12)[:, 2].min(), 0.31)
        np.testing.assert_allclose(self.evaluate(30), rest, atol=1e-6)

    # Pressed down into the ground, the box is flattened to the Flat Height, its top above its
    # bottom, never under the ground
    def test_flat(self):
        for frame in (10, 14):
            self.block.location.z = 0.1
            self.block.keyframe_insert("location", frame=frame)
        modifier = self.add()
        flat = effect.modifier_input(modifier, "Flat Height").value
        rest = self.evaluate(1)
        under = (np.abs(rest[:, 0] - 3.0) < 0.15) & (np.abs(rest[:, 1]) < 0.15)
        co = self.evaluate(30)
        np.testing.assert_allclose(co[under & (rest[:, 2] > 0.999), 2], flat, atol=1e-3)
        np.testing.assert_allclose(co[under & (rest[:, 2] < 1e-6), 2], 0.0, atol=1e-6)
        self.assertGreater(co[:, 2].min(), -1e-6)

    # A larger Stiffness bends the top down further away from the block
    def test_stiffness(self):
        modifier = self.add()
        rest = self.evaluate(1)
        far = (rest[:, 2] > 0.999) & (np.abs(np.abs(rest[:, 0] - 3.0) - 0.75) < 0.01)
        heights = []
        for stiffness in (0.1, 2.0):
            effect.modifier_input(modifier, "Stiffness").value = stiffness
            self.box.update_tag()
            heights.append(self.evaluate(12)[far, 2].mean())
        self.assertLess(heights[1], heights[0] - 0.05)

    # The sides squeezed bulge out, and fold with Crumple, the top under the block only sinking
    def test_bulge_crumple(self):
        modifier = self.add()
        rest = self.evaluate(1)
        sides = np.abs(np.abs(rest[:, 1]) - 0.5) < 1e-6
        under = (
            (rest[:, 2] > 0.999) & (np.abs(rest[:, 0] - 3.0) < 0.15) & (np.abs(rest[:, 1]) < 0.15)
        )
        plain = self.evaluate(12)
        self.assertLess(np.abs(plain[:, 1]).max(), 0.5 + 1e-6)

        effect.modifier_input(modifier, "Bulge").value = 1.0
        self.box.update_tag()
        bulged = self.evaluate(12)
        self.assertGreater(np.abs(bulged[sides, 1]).max(), 0.55)
        self.assertTrue((np.abs(bulged[sides, 1]) > 0.5 - 1e-6).all())

        effect.modifier_input(modifier, "Bulge").value = 0.0
        effect.modifier_input(modifier, "Crumple").value = 1.0
        self.box.update_tag()
        crumpled = self.evaluate(12)
        self.assertGreater(np.abs(crumpled[sides] - plain[sides]).max(), 0.005)
        # Creased under the block only down, not into it
        self.assertLess(crumpled[under, 2].max(), 0.3 + 1e-3)
        self.assertLess(crumpled[under, 2].min(), 0.3 - 0.005)

    # Buckling bends the top at a few creases, flatter between them, never above the block
    def test_buckle(self):
        modifier = self.add()
        rest = self.evaluate(1)
        top = (rest[:, 2] > 0.999) & (np.abs(rest[:, 1]) < 1e-3)
        order = np.argsort(rest[top, 0])
        steep = {}
        for buckle in (0.0, 1.0):
            effect.modifier_input(modifier, "Buckle").value = buckle
            self.box.update_tag()
            co = self.evaluate(12)
            # Share of the rise along the top taken by its steepest quarter of steps
            rise = np.sort(np.abs(np.diff(co[top][order, 2])))[::-1]
            steep[buckle] = rise[: len(rise) // 4].sum() / rise.sum()
            self.assertLess(co[top & (np.abs(rest[:, 0] - 3.0) < 0.15), 2].max(), 0.3 + 1e-3)
        self.assertGreater(steep[1.0], steep[0.0] + 0.15)

    # A turned, scaled box is crushed where the block is in the world
    def test_transformed(self):
        self.box.data.transform(Matrix.Scale(0.5, 4))
        self.box.scale = (2.0, 2.0, 2.0)
        self.box.rotation_euler.z = 0.5
        modifier = self.add()
        self.assertAlmostEqual(effect.modifier_input(modifier, "Flat Height").value, 0.1, 5)
        rest = self.evaluate(1)
        under = (
            (rest[:, 2] > 0.999) & (np.abs(rest[:, 0] - 3.0) < 0.15) & (np.abs(rest[:, 1]) < 0.15)
        )
        np.testing.assert_allclose(self.evaluate(12)[under, 2], 0.3, atol=1e-3)

    # A curved mesh nothing touches stays as it is, folds and bulge included
    def test_untouched(self):
        bm = bmesh.new()
        bmesh.ops.create_cone(
            bm,
            cap_ends=True,
            segments=32,
            radius1=0.5,
            radius2=0.5,
            depth=2.0,
            matrix=Matrix.Rotation(np.pi / 2, 4, "Y"),
        )
        bm.to_mesh(self.box.data)
        bm.free()
        set_active(self.block)
        self.box.select_set(True)
        bpy.context.view_layer.objects.active = self.box
        bpy.ops.mustardui.model_toolkit_crush(kind="METAL")
        modifier = self.box.modifiers["Crush"]
        effect.modifier_input(modifier, "Subdivisions").value = 0
        self.box.update_tag()
        rest = np.array([x.co[:] for x in self.box.data.vertices]) + [3.0, 0.0, 0.5]
        np.testing.assert_allclose(self.evaluate(1), rest, atol=1e-6)

    def tower(self, **settings):
        """The box as a 2 x 2 x 9 m tower cut every 1.5 m, its floors of 3 m, pressed down by a
        slab wider than it, crushed by the Building preset without Bulge and Crumple"""
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=5, use_grid_fill=True)
        bmesh.ops.transform(bm, matrix=Matrix.Diagonal((2.0, 2.0, 9.0, 1.0)), verts=bm.verts)
        bm.to_mesh(self.box.data)
        bm.free()
        self.box.data.materials.append(bpy.data.materials.new("Concrete"))
        self.box.location = (3.0, 0.0, 4.5)
        self.block.animation_data_clear()
        self.block.data.transform(Matrix.Diagonal((8.0, 8.0, 1.0, 1.0)))
        # Holding 1.5 m down from frame 10 to 15, then 5 m down at frame 30
        for frame, z in ((1, 9.5), (10, 7.7), (15, 7.7), (30, 4.2)):
            self.block.location = (3.0, 0.0, z)
            self.block.keyframe_insert("location", frame=frame)
        self.scene.frame_set(1)
        set_active(self.block)
        self.box.select_set(True)
        bpy.context.view_layer.objects.active = self.box
        bpy.ops.mustardui.model_toolkit_crush(kind="BUILDING")
        modifier = self.box.modifiers["Crush"]
        for name, value in {"Subdivisions": 0, "Bulge": 0.0, "Crumple": 0.0, **settings}.items():
            effect.modifier_input(modifier, name).value = value
        self.box.update_tag()
        return modifier

    # The floors under the slab crushed one after the other from the top, each down to its
    # rubble before the one under it gives, the floors under it untouched; without floors the top
    # floor is squeezed most at its top
    def test_floors(self):
        modifier = self.tower(Debris=False)
        self.assertEqual(effect.modifier_input(modifier, "Floor Height").value, 3.0)
        rest = self.evaluate(1)
        # 1.5 m down the top floor half as high, all of it; 5 m down, it is 0.45 m of rubble and
        # the floor under it 0.55 m
        for frame, heights in (
            (14, ((0.0, 0.0), (4.5, 4.5), (6.0, 6.0), (7.5, 6.75), (9.0, 7.5))),
            (40, ((0.0, 0.0), (3.0, 3.0), (4.5, 3.275), (6.0, 3.55), (7.5, 3.775), (9.0, 4.0))),
        ):
            co = self.evaluate(frame)
            for height, crushed in heights:
                level = np.abs(rest[:, 2] - height) < 1e-3
                np.testing.assert_allclose(co[level, 2], crushed, atol=0.02, err_msg=f"{height} m")
        effect.modifier_input(modifier, "Floor Height").value = 0.0
        self.box.update_tag()
        co = self.evaluate(14)
        self.assertGreater(co[np.abs(rest[:, 2] - 7.5) < 1e-3, 2].min(), 7.1)

    # Debris chips are thrown out of the sides only once crushed, with the material of the mesh,
    # and come to rest on the ground
    def test_debris(self):
        self.tower()
        faces = []
        for frame in range(1, 81):
            self.scene.frame_set(frame)
            data = self.box.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
            faces.append(len(data.polygons))
            if frame == 78:
                before = np.array([x.co[:] for x in data.vertices])
        self.assertEqual(faces[:2], [faces[0]] * 2)
        self.assertGreater(faces[-1], faces[0] + 20 * 10)
        chips = [data.materials[p.material_index] for p in data.polygons[faces[0] :]]
        self.assertTrue(all(x is not None and x.name == "Concrete" for x in chips))
        co = np.array([x.co[:] for x in data.vertices])
        # Resting on the ground, 4.5 m under the origin of the tower
        self.assertGreater(co[:, 2].min(), -4.5 - 1e-3)
        np.testing.assert_allclose(co, before, atol=0.01)
        self.assertEqual([x.message for x in self.box.modifiers["Crush"].node_warnings], [])

    def add_wheels(self):
        """Two 20 cm cubes as wheels in the box mesh, by its sides, in the Wheels group, a 10 cm
        hub touching the first one"""
        bm = bmesh.new()
        bm.from_mesh(self.box.data)
        boxes = ((0.5, -0.62, -0.4, 0.2), (-0.5, 0.62, -0.4, 0.2), (0.5, -0.77, -0.4, 0.1))
        for x, y, z, size in boxes:
            bmesh.ops.create_cube(bm, size=size, matrix=Matrix.Translation((x, y, z)))
        bm.to_mesh(self.box.data)
        bm.free()
        group = self.box.vertex_groups.new(name="Wheels")
        group.add(range(8, 24), 1.0, "REPLACE")

    def thrown(self, **settings):
        """Rest and final positions of the points of the box crushed with Loose Parts"""
        modifier = self.add()
        effect.modifier_input(modifier, "Loose Parts").value = True
        for name, value in settings.items():
            effect.modifier_input(modifier, name).value = value
        self.box.update_tag()
        return self.evaluate(1), self.evaluate(40)

    # The parts in the group are thrown off to the sides and rest on the ground, moved as rigid
    # bodies with the parts touching them, the box staying crushed
    def test_loose_parts(self):
        self.add_wheels()
        rest, co = self.thrown()
        wheels = np.abs(rest[:, 1]) > 0.51
        np.testing.assert_allclose(co[wheels, :2], rest[wheels, :2], atol=1e-6)

        parts = effect.modifier_input(self.box.modifiers["Crush"], "Parts")
        parts.type = "ATTRIBUTE"
        parts.attribute_name = "Wheels"
        self.box.update_tag()
        co = self.evaluate(40)
        np.testing.assert_allclose(co[~wheels], self.evaluate(30)[~wheels], atol=1e-6)
        for side in (-1, 1):
            wheel = wheels & (np.sign(rest[:, 1]) == side)
            # Out to the side, turned as they go
            self.assertGreater(abs(co[wheel, 1].mean()) - abs(rest[wheel, 1].mean()), 0.15)
            self.assertAlmostEqual(co[wheel, 2].min(), 0.0, delta=0.01)
            np.testing.assert_allclose(
                np.linalg.norm(co[wheel][:, None] - co[wheel][None], axis=2),
                np.linalg.norm(rest[wheel][:, None] - rest[wheel][None], axis=2),
                atol=1e-4,
            )
        self.assertEqual([x.message for x in self.box.modifiers["Crush"].node_warnings], [])

    # A part under the block is crushed with the box, not thrown, and the thrown ones come to rest
    def test_pinned_and_resting(self):
        self.add_wheels()
        bm = bmesh.new()
        bm.from_mesh(self.box.data)
        bmesh.ops.create_cube(bm, size=0.1, matrix=Matrix.Translation((0.0, 0.0, -0.3)))
        bm.to_mesh(self.box.data)
        bm.free()
        rest, co = self.thrown(Chance=1.0, **{"Part Size": 0.5})
        seat = np.linalg.norm(rest[:, :2] - [3.0, 0.0], axis=1) < 0.08
        seat &= rest[:, 2] < 0.26
        np.testing.assert_allclose(co[seat, :2], rest[seat, :2], atol=1e-6)
        wheels = np.abs(rest[:, 1]) > 0.51
        self.assertGreater(np.linalg.norm(co[wheels, :2] - rest[wheels, :2], axis=1).max(), 0.15)
        # Lying still on the ground
        np.testing.assert_allclose(self.evaluate(60)[wheels], self.evaluate(70)[wheels], atol=1e-3)
        self.assertAlmostEqual(self.evaluate(70)[wheels, 2].min(), 0.0, delta=0.01)

    # Without the group, the parts smaller than the Part Size are thrown by Chance
    def test_chance(self):
        self.add_wheels()
        for chance, thrown in ((1.0, True), (0.0, False)):
            rest, co = self.thrown(Chance=chance, **{"Part Size": 0.5})
            for side in (-1, 1):
                wheel = (np.abs(rest[:, 1]) > 0.51) & (np.sign(rest[:, 1]) == side)
                moved = np.linalg.norm(co[wheel, :2].mean(0) - rest[wheel, :2].mean(0))
                self.assertEqual(moved > 0.15, thrown)
                self.assertEqual(np.abs(co[wheel] - rest[wheel]).max() > 1e-6, thrown)
            self.box.modifiers.remove(self.box.modifiers["Crush"])

    # Without other selected meshes the model body is the Collider
    def test_body(self):
        set_active(self.box)
        bpy.ops.mustardui.model_toolkit_crush()
        colliders = effect.modifier_input(self.box.modifiers["Crush"], "Colliders").value
        self.assertEqual(list(colliders.objects), [bpy.data.objects["Tester Body"]])

    # The Colliders collection is removed with the effect, keeping its objects in the scene
    def test_remove(self):
        name = effect.modifier_input(self.add(), "Colliders").value.name
        bpy.ops.mustardui.model_toolkit_remove_crush()
        self.assertNotIn("Crush", self.box.modifiers)
        self.assertNotIn(name, bpy.data.collections)
        self.assertIn(self.block, list(self.scene.collection.objects))
        self.assertFalse(bpy.ops.mustardui.model_toolkit_remove_crush.poll())


@unittest.skipUnless(effect.effects_available(), "Needs Blender 5.2")
class TestDustMotes(BlenderTestCase):
    def setUp(self):
        super().setUp()
        configure_model(build_model())
        self.scene = bpy.context.scene
        # Away from the box, not to fade the motes
        self.camera = new_object("Camera", bpy.data.cameras.new("Camera"))
        self.camera.location = (0.0, -10.0, 1.0)
        self.scene.camera = self.camera
        self.body = bpy.data.objects["Tester Body"]

    def add(self, **settings):
        set_active(self.body)
        self.body.select_set(False)
        bpy.ops.mustardui.model_toolkit_dust_motes(**settings)
        return bpy.context.active_object

    def motes(self, box, frame=1):
        """Positions in world space, radii and ids of the motes at the frame"""
        self.scene.frame_set(frame)
        geometry = box.evaluated_get(bpy.context.evaluated_depsgraph_get()).evaluated_geometry()
        points = geometry.pointcloud
        co = np.empty(len(points.points) * 3)
        points.attributes["position"].data.foreach_get("vector", co)
        co = np.c_[co.reshape(-1, 3), np.ones(len(points.points))] @ np.array(box.matrix_world).T
        radius = np.empty(len(points.points))
        points.attributes["radius"].data.foreach_get("value", radius)
        ids = np.empty(len(points.points), dtype=np.int32)
        points.attributes["id"].data.foreach_get("value", ids)
        return co[:, :3], radius, ids, geometry

    # A box around the model body, full of slow motes, and a haze in a Sunbeam
    def test_dust_motes(self):
        box = self.add(kind="SUNBEAM")
        self.assertEqual(box.users_collection, (self.scene.collection,))
        modifier = box.modifiers["Dust Motes"]
        self.assertEqual(
            effect.modifier_input(modifier, "Motes Material").value.name, "MustardUI Dust Motes"
        )
        corners = np.array([v.co[:] for v in box.data.vertices]) + box.location[:]
        low, high = corners.min(0), corners.max(0)
        body = np.array([self.body.matrix_world @ Vector(x) for x in self.body.bound_box])
        np.testing.assert_allclose(low, body.min(0) - [0.75, 0.75, 0.0], atol=1e-5)
        np.testing.assert_allclose(high, body.max(0) + 0.75, atol=1e-5)

        co, radius, ids, geometry = self.motes(box)
        # About the Density per cubic meter, a few faded at the sides
        expected = 800.0 * np.prod(high - low)
        self.assertGreater(len(co), expected * 0.7)
        self.assertLessEqual(len(co), expected)
        self.assertTrue(np.all((co > low - 0.01) & (co < high + 0.01)))
        self.assertGreater(radius.min(), 0.0)
        self.assertAlmostEqual(np.median(radius) * 2, 0.0012 * 0.8, delta=0.0003)
        for name in ("dust_motes_light", "dust_motes_color"):
            self.assertIn(name, geometry.pointcloud.attributes)
        self.assertIsNotNone(geometry.volume)
        # The box edges, to see it
        self.assertEqual((len(geometry.mesh.edges), len(geometry.mesh.polygons)), (12, 0))
        self.assertEqual([x.message for x in modifier.node_warnings], [])

        # Very slow, about the Swirl Speed
        later, _, later_ids, _ = self.motes(box, 25)
        common, a, b = np.intersect1d(ids, later_ids, return_indices=True)
        speed = np.median(np.linalg.norm(later[b] - co[a], axis=1))
        self.assertGreater(speed, 0.002)
        self.assertLess(speed, 0.01)

        # No haze in a Room
        bpy.ops.mustardui.model_toolkit_remove_dust_motes()
        _, _, _, geometry = self.motes(self.add(kind="ROOM"))
        self.assertIsNone(geometry.volume)

    # Scaling the box keeps the motes per cubic meter and their size
    def test_scale(self):
        box = self.add()
        co, radius, _, _ = self.motes(box)
        box.scale = (2.0, 2.0, 2.0)
        bpy.context.view_layer.update()
        scaled, scaled_radius, _, _ = self.motes(box)
        self.assertAlmostEqual(len(scaled) / len(co), 8.0, delta=0.6)
        self.assertAlmostEqual(np.median(scaled_radius) * 2, np.median(radius), delta=1e-4)

    # The motes shrink away in front of the camera
    def test_camera_fade(self):
        box = self.add()
        self.camera.location = box.location + Vector((0.0, 0.0, 0.8))
        co, radius, _, _ = self.motes(box)
        near = np.linalg.norm(co - self.camera.location[:], axis=1) < 0.15
        self.assertGreater(near.sum(), 3)
        self.assertLess(radius[near].mean(), radius.mean() * 0.3)

    def test_remove(self):
        box = self.add()
        self.assertTrue(bpy.ops.mustardui.model_toolkit_remove_dust_motes.poll())
        bpy.ops.mustardui.model_toolkit_remove_dust_motes()
        self.assertNotIn(box, list(bpy.data.objects))
        self.assertFalse(bpy.ops.mustardui.model_toolkit_remove_dust_motes.poll())


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


# Attributes of the spark streaks, no mesh attributes copied to them
STREAK_ATTRIBUTES = {"position", "material_index", "aura_spark"}


@unittest.skipUnless(effect.effects_available(), "Needs Blender 5.2")
class TestAura(BlenderTestCase):
    def setUp(self):
        super().setUp()
        configure_model(build_model())
        self.scene = bpy.context.scene
        self.armature = bpy.data.objects["Tester Armature"]
        self.body = bpy.data.objects["Tester Body"]
        self.shirt = bpy.data.objects["Casual - Shirt"]
        self.start = self.scene.frame_current
        set_active(self.body)
        self.shirt.select_set(True)

    def add(self, **settings):
        bpy.ops.mustardui.model_toolkit_aura(
            **{"pulses": 2, "duration": 10, "pause": 4, **settings}
        )
        return effect.modifier_input(self.body.modifiers["Aura"], "Control").value

    def evaluated(self, obj, frame):
        self.scene.frame_set(frame)
        return obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).evaluated_geometry()

    def stepped(self, obj, frame):
        """Geometry at the frame after all the frames from the start, for the sparks to simulate"""
        for f in range(self.start, frame):
            self.scene.frame_set(f)
        return self.evaluated(obj, frame)

    def streaks(self, geometry):
        """Number of spark streaks, tubes of two rings of 4 vertices"""
        references = geometry.instance_references()
        return len(references[0].mesh.vertices) // 8 if references else 0

    def glow(self, geometry):
        glow = np.empty(len(geometry.mesh.vertices) * 3)
        geometry.mesh.attributes["aura_glow"].data.foreach_get("vector", glow)
        return glow.reshape(-1, 3)

    def surface(self, material):
        nodes = material.node_tree.nodes
        return nodes["Material Output"].inputs["Surface"].links[0].from_node

    # The meshes glow and throw sparks in pulses by the Glow of a Control at the feet of the model
    def test_aura(self):
        world = self.armature.matrix_world.copy()
        control = self.add()
        self.assertEqual(control.MustardUI_tools_creators_type, "EFFECT_AURA")
        self.assertEqual(control.users_collection, (self.scene.collection,))
        self.assertEqual(control.parent, self.armature)
        meshes = [x for x in self.armature.children if x.type == "MESH" and x.visible_get()]
        corners = np.array([x.matrix_world @ Vector(c) for x in meshes for c in x.bound_box])
        low, high = corners.min(0), corners.max(0)
        np.testing.assert_allclose(
            control.matrix_world.translation, [*(low[:2] + high[:2]) / 2, low[2]], atol=1e-6
        )
        modifier = self.body.modifiers["Aura"]
        self.assertEqual([m.type for m in self.body.modifiers], ["ARMATURE", "MASK", "NODES"])
        self.assertEqual(effect.modifier_input(modifier, "Control").value, control)
        # Without the hands and feet of an MHX model, no Hot Spots
        self.assertIsNone(effect.modifier_input(modifier, "Hot Spots").value)
        self.assertEqual(effect.modifier_input(modifier, "Body Glow").value, 1.0)

        # Glowing and throwing sparks in a pulse, the model left in place
        geometry = self.stepped(self.body, self.start + 6)
        self.assertEqual(self.armature.parent, None)
        np.testing.assert_allclose(self.armature.matrix_world, world, atol=1e-6)
        self.assertAlmostEqual(effect.modifier_input(modifier, "Glow").value, 1.0, places=4)
        glow = self.glow(geometry)
        # Without Hot Spots, an even outline glow and no fill
        self.assertGreater(glow[:, 0].min(), 0.0)
        self.assertAlmostEqual(glow[:, 0].mean(), 1.0, delta=0.35)
        self.assertEqual(np.abs(glow[:, 1:]).max(), 0.0)
        (reference,) = geometry.instance_references()
        streaks = reference.mesh
        # Amount per square meter per second of Glow, about 0.2 s of it by now
        area = 6 * (2 * 0.5) ** 2
        self.assertAlmostEqual(self.streaks(geometry), 80.0 * area * 0.2, delta=80.0 * area * 0.08)
        self.assertEqual(streaks.materials[0].name, "MustardUI Aura Sparks")
        self.assertEqual(
            {x.name for x in streaks.attributes if not x.name.startswith(".")},
            STREAK_ATTRIBUTES,
        )
        self.assertEqual([x.message for x in modifier.node_warnings], [])
        # The sparks flying on in the pause
        geometry = self.stepped(self.body, self.start + 13)
        self.assertNotIn("aura_glow", geometry.mesh.attributes)
        self.assertGreater(self.streaks(geometry), 50)

        # The skin glows under its shader
        material = self.body.material_slots[0].material
        group = self.surface(material)
        self.assertEqual(group.node_tree.name, "MustardUI Aura Glow Settings")
        self.assertEqual(group.inputs["Shader"].links[0].from_node.type, "BSDF_PRINCIPLED")

    # Sparks rise up the Control from the surface while flying, as streaks fading to their tails
    def test_sparks(self):
        self.add(duration=48)
        geometry = self.stepped(self.body, self.start + 14)
        reference = geometry.instance_references()[0]
        streaks = reference.mesh
        n = len(streaks.vertices)
        co, light = np.empty(n * 3), np.empty(n * 3)
        streaks.attributes["position"].data.foreach_get("vector", co)
        streaks.attributes["aura_spark"].data.foreach_get("vector", light)
        # Rings of the head and of the tail of each streak
        co, light = co.reshape(-1, 2, 4, 3), light.reshape(-1, 2, 4, 3)
        centers = co.mean(2)
        radius = np.linalg.norm(co - centers[:, :, None], axis=3).mean(2)
        heads, tails = centers[:, 0], centers[:, 1]
        light = light.max(2)
        # The rise lifts the sparks off the top face on average
        self.assertGreater(heads[:, 2].max(), 1.5)
        self.assertGreater(np.mean(heads[:, 2]), 1.0)
        # Tails the Length behind the heads, below them, thinner and dark
        np.testing.assert_allclose(np.linalg.norm(heads - tails, axis=1), 0.05, atol=1e-4)
        self.assertGreater(np.mean(heads[:, 2] > tails[:, 2]), 0.9)
        np.testing.assert_allclose(radius[:, 1], radius[:, 0] * 0.3, atol=1e-6)
        # Up to the Size, 4 mm thick, times 1.5 at most
        self.assertLess(radius[:, 0].max(), 0.004 / 2 * 1.5 + 1e-6)
        self.assertGreater(radius[:, 0].max(), 0.001)
        self.assertGreater(light[:, 0].max(), 1.0)
        self.assertEqual(np.abs(light[:, 1]).max(), 0.0)

    # Sparks fly on after the Glow ends, until their Lifetime, at most 1.3 times 2 s
    def test_linger(self):
        control = self.add(duration=12, pulses=1)
        # The Glow fades out at frame 15, 2 frames after the pulse
        geometry = self.stepped(self.body, self.start + 16)
        self.assertEqual(control["Glow"], 0.0)
        self.assertGreater(self.streaks(geometry), 50)
        self.assertGreater(self.streaks(self.stepped(self.body, self.start + 60)), 0)
        self.assertEqual(self.streaks(self.stepped(self.body, self.start + 16 + 64)), 0)

    # On MHX models, Empties on the bones of the hands and feet glow, nothing else
    def test_hot_spots(self):
        set_active(self.armature)
        bpy.ops.object.mode_set(mode="EDIT")
        bone = self.armature.data.edit_bones.new("hand.L")
        bone.head, bone.tail = (0.0, -0.5, 0.3), (0.0, -0.5, 0.5)
        bpy.ops.object.mode_set(mode="OBJECT")
        self.body.vertex_groups.new(name="hand.L").add([0, 1], 1.0, "REPLACE")
        # Little weight, not part of the hand
        self.body.vertex_groups.new(name="f_index.01.L").add([2], 0.3, "REPLACE")
        set_active(self.body)
        self.shirt.select_set(True)
        self.add()

        spots = effect.modifier_input(self.body.modifiers["Aura"], "Hot Spots").value
        self.assertEqual(spots.name, "Tester Armature Aura Hot Spots")
        self.assertIn(spots, list(self.scene.collection.children))
        (empty,) = spots.objects
        self.assertEqual(empty.name, "Tester Armature Aura Hand.L")
        self.assertEqual((empty.parent, empty.parent_type), (self.armature, "BONE"))
        self.assertEqual(empty.parent_bone, "hand.L")
        self.assertEqual(empty.MustardUI_tools_creators_type, "EFFECT_AURA_HOT_SPOT")
        # Around the two vertices of the hand
        bpy.context.view_layer.update()
        np.testing.assert_allclose(empty.matrix_world.translation, (0.0, -0.5, 0.5), atol=1e-5)
        self.assertAlmostEqual(empty.matrix_world.to_scale().x, 0.5 * 1.15, places=5)
        # On all the meshes of the model, the outline only on the Hot Spots
        for obj in (self.body, self.shirt):
            modifier = obj.modifiers["Aura"]
            self.assertEqual(effect.modifier_input(modifier, "Hot Spots").value, spots)
            self.assertEqual(effect.modifier_input(modifier, "Body Glow").value, 0.0)

        # Glowing inside the sphere, outline and fill, nothing out of it, without shimmer
        effect.modifier_input(self.body.modifiers["Aura"], "Shimmer").value = 0.0
        self.body.update_tag()
        glow = self.glow(self.evaluated(self.body, self.start + 6))
        # Vertices at 87% of the radius, fully glowing inside 90% of it with the Softness 0.2
        np.testing.assert_allclose(glow[:2], [[3.0, 1.0, 0.0]] * 2, atol=1e-4)
        self.assertEqual(np.abs(glow[2:]).max(), 0.0)
        # Softer, fading out from 75% to 125% of the radius
        effect.modifier_input(self.body.modifiers["Aura"], "Softness").value = 0.5
        self.body.update_tag()
        glow = self.glow(self.evaluated(self.body, self.start + 6))
        hot = 0.76**2 * (3 - 2 * 0.76)
        np.testing.assert_allclose(glow[:2, 0], 3.0 * hot, atol=0.05)
        self.assertEqual(np.abs(glow[2:]).max(), 0.0)

        # A fifth of the sparks off the Hot Spots without Body Glow, the Empty away from the shirt
        empty.matrix_world = Matrix.Translation((10.0, 0.0, 0.0)) @ empty.matrix_world
        bpy.context.view_layer.update()
        few = self.streaks(self.stepped(self.shirt, self.start + 10))
        effect.modifier_input(self.shirt.modifiers["Aura"], "Body Glow").value = 1.0
        self.shirt.update_tag()
        many = self.streaks(self.stepped(self.shirt, self.start + 10))
        self.assertGreater(few, 0)
        self.assertAlmostEqual(few / many, 0.2, delta=0.1)

    # The glow is under the mixes with transparency, given the alpha of the shaders
    def test_transparency(self):
        material = bpy.data.materials.new("Lashes")
        nodes, links = material.node_tree.nodes, material.node_tree.links
        principled = nodes["Principled BSDF"]
        alpha = nodes.new("ShaderNodeValue")
        links.new(alpha.outputs[0], principled.inputs["Alpha"])
        mix = nodes.new("ShaderNodeMixShader")
        links.new(nodes.new("ShaderNodeBsdfTransparent").outputs[0], mix.inputs[1])
        links.new(principled.outputs[0], mix.inputs[2])
        links.new(mix.outputs[0], nodes["Material Output"].inputs["Surface"])
        self.shirt.data.materials.append(material)
        self.add()
        self.assertEqual(self.surface(material), mix)
        group = mix.inputs[2].links[0].from_node
        self.assertEqual(group.node_tree.name, "MustardUI Aura Glow Settings")
        self.assertEqual(group.inputs["Opacity"].links[0].from_node, alpha)

    # Removing it from all the meshes removes the Control, the Hot Spots and the glow
    def test_remove(self):
        set_active(self.armature)
        bpy.ops.object.mode_set(mode="EDIT")
        bone = self.armature.data.edit_bones.new("foot.R")
        bone.head, bone.tail = (0.0, 0.5, 0.3), (0.0, 0.5, 0.5)
        bpy.ops.object.mode_set(mode="OBJECT")
        self.body.vertex_groups.new(name="foot.R").add([2, 3], 1.0, "REPLACE")
        set_active(self.body)
        self.shirt.select_set(True)
        control = self.add()
        spots = effect.modifier_input(self.body.modifiers["Aura"], "Hot Spots").value
        # An Empty added by hand, kept in the scene
        mine = new_object("Mine", collection=spots)

        # Removed from the body only, the shirt keeps the Control and the Hot Spots
        set_active(self.body)
        bpy.ops.mustardui.model_toolkit_remove_aura()
        self.assertNotIn("Aura", self.body.modifiers)
        self.assertFalse(self.body.animation_data and self.body.animation_data.drivers)
        self.assertIn(control, list(bpy.data.objects))
        self.assertIn(spots, list(bpy.data.collections))

        set_active(self.shirt)
        bpy.ops.mustardui.model_toolkit_remove_aura()
        self.assertNotIn(control, list(bpy.data.objects))
        self.assertNotIn(spots, list(bpy.data.collections))
        self.assertFalse([x for x in bpy.data.objects if x.name.startswith("Tester Armature Aura")])
        self.assertEqual(mine.users_collection, (self.scene.collection,))
        skin = self.body.material_slots[0].material
        self.assertEqual(self.surface(skin).type, "BSDF_PRINCIPLED")
        self.assertFalse(bpy.ops.mustardui.model_toolkit_remove_aura.poll())
