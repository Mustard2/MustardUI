import importlib

import bmesh
import bpy
import numpy as np
from fake_ui import Drawer, FakeLayout
from helpers import ADDON, BlenderTestCase, new_object
from mathutils import Matrix
from mathutils.bvhtree import BVHTree

fit_to_body = importlib.import_module(ADDON + ".model_toolkit.outfits.ops_fit_to_body")
fit_optimizer = importlib.import_module(ADDON + ".model_toolkit.outfits.fit_optimizer")
weight_transfer = importlib.import_module(ADDON + ".model_toolkit.mesh.weight_transfer")
mesh_deform = importlib.import_module(ADDON + ".misc.mesh_deform")
ops_transfer = importlib.import_module(ADDON + ".model_toolkit.mesh.ops_transfer_vertex_groups")
preview = importlib.import_module(ADDON + ".model_toolkit.mesh.shape_key_preview")
intersection = importlib.import_module(ADDON + ".misc.mesh_intersection")
squish = importlib.import_module(ADDON + ".model_toolkit.outfits.ops_squish")
smooth_sk = importlib.import_module(ADDON + ".model_toolkit.mesh.ops_smooth_shape_key")


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
        bpy.ops.mustardui.model_toolkit_transfer_shape_keys()

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

        bpy.ops.mustardui.model_toolkit_transfer_shape_keys(link=False)

        offsets = key_offsets(self.target, "Lift")
        xs = np.array([v.co.x for v in self.target.data.vertices])
        # Rotated by 180 degrees around x and scaled by 2
        np.testing.assert_allclose(offsets[:, 2], -0.05 * (2.0 * xs + 1.0), atol=1e-5)

    # The threshold is in world space, whatever the scale of the target
    def test_threshold_scale(self):
        tiny = self.source.shape_key_add(name="Tiny", from_mix=False)
        for d in tiny.data:
            d.co.z += 0.00005
        # Scale 0.01 with the mesh 100 times bigger, as some imported models
        self.target.data.transform(Matrix.Scale(100.0, 4))
        self.target.scale = (0.01, 0.01, 0.01)
        bpy.context.view_layer.update()

        bpy.ops.mustardui.model_toolkit_transfer_shape_keys(threshold=0.0001)
        sks = self.target.data.shape_keys.key_blocks
        self.assertIn("Lift", sks)
        self.assertNotIn("Tiny", sks)

    # Smoothing removes the noise of the transferred Shape Keys, keeping their size
    def test_smooth(self):
        noisy = self.source.shape_key_add(name="Noisy", from_mix=False)
        rng = np.random.default_rng(2)
        for d in noisy.data:
            d.co.z += 0.1 * (d.co.x + 1.0) + rng.uniform(-0.01, 0.01)

        bpy.ops.mustardui.model_toolkit_transfer_shape_keys(link=False)
        plain = key_offsets(self.target, "Noisy")[:, 2]
        self.target.shape_key_remove(self.target.data.shape_keys.key_blocks["Noisy"])
        bpy.ops.mustardui.model_toolkit_transfer_shape_keys(link=False, smooth=0.3)
        smooth = key_offsets(self.target, "Noisy")[:, 2]

        def noise(z):
            z = z.reshape(8, 8)
            return np.abs(np.diff(z, 2, axis=0)).mean() + np.abs(np.diff(z, 2, axis=1)).mean()

        self.assertLess(noise(smooth), 0.5 * noise(plain))
        self.assertAlmostEqual(smooth.max(), plain.max(), delta=0.01)

    # Keys relative to another key transfer only their own offset
    def test_relative_key(self):
        lift = self.source.data.shape_keys.key_blocks["Lift"]
        more = self.source.shape_key_add(name="More", from_mix=False)
        for d, base in zip(more.data, lift.data, strict=True):
            d.co = base.co
            d.co.z += 0.05
        more.relative_key = lift

        bpy.ops.mustardui.model_toolkit_transfer_shape_keys()

        offsets = key_offsets(self.target, "More")
        np.testing.assert_allclose(offsets[:, 2], 0.05, atol=1e-5)

    # Existing keys are kept unless overwrite is enabled
    def test_overwrite(self):
        self.target.shape_key_add(name="Basis")
        self.target.shape_key_add(name="Lift")

        bpy.ops.mustardui.model_toolkit_transfer_shape_keys()
        self.assertAlmostEqual(np.abs(key_offsets(self.target, "Lift")).max(), 0.0)

        bpy.ops.mustardui.model_toolkit_transfer_shape_keys(overwrite=True)
        self.assertGreater(np.abs(key_offsets(self.target, "Lift")).max(), 0.01)

    # Overwrite never writes the reference key, and resets the keys below the threshold
    def test_overwrite_reference_and_threshold(self):
        reference = self.target.shape_key_add(name="Lift")
        basis = np.array([d.co for d in reference.data])
        empty = self.target.shape_key_add(name="Empty", from_mix=False)
        for d in empty.data:
            d.co.z += 0.5

        bpy.ops.mustardui.model_toolkit_transfer_shape_keys(overwrite=True)

        sks = self.target.data.shape_keys
        self.assertEqual(sks.reference_key, reference)
        np.testing.assert_allclose([d.co for d in reference.data], basis)
        self.assertAlmostEqual(np.abs(key_offsets(self.target, "Empty")).max(), 0.0)

    # Vertices beyond the max distance are not moved
    def test_max_distance(self):
        far = grid_object("Far", size=0.5, subdivisions=3, location=(0, 0, 1.0))
        self.select(self.target, far, self.source)

        bpy.ops.mustardui.model_toolkit_transfer_shape_keys(max_distance=0.1)

        self.assertIn("Lift", self.target.data.shape_keys.key_blocks)
        self.assertIsNone(far.data.shape_keys)

    # Nearest vertex copies the offsets of meshes sharing the vertices
    def test_nearest_vertex(self):
        copy = grid_object("Copy")
        self.select(copy, self.source)

        bpy.ops.mustardui.model_toolkit_transfer_shape_keys(method="VERTEX")

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

        bpy.ops.mustardui.model_toolkit_transfer_shape_keys(vertex_group="Mask")

        offsets = key_offsets(self.target, "Lift")[:, 2]
        xs = np.array([v.co.x for v in self.target.data.vertices])
        np.testing.assert_allclose(offsets[xs < 0.0], 0.1 * (xs[xs < 0.0] + 1.0), atol=1e-5)
        np.testing.assert_allclose(offsets[xs >= 0.0], 0.0, atol=1e-6)
        self.assertGreater(key_offsets(other, "Lift")[:, 2].min(), 0.0)

        bpy.ops.mustardui.model_toolkit_transfer_shape_keys(
            vertex_group="Mask", invert_vertex_group=True, overwrite=True
        )

        offsets = key_offsets(self.target, "Lift")[:, 2]
        np.testing.assert_allclose(offsets[xs < 0.0], 0.0, atol=1e-6)
        np.testing.assert_allclose(offsets[xs >= 0.0], 0.1 * (xs[xs >= 0.0] + 1.0), atol=1e-5)


