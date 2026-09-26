import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

from ...misc.mesh_deform import (
    DeformTarget,
    geometry_bvh,
    mesh_triangles,
    mesh_vertex_normals,
    rest_coordinates,
    rest_geometry,
    write_vertex_group,
)
from .shape_key_preview import (
    ShapeKeyPreviewOperator,
    create_followers_shape_keys,
    preview_draw_footer,
    preview_draw_presets,
    preview_preset_classes,
    preview_running,
    preview_session,
    preview_settings_update,
    write_shape_key,
)

SQUISHER_TYPES = {"MESH", "CURVE", "SURFACE", "META", "FONT"}
SQUISH_ORIENTATION_DISTANCE = 0.1


def squisher_is_flipped(co, tris, body_bvh, max_dist, volume):
    """Check if the squisher normals point inwards, as they often do in clothes"""

    p0, p1, p2 = co[tris[:, 0]], co[tris[:, 1]], co[tris[:, 2]]
    face_normals = np.cross(p1 - p0, p2 - p0)

    # Volume: sign of the enclosed volume
    if volume:
        center = co.mean(axis=0)
        return np.einsum("ij,ij->", p0 - center, face_normals) < 0.0

    # Surface: the squisher should face as the closest body surface
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
                "The body vertices poking out of the squishing surface are pushed under it (e.g. "
                "clothes, straps)",
            ),
            (
                "VOLUME",
                "Volume",
                "The body vertices inside the squishing volume are pushed out of it (e.g. hands, "
                "closed objects pressing on the body)",
            ),
        ),
        default="SURFACE",
        update=preview_settings_update,
    )

    use_modifiers: bpy.props.BoolProperty(
        name="Use Modifiers",
        default=True,
        description="Use the squishing objects with their modifiers evaluated",
        update=preview_settings_update,
    )

    vertex_group: bpy.props.StringProperty(
        name="Vertex Group",
        description="Restrict the effect to this Vertex Group of the body",
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

    move_squishers: bpy.props.BoolProperty(
        name="Move Squishers",
        default=True,
        description="Move also the squishing objects by the Tightness, with Shape Keys driven "
        "by the squish one, so that they stay on the squished body",
        update=preview_settings_update,
    )

    squishers_movement: bpy.props.FloatProperty(
        name="Squishers Movement",
        default=0.75,
        min=0.0,
        max=1.0,
        subtype="FACTOR",
        description="Fraction of the Tightness the squishing objects are moved by.\nThe body "
        "is squished by the whole Tightness, so lower values keep the squishing objects "
        "slightly over the squished body, avoiding clipping",
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
        description="Additional distance of the squished vertices from the squishing surface",
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
        description="Move each vertex of the squishing objects along its normal by this "
        "distance, into the body for Surface and inflating for Volume.\nUseful to squish "
        "objects resting on the body without intersecting it (e.g. fitted clothes)",
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
        soft_max=2.0,
        description="Push the vertices around the squished area outwards, as the flesh "
        "displaced by the squishing objects",
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
        description="Keep the squished vertices under the squishing objects while smoothing",
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


SquishPresetsMenu, SquishPresetAdd = preview_preset_classes(
    "Squish",
    "Squish",
    MustardUI_ToolsCreators_SquishSettings,
    "MustardUI_ToolsCreators_SquishSettings",
)


class SquisherFollower:
    """Squishing object moved along its normals by the Tightness"""

    def __init__(self, obj, body_bvh, key_name):
        self.obj = obj
        self.body_bvh = body_bvh
        self.basis, self.co, self.mat3_inv = rest_coordinates(obj, key_name)
        self.tris = mesh_triangles(obj.data)
        self._directions = {}

    def directions(self, mode):
        """Local directions moving the vertices into the body, or inflating the volume"""

        if mode not in self._directions:
            volume = mode == "VOLUME"
            flipped = squisher_is_flipped(
                self.co, self.tris, self.body_bvh, SQUISH_ORIENTATION_DISTANCE, volume
            )
            normals = mesh_vertex_normals(self.co, self.tris)
            normals *= (-1.0 if flipped else 1.0) * (1.0 if volume else -1.0)
            self._directions[mode] = normals @ self.mat3_inv.T
        return self._directions[mode]

    def enabled(self, settings):
        return (
            settings.move_squishers
            and settings.tightness > 0.0
            and settings.squishers_movement > 0.0
        )

    def shape(self, solver, settings):
        if not self.enabled(settings):
            return self.basis
        amount = settings.tightness * settings.squishers_movement * settings.factor
        return self.basis + self.directions(settings.mode) * amount


class SquishSolver:
    """Compute the squish Shape Key, caching the results not affected by the changed settings"""

    def __init__(self, context, body, squishers, key_name):
        self.body = body
        self.squishers = squishers
        self.target = DeformTarget(body, key_name)
        self.body_bvh = BVHTree.FromPolygons(self.target.co.tolist(), self.target.tris.tolist())
        self.children = self.target.rigid_children(squishers)
        self.followers = self.children + [
            SquisherFollower(obj, self.body_bvh, key_name)
            for obj in squishers
            if obj.type == "MESH" and len(obj.data.vertices)
        ]
        self.disp = None

        self._geometry = {}
        self._bvh = (None, None)
        self._flipped = {}
        self._depth = (None, None)
        self._bulge = (None, None)
        self._covered = None
        self.influence = None

    def squishers_bvh(self, context, settings):
        key = (settings.use_modifiers, settings.mode, settings.tightness)
        if self._bvh[0] == key:
            return self._bvh[1]

        if settings.use_modifiers not in self._geometry:
            self._geometry[settings.use_modifiers] = rest_geometry(
                context,
                self.squishers,
                [self.body],
                settings.use_modifiers,
                self.target.key_name,
            )
        geometry = self._geometry[settings.use_modifiers]
        volume = settings.mode == "VOLUME"
        flips_key = (settings.use_modifiers, settings.mode)
        if flips_key not in self._flipped:
            self._flipped[flips_key] = [
                squisher_is_flipped(co, tri, self.body_bvh, SQUISH_ORIENTATION_DISTANCE, volume)
                for co, tri in geometry
            ]
        flipped = self._flipped[flips_key]

        # Move each vertex along its normal: into the body for surfaces, inflating volumes
        if settings.tightness > 0.0:
            moved = []
            for (co, tri), flip in zip(geometry, flipped, strict=True):
                normals = mesh_vertex_normals(co, tri) * (-1.0 if flip else 1.0)
                moved.append((co + normals * settings.tightness * (1.0 if volume else -1.0), tri))
            geometry = moved

        self._bvh = (key, geometry_bvh(geometry, flipped))
        return self._bvh[1]

    def depth(self, context, settings, weights):
        """Penetration depth along the inverted body normal"""

        surface = settings.mode == "SURFACE"
        key = (
            settings.use_modifiers,
            settings.mode,
            settings.vertex_group,
            settings.invert_vertex_group,
            settings.offset,
            settings.tightness,
            settings.max_depth,
        )
        if self._depth[0] == key:
            return self._depth[1]

        bvh, squishers_co = self.squishers_bvh(context, settings)
        if bvh is None:
            return None

        # Only check the vertices close to the squishers
        co = self.target.co
        normals = self.target.normals
        margin = settings.max_depth
        bb_min = squishers_co.min(axis=0) - margin
        bb_max = squishers_co.max(axis=0) + margin
        candidates = np.nonzero(np.all((co >= bb_min) & (co <= bb_max), axis=1) & (weights > 0.0))[
            0
        ]

        depth = np.zeros(self.target.n_verts)
        covered = np.zeros(self.target.n_verts, dtype=bool)
        eps = 1e-5
        for i in candidates:
            v = Vector(co[i])
            n = Vector(normals[i])
            inside = True
            if not surface:
                nearest, nearest_normal, _, _ = bvh.find_nearest(v)
                inside = nearest is not None and (v - nearest).dot(nearest_normal) <= 0.0
            if inside:
                hit, hit_normal, _, dist = bvh.ray_cast(v + n * eps, -n, settings.max_depth + eps)
                # Surface: squisher facing as the body, Volume: exit face of the squisher
                if hit is not None:
                    facing = hit_normal.dot(n)
                    if (surface and facing > 0.5) or (not surface and facing < 0.0):
                        depth[i] = max(dist - eps + settings.offset, 0.0)
            if depth[i] > 0.0:
                continue

            # Vertices covered by the squishers are not moved outwards
            if bvh.ray_cast(v + n * eps, n, settings.max_depth)[0] is not None:
                covered[i] = True

        self._covered = covered
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
        weights = target.weights(settings.vertex_group, settings.invert_vertex_group)
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

        # Vertices covered by the squishers are only pushed inwards
        outwards = np.maximum(np.einsum("ij,ij->i", disp, normals), 0.0) * self._covered
        disp -= normals * outwards[:, None]

        self.influence = None
        if settings.auto_influence:
            self.influence = target.influence(self._depth[0], contact, settings.influence_radius)
            disp *= self.influence[:, None]

        disp *= (settings.factor * weights)[:, None]

        if settings.rigid_group:
            islands = target.rigid_islands(settings.rigid_group, settings.invert_rigid_group)
            if islands is None:
                return target.basis, 0, "Rigid Vertex Group not found"
            disp = target.rigidify(disp, islands)

        self.disp = disp
        return target.local(disp), len(contact), ""


class MustardUI_ToolsCreators_Squish(ShapeKeyPreviewOperator, bpy.types.Operator):
    """Create a Shape Key on the Active Object squished by the other selected Objects (e.g. clothes, straps, hands), with a live preview.\nThe Rest Pose of the models is used"""  # noqa: E501

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
        return any(x != obj and x.type in SQUISHER_TYPES for x in context.selected_objects)

    def preview_settings(self, context):
        return context.window_manager.MustardUI_ToolsCreators_SquishSettings

    def solver(self, context):
        settings = self.preview_settings(context)
        body = context.active_object
        squishers = [x for x in context.selected_objects if x != body and x.type in SQUISHER_TYPES]
        name = settings.shape_key_name.strip()

        if not name:
            self.report({"ERROR"}, "MustardUI - Choose a Shape Key name")
            return None

        if body.data.shape_keys is not None and body.data.shape_keys.reference_key.name == name:
            self.report({"ERROR"}, "MustardUI - The Basis Shape Key can not be overwritten")
            return None

        return SquishSolver(context, body, squishers, name)

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
        create_followers_shape_keys(solver, settings, solver.body, sk.name)
        self.report({"INFO"}, f"MustardUI - Shape Key '{sk.name}' created ({contact} vertices)")
        return {"FINISHED"}

    def invoke(self, context, event):
        settings = self.preview_settings(context)
        squishers = [
            x.name
            for x in context.selected_objects
            if x != context.active_object and x.type in SQUISHER_TYPES
        ]
        settings.shape_key_name = f"Squish - {', '.join(sorted(squishers))}"

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
    preview_draw_presets(box, SquishPresetsMenu, SquishPresetAdd)
    col = box.column()
    col.use_property_split = True
    col.use_property_decorate = False

    col.prop(settings, "shape_key_name")
    col.prop(settings, "mode")
    col.prop(settings, "use_modifiers")
    for group, invert in (
        ("vertex_group", "invert_vertex_group"),
        ("rigid_group", "invert_rigid_group"),
    ):
        row = col.row(align=True)
        row.prop_search(settings, group, session.obj, "vertex_groups")
        sub = row.row(align=True)
        sub.enabled = bool(getattr(settings, group))
        sub.prop(settings, invert, text="", icon="ARROW_LEFTRIGHT")
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
    sub.prop(settings, "tightness")
    row = sub.row(align=True)
    row.enabled = settings.tightness > 0.0
    row.prop(settings, "move_squishers")
    row = sub.row(align=True)
    row.enabled = settings.tightness > 0.0 and settings.move_squishers
    row.prop(settings, "squishers_movement")
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
    bpy.utils.register_class(SquishPresetsMenu)
    bpy.utils.register_class(SquishPresetAdd)

    bpy.types.WindowManager.MustardUI_ToolsCreators_SquishSettings = bpy.props.PointerProperty(
        type=MustardUI_ToolsCreators_SquishSettings
    )


def unregister():
    del bpy.types.WindowManager.MustardUI_ToolsCreators_SquishSettings

    bpy.utils.unregister_class(SquishPresetAdd)
    bpy.utils.unregister_class(SquishPresetsMenu)
    bpy.utils.unregister_class(MustardUI_ToolsCreators_Squish)
    bpy.utils.unregister_class(MustardUI_ToolsCreators_SquishSettings)
