import bpy
import numpy as np
from helpers import BlenderTestCase, new_object


def grid_object(name, size=1.0, subdivisions=10, location=(0.0, 0.0, 0.0)):
    mesh = bpy.data.meshes.new(name)
    n = subdivisions + 1
    lin = np.linspace(-size, size, n)
    verts = [(x, y, 0.0) for y in lin for x in lin]
    faces = [
        (j * n + i, j * n + i + 1, (j + 1) * n + i + 1, (j + 1) * n + i)
        for j in range(subdivisions)
        for i in range(subdivisions)
    ]
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = new_object(name, mesh)
    obj.location = location
    return obj


def key_offsets(obj, name):
    sks = obj.data.shape_keys
    co = np.array([d.co for d in sks.key_blocks[name].data])
    basis = np.array([d.co for d in sks.reference_key.data])
    return co - basis


class TestTransferShapeKeys(BlenderTestCase):
    def setUp(self):
        super().setUp()
        self.source = grid_object("Source")
        self.source.shape_key_add(name="Basis")
        # Shape Key raising the vertices by their x coordinate
        lift = self.source.shape_key_add(name="Lift", from_mix=False)
        for d in lift.data:
            d.co.z += 0.1 * (d.co.x + 1.0)
        lift.slider_max = 2.0
        # Shape Key without effect
        self.source.shape_key_add(name="Empty", from_mix=False)

        self.target = grid_object("Target", size=0.5, subdivisions=7, location=(0, 0, 0.001))
        self.select(self.target, self.source)

    def select(self, *objs):
        bpy.context.view_layer.update()
        for obj in bpy.context.view_layer.objects:
            obj.select_set(obj in objs)
        bpy.context.view_layer.objects.active = objs[-1]

    # The offsets are interpolated on the source surface, empty keys skipped
    def test_transfer(self):
        bpy.ops.mustardui.tools_creators_transfer_shape_keys()

        sks = self.target.data.shape_keys
        self.assertIn("Lift", sks.key_blocks)
        self.assertNotIn("Empty", sks.key_blocks)
        self.assertEqual(sks.key_blocks["Lift"].slider_max, 2.0)

        offsets = key_offsets(self.target, "Lift")
        xs = np.array([v.co.x for v in self.target.data.vertices])
        np.testing.assert_allclose(offsets[:, 2], 0.1 * (xs + 1.0), atol=1e-5)

        # Values driven by the source
        fcurve = sks.animation_data.drivers.find('key_blocks["Lift"].value')
        self.assertIsNotNone(fcurve)

    # Offsets follow the object transforms
    def test_transformed_target(self):
        self.target.rotation_euler = (np.pi, 0.0, 0.0)
        self.target.scale = (2.0, 2.0, 2.0)
        self.target.location = (0.0, 0.0, 0.0)
        bpy.context.view_layer.update()

        bpy.ops.mustardui.tools_creators_transfer_shape_keys(link=False)

        offsets = key_offsets(self.target, "Lift")
        xs = np.array([v.co.x for v in self.target.data.vertices])
        # Rotated by 180 degrees around x and scaled by 2
        np.testing.assert_allclose(offsets[:, 2], -0.05 * (2.0 * xs + 1.0), atol=1e-5)

    # Keys relative to another key transfer only their own offset
    def test_relative_key(self):
        lift = self.source.data.shape_keys.key_blocks["Lift"]
        more = self.source.shape_key_add(name="More", from_mix=False)
        for d, base in zip(more.data, lift.data, strict=True):
            d.co = base.co
            d.co.z += 0.05
        more.relative_key = lift

        bpy.ops.mustardui.tools_creators_transfer_shape_keys()

        offsets = key_offsets(self.target, "More")
        np.testing.assert_allclose(offsets[:, 2], 0.05, atol=1e-5)

    # Existing keys are kept unless overwrite is enabled
    def test_overwrite(self):
        self.target.shape_key_add(name="Basis")
        self.target.shape_key_add(name="Lift")

        bpy.ops.mustardui.tools_creators_transfer_shape_keys()
        self.assertAlmostEqual(np.abs(key_offsets(self.target, "Lift")).max(), 0.0)

        bpy.ops.mustardui.tools_creators_transfer_shape_keys(overwrite=True)
        self.assertGreater(np.abs(key_offsets(self.target, "Lift")).max(), 0.01)

    # Vertices beyond the max distance are not moved
    def test_max_distance(self):
        far = grid_object("Far", size=0.5, subdivisions=3, location=(0, 0, 1.0))
        self.select(self.target, far, self.source)

        bpy.ops.mustardui.tools_creators_transfer_shape_keys(max_distance=0.1)

        self.assertIn("Lift", self.target.data.shape_keys.key_blocks)
        self.assertIsNone(far.data.shape_keys)

    # Nearest vertex copies the offsets of meshes sharing the vertices
    def test_nearest_vertex(self):
        copy = grid_object("Copy")
        self.select(copy, self.source)

        bpy.ops.mustardui.tools_creators_transfer_shape_keys(method="VERTEX")

        np.testing.assert_allclose(
            key_offsets(copy, "Lift"), key_offsets(self.source, "Lift"), atol=1e-6
        )

    # The Vertex Group restricts the targets having it, inverted if requested
    def test_vertex_group(self):
        group = self.target.vertex_groups.new(name="Mask")
        left = [v.index for v in self.target.data.vertices if v.co.x < 0.0]
        group.add(left, 1.0, "REPLACE")
        other = grid_object("Other", size=0.5, subdivisions=3, location=(0, 0, 0.001))
        self.select(self.target, other, self.source)

        bpy.ops.mustardui.tools_creators_transfer_shape_keys(vertex_group="Mask")

        offsets = key_offsets(self.target, "Lift")[:, 2]
        xs = np.array([v.co.x for v in self.target.data.vertices])
        np.testing.assert_allclose(offsets[xs < 0.0], 0.1 * (xs[xs < 0.0] + 1.0), atol=1e-5)
        np.testing.assert_allclose(offsets[xs >= 0.0], 0.0, atol=1e-6)
        self.assertGreater(key_offsets(other, "Lift")[:, 2].min(), 0.0)

        bpy.ops.mustardui.tools_creators_transfer_shape_keys(
            vertex_group="Mask", invert_vertex_group=True, overwrite=True
        )

        offsets = key_offsets(self.target, "Lift")[:, 2]
        np.testing.assert_allclose(offsets[xs < 0.0], 0.0, atol=1e-6)
        np.testing.assert_allclose(offsets[xs >= 0.0], 0.1 * (xs[xs >= 0.0] + 1.0), atol=1e-5)