class TestTriangleBarycentric(BlenderTestCase):
    # Points on a triangle get their coordinates, triangles without area weight corners equally
    def test_barycentric(self):
        corners = np.array([[[0, 0, 0], [1, 0, 0], [0, 1, 0]], [[0, 0, 0], [1, 0, 0], [2, 0, 0]]])
        points = np.array([[0.25, 0.25, 0.0], [0.5, 0.0, 0.0]])
        bary = mesh_deform.triangle_barycentric(points, corners.astype(np.float64))
        np.testing.assert_allclose(bary, [[0.5, 0.25, 0.25], [1 / 3, 1 / 3, 1 / 3]])


class TestTransferVertexGroups(BlenderTestCase):
    def setUp(self):
        super().setUp()
        self.source = grid_object("Source")
        # Weights growing with x
        foo = self.source.vertex_groups.new(name="Foo")
        for v in self.source.data.vertices:
            foo.add([v.index], (v.co.x + 1.0) / 2.0, "REPLACE")
        self.source.vertex_groups.new(name="Bar").add([0], 1.0, "REPLACE")

        self.target = grid_object("Target", size=0.5, subdivisions=7, location=(0, 0, 0.001))

        bpy.context.view_layer.update()
        for obj in bpy.context.view_layer.objects:
            obj.select_set(obj in (self.source, self.target))
        bpy.context.view_layer.objects.active = self.source

        items = bpy.context.window_manager.MustardUI_ModelToolkit_TransferVertexGroups_Items
        items.clear()
        items.add().group_name = "Foo"

    # Only the listed groups are transferred, copying the weights of the close source
    def test_transfer(self):
        self.assertTrue(bpy.ops.mustardui.model_toolkit_transfer_vertex_groups.poll())
        bpy.ops.mustardui.model_toolkit_transfer_vertex_groups()

        self.assertIn("Foo", self.target.vertex_groups)
        self.assertNotIn("Bar", self.target.vertex_groups)

        index = self.target.vertex_groups["Foo"].index
        for v in self.target.data.vertices:
            weight = next(g.weight for g in v.groups if g.group == index)
            self.assertAlmostEqual(weight, (v.co.x + 1.0) / 2.0, places=4)

    def transfer(self, **settings):
        items = bpy.context.window_manager.MustardUI_ModelToolkit_TransferVertexGroups_Items
        items.clear()
        for name in ("Foo", "Baz"):
            items.add().group_name = name
        # A second group completing the first one to 1
        baz = self.source.vertex_groups.new(name="Baz")
        for v in self.source.data.vertices:
            baz.add([v.index], 1.0 - (v.co.x + 1.0) / 2.0, "REPLACE")
        bpy.ops.mustardui.model_toolkit_transfer_vertex_groups(**settings)
        weights = mesh_deform.read_weights(self.target, ["Foo", "Baz"])
        return weights, np.array([v.co for v in self.target.data.vertices])

    # Existing groups are kept without Overwrite, locked ones also with it
    def test_overwrite(self):
        foo = self.target.vertex_groups.new(name="Foo")
        foo.add([0], 0.3, "REPLACE")
        weights, co = self.transfer(overwrite=False)
        np.testing.assert_allclose(weights[:, 0], [0.3] + [0.0] * (len(weights) - 1))
        self.assertTrue(np.all(weights[1:, 1] > 0.0))
        result = bpy.ops.mustardui.model_toolkit_transfer_vertex_groups(overwrite=False)
        self.assertEqual(result, {"CANCELLED"})

        foo.lock_weight = True
        bpy.ops.mustardui.model_toolkit_transfer_vertex_groups(overwrite=True)
        np.testing.assert_allclose(
            mesh_deform.read_weights(self.target, ["Foo"])[:, 0], weights[:, 0]
        )

        foo.lock_weight = False
        bpy.ops.mustardui.model_toolkit_transfer_vertex_groups(overwrite=True)
        weights = mesh_deform.read_weights(self.target, ["Foo"])[:, 0]
        np.testing.assert_allclose(weights, (co[:, 0] + 1.0) / 2.0, atol=1e-4)

    # The vertices far from the source are filled smoothly from the matched ones
    def test_fill(self):
        for v in self.target.data.vertices:
            if v.co.x > 0.1:
                v.co.z += 0.05
        weights, co = self.transfer(mark_unmatched=True)

        lifted = co[:, 0] > 0.1
        unmatched = mesh_deform.read_weights(self.target, [ops_transfer.UNMATCHED_GROUP])[:, 0]
        np.testing.assert_array_equal(unmatched > 0.5, lifted)
        # The matched weights are copied, the filled ones continue them smoothly
        np.testing.assert_allclose(weights[~lifted, 0], (co[~lifted, 0] + 1.0) / 2.0, atol=1e-4)
        rows = weights[:, 0].reshape(8, 8)
        self.assertTrue(np.all(np.diff(rows, axis=1) >= -1e-6))
        self.assertLess(np.abs(np.diff(rows[:, 4:6], axis=1)).max(), 0.1)
        self.assertLessEqual(weights[lifted, 0].max(), 0.75)
        np.testing.assert_allclose(weights.sum(axis=1), 1.0, atol=1e-3)

    # Regions too large to fill keep the closest weights
    def test_fill_too_large(self):
        for v in self.target.data.vertices:
            if v.co.x > 0.1:
                v.co.z += 0.05
        limit = weight_transfer.MAX_FACTOR_ENTRIES
        self.addCleanup(setattr, weight_transfer, "MAX_FACTOR_ENTRIES", limit)
        weight_transfer.MAX_FACTOR_ENTRIES = 0
        weights, co = self.transfer()
        np.testing.assert_allclose(weights[:, 0], (co[:, 0] + 1.0) / 2.0, atol=1e-4)

    # The groups without weights on the target are not left empty
    def test_empty_groups(self):
        # Bar only weights the source corner, far from the target, which already has a Bar group
        self.target.vertex_groups.new(name="Bar")
        items = bpy.context.window_manager.MustardUI_ModelToolkit_TransferVertexGroups_Items
        items.add().group_name = "Bar"
        bpy.ops.mustardui.model_toolkit_transfer_vertex_groups()
        self.assertIn("Foo", self.target.vertex_groups)
        self.assertNotIn("Bar", self.target.vertex_groups)

    # With a large distance and any angle, the weights of the nearest point are copied everywhere
    def test_nearest(self):
        for v in self.target.data.vertices:
            if v.co.x > 0.1:
                v.co.z += 0.05
        weights, co = self.transfer(max_distance=1.0, max_angle=np.pi, mark_unmatched=True)

        unmatched = mesh_deform.read_weights(self.target, [ops_transfer.UNMATCHED_GROUP])
        self.assertFalse(np.any(unmatched > 0.0))
        np.testing.assert_allclose(weights[:, 0], (co[:, 0] + 1.0) / 2.0, atol=1e-4)

    # A loose piece far from the source moves rigidly with its closest point
    def test_rigid_piece(self):
        mesh = self.target.data
        piece = grid_object("Piece", size=0.05, subdivisions=2, location=(0.7, 0.0, 0.2))
        for obj in bpy.context.view_layer.objects:
            obj.select_set(obj in (piece, self.target))
        bpy.context.view_layer.objects.active = self.target
        bpy.ops.object.join()
        bpy.context.view_layer.objects.active = self.source
        self.source.select_set(True)
        weights, co = self.transfer(mark_unmatched=True)

        loose = np.arange(len(mesh.vertices)) >= 64
        self.assertLess(np.abs(weights[loose] - weights[loose][0]).max(), 1e-6)
        self.assertGreater(weights[loose][0, 0], 0.5)
        # The piece copied its weights, it was not filled
        filled = mesh_deform.read_weights(self.target, [ops_transfer.UNMATCHED_GROUP])
        self.assertFalse(np.any(filled[loose] > 0.0))

        # Without marking, the group of the previous transfer is removed
        bpy.ops.mustardui.model_toolkit_transfer_vertex_groups(mark_unmatched=False)
        self.assertNotIn(ops_transfer.UNMATCHED_GROUP, self.target.vertex_groups)

    # Meshes without faces copy the weights of the closest points
    def test_edges_only(self):
        mesh = bpy.data.meshes.new("Wire")
        mesh.from_pydata([(-0.5, 0.0, 0.001), (0.5, 0.0, 0.001)], [(0, 1)], [])
        wire = new_object("Wire", mesh)
        bpy.context.view_layer.update()
        for obj in bpy.context.view_layer.objects:
            obj.select_set(obj in (self.source, wire))
        bpy.context.view_layer.objects.active = self.source
        bpy.ops.mustardui.model_toolkit_transfer_vertex_groups()

        weights = mesh_deform.read_weights(wire, ["Foo"])[:, 0]
        np.testing.assert_allclose(weights, [0.25, 0.75], atol=1e-4)

    # Smoothing softens the seam with the copied weights, or all of them with Smooth All
    def test_smooth(self):
        for v in self.target.data.vertices:
            if v.co.x > 0.1:
                v.co.z += 0.05
        base, co = self.transfer()
        results = {}
        for smooth_all in (False, True):
            bpy.ops.mustardui.model_toolkit_transfer_vertex_groups(smooth=10, smooth_all=smooth_all)
            results[smooth_all] = mesh_deform.read_weights(self.target, ["Foo", "Baz"])
            np.testing.assert_allclose(results[smooth_all].sum(axis=1), 1.0, atol=1e-3)

        # Columns of the 8x8 grid: filled from x > 0.1, the seam band reaches 2 columns before
        columns = np.round((co[:, 0] + 0.5) / (1.0 / 7.0)).astype(int)
        band = (columns >= 2) & (columns <= 4)
        far = columns <= 1
        self.assertGreater(np.abs(results[False][band, 0] - base[band, 0]).max(), 1e-4)
        np.testing.assert_allclose(results[False][far], base[far], atol=1e-6)
        self.assertGreater(np.abs(results[True][far, 0] - base[far, 0]).max(), 1e-4)

    # Only the masked vertices change, and the groups without weights around them are skipped
    def test_smooth_weights(self):
        n = 5
        edges = [(j * n + i, j * n + i + 1) for j in range(n) for i in range(n - 1)]
        edges += [(j * n + i, (j + 1) * n + i) for j in range(n - 1) for i in range(n)]
        edges = np.array(edges)
        weights = np.zeros((n * n, 2))
        weights[12, 0] = 1.0
        weights[0, 1] = 1.0
        mask = np.zeros(n * n, dtype=bool)
        mask[[6, 7, 8, 11, 12, 13, 16, 17, 18]] = True

        smoothed = weight_transfer.smooth_weights(weights, edges, mask, 5)
        np.testing.assert_array_equal(smoothed[~mask], weights[~mask])
        np.testing.assert_array_equal(smoothed[:, 1], weights[:, 1])
        self.assertLess(smoothed[12, 0], 1.0)
        self.assertGreater(smoothed[7, 0], 0.0)

    # The weights of each vertex are limited to the largest ones, keeping their sum
    def test_limit_influences(self):
        weights = np.array([[0.5, 0.3, 0.2], [0.1, 0.1, 0.8]])
        limited = weight_transfer.limit_influences(weights, 2)
        np.testing.assert_array_equal(np.count_nonzero(limited, axis=1), [2, 2])
        np.testing.assert_allclose(limited.sum(axis=1), 1.0)
        np.testing.assert_allclose(limited[0], [0.625, 0.375, 0.0])
        # Groups not summing to 1 (e.g. masks) are kept within 1
        limited = weight_transfer.limit_influences(np.array([[1.0, 1.0, 1.0]]), 1)
        np.testing.assert_allclose(limited, [[1.0, 0.0, 0.0]])


