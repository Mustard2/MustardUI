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

    # Collision off: the sheet falls through the box; the X removes the cloth from its mesh
    @unittest.skipUnless(solver.gpu_available(), "Needs a GPU with compute shaders")
    def test_collision_off_and_remove(self):
        box = new_box()
        sheet = new_sheet()
        sheet.MustardUI_Cloth.collider = box
        sheet.MustardUI_Cloth.follow = 0.0
        sheet.MustardUI_Cloth.collision = False
        set_active(sheet)
        bpy.ops.mustardui.model_toolkit_cloth_enable()
        bpy.context.scene.frame_start, bpy.context.scene.frame_end = 1, 20
        bpy.ops.mustardui.model_toolkit_cloth_bake()
        pos = solver.WORLD["world"].cache[20][0]
        self.assertLess(pos[np.linalg.norm(pos[:, :2], axis=1) < 0.2, 2].max(), 1.25)

        set_active(box)
        bpy.ops.mustardui.model_toolkit_cloth_remove(name=sheet.name)
        self.assertFalse(sheet.MustardUI_Cloth.enabled)
        self.assertIsNone(sheet.modifiers.get(solver.RESULT_MOD))
        self.assertIsNone(bpy.data.objects.get(solver.helper_name(sheet)))

    # Follow Body pulls toward a collider deformed by its modifiers (here a Hook, physics cages on
    # models), and toward the cloth's own shape when the collider only moves
    @unittest.skipUnless(solver.gpu_available(), "Needs a GPU with compute shaders")
    def test_follow_deformed_collider(self):
        moved = []
        for hooked in (False, True):
            box = new_box()
            sheet = new_sheet()
            mover = box
            if hooked:
                mover = new_object("Hook")
                mover.location = box.location
                hook = box.modifiers.new("Hook", "HOOK")
                hook.object = mover
                hook.vertex_indices_set(range(len(box.data.vertices)))
            mover.keyframe_insert("location", index=0, frame=1)
            mover.location.x = 0.1
            mover.keyframe_insert("location", index=0, frame=20)
            mover.location.x = 0.0
            cloth = sheet.MustardUI_Cloth
            cloth.collider, cloth.follow = box, 1.0
            set_active(sheet)
            bpy.ops.mustardui.model_toolkit_cloth_enable()
            bpy.context.scene.frame_start, bpy.context.scene.frame_end = 1, 20
            bpy.ops.mustardui.model_toolkit_cloth_bake()
            world = solver.WORLD["world"]
            moved.append(world.cache[20][0][:, 0].mean() - world.cache[1][0][:, 0].mean())
            bpy.ops.mustardui.model_toolkit_cloth_remove(name=sheet.name)
        self.assertLess(abs(moved[0]), 0.03)
        self.assertGreater(moved[1], 0.08)

    # Floor: the sheet, without a collider, falls onto it and rests there
    @unittest.skipUnless(solver.gpu_available(), "Needs a GPU with compute shaders")
    def test_floor(self):
        sheet = new_sheet()
        sheet.MustardUI_Cloth.follow = 0.0
        set_active(sheet)
        bpy.ops.mustardui.model_toolkit_cloth_enable()
        scene = bpy.context.scene
        scene.MustardUI_ClothScene.floor = True
        scene.MustardUI_ClothScene.floor_height = 1.0
        scene.frame_start, scene.frame_end = 1, 30
        bpy.ops.mustardui.model_toolkit_cloth_bake()
        pos = solver.WORLD["world"].cache[30][0]
        self.assertGreater(pos[:, 2].min(), 1.0)
        self.assertLess(pos[:, 2].max(), 1.01)

    # Pin Empties: the cloth around the 3D cursor follows the animated Empty, removed with it
    @unittest.skipUnless(solver.gpu_available(), "Needs a GPU with compute shaders")
    def test_pin_empty(self):
        box = new_box()
        sheet = new_sheet()
        sheet.MustardUI_Cloth.collider = box
        set_active(sheet)
        bpy.ops.mustardui.model_toolkit_cloth_enable()
        scene = bpy.context.scene
        scene.cursor.location = (0.4, 0.4, 1.4)
        self.assertEqual(bpy.ops.mustardui.model_toolkit_cloth_add_pin_empty(), {"FINISHED"})
        item = sheet.MustardUI_Cloth.pin_empties[0]
        empty, group = item.empty, item.group
        # A larger radius pins more of the cloth, at once
        pinned = len(solver.WORLD["world"].empty_bind[0][1])
        item.radius = 0.1
        self.assertGreater(len(solver.WORLD["world"].empty_bind[0][1]), 2 * pinned)
        self.assertAlmostEqual(empty.empty_display_size, 0.1, places=6)
        empty.keyframe_insert("location", index=2, frame=1)
        empty.location.z += 0.15
        empty.keyframe_insert("location", index=2, frame=20)
        scene.frame_start, scene.frame_end = 1, 20
        bpy.ops.mustardui.model_toolkit_cloth_bake()
        world = solver.WORLD["world"]
        pinned = world.empty_bind[0][1]
        lift = world.cache[20][0][pinned, 2] - world.cache[1][0][pinned, 2]
        self.assertTrue(np.allclose(lift, 0.15, atol=0.002))

        bpy.ops.mustardui.model_toolkit_cloth_remove_pin_empty()
        self.assertEqual(len(sheet.MustardUI_Cloth.pin_empties), 0)
        self.assertIsNone(sheet.vertex_groups.get(group))
        self.assertNotIn("Sheet Pin", bpy.data.objects)

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
