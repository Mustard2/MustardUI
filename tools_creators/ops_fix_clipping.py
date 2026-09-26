import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from ..misc.mesh_deform import (
    DeformTarget,
    geometry_bvh,
    mesh_vertex_normals,
    rest_geometry,
    write_vertex_group,
)
from .ops_squish import SQUISH_ORIENTATION_DISTANCE, squish_creator_is_flipped
from .shape_key_preview import (
    ShapeKeyPreviewOperator,
    create_children_shape_keys,
    preview_draw_footer,
    preview_running,
    preview_session,
    preview_settings_update,
    write_shape_key,
)


class MustardUI_ToolsCreators_FixClippingSettings(bpy.types.PropertyGroup):
    shape_key_name: bpy.props.StringProperty(
        name="Shape Key",
        default="Fix Clipping",
        description="Name of the Shape Key. If it already exists, it is overwritten",
    )

    result: bpy.props.EnumProperty(
        name="Result",
        items=(
            ("SHAPE_KEY", "Shape Key", "Create a Shape Key with the fix"),
            (
                "MESH",
                "Mesh",
                "Apply the fix to the mesh and all its Shape Keys",
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

    rigid_group: bpy.props.StringProperty(
        name="Rigid Vertex Group",
        description="Vertex Group of the rigid parts (e.g. buttons), which are moved without "
        "deforming them",
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
        description="Also fix the body vertices passing through the outfit faces, useful when "
        "the outfit has less vertices than the body",
        update=preview_settings_update,
    )

    factor: bpy.props.FloatProperty(
        name="Factor",
        default=1.0,
        min=0.0,
        soft_max=1.0,
        description="Strength of the fix",
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

    max_depth: bpy.props.FloatProperty(
        name="Max Depth",
        default=0.05,
        min=0.0001,
        soft_max=0.2,
        subtype="DISTANCE",
        description="Maximum clipping depth to consider. Increase it if some vertices are not "
        "fixed, decrease it if far vertices are moved by mistake",
        update=preview_settings_update,
    )

    smooth_iterations: bpy.props.IntProperty(
        name="Smooth",
        default=10,
        min=1,
        soft_max=100,
        description="Smoothing iterations of the fix, to spread it on the neighbouring "
        "vertices and preserve the outfit shape",
        update=preview_settings_update,
    )

    keep_contact: bpy.props.BoolProperty(
        name="Keep Contact",
        default=True,
        description="Keep the fixed vertices out of the body while smoothing",
        update=preview_settings_update,
    )

    relax_iterations: bpy.props.IntProperty(
        name="Relax",
        default=0,
        min=0,
        soft_max=50,
        description="Relaxation iterations, to even out the vertices distribution in the "
        "fixed area",
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


class FixClippingSolver:
    """Compute the fixed outfit, caching the results not affected by the changed settings"""

    def __init__(self, context, outfit, bodies, key_name):
        self.outfit = outfit
        self.bodies = bodies
        self.target = DeformTarget(outfit, key_name)
        self.children = self.target.rigid_children(bodies)
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
            self._outfit_flipped = squish_creator_is_flipped(
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

    def detect(self, context, settings, weights):
        key = (
            settings.use_modifiers,
            settings.vertex_group,
            settings.check_body,
            settings.offset,
            settings.max_depth,
        )
        if self._detect[0] != key:
            self._detect = (key, self.clipping(context, settings, weights, self.target.co))
        return self._detect[1]

    def solve(self, context, settings):
        """Return the Shape Key coordinates, the number of fixed vertices and the error"""

        target = self.target
        self.disp = None
        weights = target.weights(settings.vertex_group)
        if weights is None:
            return target.basis, 0, "Vertex Group not found"

        if self.body(context, settings.use_modifiers)[0] is None:
            return target.basis, 0, "The selected Objects have no faces"

        required, directions = self.detect(context, settings, weights)
        contact = np.nonzero(required > 0.0)[0]
        if not len(contact):
            return target.basis, 0, ""

        disp = directions * required[:, None]
        disp = target.smooth(
            disp,
            settings.smooth_iterations,
            contact,
            directions[contact],
            required[contact],
            settings.keep_contact,
        )
        disp = target.relax(disp, settings.relax_iterations, settings.relax_factor)

        self.influence = None
        if settings.auto_influence:
            self.influence = target.influence(self._detect[0], contact, settings.influence_radius)
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
                    max(settings.smooth_iterations, 5),
                    again_contact,
                    again_dirs[again_contact],
                    again[again_contact],
                    True,
                )

        disp *= (settings.factor * weights)[:, None]

        if settings.rigid_group:
            islands = target.rigid_islands(settings.rigid_group)
            if islands is None:
                return target.basis, 0, "Rigid Vertex Group not found"
            disp = target.rigidify(disp, islands)

        self.disp = disp
        return target.local(disp), len(contact), ""


class MustardUI_ToolsCreators_FixClipping(ShapeKeyPreviewOperator, bpy.types.Operator):
    """Fix the Active Object (e.g. an outfit) clipping through the other selected Objects (e.g.
    the body), with a live preview.\nThe Rest Pose of the models is used"""

    bl_idname = "mustardui.tools_creators_fix_clipping"
    bl_label = "Fix Clipping"
    bl_options = {"REGISTER", "UNDO"}

    preview_tool = "FIX_CLIPPING"
    preview_verb = "fixed"

    @classmethod
    def poll(cls, context):
        if preview_running():
            return False
        obj = context.active_object
        if obj is None or obj.type != "MESH" or obj.mode != "OBJECT":
            return False
        return any(x != obj and x.type == "MESH" for x in context.selected_objects)

    def preview_settings(self, context):
        return context.window_manager.MustardUI_ToolsCreators_FixClippingSettings

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

        return FixClippingSolver(context, outfit, bodies, name)

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
            self.report({"WARNING"}, "MustardUI - No vertex is clipping")
            return {"CANCELLED"}

        name = settings.shape_key_name.strip()
        if solver.influence is not None:
            write_vertex_group(solver.outfit, name, solver.influence)
        if settings.result == "MESH":
            fix_clipping_apply_to_mesh(solver.outfit, shape_co - solver.target.basis)
            fix_clipping_apply_to_children(solver, settings)
            self.report({"INFO"}, f"MustardUI - Clipping fixed ({count} vertices)")
        else:
            sk = write_shape_key(solver.outfit, name, shape_co)
            create_children_shape_keys(solver, settings, solver.outfit, sk.name)
            self.report({"INFO"}, f"MustardUI - Shape Key '{sk.name}' created ({count} vertices)")
        return {"FINISHED"}

    def invoke(self, context, event):
        settings = self.preview_settings(context)
        bodies = [
            x.name
            for x in context.selected_objects
            if x != context.active_object and x.type == "MESH"
        ]
        settings.shape_key_name = f"Fix Clipping - {', '.join(sorted(bodies))}"

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
        fix_clipping_apply_to_mesh(session.obj, disp)
        fix_clipping_apply_to_children(session.solver, session.settings)
        if session.solver.influence is not None:
            name = session.settings.shape_key_name.strip() or session.key_name
            write_vertex_group(session.obj, name, session.solver.influence)
        return f"Clipping fixed ({session.count} vertices)"


def fix_clipping_apply_to_mesh(obj, disp):
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


def fix_clipping_apply_to_children(solver, settings):
    if settings.move_children:
        for child in solver.children:
            fix_clipping_apply_to_mesh(child.obj, child.coordinates(solver.disp) - child.basis)


def fix_clipping_draw_settings(layout, context):
    """Draw the settings of the running preview"""

    session = preview_session("FIX_CLIPPING")
    if session is None:
        return
    settings = session.settings

    box = layout.box()
    col = box.column()
    col.use_property_split = True
    col.use_property_decorate = False

    col.prop(settings, "result")
    row = col.row()
    row.enabled = settings.result == "SHAPE_KEY"
    row.prop(settings, "shape_key_name")
    col.prop(settings, "use_modifiers")
    col.prop(settings, "check_body")
    col.prop_search(settings, "vertex_group", session.obj, "vertex_groups")
    col.prop_search(settings, "rigid_group", session.obj, "vertex_groups")
    row = col.row()
    row.enabled = bool(session.solver.children)
    row.prop(settings, "move_children", text=f"Child Objects ({len(session.solver.children)})")
    col.prop(settings, "auto_influence")
    row = col.row()
    row.enabled = settings.auto_influence
    row.prop(settings, "influence_radius")

    col.separator()
    sub = col.column(align=True)
    sub.prop(settings, "factor")
    sub.prop(settings, "offset")
    sub.prop(settings, "max_depth")

    col.separator()
    sub = col.column(align=True)
    sub.prop(settings, "smooth_iterations")
    sub.prop(settings, "keep_contact")

    col.separator()
    sub = col.column(align=True)
    sub.prop(settings, "relax_iterations")
    row = sub.row(align=True)
    row.enabled = settings.relax_iterations > 0
    row.prop(settings, "relax_factor")

    col.separator()
    col.prop(settings, "final_check")

    preview_draw_footer(box, session)


def register():
    bpy.utils.register_class(MustardUI_ToolsCreators_FixClippingSettings)
    bpy.utils.register_class(MustardUI_ToolsCreators_FixClipping)

    bpy.types.WindowManager.MustardUI_ToolsCreators_FixClippingSettings = bpy.props.PointerProperty(
        type=MustardUI_ToolsCreators_FixClippingSettings
    )


def unregister():
    del bpy.types.WindowManager.MustardUI_ToolsCreators_FixClippingSettings

    bpy.utils.unregister_class(MustardUI_ToolsCreators_FixClipping)
    bpy.utils.unregister_class(MustardUI_ToolsCreators_FixClippingSettings)
