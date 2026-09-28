import importlib

import bpy
import numpy as np
from helpers import ADDON, BlenderTestCase, new_object
from mathutils import Matrix

fit_to_body = importlib.import_module(ADDON + ".model_toolkit.mesh.ops_fit_to_body")
preview = importlib.import_module(ADDON + ".model_toolkit.mesh.shape_key_preview")
squish = importlib.import_module(ADDON + ".model_toolkit.mesh.ops_squish")
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


class TestFitToBody(BlenderTestCase):
    def setUp(self):
        super().setUp()
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=0.5)
        self.body = bpy.context.active_object
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.49)
        self.outfit = bpy.context.active_object
        self.settings = bpy.context.window_manager.MustardUI_ModelToolkit_FitToBodySettings
        self.settings.refit_iterations = 50

    def solve(self, auto):
        self.settings.refit_auto = auto
        solver = fit_to_body.FitToBodySolver(bpy.context, self.outfit, [self.body], "Fit")
        co, count, error = solver.solve(bpy.context, self.settings)
        return np.linalg.norm(co, axis=1), solver.refit_count

    # The outfit inside the body is pushed out of it
    def test_fit(self):
        radius, _ = self.solve(auto=True)
        self.assertGreater(radius.min(), 0.5)
        self.assertLess(radius.max(), 0.52)

    # The refit keeps the details of the outfit, e.g. a knot far from the body
    def test_refit_keeps_details(self):
        mesh = self.outfit.data
        top = int(np.argmax([v.co.z for v in mesh.vertices]))
        mesh.vertices[top].co.z += 0.03
        radius, _ = self.solve(auto=True)
        neighbours = [sum(e.vertices) - top for e in mesh.edges if top in e.vertices]
        # The detail still sticks out of the surface around it
        self.assertGreater(radius[top] - radius[neighbours].mean(), 0.025)

    # The automatic refit stops early, with the same result as all the iterations
    def test_refit_auto(self):
        auto_radius, auto_count = self.solve(auto=True)
        radius, count = self.solve(auto=False)
        self.assertLess(auto_count, 50)
        self.assertEqual(count, 50)
        self.assertLess(np.abs(auto_radius - radius).mean(), 0.0005)
        self.assertGreater(auto_radius.min(), 0.5)

    # The preview debug information shows the refit iterations
    def test_preview_info(self):
        solver = fit_to_body.FitToBodySolver(bpy.context, self.outfit, [self.body], "Fit")
        session = preview.ShapeKeyPreviewSession(
            "FIT_TO_BODY", self.outfit, "Fit", solver, self.settings
        )
        preview.PREVIEW_SESSION = session
        try:
            operator = type("Operator", (), {"preview_verb": "fitted"})()
            result = solver.solve(bpy.context, self.settings)
            preview.ShapeKeyPreviewOperator.preview_result(operator, bpy.context, result)
        finally:
            preview.PREVIEW_SESSION = None
        self.assertGreater(solver.refit_count, 0)
        self.assertIn(f", {solver.refit_count} refit iterations (", session.info)


class TestSquish(BlenderTestCase):
    # The body is pushed under the squishing surface
    def test_squish(self):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=0.5)
        body = bpy.context.active_object
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.48)
        squisher = bpy.context.active_object
        settings = bpy.context.window_manager.MustardUI_ModelToolkit_SquishSettings

        solver = squish.SquishSolver(bpy.context, body, [squisher], "Squish")
        co, count, error = solver.solve(bpy.context, settings)
        self.assertEqual(error, "")
        self.assertGreater(count, 0)

        bvh, _ = solver.squishers_bvh(bpy.context, settings)
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

        solver = squish.SquishSolver(bpy.context, body, [squisher], "Squish")
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

        solver = squish.SquishSolver(bpy.context, body, [squisher], "Squish")
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