class TestFitToBody(BlenderTestCase):
    def setUp(self):
        super().setUp()
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=0.5)
        self.body = bpy.context.active_object
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.49)
        self.outfit = bpy.context.active_object
        self.settings = bpy.context.window_manager.MustardUI_ModelToolkit_FitToBodySettings

    def solve(self):
        solver = fit_to_body.FitToBodySolver(self.outfit, [self.body], "Fit")
        co, count, error = solver.solve(bpy.context, self.settings)
        self.assertEqual(error, "")
        return np.linalg.norm(co, axis=1)

    # The outfit inside the body is pushed out of it
    def test_fit(self):
        radius = self.solve()
        self.assertGreater(radius.min(), 0.5)
        self.assertLess(radius.max(), 0.52)

    # The fit keeps the details of the outfit, e.g. a knot far from the body
    def test_keeps_details(self):
        mesh = self.outfit.data
        top = int(np.argmax([v.co.z for v in mesh.vertices]))
        mesh.vertices[top].co.z += 0.03
        radius = self.solve()
        neighbours = [sum(e.vertices) - top for e in mesh.edges if top in e.vertices]
        # The detail still sticks out of the surface around it
        self.assertGreater(radius[top] - radius[neighbours].mean(), 0.025)

    # The metrics count the outfit inside the body before the fit, and nothing after it
    def test_metrics(self):
        solver = fit_to_body.FitToBodySolver(self.outfit, [self.body], "Fit", check=True)
        solver.solve(bpy.context, self.settings)
        before, after = solver.metrics
        self.assertEqual(before.buried, len(self.outfit.data.vertices))
        self.assertEqual(before.through, 0)
        self.assertEqual(after, (0, 0, 0))

        # Without the check, no metrics are computed
        solver = fit_to_body.FitToBodySolver(self.outfit, [self.body], "Fit")
        solver.solve(bpy.context, self.settings)
        self.assertIsNone(solver.metrics)

    # The body is used with its current Shape Keys, or with its Basis shape ignoring them
    def test_body_shape_keys(self):
        option = "ignore_body_shape_keys"
        self.addCleanup(setattr, self.settings, option, getattr(self.settings, option))
        self.body.shape_key_add(name="Basis")
        grow = self.body.shape_key_add(name="Grow", from_mix=False)
        for d in grow.data:
            d.co *= 1.1
        grow.value = 1.0
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.52)
        outfit = bpy.context.active_object

        for ignore in (False, True):
            self.settings.ignore_body_shape_keys = ignore
            solver = fit_to_body.FitToBodySolver(outfit, [self.body], "Fit")
            co, count, _ = solver.solve(bpy.context, self.settings)
            if ignore:
                self.assertEqual(count, 0)
            else:
                self.assertGreater(np.linalg.norm(co, axis=1).min(), 0.55)
        # The Shape Keys of the body are restored
        self.assertFalse(grow.mute)

    # A loose vertex, last in the mesh, does not break the fit
    def test_loose_vertex(self):
        bm = bmesh.new()
        bm.from_mesh(self.outfit.data)
        bm.verts.new((0.0, 0.0, 0.0))
        bm.to_mesh(self.outfit.data)
        bm.free()
        solver = fit_to_body.FitToBodySolver(self.outfit, [self.body], "Fit")
        co, _, error = solver.solve(bpy.context, self.settings)
        self.assertEqual(error, "")
        self.assertTrue(np.all(np.isfinite(co)))

    # The layers of the outfit do not cross each other when pushed out of the body
    def test_layers(self):
        self.addCleanup(setattr, self.settings, "self_collisions", self.settings.self_collisions)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.495)
        layer = bpy.context.active_object
        self.outfit.select_set(True)
        layer.select_set(True)
        bpy.context.view_layer.objects.active = self.outfit
        bpy.ops.object.join()
        # The sphere quads have equal diagonals, split differently at each run otherwise
        for obj in (self.body, self.outfit):
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bmesh.ops.triangulate(bm, faces=bm.faces, quad_method="FIXED")
            bm.to_mesh(obj.data)
            bm.free()

        for self_collisions in (True, False):
            self.settings.self_collisions = self_collisions
            solver = fit_to_body.FitToBodySolver(self.outfit, [self.body], "Fit", check=True)
            solver.solve(bpy.context, self.settings)
            after = solver.metrics[1]
            if self_collisions:
                self.assertEqual(after, (0, 0, 0))
            else:
                self.assertGreater(after.through + after.crossing, 0)

    # The triangles of a coarse outfit do not cross the body, even with the vertices outside it
    def test_triangles(self):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=0.5)
        body = bpy.context.active_object
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.52)
        outfit = bpy.context.active_object

        solver = fit_to_body.FitToBodySolver(outfit, [body], "Fit", check=True)
        solver.solve(bpy.context, self.settings)
        before, after = solver.metrics
        self.assertEqual(before.buried, 0)
        self.assertGreater(before.through, 0)
        self.assertEqual(after.through, 0)

    # The check of the best result counts the vertices inside the body
    def test_check_buried(self):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=0.52)
        outfit = bpy.context.active_object
        solver = fit_to_body.FitToBodySolver(outfit, [self.body], "Fit")
        body_bvh, body_co, body_normals = solver.body(bpy.context, (False, False))
        optimizer = fit_optimizer.FitOptimizer(
            solver.target,
            body_co,
            solver._body_tris[(False, False)],
            body_normals,
            body_bvh,
            lambda: solver.winding(bpy.context, (False, False)),
        )
        co = solver.target.co.copy()
        gap = self.settings.offset
        planes = optimizer.body_planes(co, np.arange(len(co)), 0.1)
        self.assertEqual(optimizer.check(co, planes, gap), 0)

        # A vertex just under the body surface, with its triangles still outside it
        top = int(np.argmax(co[:, 2]))
        co[top] *= 0.498 / np.linalg.norm(co[top])
        tris = solver.target.tris
        bvh = BVHTree.FromPolygons(co.tolist(), tris.tolist())
        others = len(np.unique(intersection.intersecting_triangles(bvh, body_bvh)[:, 0]))
        self.assertEqual(optimizer.check(co, planes, gap), others + 1)

    # The preview settings draw, with the debug information too, also while solving
    def test_draw(self):
        solver = fit_to_body.FitToBodySolver(self.outfit, [self.body], "Fit", check=True)
        session = preview.ShapeKeyPreviewSession(
            "FIT_TO_BODY", self.outfit, "Fit", solver, self.settings
        )
        preview.PREVIEW_SESSION = session
        preferences = bpy.context.preferences.addons[ADDON].preferences
        self.addCleanup(setattr, preferences, "debug", preferences.debug)
        drawer = Drawer()
        try:
            layout = FakeLayout(drawer)
            draw = fit_to_body.fit_to_body_draw_settings
            for debug in (False, True):
                preferences.debug = debug
                drawer.run(f"unsolved, debug {debug}", draw, layout, bpy.context)
            solver.solve(bpy.context, self.settings)
            for debug in (False, True):
                preferences.debug = debug
                drawer.run(f"solved, debug {debug}", draw, layout, bpy.context)
        finally:
            preview.PREVIEW_SESSION = None
        self.assertEqual(drawer.errors, [])

    # The preview shows the result first, then measures it a bit at a time
    def test_preview_check_after_result(self):
        solver = fit_to_body.FitToBodySolver(self.outfit, [self.body], "Fit", check=True)
        session = preview.ShapeKeyPreviewSession(
            "FIT_TO_BODY", self.outfit, "Fit", solver, self.settings
        )
        preview.PREVIEW_SESSION = session
        try:
            operator = type("Operator", (), {"preview_verb": "fitted"})()
            result = fit_to_body.run_steps(solver.solve_steps(bpy.context, self.settings))
            preview.ShapeKeyPreviewOperator.preview_result(operator, bpy.context, result)
            self.assertIsNone(solver.metrics)
            self.assertIsNotNone(session.checks)
            for _ in session.checks:
                pass
        finally:
            preview.PREVIEW_SESSION = None
        self.assertEqual(solver.metrics[1], (0, 0, 0))


