import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from ...misc.mesh_deform import (
    DeformTarget,
    geometry_bvh,
    mesh_vertex_normals,
    rest_geometry,
    write_vertex_group,
)
from ...misc.mesh_intersection import WindingNumbers
from ...misc.ui_progress import run_steps
from ..mesh.shape_key_preview import (
    ShapeKeyPreviewOperator,
    create_followers_shape_keys,
    preview_debug,
    preview_draw_footer,
    preview_draw_masks,
    preview_draw_presets,
    preview_preset_classes,
    preview_running,
    preview_section,
    preview_session,
    preview_settings_update,
    write_shape_key,
)
from .fit_optimizer import FitOptimizer, outfit_metrics
from .ops_squish import SQUISH_ORIENTATION_DISTANCE, squisher_is_flipped

# Outfit vertices checked at a time by the live preview metrics
CHECK_CHUNK = 2048


class MustardUI_ModelToolkit_FitToBodySettings(bpy.types.PropertyGroup):
    shape_key_name: bpy.props.StringProperty(
        name="Shape Key",
        default="Fit to Body",
        description="Name of the Shape Key. If it already exists, it is overwritten",
    )

    result: bpy.props.EnumProperty(
        name="Result",
        items=(
            ("SHAPE_KEY", "Shape Key", "Create a Shape Key with the fit"),
            (
                "MESH",
                "Mesh",
                "Apply the fit to the mesh and all its Shape Keys",
            ),
        ),
        default="SHAPE_KEY",
    )

    use_modifiers: bpy.props.BoolProperty(
        name="Use Body Modifiers",
        default=False,
        description="Use the body with its modifiers evaluated.\nNote: Mask modifiers might "
        "remove the body under the outfit",
        update=preview_settings_update,
    )

    ignore_body_shape_keys: bpy.props.BoolProperty(
        name="Ignore Body Shape Keys",
        default=False,
        description="Fit to the Basis shape of the body, without its current Shape Keys",
        update=preview_settings_update,
    )

    vertex_group: bpy.props.StringProperty(
        name="Vertex Group",
        description="Restrict the effect to this Vertex Group of the outfit",
        update=preview_settings_update,
    )

    invert_vertex_group: bpy.props.BoolProperty(
        name="Invert",
        default=False,
        description="Invert the Vertex Group weights",
        update=preview_settings_update,
    )

    rigid_group: bpy.props.StringProperty(
        name="Rigid Vertex Group",
        description="Vertex Group of the rigid parts (e.g. buttons), which are moved without "
        "deforming them",
        update=preview_settings_update,
    )

    invert_rigid_group: bpy.props.BoolProperty(
        name="Invert",
        default=False,
        description="Invert the Rigid Vertex Group weights",
        update=preview_settings_update,
    )

    move_children: bpy.props.BoolProperty(
        name="Child Objects",
        default=True,
        description="Move the mesh objects parented to the Active Object (e.g. buttons) "
        "without deforming them, following the surface under them.\nTheir Shape Keys are "
        "driven by the main one",
        update=preview_settings_update,
    )

    auto_influence: bpy.props.BoolProperty(
        name="Auto Influence",
        default=False,
        description="Restrict the effect around the intersections between the meshes.\nThe "
        "influence is saved as a Vertex Group, with the name of the Shape Key",
        update=preview_settings_update,
    )

    influence_radius: bpy.props.FloatProperty(
        name="Influence Radius",
        default=0.05,
        min=0.0,
        soft_max=0.2,
        subtype="DISTANCE",
        description="Distance from the intersections where the influence fades to zero",
        update=preview_settings_update,
    )

    check_body: bpy.props.BoolProperty(
        name="Body Vertices",
        default=True,
        description="Also consider the body vertices passing through the outfit faces, useful when "
        "the outfit has less vertices than the body",
        update=preview_settings_update,
    )

    factor: bpy.props.FloatProperty(
        name="Factor",
        default=1.0,
        min=0.0,
        soft_max=1.0,
        description="Strength of the fit",
        update=preview_settings_update,
    )

    offset: bpy.props.FloatProperty(
        name="Offset",
        default=0.001,
        min=0.0,
        soft_max=0.01,
        step=0.01,
        precision=4,
        subtype="DISTANCE",
        description="Minimum distance of the outfit from the body",
        update=preview_settings_update,
    )

    fit_distance: bpy.props.FloatProperty(
        name="Fit Distance",
        default=0.01,
        min=0.0,
        soft_max=0.05,
        subtype="DISTANCE",
        description="Pull towards the body the outfit parts within this distance from it, to "
        "make them fit better.\nThe farther parts keep their shape. Set to 0 to only fix the "
        "clipping",
        update=preview_settings_update,
    )

    max_depth: bpy.props.FloatProperty(
        name="Max Depth",
        default=0.05,
        min=0.0001,
        soft_max=0.2,
        subtype="DISTANCE",
        description="Maximum clipping depth to consider. Increase it if some vertices are not "
        "fitted, decrease it if far vertices are moved by mistake",
        update=preview_settings_update,
    )

    smooth_distance: bpy.props.FloatProperty(
        name="Smooth",
        default=0.02,
        min=0.0,
        soft_max=0.1,
        subtype="DISTANCE",
        description="Distance the fit is smoothed over, to spread it on the neighbouring "
        "vertices and preserve the outfit shape.\nIt does not depend on the mesh density",
        update=preview_settings_update,
    )

    iterations: bpy.props.IntProperty(
        name="Iterations",
        default=200,
        min=1,
        soft_max=1000,
        description="Maximum iterations of the optimization, which stops earlier when the "
        "shape does not change anymore",
        update=preview_settings_update,
    )

    stiffness: bpy.props.FloatProperty(
        name="Stiffness",
        default=1.0,
        min=0.0,
        soft_max=10.0,
        description="Preservation of the outfit shape: higher values keep the details and the "
        "edge lengths, lower values fit closer to the body",
        update=preview_settings_update,
    )

    self_collisions: bpy.props.BoolProperty(
        name="Self Collisions",
        default=True,
        description="Keep the outfit layers on the side they had before the fit",
        update=preview_settings_update,
    )


