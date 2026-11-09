import importlib
import unittest

import bmesh
import bpy
import gpu
import numpy as np
from helpers import ADDON, BlenderTestCase, new_object, set_active

solver = importlib.import_module(ADDON + ".model_toolkit.cloth.solver")
try:
    gpu.init()  # headless: Cloth Physics needs a GPU context
except Exception:
    pass


def new_box():
    """0.6 m cube centered at z 1 (top at 1.3), outward normals (the helpers' cube faces inward)"""
    mesh = bpy.data.meshes.new("Box")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=0.6)
    bm.to_mesh(mesh)
    bm.free()
    obj = new_object("Box", mesh)
    obj.location.z = 1.0
    return obj


def new_sheet(z=1.4):
    mesh = bpy.data.meshes.new("Sheet")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=24, y_segments=24, size=0.4)
    bm.to_mesh(mesh)
    bm.free()
    obj = new_object("Sheet", mesh)
    obj.location.z = z
    return obj


class TestCloth(BlenderTestCase):
    # Baking drapes the sheet on the box: it falls, stays finite and outside the box
    @unittest.skipUnless(solver.gpu_available(), "Needs a GPU with compute shaders")
    def test_bake(self):
        box = new_box()
        sheet = new_sheet()
        sheet.MustardUI_Cloth.collider = box
        sheet.MustardUI_Cloth.follow = 0.0  # no Armature: Follow Body would hold the rest shape
        set_active(sheet)
        self.assertEqual(bpy.ops.mustardui.model_toolkit_cloth_enable(), {"FINISHED"})
        scene = bpy.context.scene
        scene.frame_start, scene.frame_end = 1, 20
        self.assertEqual(bpy.ops.mustardui.model_toolkit_cloth_bake(), {"FINISHED"})

        world = solver.WORLD["world"]
        self.assertEqual(sorted(world.cache), list(range(1, 21)))
        pos = world.cache[20][0]
        self.assertTrue(np.isfinite(pos).all())
        self.assertLess(pos[:, 2].max(), 1.4 - 0.05)
        # The box top is at z 1.3: the middle of the sheet rests on it
        middle = np.linalg.norm(pos[:, :2], axis=1) < 0.2
        self.assertGreater(pos[middle, 2].min(), 1.3 - 0.003)

    # Without a GPU the operators are disabled
    def test_without_gpu(self):
        sheet = new_sheet()
        set_active(sheet)
        available = solver.gpu_available
        solver.gpu_available = lambda: False
        try:
            self.assertFalse(bpy.ops.mustardui.model_toolkit_cloth_enable.poll())
        finally:
            solver.gpu_available = available


if __name__ == "__main__":
    unittest.main()