def mesh_arrays(obj):
    mesh = obj.data
    mesh.calc_loop_triangles()
    co = np.array([obj.matrix_world @ v.co for v in mesh.vertices], dtype=np.float64)
    tris = np.array([t.vertices[:] for t in mesh.loop_triangles], dtype=np.int64)
    return co, tris


class TestMeshIntersection(BlenderTestCase):
    def setUp(self):
        super().setUp()
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=0.5)
        self.sphere = bpy.context.active_object
        rng = np.random.default_rng(0)
        self.points = rng.uniform(-0.8, 0.8, (500, 3))

    # Points inside the closed mesh have winding number 1, outside 0
    def test_winding_closed(self):
        co, tris = mesh_arrays(self.sphere)
        winding = intersection.WindingNumbers(co, tris)(self.points)
        radius = np.linalg.norm(self.points, axis=1)
        np.testing.assert_allclose(winding[radius < 0.45], 1.0, atol=0.05)
        np.testing.assert_allclose(winding[radius > 0.55], 0.0, atol=0.05)

    # The tree approximation agrees with the exact winding numbers
    def test_winding_approximation(self):
        co, tris = mesh_arrays(self.sphere)
        exact = intersection.WindingNumbers(co, tris, beta=np.inf)(self.points)
        winding = intersection.WindingNumbers(co, tris)(self.points)
        self.assertLess(np.abs(winding - exact).max(), 0.05)

    # With a hole in the mesh, the points inside away from it are still inside
    def test_winding_open(self):
        co, tris = mesh_arrays(self.sphere)
        tris = tris[co[tris].mean(axis=1)[:, 2] < 0.4]
        points = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, -0.3], [0.2, 0.0, 0.1], [0.0, 0.0, 0.7]])
        winding = intersection.WindingNumbers(co, tris)(points)
        self.assertTrue(np.all(winding[:3] > 0.5))
        self.assertLess(winding[3], 0.5)

    # Self intersections are counted once, without the neighbouring triangles
    def test_self_intersections(self):
        co = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0), (0.5, 0.5, -0.5), (0.5, 0.5, 0.5)]
        co.append((0.6, 0.4, 0.5))
        bvh = intersection.BVHTree.FromPolygons(co, [(0, 1, 3), (0, 3, 2), (4, 5, 6)])
        self.assertEqual(intersection.intersecting_triangles(bvh).tolist(), [[0, 2]])

        co, tris = mesh_arrays(self.sphere)
        bvh = intersection.BVHTree.FromPolygons(co.tolist(), tris.tolist())
        self.assertEqual(len(intersection.intersecting_triangles(bvh)), 0)


