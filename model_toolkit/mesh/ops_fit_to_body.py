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
from .ops_squish import SQUISH_ORIENTATION_DISTANCE, squisher_is_flipped
from .shape_key_preview import (
    ShapeKeyPreviewOperator,
    create_followers_shape_keys,
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


class MustardUI_ToolsCreators_FitToBodySettings(bpy.types.PropertyGroup):
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

    fit_strength: bpy.props.FloatProperty(
        name="Fit Strength",
        default=1.0,
        min=0.0,
        max=1.0,
        description="Fraction of the distance from the body closed by the pull",
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

    keep_contact: bpy.props.BoolProperty(
        name="Keep Contact",
        default=True,
        description="Keep the fitted vertices out of the body while smoothing",
        update=preview_settings_update,
    )

    relax_iterations: bpy.props.IntProperty(
        name="Relax",
        default=0,
        min=0,
        soft_max=50,
        description="Relaxation iterations, to even out the vertices distribution in the "
        "fitted area",
        update=preview_settings_update,
    )

    relax_factor: bpy.props.FloatProperty(
        name="Relax Factor",
        default=0.5,
        min=0.0,
        max=1.0,
        description="Strength of each relaxation iteration",
        update=preview_settings_update,
    )

    final_check: bpy.props.BoolProperty(
        name="Final Check",
        default=True,
        description="Push out again the vertices still clipping after smoothing and relaxing",
        update=preview_settings_update,
    )


def clipping_vertices(bvh, co, indices, offset, max_depth):
    """Distance to move each vertex along the body normal to be outside the body"""

    required = np.zeros(len(indices))
    directions = np.zeros((len(indices), 3))
    for k, i in enumerate(indices):
        v = Vector(co[i])
        loc, normal, _, _ = bvh.find_nearest(v, max_depth + offset)
        if loc is None:
            continue
        signed = (v - loc).dot(normal)
        if signed < offset:
            required[k] = offset - signed
            directions[k] = normal
    return required, directions


def pulling_vertices(bvh, co, indices, offset, distance, strength):
    """Distance to move each vertex towards the body, fading to zero at the fit distance"""

    pull = np.zeros(len(indices))
    directions = np.zeros((len(indices), 3))
    for k, i in enumerate(indices):
        v = Vector(co[i])
        loc, normal, _, _ = bvh.find_nearest(v, offset + distance)
        if loc is None:
            continue
        gap = (v - loc).dot(normal) - offset
        if 0.0 < gap < distance:
            # Full pull up to half the distance, then fading out
            t = max(2.0 * gap / distance - 1.0, 0.0)
            pull[k] = gap * strength * (1.0 - t * t * (3.0 - 2.0 * t))
            directions[k] = -normal
    return pull, directions


FitToBodyPresetsMenu, FitToBodyPresetAdd = preview_preset_classes(
    "FitToBody",
    "Fit to Body",
    MustardUI_ToolsCreators_FitToBodySettings,
    "MustardUI_ToolsCreators_FitToBodySettings",
)


class FitToBodySolver:
    """Compute the fitted outfit, caching the results not affected by the changed settings"""

    def __init__(self, context, outfit, bodies, key_name):
        self.outfit = outfit
        self.bodies = bodies
        self.target = DeformTarget(outfit, key_name)
        self.children = self.target.rigid_children(bodies)
        self.followers = self.children
        self.disp = None

        self._body = {}
        self._outfit_flipped = None
        self._detect = (None, None)
        self.influence = None

    def body(self, context, use_modifiers):
        """Body BVHTree, coordinates and normals"""

        if use_modifiers not in self._body:
            geometry = rest_geometry(context, self.bodies, [self.outfit], use_modifiers)
            bvh, co = geometry_bvh(geometry)
            normals = None
            if bvh is not None:
                offset = 0
                tris = []
                for item_co, tri in geometry:
                    tris.append(tri + offset)
                    offset += len(item_co)
                normals = mesh_vertex_normals(co, np.concatenate(tris))
            self._body[use_modifiers] = (bvh, co, normals)
        return self._body[use_modifiers]

    def outfit_flipped(self, body_bvh):
        if self._outfit_flipped is None:
            target = self.target
            self._outfit_flipped = squisher_is_flipped(
                target.co, target.tris, body_bvh, SQUISH_ORIENTATION_DISTANCE, False
            )
        return self._outfit_flipped

    def clipping(self, context, settings, weights, co, outfit_mask=None):
        """Required displacement along the directions to fix the clipping of the outfit with
        the given coordinates, checking only the masked outfit vertices"""

        body_bvh, body_co, body_normals = self.body(context, settings.use_modifiers)
        target = self.target
        margin = settings.max_depth + settings.offset
        active = weights > 0.0
        if outfit_mask is not None:
            active &= outfit_mask

        # Outfit vertices inside the body
        bb_min = body_co.min(axis=0) - margin
        bb_max = body_co.max(axis=0) + margin
        candidates = np.nonzero(np.all((co >= bb_min) & (co <= bb_max), axis=1) & active)[0]
        required = np.zeros(target.n_verts)
        directions = np.zeros((target.n_verts, 3))
        required[candidates], directions[candidates] = clipping_vertices(
            body_bvh, co, candidates, settings.offset, settings.max_depth
        )

        # Body vertices through the outfit faces
        if settings.check_body and np.any(active):
            tris = target.tris[:, ::-1] if self.outfit_flipped(body_bvh) else target.tris
            outfit_bvh = BVHTree.FromPolygons(co.tolist(), tris.tolist())
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
                need = dist - eps + settings.offset
                for k in target.tris[face]:
                    if active[k] and need > required[k]:
                        required[k] = need
                        directions[k] = n

        return required, directions

    def pulls(self, context, settings, weights, co, outfit_mask=None):
        """Displacement pulling the outfit parts near the body towards it, checking only the
        masked outfit vertices"""

        body_bvh, body_co, _ = self.body(context, settings.use_modifiers)
        target = self.target
        disp = np.zeros((target.n_verts, 3))
        active = weights > 0.0
        if outfit_mask is not None:
            active &= outfit_mask
        if settings.fit_distance <= 0.0 or settings.fit_strength <= 0.0:
            return disp

        margin = settings.fit_distance + settings.offset
        bb_min = body_co.min(axis=0) - margin
        bb_max = body_co.max(axis=0) + margin
        candidates = np.nonzero(np.all((co >= bb_min) & (co <= bb_max), axis=1) & active)[0]
        pull, directions = pulling_vertices(
            body_bvh, co, candidates, settings.offset, settings.fit_distance, settings.fit_strength
        )
        disp[candidates] = directions * pull[:, None]
        return disp

    def layers(self, context, settings, weights):
        """Outfit vertices over another layer of the outfit, with the face under them"""

        body_bvh, body_co, _ = self.body(context, settings.use_modifiers)
        target = self.target
        co = target.co
        margin = max(settings.fit_distance, settings.max_depth) + settings.offset
        bb_min = body_co.min(axis=0) - margin
        bb_max = body_co.max(axis=0) + margin
        candidates = np.nonzero(np.all((co >= bb_min) & (co <= bb_max), axis=1) & (weights > 0.0))[
            0
        ]

        outfit_bvh = BVHTree.FromPolygons(co.tolist(), target.tris.tolist())
        eps = 1e-4
        outer = []
        under = []
        for i in candidates:
            v = Vector(co[i])
            loc, normal, _, _ = body_bvh.find_nearest(v, margin)
            if loc is None:
                continue
            hit, _, face, _ = outfit_bvh.ray_cast(v - normal * eps, -normal, margin)
            if hit is not None and i not in target.tris[face]:
                outer.append(i)
                under.append(target.tris[face])
        return np.array(outer, dtype=np.int64), np.array(under, dtype=np.int64).reshape(-1, 3)

    def detect(self, context, settings, weights):
        key = (
            settings.use_modifiers,
            settings.vertex_group,
            settings.invert_vertex_group,
            settings.check_body,
            settings.offset,
            settings.max_depth,
            settings.fit_distance,
            settings.fit_strength,
        )
        if self._detect[0] != key:
            clipping = self.clipping(context, settings, weights, self.target.co)
            pulls = self.pulls(context, settings, weights, self.target.co)
            layers = self.layers(context, settings, weights)
            self._detect = (key, (*clipping, pulls, layers))
        return self._detect[1]

    def solve(self, context, settings):
        """Return the Shape Key coordinates, the number of fitted vertices and the error"""

        target = self.target
        self.disp = None
        weights = target.weights(settings.vertex_group, settings.invert_vertex_group)
        if weights is None:
            return target.basis, 0, "Vertex Group not found"

        if self.body(context, settings.use_modifiers)[0] is None:
            return target.basis, 0, "The selected Objects have no faces"

        required, directions, pull, (outer, under) = self.detect(context, settings, weights)
        fitted = np.nonzero((required > 0.0) | np.any(pull != 0.0, axis=1))[0]
        if not len(fitted):
            return target.basis, 0, ""

        disp = directions * required[:, None] + pull

        contact = np.nonzero(required > 0.0)[0]
        disp = target.smooth(
            disp,
            settings.smooth_distance,
            contact,
            directions[contact],
            required[contact],
            settings.keep_contact,
            min_iterations=1,
        )
        disp = target.relax(disp, settings.relax_iterations, settings.relax_factor)

        self.influence = None
        if settings.auto_influence:
            self.influence = target.influence(self._detect[0], fitted, settings.influence_radius)
            disp *= self.influence[:, None]

        # Push out the moved vertices clipping again
        if settings.final_check:
            for _ in range(3):
                moved = np.linalg.norm(disp, axis=1) > 1e-7
                again, again_dirs = self.clipping(
                    context, settings, weights, target.co + disp, moved
                )
                again_contact = np.nonzero(again > 0.0)[0]
                if not len(again_contact):
                    break
                # Smoothed anyway, as unsmoothed pushes build spikes
                disp += target.smooth(
                    again_dirs * again[:, None],
                    settings.smooth_distance,
                    again_contact,
                    again_dirs[again_contact],
                    again[again_contact],
                    True,
                    min_iterations=5,
                )

        # Outer layers follow the layer under them, keeping the thickness
        for _ in range(2):
            disp[outer] = disp[under].mean(axis=1)

        disp *= (settings.factor * weights)[:, None]

        if settings.rigid_group:
            islands = target.rigid_islands(settings.rigid_group, settings.invert_rigid_group)
            if islands is None:
                return target.basis, 0, "Rigid Vertex Group not found"
            disp = target.rigidify(disp, islands)

        self.disp = disp
        return target.local(disp), len(fitted), ""


class MustardUI_ToolsCreators_FitToBody(ShapeKeyPreviewOperator, bpy.types.Operator):
    """Fit the Active Object (e.g. an outfit) to the other selected Objects (e.g. the body), pushing out the parts clipping through them, with a live preview.\nThe Rest Pose of the models is used"""  # noqa: E501

    bl_idname = "mustardui.tools_creators_fit_to_body"
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
        return context.window_manager.MustardUI_ToolsCreators_FitToBodySettings

    def solver(self, context):
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

        return FitToBodySolver(context, outfit, bodies, name)

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

        solver = self.solver(context)
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
        col.prop(settings, "final_check")
        col.separator()
        sub = col.column(align=True)
        sub.prop(settings, "fit_distance", text="Pull Distance")
        row = sub.row(align=True)
        row.enabled = settings.fit_distance > 0.0
        row.prop(settings, "fit_strength", text="Pull Strength")
        col.separator()
        col.prop(settings, "use_modifiers", text="Body Modifiers")

    col = preview_section(box, "mustardui_fit_shape", "Shape", "MOD_SMOOTH")
    if col is not None:
        sub = col.column(align=True)
        sub.prop(settings, "smooth_distance")
        sub.prop(settings, "keep_contact")
        sub = col.column(align=True)
        sub.prop(settings, "relax_iterations")
        row = sub.row(align=True)
        row.enabled = settings.relax_iterations > 0
        row.prop(settings, "relax_factor", text="Factor")

    preview_draw_masks(box, session, "fit")
    preview_draw_footer(box, session)


def register():
    bpy.utils.register_class(MustardUI_ToolsCreators_FitToBodySettings)
    bpy.utils.register_class(MustardUI_ToolsCreators_FitToBody)
    bpy.utils.register_class(FitToBodyPresetsMenu)
    bpy.utils.register_class(FitToBodyPresetAdd)

    bpy.types.WindowManager.MustardUI_ToolsCreators_FitToBodySettings = bpy.props.PointerProperty(
        type=MustardUI_ToolsCreators_FitToBodySettings
    )


def unregister():
    del bpy.types.WindowManager.MustardUI_ToolsCreators_FitToBodySettings

    bpy.utils.unregister_class(FitToBodyPresetAdd)
    bpy.utils.unregister_class(FitToBodyPresetsMenu)
    bpy.utils.unregister_class(MustardUI_ToolsCreators_FitToBody)
    bpy.utils.unregister_class(MustardUI_ToolsCreators_FitToBodySettings)
