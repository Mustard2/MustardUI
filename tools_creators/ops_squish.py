import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

from ..misc.mesh_deform import DeformTarget, geometry_bvh, rest_geometry, write_vertex_group
from .shape_key_preview import (
    ShapeKeyPreviewOperator,
    create_children_shape_keys,
    preview_draw_footer,
    preview_running,
    preview_session,
    preview_settings_update,
    write_shape_key,
)

SQUISH_CREATOR_TYPES = {"MESH", "CURVE", "SURFACE", "META", "FONT"}
SQUISH_ORIENTATION_DISTANCE = 0.1


def squish_creator_is_flipped(co, tris, body_bvh, max_dist, volume):
    """Check if the creator normals point inwards, as they often do in clothes"""

    p0, p1, p2 = co[tris[:, 0]], co[tris[:, 1]], co[tris[:, 2]]
    face_normals = np.cross(p1 - p0, p2 - p0)

    # Volume: sign of the enclosed volume
    if volume:
        center = co.mean(axis=0)
        return np.einsum("ij,ij->", p0 - center, face_normals) < 0.0

    # Surface: the creator should face as the closest body surface
    centers = (p0 + p1 + p2) / 3.0
    step = max(1, len(tris) // 5000)
    vote = 0.0
    for c, n in zip(centers[::step], face_normals[::step], strict=True):
        loc, body_normal, _, _ = body_bvh.find_nearest(Vector(c), max_dist)
        if loc is not None:
            vote += Vector(n).normalized().dot(body_normal)
    return vote < 0.0


class MustardUI_ToolsCreators_SquishSettings(bpy.types.PropertyGroup):
    shape_key_name: bpy.props.StringProperty(
        name="Shape Key",
        default="Squish",
        description="Name of the Shape Key. If it already exists, it is overwritten",
    )

    mode: bpy.props.EnumProperty(
        name="Mode",
        items=(
            (
                "SURFACE",
                "Surface",
                "The body vertices poking out of the creator surface are pushed under it (e.g. "
                "clothes, straps)",
            ),
            (
                "VOLUME",
                "Volume",
                "The body vertices inside the creator volume are pushed out of it (e.g. hands, "
                "closed objects pressing on the body)",
            ),
        ),
        default="SURFACE",
        update=preview_settings_update,
    )

    use_modifiers: bpy.props.BoolProperty(
        name="Use Modifiers",
        default=True,
        description="Use the creators with their modifiers evaluated",
        update=preview_settings_update,
    )

    vertex_group: bpy.props.StringProperty(
        name="Vertex Group",
        description="Restrict the effect to this Vertex Group of the body",
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

    factor: bpy.props.FloatProperty(
        name="Factor",
        default=1.0,
        min=0.0,
        soft_max=2.0,
        description="Strength of the squish",
        update=preview_settings_update,
    )

    offset: bpy.props.FloatProperty(
        name="Offset",
        default=0.001,
        soft_min=-0.01,
        soft_max=0.01,
        step=0.01,
        precision=4,
        subtype="DISTANCE",
        description="Additional distance of the squished vertices from the creator surface",
        update=preview_settings_update,
    )

    tightness: bpy.props.FloatProperty(
        name="Tightness",
        default=0.0,
        min=0.0,
        soft_max=0.01,
        step=0.01,
        precision=4,
        subtype="DISTANCE",
        description="Shrink the creator into the body by this distance, to squish creators "
        "resting on the body without intersecting it (e.g. fitted clothes)",
        update=preview_settings_update,
    )

    max_depth: bpy.props.FloatProperty(
        name="Max Depth",
        default=0.05,
        min=0.0001,
        soft_max=0.2,
        subtype="DISTANCE",
        description="Maximum penetration depth to consider. Increase it if some vertices are "
        "not squished, decrease it if far vertices are squished by mistake",
        update=preview_settings_update,
    )

    bulge: bpy.props.FloatProperty(
        name="Bulge",
        default=0.3,
        min=0.0,
        soft_max=1.0,
        description="Push the vertices around the squished area outwards, as the flesh "
        "displaced by the creator",
        update=preview_settings_update,
    )

    bulge_radius: bpy.props.FloatProperty(
        name="Bulge Radius",
        default=0.02,
        min=0.0,
        soft_max=0.1,
        subtype="DISTANCE",
        description="Distance from the squished area affected by the bulge",
        update=preview_settings_update,
    )

    smooth_iterations: bpy.props.IntProperty(
        name="Smooth",
        default=5,
        min=0,
        soft_max=100,
        description="Smoothing iterations of the squish displacement, to spread it on the "
        "neighbouring vertices",
        update=preview_settings_update,
    )

    keep_contact: bpy.props.BoolProperty(
        name="Keep Contact",
        default=True,
        description="Keep the squished vertices under the creator while smoothing",
        update=preview_settings_update,
    )

    relax_iterations: bpy.props.IntProperty(
        name="Relax",
        default=5,
        min=0,
        soft_max=50,
        description="Relaxation iterations, to even out the vertices distribution in the "
        "squished area",
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


class SquishSolver:
    """Compute the squish Shape Key, caching the results not affected by the changed settings"""

    def __init__(self, context, body, creators, key_name):
        self.body = body
        self.creators = creators
        self.target = DeformTarget(body, key_name)
        self.children = self.target.rigid_children(creators)
        self.disp = None
        self.body_bvh = BVHTree.FromPolygons(self.target.co.tolist(), self.target.tris.tolist())

        self._geometry = {}
        self._bvh = {}
        self._depth = (None, None)
        self._bulge = (None, None)
        self.influence = None

    def creators_bvh(self, context, settings):
        key = (settings.use_modifiers, settings.mode)
        if key not in self._bvh:
            if settings.use_modifiers not in self._geometry:
                self._geometry[settings.use_modifiers] = rest_geometry(
                    context, self.creators, [self.body], settings.use_modifiers
                )
            geometry = self._geometry[settings.use_modifiers]
            volume = settings.mode == "VOLUME"
            flipped = [
                squish_creator_is_flipped(
                    co, tri, self.body_bvh, SQUISH_ORIENTATION_DISTANCE, volume
                )
                for co, tri in geometry
            ]
            self._bvh[key] = geometry_bvh(geometry, flipped)
        return self._bvh[key]

    def depth(self, context, settings, weights):
        """Penetration depth along the inverted body normal"""

        surface = settings.mode == "SURFACE"
        tightness = settings.tightness if surface else 0.0
        key = (
            settings.use_modifiers,
            settings.mode,
            settings.vertex_group,
            settings.offset,
            tightness,
            settings.max_depth,
        )
        if self._depth[0] == key:
            return self._depth[1]

        bvh, creators_co = self.creators_bvh(context, settings)
        if bvh is None:
            return None

        # Only check the vertices close to the creators
        co = self.target.co
        normals = self.target.normals
        margin = settings.max_depth + tightness
        bb_min = creators_co.min(axis=0) - margin
        bb_max = creators_co.max(axis=0) + margin
        candidates = np.nonzero(np.all((co >= bb_min) & (co <= bb_max), axis=1) & (weights > 0.0))[
            0
        ]

        depth = np.zeros(self.target.n_verts)
        eps = 1e-5
        start = eps + tightness
        for i in candidates:
            v = Vector(co[i])
            n = Vector(normals[i])
            if not surface:
                nearest, nearest_normal, _, _ = bvh.find_nearest(v)
                if nearest is None or (v - nearest).dot(nearest_normal) > 0.0:
                    continue
            hit, hit_normal, _, dist = bvh.ray_cast(v + n * start, -n, settings.max_depth + start)
            if hit is None:
                continue
            # Surface: creator facing as the body, Volume: exit face of the creator
            facing = hit_normal.dot(n)
            if (surface and facing > 0.5) or (not surface and facing < 0.0):
                depth[i] = max(dist - eps + settings.offset, 0.0)

        self._depth = (key, depth)
        return depth

    def bulge(self, depth, contact, weights, radius):
        """Bulge around the squished area, before the Bulge factor"""

        key = (self._depth[0], radius)
        if self._bulge[0] == key:
            return self._bulge[1]

        co = self.target.co
        bulge = np.zeros(self.target.n_verts)
        kd = KDTree(len(contact))
        for k, i in enumerate(contact):
            kd.insert(co[i], k)
        kd.balance()

        bb_min = co[contact].min(axis=0) - radius
        bb_max = co[contact].max(axis=0) + radius
        near = np.all((co >= bb_min) & (co <= bb_max), axis=1) & (weights > 0.0) & (depth == 0.0)
        for i in np.nonzero(near)[0]:
            value = 0.0
            for _, k, d in kd.find_range(co[i], radius):
                falloff = 1.0 - d / radius
                value = max(value, depth[contact[k]] * falloff * falloff)
            bulge[i] = value

        self._bulge = (key, bulge)
        return bulge

    def solve(self, context, settings):
        """Return the Shape Key coordinates, the number of squished vertices and the error"""

        target = self.target
        self.disp = None
        weights = target.weights(settings.vertex_group)
        if weights is None:
            return target.basis, 0, "Vertex Group not found"

        depth = self.depth(context, settings, weights)
        if depth is None:
            return target.basis, 0, "The selected Objects have no faces"

        contact = np.nonzero(depth > 0.0)[0]
        if not len(contact):
            return target.basis, 0, ""

        normals = target.normals
        disp = -normals * depth[:, None]

        if settings.bulge > 0.0 and settings.bulge_radius > 0.0:
            bulge = self.bulge(depth, contact, weights, settings.bulge_radius)
            disp += normals * (bulge * settings.bulge)[:, None]

        disp = target.smooth(
            disp,
            settings.smooth_iterations,
            contact,
            -normals[contact],
            depth[contact],
            settings.keep_contact,
        )
        disp = target.relax(disp, settings.relax_iterations, settings.relax_factor)

        self.influence = None
        if settings.auto_influence:
            self.influence = target.influence(self._depth[0], contact, settings.influence_radius)
            disp *= self.influence[:, None]

        disp *= (settings.factor * weights)[:, None]

        if settings.rigid_group:
            islands = target.rigid_islands(settings.rigid_group)
            if islands is None:
                return target.basis, 0, "Rigid Vertex Group not found"
            disp = target.rigidify(disp, islands)

        self.disp = disp
        return target.local(disp), len(contact), ""


class MustardUI_ToolsCreators_Squish(ShapeKeyPreviewOperator, bpy.types.Operator):
    """Create a Shape Key on the Active Object squished by the other selected Objects (e.g.
    clothes, straps, hands), with a live preview.\nThe Rest Pose of the models is used"""

    bl_idname = "mustardui.tools_creators_squish"
    bl_label = "Create Squish Shape Key"
    bl_options = {"REGISTER", "UNDO"}

    preview_tool = "SQUISH"
    preview_verb = "squished"

    @classmethod
    def poll(cls, context):
        if preview_running():
            return False
        obj = context.active_object
        if obj is None or obj.type != "MESH" or obj.mode != "OBJECT":
            return False
        return any(x != obj and x.type in SQUISH_CREATOR_TYPES for x in context.selected_objects)

    def preview_settings(self, context):
        return context.window_manager.MustardUI_ToolsCreators_SquishSettings

    def solver(self, context):
        settings = self.preview_settings(context)
        body = context.active_object
        creators = [
            x for x in context.selected_objects if x != body and x.type in SQUISH_CREATOR_TYPES
        ]
        name = settings.shape_key_name.strip()

        if not name:
            self.report({"ERROR"}, "MustardUI - Choose a Shape Key name")
            return None

        if body.data.shape_keys is not None and body.data.shape_keys.reference_key.name == name:
            self.report({"ERROR"}, "MustardUI - The Basis Shape Key can not be overwritten")
            return None

        return SquishSolver(context, body, creators, name)

    def execute(self, context):
        settings = self.preview_settings(context)
        solver = self.solver(context)
        if solver is None:
            return {"CANCELLED"}

        shape_co, contact, error = solver.solve(context, settings)
        if error:
            self.report({"ERROR"}, f"MustardUI - {error}")
            return {"CANCELLED"}
        if not contact:
            self.report({"WARNING"}, "MustardUI - No vertex is squished by the selected Objects")
            return {"CANCELLED"}

        sk = write_shape_key(solver.body, settings.shape_key_name.strip(), shape_co)
        if solver.influence is not None:
            write_vertex_group(solver.body, sk.name, solver.influence)
        create_children_shape_keys(solver, settings, solver.body, sk.name)
        self.report({"INFO"}, f"MustardUI - Shape Key '{sk.name}' created ({contact} vertices)")
        return {"FINISHED"}

    def invoke(self, context, event):
        settings = self.preview_settings(context)
        creators = [
            x.name
            for x in context.selected_objects
            if x != context.active_object and x.type in SQUISH_CREATOR_TYPES
        ]
        settings.shape_key_name = f"Squish - {', '.join(sorted(creators))}"

        solver = self.solver(context)
        if solver is None:
            return {"CANCELLED"}

        return self.preview_start(context, solver.body, settings.shape_key_name.strip(), solver)


def squish_draw_settings(layout, context):
    """Draw the settings of the running preview"""

    session = preview_session("SQUISH")
    if session is None:
        return
    settings = context.window_manager.MustardUI_ToolsCreators_SquishSettings

    box = layout.box()
    col = box.column()
    col.use_property_split = True
    col.use_property_decorate = False

    col.prop(settings, "shape_key_name")
    col.prop(settings, "mode")
    col.prop(settings, "use_modifiers")
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
    row = sub.row(align=True)
    row.enabled = settings.mode == "SURFACE"
    row.prop(settings, "tightness")
    sub.prop(settings, "max_depth")

    col.separator()
    sub = col.column(align=True)
    sub.prop(settings, "bulge")
    row = sub.row(align=True)
    row.enabled = settings.bulge > 0.0
    row.prop(settings, "bulge_radius")

    col.separator()
    sub = col.column(align=True)
    sub.prop(settings, "smooth_iterations")
    row = sub.row(align=True)
    row.enabled = settings.smooth_iterations > 0
    row.prop(settings, "keep_contact")

    col.separator()
    sub = col.column(align=True)
    sub.prop(settings, "relax_iterations")
    row = sub.row(align=True)
    row.enabled = settings.relax_iterations > 0
    row.prop(settings, "relax_factor")

    preview_draw_footer(box, session)


def register():
    bpy.utils.register_class(MustardUI_ToolsCreators_SquishSettings)
    bpy.utils.register_class(MustardUI_ToolsCreators_Squish)

    bpy.types.WindowManager.MustardUI_ToolsCreators_SquishSettings = bpy.props.PointerProperty(
        type=MustardUI_ToolsCreators_SquishSettings
    )


def unregister():
    del bpy.types.WindowManager.MustardUI_ToolsCreators_SquishSettings

    bpy.utils.unregister_class(MustardUI_ToolsCreators_Squish)
    bpy.utils.unregister_class(MustardUI_ToolsCreators_SquishSettings)