class TestSquish(BlenderTestCase):
    # The body is pushed under the squishing surface
    def test_squish(self):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=0.5)
        body = bpy.context.active_object
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.48)
        squisher = bpy.context.active_object
        settings = bpy.context.window_manager.MustardUI_ModelToolkit_SquishSettings

        solver = squish.SquishSolver(body, [squisher], "Squish")
        co, count, error = solver.solve(bpy.context, settings)
        self.assertEqual(error, "")
        self.assertGreater(count, 0)

        bvh = solver.squishers_bvh(bpy.context, settings)[0]
        moved = np.nonzero(np.linalg.norm(solver.disp, axis=1) > 0.0)[0]
        left = solver.penetration(bvh, solver.target.co + solver.disp, moved, settings)
        self.assertFalse(np.any(left > 0.0))

    # The bulge pushes out the body around the squished area, and survives the smoothing
    def test_bulge(self):
        bpy.ops.mesh.primitive_grid_add(x_subdivisions=80, y_subdivisions=80, size=0.4)
        body = bpy.context.active_object
        bpy.ops.mesh.primitive_plane_add(size=0.1, location=(0.0, 0.0, -0.005))
        squisher = bpy.context.active_object
        settings = bpy.context.window_manager.MustardUI_ModelToolkit_SquishSettings
        for name in ("bulge", "smooth_distance"):
            self.addCleanup(setattr, settings, name, getattr(settings, name))
        settings.smooth_distance = 0.02

        solver = squish.SquishSolver(body, [squisher], "Squish")
        outward = {}
        for bulge in (0.0, 1.0):
            settings.bulge = bulge
            solver.solve(bpy.context, settings)
            outward[bulge] = solver.disp[:, 2].max()
        depth = -solver.disp[:, 2].min()
        self.assertAlmostEqual(depth, 0.006, places=4)
        self.assertLess(outward[0.0], 1e-4)
        # Its peak, not flattened by the smoothing
        self.assertGreater(outward[1.0], 0.8 * squish.BULGE_STRENGTH * depth)

    # The moved squishers go in by the Tightness, but never deeper than the body under them
    def test_tightness_borders(self):
        bpy.ops.mesh.primitive_grid_add(x_subdivisions=80, y_subdivisions=80, size=0.4)
        body = bpy.context.active_object
        # Its borders between the body vertices, as for clothes
        bpy.ops.mesh.primitive_grid_add(
            x_subdivisions=40, y_subdivisions=40, size=0.2, location=(0.0025, 0.0025, 0.0)
        )
        squisher = bpy.context.active_object
        settings = bpy.context.window_manager.MustardUI_ModelToolkit_SquishSettings
        for name in ("tightness", "squishers_movement", "bulge"):
            self.addCleanup(setattr, settings, name, getattr(settings, name))
        settings.tightness = 0.005
        settings.squishers_movement = 1.0
        settings.bulge = 0.0

        solver = squish.SquishSolver(body, [squisher], "Squish")
        solver.solve(bpy.context, settings)
        follower = next(x for x in solver.followers if x.obj == squisher)
        moved = follower.basis[:, 2] - follower.shape(solver, settings)[:, 2]

        centre = np.argmin(np.abs(follower.basis).sum(axis=1))
        corner = np.argmax(np.abs(follower.basis).sum(axis=1))
        self.assertAlmostEqual(moved[centre], 0.005)
        self.assertLess(moved[corner], 0.004)

    # The settings of the running preview go back to their defaults, but the Shape Key name
    def test_reset_settings(self):
        settings = bpy.context.window_manager.MustardUI_ModelToolkit_SquishSettings
        self.addCleanup(setattr, settings, "shape_key_name", settings.shape_key_name)
        settings.shape_key_name = "Squish - Top"
        settings.mode = "VOLUME"
        settings.bulge = 1.5
        settings.vertex_group = "Group"
        settings.move_squishers = not settings.move_squishers

        preview.PREVIEW_SESSION = type("Session", (), {"settings": settings})()
        try:
            bpy.ops.mustardui.model_toolkit_preview_reset()
        finally:
            preview.PREVIEW_SESSION = None

        props = settings.bl_rna.properties
        for name in ("mode", "bulge", "vertex_group", "move_squishers"):
            self.assertEqual(getattr(settings, name), props[name].default, name)
        self.assertEqual(settings.shape_key_name, "Squish - Top")


