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

disintegration = importlib.import_module(ADDON + ".model_toolkit.effects.ops_disintegration")


class TestDisintegration(BlenderTestCase):
    def setUp(self):
        super().setUp()
        configure_model(build_model())
        self.shirt = bpy.data.objects["Casual - Shirt"]
        self.pants = bpy.data.objects["Casual - Pants"]
        self.shirt.modifiers.new("Subdivision", "SUBSURF")
        set_active(self.shirt)
        self.pants.select_set(True)

    @unittest.skipIf(bpy.app.version >= (5, 2, 0), "Blender 5.2 supports the effect")
    def test_unavailable(self):
        self.assertFalse(bpy.ops.mustardui.model_toolkit_disintegration.poll())

    # The meshes are cut by the growing Control, and emit particles from the cut
    @unittest.skipUnless(disintegration.disintegration_available(), "Needs Blender 5.2")
    def test_disintegration(self):
        bpy.ops.mustardui.model_toolkit_disintegration(duration=10)
        self.assertEqual([m.type for m in self.shirt.modifiers], ["ARMATURE", "NODES", "SUBSURF"])
        modifier = self.shirt.modifiers["Disintegration"]
        control = disintegration.modifier_input(modifier, "Control").value
        self.assertEqual(
            control, disintegration.modifier_input(self.pants.modifiers[-1], "Control").value
        )
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
    @unittest.skipUnless(disintegration.disintegration_available(), "Needs Blender 5.2")
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
    @unittest.skipUnless(disintegration.disintegration_available(), "Needs Blender 5.2")
    def test_remove(self):
        bpy.ops.mustardui.model_toolkit_disintegration()
        control = disintegration.modifier_input(
            self.shirt.modifiers["Disintegration"], "Control"
        ).value
        name = control.name

        set_active(self.shirt)
        bpy.ops.mustardui.model_toolkit_remove_disintegration()
        self.assertNotIn("Disintegration", self.shirt.modifiers)
        self.assertIn(name, bpy.data.objects)

        set_active(self.pants)
        bpy.ops.mustardui.model_toolkit_remove_disintegration()
        self.assertNotIn("Disintegration", self.pants.modifiers)
        self.assertNotIn(name, bpy.data.objects)