FitToBodyPresetsMenu, FitToBodyPresetAdd = preview_preset_classes(
    "FitToBody",
    "Fit to Body",
    MustardUI_ModelToolkit_FitToBodySettings,
    "MustardUI_ModelToolkit_FitToBodySettings",
)


class FitToBodySolver:
    """Compute the fitted outfit, caching the results"""

    def __init__(self, outfit, bodies, key_name, check=False):
        self.outfit = outfit
        self.bodies = bodies
        self.target = DeformTarget(outfit, key_name)
        self.children = self.target.rigid_children(bodies)
        self.followers = self.children
        self.disp = None
        self.iterations = 0
        self.check = check
        self.metrics = None

        self._body = {}
        self._body_tris = {}
        self._before = {}
        self._winding = {}
        self._optimizer = {}
        self._outfit_flipped = None
        self._detect = (None, None)
        self.influence = None

    @staticmethod
    def body_key(settings):
        """Settings changing the body geometry, the key of its cached data"""

        return settings.use_modifiers, settings.ignore_body_shape_keys

    def body(self, context, key):
        """Body BVHTree, coordinates and normals"""

        if key not in self._body:
            use_modifiers, basis = key
            geometry = rest_geometry(
                context, self.bodies, [self.outfit], use_modifiers, basis=basis
            )
            bvh, co, self._body_tris[key] = geometry_bvh(geometry)
            normals = mesh_vertex_normals(co, self._body_tris[key]) if bvh is not None else None
            self._body[key] = (bvh, co, normals)
        return self._body[key]

    def winding(self, context, key):
        """Winding numbers of the body, built once"""

        if key not in self._winding:
            body_co = self.body(context, key)[1]
            self._winding[key] = WindingNumbers(body_co, self._body_tris[key])
        return self._winding[key]

    def check_steps(self, context, settings):
        """Store the metrics before and after the last fit, a bit at a time"""

        target = self.target
        disp = self.disp if self.disp is not None else np.zeros_like(target.co)
        key = self.body_key(settings)
        tree = self.winding(context, key)
        body_bvh = self.body(context, key)[0]

        def winding_steps(points):
            winding = np.empty(len(points))
            for start in range(0, len(points), CHECK_CHUNK):
                winding[start : start + CHECK_CHUNK] = tree(points[start : start + CHECK_CHUNK])
                yield
            return winding

        if key not in self._before:
            winding = yield from winding_steps(target.co)
            buried = int(np.count_nonzero(np.abs(winding) > 0.5))
            before = outfit_metrics(target.co, target.tris, body_bvh, buried)
            yield
            # Rest distance of the outfit vertices from the body
            distance = np.array([body_bvh.find_nearest(Vector(c))[3] for c in target.co])
            self._before[key] = (before, winding, distance)
            yield
        before, winding, distance = self._before[key]

        # Only the vertices moved farther than the body surface can change side
        moved = np.linalg.norm(disp, axis=1) >= distance - 1e-6
        winding = winding.copy()
        winding[moved] = yield from winding_steps(target.co[moved] + disp[moved])
        buried = int(np.count_nonzero(np.abs(winding) > 0.5))
        self.metrics = (before, outfit_metrics(target.co + disp, target.tris, body_bvh, buried))

    def optimize(self, context, settings, weights, disp):
        """Refine the fit minimizing the energy of the optimizer, yielding the progress"""

        target = self.target
        key = self.body_key(settings)
        if key not in self._optimizer:
            body_bvh, body_co, body_normals = self.body(context, key)
            self._optimizer[key] = FitOptimizer(
                target,
                body_co,
                self._body_tris[key],
                body_normals,
                body_bvh,
                lambda: self.winding(context, key),
            )
        free = weights > 0.0
        if self.influence is not None:
            free &= self.influence > 0.0
        steps = self._optimizer[key].run(target.co + disp, free, settings)
        while True:
            try:
                factor, text = next(steps)
            except StopIteration as stop:
                co, self.iterations = stop.value
                return co - target.co
            yield 0.4 + 0.5 * factor, text

    def clipping(self, context, settings, weights):
        """Required displacement along the directions to fix the clipping of the outfit"""

        body_bvh, body_co, body_normals = self.body(context, self.body_key(settings))
        target = self.target
        co = target.co
        margin = settings.max_depth + settings.offset
        active = weights > 0.0

        # Outfit vertices inside the body
        bb_min = body_co.min(axis=0) - margin
        bb_max = body_co.max(axis=0) + margin
        inside = np.all((co >= bb_min) & (co <= bb_max), axis=1) & active
        required = np.zeros(target.n_verts)
        directions = np.zeros((target.n_verts, 3))
        for i in np.nonzero(inside)[0]:
            v = Vector(co[i])
            loc, normal, _, _ = body_bvh.find_nearest(v, margin)
            if loc is None:
                continue
            signed = (v - loc).dot(normal)
            if signed < settings.offset:
                required[i] = settings.offset - signed
                directions[i] = normal

        # Body vertices through the outfit faces
        if settings.check_body and np.any(active):
            if self._outfit_flipped is None:
                self._outfit_flipped = squisher_is_flipped(
                    target.co, target.tris, body_bvh, SQUISH_ORIENTATION_DISTANCE, False
                )
            tris = target.tris[:, ::-1] if self._outfit_flipped else target.tris
            # Only the faces of the checked vertices
            faces = np.nonzero(active[target.tris].any(axis=1))[0]
            outfit_bvh = BVHTree.FromPolygons(co.tolist(), tris[faces].tolist())
            bb_min = co[active].min(axis=0) - margin
            bb_max = co[active].max(axis=0) + margin
            eps = 1e-5
            for i in np.nonzero(np.all((body_co >= bb_min) & (body_co <= bb_max), axis=1))[0]:
                n = Vector(body_normals[i])
                hit, hit_normal, face, dist = outfit_bvh.ray_cast(
                    Vector(body_co[i]) + n * eps, -n, settings.max_depth + eps
                )
                if hit is None or hit_normal.dot(n) < 0.5:
                    continue
                # Skip internal body parts, with the skin between them and the outfit
                if body_bvh.ray_cast(Vector(body_co[i]) - n * eps, -n, dist - 2 * eps)[0]:
                    continue
                # Skip outfit faces not buried as deep (e.g. seen through body openings)
                loc, loc_normal, _, _ = body_bvh.find_nearest(hit)
                if loc is not None and (loc - hit).dot(loc_normal) < 0.25 * (dist - eps):
                    continue
                need = dist - eps + settings.offset
                for k in target.tris[faces[face]]:
                    if active[k] and need > required[k]:
                        required[k] = need
                        directions[k] = n

        return required, directions

    def pulled(self, context, settings, weights):
        """Outfit vertices near the body, which the optimization pulls towards it"""

        target = self.target
        pulled = np.zeros(target.n_verts, dtype=bool)
        if settings.fit_distance <= 0.0:
            return pulled
        body_bvh, body_co, _ = self.body(context, self.body_key(settings))

        margin = settings.fit_distance + settings.offset
        bb_min = body_co.min(axis=0) - margin
        bb_max = body_co.max(axis=0) + margin
        inside = np.all((target.co >= bb_min) & (target.co <= bb_max), axis=1) & (weights > 0.0)
        for i in np.nonzero(inside)[0]:
            v = Vector(target.co[i])
            loc, normal, _, _ = body_bvh.find_nearest(v, margin)
            if loc is not None:
                pulled[i] = 0.0 < (v - loc).dot(normal) - settings.offset < settings.fit_distance
        return pulled

    def detect(self, context, settings, weights):
        key = (
            self.body_key(settings),
            settings.vertex_group,
            settings.invert_vertex_group,
            settings.check_body,
            settings.offset,
            settings.max_depth,
            settings.fit_distance,
        )
        if self._detect[0] != key:
            clipping = self.clipping(context, settings, weights)
            self._detect = (key, (*clipping, self.pulled(context, settings, weights)))
        return self._detect[1]

    def solve(self, context, settings):
        """Return the Shape Key coordinates, the number of fitted vertices and the error"""

        result = run_steps(self.solve_steps(context, settings))
        if self.check:
            run_steps(self.check_steps(context, settings))
        return result

    def solve_steps(self, context, settings):
        """Solve like solve, yielding the progress and the current step"""

        target = self.target
        self.disp = None
        self.iterations = 0
        self.metrics = None
        weights = target.weights(settings.vertex_group, settings.invert_vertex_group)
        if weights is None:
            return target.basis, 0, "Vertex Group not found"

        if self.body(context, self.body_key(settings))[0] is None:
            return target.basis, 0, "The selected Objects have no faces"

        yield 0.0, "Clipping"
        required, directions, pulled = self.detect(context, settings, weights)
        fitted = np.nonzero((required > 0.0) | pulled)[0]
        if not len(fitted):
            return target.basis, 0, ""

        # The optimization pulls by itself, as the pulls moving single vertices cross the outfit
        disp = directions * required[:, None]

        yield 0.2, "Smoothing"
        contact = np.nonzero(required > 0.0)[0]
        disp = target.smooth(
            disp,
            settings.smooth_distance,
            contact,
            directions[contact],
            required[contact],
            min_iterations=1,
        )

        self.influence = None
        if settings.auto_influence:
            self.influence = target.influence(self._detect[0], fitted, settings.influence_radius)
            disp *= self.influence[:, None]

        disp = yield from self.optimize(context, settings, weights, disp)

        disp *= (settings.factor * weights)[:, None]

        if settings.rigid_group:
            islands = target.rigid_islands(settings.rigid_group, settings.invert_rigid_group)
            if islands is None:
                return target.basis, 0, "Rigid Vertex Group not found"
            disp = target.rigidify(disp, islands)

        self.disp = disp
        return target.local(disp), len(fitted), ""