class TestSmoothShapeKey(BlenderTestCase):
    def setUp(self):
        super().setUp()
        self.obj = grid_object("Grid", subdivisions=20)
        self.obj.shape_key_add(name="Basis")
        noisy = self.obj.shape_key_add(name="Noisy", from_mix=False)
        rng = np.random.default_rng(0)
        for d in noisy.data:
            d.co.z += 0.01 + rng.uniform(-0.005, 0.005)
        noisy.value = 0.3
        self.obj.active_shape_key_index = 1
        bpy.context.view_layer.objects.active = self.obj
        self.settings = bpy.context.window_manager.MustardUI_ModelToolkit_SmoothShapeKeySettings
        self.settings.smooth_distance = 0.3
        self.settings.keep_borders = False

    def roughness(self):
        offsets = key_offsets(self.obj, "Noisy")[:, 2].reshape(21, 21)
        return np.abs(np.diff(offsets, axis=0)).mean() + np.abs(np.diff(offsets, axis=1)).mean()

    # The deformation is smoothed, keeping the Basis and the value of the Shape Key
    def test_smooth(self):
        before = self.roughness()
        basis = [d.co.copy() for d in self.obj.data.shape_keys.reference_key.data]
        bpy.ops.mustardui.model_toolkit_smooth_shape_key()
        self.assertLess(self.roughness(), 0.3 * before)
        self.assertEqual(basis, [d.co for d in self.obj.data.shape_keys.reference_key.data])
        self.assertAlmostEqual(self.obj.data.shape_keys.key_blocks["Noisy"].value, 0.3)

    # Strength and Vertex Group restrict the smoothing
    def test_factor_and_mask(self):
        offsets = key_offsets(self.obj, "Noisy")
        self.settings.factor = 0.0
        bpy.ops.mustardui.model_toolkit_smooth_shape_key()
        np.testing.assert_allclose(key_offsets(self.obj, "Noisy"), offsets)

        self.settings.factor = 1.0
        group = self.obj.vertex_groups.new(name="Half")
        xs = np.array([v.co.x for v in self.obj.data.vertices])
        group.add([int(i) for i in np.nonzero(xs < -0.5)[0]], 1.0, "REPLACE")
        self.settings.vertex_group = "Half"
        bpy.ops.mustardui.model_toolkit_smooth_shape_key()
        changed = np.abs(key_offsets(self.obj, "Noisy") - offsets).max(axis=1) > 1e-7
        self.assertTrue(changed[xs < -0.5].all())
        self.assertFalse(changed[xs >= -0.5].any())

    # The preview shows the Shape Key at full value, and cancelling restores it
    def test_preview(self):
        offsets = key_offsets(self.obj, "Noisy")
        solver = smooth_sk.SmoothShapeKeySolver(self.obj, "Noisy")
        session = preview.ShapeKeyPreviewSession(
            "SMOOTH_SHAPE_KEY", self.obj, "Noisy", solver, self.settings
        )
        preview.PREVIEW_SESSION = session
        try:
            operator = type("Operator", (), {"preview_verb": "smoothed"})()
            result = solver.solve(bpy.context, self.settings)
            preview.ShapeKeyPreviewOperator.preview_result(operator, bpy.context, result)
            key = self.obj.data.shape_keys.key_blocks["Noisy"]
            self.assertEqual(key.value, 1.0)
            self.assertGreater(session.count, 0)
            session.restore()
        finally:
            preview.PREVIEW_SESSION = None
        np.testing.assert_allclose(key_offsets(self.obj, "Noisy"), offsets, atol=1e-7)
        self.assertAlmostEqual(key.value, 0.3)

    # Driven Shape Keys are shown in the preview, with the driver restored at the end
    def test_preview_driver(self):
        key = self.obj.data.shape_keys.key_blocks["Noisy"]
        driver = key.driver_add("value")
        driver.driver.expression = "0.3"
        bpy.context.view_layer.update()

        solver = smooth_sk.SmoothShapeKeySolver(self.obj, "Noisy")
        session = preview.ShapeKeyPreviewSession(
            "SMOOTH_SHAPE_KEY", self.obj, "Noisy", solver, self.settings
        )
        preview.PREVIEW_SESSION = session
        operator = type("Operator", (), {"preview_verb": "smoothed", "_timer": None})()
        try:
            result = solver.solve(bpy.context, self.settings)
            preview.ShapeKeyPreviewOperator.preview_result(operator, bpy.context, result)
            bpy.context.view_layer.update()
            self.assertEqual(key.value, 1.0)
        finally:
            session.restore()
            preview.ShapeKeyPreviewOperator.preview_end(operator, bpy.context)
        self.assertFalse(driver.mute)
        bpy.context.view_layer.update()
        self.assertAlmostEqual(key.value, 0.3)

    # The details are removed, keeping the size of the deformation
    def test_keep_size(self):
        # A fine grid, for the many iterations that enlarge Taubin smoothing
        self.obj = grid_object("Fine", subdivisions=60)
        self.obj.shape_key_add(name="Basis")
        bump = self.obj.shape_key_add(name="Bump", from_mix=False)
        rng = np.random.default_rng(1)
        for d in bump.data:
            r = np.hypot(d.co.x, d.co.y)
            d.co.z += 0.1 * max(1.0 - r / 0.6, 0.0) + rng.uniform(-0.002, 0.002)
        self.obj.active_shape_key_index = 1
        bpy.context.view_layer.objects.active = self.obj

        before = key_offsets(self.obj, "Bump")[:, 2]
        bpy.ops.mustardui.model_toolkit_smooth_shape_key()
        after = key_offsets(self.obj, "Bump")[:, 2]
        noise = np.abs(np.diff(after.reshape(61, 61), 2, axis=1)).mean()
        self.assertLess(noise, 0.5 * np.abs(np.diff(before.reshape(61, 61), 2, axis=1)).mean())
        self.assertGreater(after.max(), 0.8 * before.max())
        # Not enlarged either, as Taubin smoothing does after many iterations
        self.settings.smooth_distance = 1.0
        bpy.ops.mustardui.model_toolkit_smooth_shape_key()
        self.assertLess(key_offsets(self.obj, "Bump")[:, 2].max(), 1.05 * before.max())

    # Hiding the result shows the original Shape Key, not the mesh without it
    def test_preview_show_original(self):
        offsets = key_offsets(self.obj, "Noisy")
        solver = smooth_sk.SmoothShapeKeySolver(self.obj, "Noisy")
        session = preview.ShapeKeyPreviewSession(
            "SMOOTH_SHAPE_KEY", self.obj, "Noisy", solver, self.settings
        )
        preview.PREVIEW_SESSION = session
        wm = bpy.context.window_manager
        try:
            operator = type("Operator", (), {"preview_verb": "smoothed"})()
            result = solver.solve(bpy.context, self.settings)
            preview.ShapeKeyPreviewOperator.preview_result(operator, bpy.context, result)
            smoothed = key_offsets(self.obj, "Noisy")

            wm.MustardUI_ModelToolkit_PreviewShow = False
            key = self.obj.data.shape_keys.key_blocks["Noisy"]
            self.assertEqual(key.value, 1.0)
            np.testing.assert_allclose(key_offsets(self.obj, "Noisy"), offsets, atol=1e-7)

            wm.MustardUI_ModelToolkit_PreviewShow = True
            np.testing.assert_allclose(key_offsets(self.obj, "Noisy"), smoothed, atol=1e-7)

            # Applied while hidden, the smoothed Shape Key is kept
            wm.MustardUI_ModelToolkit_PreviewShow = False
            smooth_sk.MustardUI_ModelToolkit_SmoothShapeKey.preview_finish(
                operator, bpy.context, session
            )
            np.testing.assert_allclose(key_offsets(self.obj, "Noisy"), smoothed, atol=1e-7)
            self.assertAlmostEqual(key.value, 0.3)
        finally:
            preview.PREVIEW_SESSION = None
            wm.MustardUI_ModelToolkit_PreviewShow = True

    # The open borders keep the Shape Key, with the smoothing fading in from them
    def test_keep_borders(self):
        offsets = key_offsets(self.obj, "Noisy")
        self.settings.keep_borders = True
        self.settings.border_distance = 0.25
        bpy.ops.mustardui.model_toolkit_smooth_shape_key()
        changed = np.abs(key_offsets(self.obj, "Noisy") - offsets).max(axis=1)
        co = np.array([v.co[:2] for v in self.obj.data.vertices])
        border = np.abs(co).max(axis=1)
        self.assertLess(changed[border > 0.999].max(), 1e-7)
        # Fading in, then smoothed as usual inside
        self.assertLess(changed[np.isclose(border, 0.9)].mean(), changed[border < 0.7].mean())
        self.assertGreater(changed[border < 0.7].min(), 0.0)

    # The Shape mode smooths also the roughness of the mesh, only where the Shape Key moves it
    def test_shape_mode(self):
        rng = np.random.default_rng(3)
        for v, d in zip(
            self.obj.data.vertices, self.obj.data.shape_keys.reference_key.data, strict=True
        ):
            v.co.z = d.co.z = rng.uniform(-0.005, 0.005)
        # Smooth lift fading to zero, moving only the middle of the grid
        lift = self.obj.shape_key_add(name="Lift", from_mix=False)
        for d in lift.data:
            r = np.hypot(d.co.x, d.co.y)
            d.co.z += 0.05 * max(1.0 - r / 0.7, 0.0) ** 2
        self.obj.active_shape_key_index = len(self.obj.data.shape_keys.key_blocks) - 1
        shape = np.array([d.co[:] for d in lift.data])
        area = np.hypot(shape[:, 0], shape[:, 1]) < 0.4

        def bumps():
            z = np.array([d.co.z for d in lift.data]).reshape(21, 21)
            inner = np.abs(np.diff(z, 2, axis=0))[:, 1:-1] + np.abs(np.diff(z, 2, axis=1))[1:-1]
            return inner.reshape(-1)[area.reshape(21, 21)[1:-1, 1:-1].reshape(-1)].mean()

        before = bumps()
        self.settings.mode = "SHAPE"
        bpy.ops.mustardui.model_toolkit_smooth_shape_key()
        after = np.array([d.co[:] for d in lift.data])
        self.assertLess(bumps(), 0.5 * before)
        # Outside the moved area the Shape Key is not changed
        outside = np.hypot(shape[:, 0], shape[:, 1]) > 0.75
        np.testing.assert_allclose(after[outside], shape[outside], atol=1e-7)