class MustardUI_ModelToolkit_FitToBody(ShapeKeyPreviewOperator, bpy.types.Operator):
    """Fit the Active Object (e.g. an outfit) to the other selected Objects (e.g. the body), pushing out the parts clipping through them, with a live preview.\nThe Rest Pose of the models is used"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_fit_to_body"
    bl_label = "Fit to Body"
    bl_options = {"REGISTER", "UNDO"}

    preview_tool = "FIT_TO_BODY"
    preview_verb = "fitted"

    @classmethod
    def poll(cls, context):
        if preview_running():
            return False
        obj = context.active_object
        if obj is None or obj.type != "MESH" or obj.mode != "OBJECT":
            return False
        return any(x != obj and x.type == "MESH" for x in context.selected_objects)

    def preview_settings(self, context):
        return context.window_manager.MustardUI_ModelToolkit_FitToBodySettings

    def solver(self, context, check=False):
        settings = self.preview_settings(context)
        outfit = context.active_object
        bodies = [x for x in context.selected_objects if x != outfit and x.type == "MESH"]
        name = settings.shape_key_name.strip()

        if not name:
            self.report({"ERROR"}, "MustardUI - Choose a Shape Key name")
            return None

        if outfit.data.shape_keys is not None and outfit.data.shape_keys.reference_key.name == name:
            self.report({"ERROR"}, "MustardUI - The Basis Shape Key can not be overwritten")
            return None

        return FitToBodySolver(outfit, bodies, name, check)

    def execute(self, context):
        settings = self.preview_settings(context)
        solver = self.solver(context)
        if solver is None:
            return {"CANCELLED"}

        shape_co, count, error = solver.solve(context, settings)
        if error:
            self.report({"ERROR"}, f"MustardUI - {error}")
            return {"CANCELLED"}
        if not count:
            self.report({"WARNING"}, "MustardUI - No vertex to fit")
            return {"CANCELLED"}

        name = settings.shape_key_name.strip()
        if solver.influence is not None:
            write_vertex_group(solver.outfit, name, solver.influence)
        if settings.result == "MESH":
            fit_to_body_apply_to_mesh(solver.outfit, shape_co - solver.target.basis)
            fit_to_body_apply_to_children(solver, settings)
            self.report({"INFO"}, f"MustardUI - Fitted to body ({count} vertices)")
        else:
            sk = write_shape_key(solver.outfit, name, shape_co)
            create_followers_shape_keys(solver, settings, solver.outfit, sk.name)
            self.report({"INFO"}, f"MustardUI - Shape Key '{sk.name}' created ({count} vertices)")
        return {"FINISHED"}

    def invoke(self, context, event):
        settings = self.preview_settings(context)
        bodies = [
            x.name
            for x in context.selected_objects
            if x != context.active_object and x.type == "MESH"
        ]
        settings.shape_key_name = f"Fit to Body - {', '.join(sorted(bodies))}"

        solver = self.solver(context, check=preview_debug())
        if solver is None:
            return {"CANCELLED"}

        return self.preview_start(context, solver.outfit, settings.shape_key_name.strip(), solver)

    def preview_finish(self, context, session):
        if session.settings.result != "MESH":
            return super().preview_finish(context, session)

        sk = session.obj.data.shape_keys.key_blocks[session.key_name]
        co = np.empty(len(sk.data) * 3, dtype=np.float64)
        sk.data.foreach_get("co", co)
        disp = co.reshape(-1, 3) - session.solver.target.basis

        session.restore()
        fit_to_body_apply_to_mesh(session.obj, disp)
        fit_to_body_apply_to_children(session.solver, session.settings)
        if session.solver.influence is not None:
            name = session.settings.shape_key_name.strip() or session.key_name
            write_vertex_group(session.obj, name, session.solver.influence)
        return f"Fitted to body ({session.count} vertices)"


def fit_to_body_apply_to_mesh(obj, disp):
    """Add the local displacement to the mesh and all its Shape Keys"""

    mesh = obj.data
    co = np.empty(len(mesh.vertices) * 3, dtype=np.float64)
    mesh.vertices.foreach_get("co", co)
    mesh.vertices.foreach_set("co", co + disp.ravel())
    if mesh.shape_keys is not None:
        for kb in mesh.shape_keys.key_blocks:
            kb.data.foreach_get("co", co)
            kb.data.foreach_set("co", co + disp.ravel())
    mesh.update()


def fit_to_body_apply_to_children(solver, settings):
    for follower in solver.followers:
        if follower.enabled(settings):
            fit_to_body_apply_to_mesh(
                follower.obj, follower.shape(solver, settings) - follower.basis
            )


def fit_to_body_draw_settings(layout, context):
    """Draw the settings of the running preview"""

    session = preview_session("FIT_TO_BODY")
    if session is None:
        return
    settings = session.settings

    box = layout.box()
    preview_draw_presets(box, FitToBodyPresetsMenu, FitToBodyPresetAdd)
    col = box.column()
    col.use_property_split = True
    col.use_property_decorate = False
    col.prop(settings, "factor", text="Strength")

    col = preview_section(box, "mustardui_fit_output", "Output", "SHAPEKEY_DATA")
    if col is not None:
        col.prop(settings, "result")
        row = col.row()
        row.enabled = settings.result == "SHAPE_KEY"
        row.prop(settings, "shape_key_name")

    col = preview_section(box, "mustardui_fit_fitting", "Fitting", "MOD_CLOTH")
    if col is not None:
        col.prop(settings, "offset", text="Skin Distance")
        col.separator()
        col.prop(settings, "max_depth")
        col.prop(settings, "check_body", text="Body Vertices")
        col.separator()
        col.prop(settings, "fit_distance", text="Pull Distance")
        col.separator()
        col.prop(settings, "use_modifiers", text="Body Modifiers")
        col.prop(settings, "ignore_body_shape_keys")

    col = preview_section(box, "mustardui_fit_shape", "Shape", "MOD_SMOOTH")
    if col is not None:
        col.prop(settings, "smooth_distance")
        col.prop(settings, "stiffness")
        col.prop(settings, "iterations")
        col.prop(settings, "self_collisions")

    preview_draw_masks(box, session, "fit")

    if preview_debug() and (
        col := preview_section(box, "mustardui_fit_debug", "Debug", "CONSOLE", True)
    ):
        metrics = session.solver.metrics
        rows = [
            ("Fitted Vertices", str(session.count)),
            ("Iterations", str(session.solver.iterations)),
            ("Time", f"{session.elapsed:.2f} s"),
        ]
        labels = ("Buried Vertices", "Through Body", "Self Intersections")
        for index, label in enumerate(labels):
            value = "..." if metrics is None else f"{metrics[0][index]} → {metrics[1][index]}"
            rows.append((label, value))
        for label, value in rows:
            split = col.split(factor=0.4)
            row = split.row()
            row.alignment = "RIGHT"
            row.label(text=label)
            split.label(text=value)

    preview_draw_footer(box, session, info=False)


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_FitToBodySettings)
    bpy.utils.register_class(MustardUI_ModelToolkit_FitToBody)
    bpy.utils.register_class(FitToBodyPresetsMenu)
    bpy.utils.register_class(FitToBodyPresetAdd)

    bpy.types.WindowManager.MustardUI_ModelToolkit_FitToBodySettings = bpy.props.PointerProperty(
        type=MustardUI_ModelToolkit_FitToBodySettings
    )


def unregister():
    del bpy.types.WindowManager.MustardUI_ModelToolkit_FitToBodySettings

    bpy.utils.unregister_class(FitToBodyPresetAdd)
    bpy.utils.unregister_class(FitToBodyPresetsMenu)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_FitToBody)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_FitToBodySettings)
