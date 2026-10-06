import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.interpolate import poly_3d_calc
from rna_prop_ui import rna_idprop_ui_create

from ... import __package__ as base_package
from ...custom_properties.misc import assign_ptr, mustardui_add_driver, mustardui_check_cp
from ...misc.mesh_deform import (
    DeformTarget,
    geometry_bvh,
    kdtree,
    mesh_vertex_normals,
    rest_geometry,
    smooth_deformation,
    write_vertex_group,
)
from ..mesh.shape_key_preview import (
    ShapeKeyPreviewOperator,
    create_followers_shape_keys,
    preview_draw_debug,
    preview_draw_footer,
    preview_draw_masks,
    preview_draw_presets,
    preview_draw_vertex_group,
    preview_preset_classes,
    preview_running,
    preview_section,
    preview_session,
    preview_settings_update,
    write_shape_key,
)

SQUISHER_TYPES = {"MESH", "CURVE", "SURFACE", "META", "FONT"}
SQUISH_ORIENTATION_DISTANCE = 0.1
# Body vertices checked at a time by the debug information
SQUISH_CHECK_CHUNK = 2000
# Depth allowed beyond the one of the closest squishing surface, see penetration
SQUISH_DEPTH_TOLERANCE = 0.002
# The Bulge settings scale these, for a visible bulge at their default values
BULGE_STRENGTH = 1.5
BULGE_RANGE = 1.5


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


class MustardUI_ModelToolkit_SquishSettings(bpy.types.PropertyGroup):
    shape_key_name: bpy.props.StringProperty(
        name="Shape Key",
        default="Squish",
        maxlen=63,
        description="Name of the Shape Key. If it already exists, it is overwritten",
    )

    outfit_property: bpy.props.BoolProperty(
        name="Outfit Property",
        default=False,
        description="Drive the Shape Key with a hidden custom property of the MustardUI "
        "Outfit of the squishing objects, switched on and off with the Outfit",
    )
    outfit_property_hidden: bpy.props.BoolProperty(
        name="Hidden",
        default=True,
        description="The custom property is added as a hidden property of the MustardUI",
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

    squishers_rigid_group: bpy.props.StringProperty(
        name="Squishers Rigid Vertex Group",
        description="Vertex Group of the rigid parts of the squishing objects (e.g. buttons), "
        "which are moved without deforming them",
        update=preview_settings_update,
    )

    invert_squishers_rigid_group: bpy.props.BoolProperty(
        name="Invert",
        default=False,
        description="Invert the Squishers Rigid Vertex Group weights",
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
        default=0.02,
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
        max=10.0,
        soft_max=1.0,
        description="Push the vertices around the squished area outwards, as the flesh "
        "displaced by the squishing objects.\nWith 1, the volume pushed in comes out around them",
        update=preview_settings_update,
    )

    bulge_radius: bpy.props.FloatProperty(
        name="Bulge Radius",
        default=0.05,
        min=0.0,
        soft_max=0.1,
        subtype="DISTANCE",
        description="Distance from the squished area affected by the bulge",
        update=preview_settings_update,
    )

    smooth_distance: bpy.props.FloatProperty(
        name="Smooth",
        default=0.005,
        min=0.0,
        soft_max=0.05,
        subtype="DISTANCE",
        description="Distance the squish is smoothed over, to blend it with the neighbouring "
        "surface.\nIt does not depend on the mesh density",
        update=preview_settings_update,
    )


SquishPresetsMenu, SquishPresetAdd = preview_preset_classes(
    "Squish",
    "Squish",
    MustardUI_ModelToolkit_SquishSettings,
    "MustardUI_ModelToolkit_SquishSettings",
)


class SquisherFollower:
    """Squishing object moved by the Tightness, into the body for surfaces, inflating volumes"""

    def __init__(self, obj, target, body_bvh, key_name):
        self.obj = obj
        self.body_bvh = body_bvh
        self.target = target
        self.mesh = DeformTarget(obj, key_name)
        self.basis = self.mesh.basis
        self._volume_normals = None
        self._inward = (None, None)

        # The body triangle under each vertex, to follow its squish
        co = self.mesh.co
        self.under = np.zeros((len(co), 3), dtype=np.int64)
        self.under_weights = np.zeros((len(co), 3))
        for i, c in enumerate(co):
            location, _, index, _ = body_bvh.find_nearest(Vector(c))
            if location is None:
                continue
            tri = target.tris[index]
            self.under[i] = tri
            self.under_weights[i] = poly_3d_calc([Vector(target.co[j]) for j in tri], location)

    def inward(self, distance):
        """Body normals under the vertices, averaged over the distance not to flip in its folds"""

        if self._inward[0] == distance:
            return self._inward[1]
        target = self.target
        normals = target.normals
        if distance > 0.0:
            normals = normals.copy()
            kd = target.kdtree()
            for i in np.unique(self.under):
                near = [j for _, j, _ in kd.find_range(target.co[i], distance)]
                normals[i] = target.normals[near].mean(axis=0)
        # Not normalized: shorter where the normals cancel out, as over the folds
        inward = -np.einsum("ijk,ij->ik", normals[self.under], self.under_weights)
        self._inward = (distance, inward)
        return inward

    def enabled(self, settings):
        return (
            settings.move_squishers
            and settings.tightness > 0.0
            and settings.squishers_movement > 0.0
        )

    def shape(self, solver, settings):
        if not self.enabled(settings):
            return self.basis

        amount = np.full(len(self.basis), settings.tightness * settings.squishers_movement)
        amount *= settings.factor
        if settings.mode == "VOLUME":
            if self._volume_normals is None:
                flipped = squisher_is_flipped(
                    self.mesh.co, self.mesh.tris, self.body_bvh, SQUISH_ORIENTATION_DISTANCE, True
                )
                self._volume_normals = self.mesh.normals * (-1.0 if flipped else 1.0)
            directions = self._volume_normals
        else:
            # Along the body normals, keeping the thickness of the double sided parts
            directions = self.inward(settings.smooth_distance)
            # Never deeper than the body under them, not to sink at their borders, and lifted
            # by its bulge
            if solver.disp is not None:
                under = np.einsum("ijk,ij->ik", solver.disp[self.under], self.under_weights)
                amount = np.minimum(amount, np.einsum("ij,ij->i", under, directions))
        disp = directions * amount[:, None]

        # Squishers without the Vertex Group are fully deformed
        if settings.squishers_rigid_group:
            islands = self.mesh.rigid_islands(
                settings.squishers_rigid_group, settings.invert_squishers_rigid_group
            )
            if islands is not None:
                disp = self.mesh.rigidify(disp, islands)
        return self.mesh.local(disp)


class SquishSolver:
    """Compute the squish Shape Key, caching the results not affected by the changed settings"""

    def __init__(self, body, squishers, key_name):
        self.body = body
        self.squishers = squishers
        # Set by the preview, to measure the result with check_steps
        self.check = False
        self.debug = []
        self.target = DeformTarget(body, key_name)
        self.body_bvh = BVHTree.FromPolygons(self.target.co.tolist(), self.target.tris.tolist())
        self.children = self.target.rigid_children(squishers)
        self.followers = self.children + [
            SquisherFollower(obj, self.target, self.body_bvh, key_name)
            for obj in squishers
            if obj.type == "MESH" and len(obj.data.vertices)
        ]
        self.disp = None

        self._geometry = {}
        self._bvh = (None, None)
        self._flipped = {}
        self._depth = (None, None)
        self._overriding = (None, [])
        self._smoothed = (None, None)
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

        bvh, squishers_co, _ = self.squishers_bvh(context, settings)
        if bvh is None:
            return None

        # Only check the vertices close to the squishers
        co = self.target.co
        normals = self.target.normals
        margin = settings.max_depth
        bb_min = squishers_co.min(axis=0) - margin
        bb_max = squishers_co.max(axis=0) + margin
        near = np.all((co >= bb_min) & (co <= bb_max), axis=1)
        candidates = np.flatnonzero(near & (weights > 0.0))

        depth = self.penetration(bvh, co, candidates, settings)
        covered = np.zeros(self.target.n_verts, dtype=bool)
        for i in candidates:
            # Vertices covered by the squishers are not moved outwards
            if depth[i] == 0.0:
                n = Vector(normals[i])
                if bvh.ray_cast(Vector(co[i]) + n * 1e-5, n, settings.max_depth)[0] is not None:
                    covered[i] = True

        self._covered = covered
        self._depth = (key, depth)
        return depth

    def penetration(self, bvh, co, indices, settings):
        """Depth of the vertices under the squishers, along the inverted body normal"""

        surface = settings.mode == "SURFACE"
        normals = self.target.normals
        depth = np.zeros(self.target.n_verts)
        eps = 1e-5
        for i in indices:
            v = Vector(co[i])
            n = Vector(normals[i])
            if not surface:
                nearest, nearest_normal, _, _ = bvh.find_nearest(v)
                if nearest is None or (v - nearest).dot(nearest_normal) > 0.0:
                    continue
            hit, hit_normal, _, dist = bvh.ray_cast(v + n * eps, -n, settings.max_depth + eps)
            if hit is None:
                continue
            # Surface: squisher facing as the body, Volume: exit face of the squisher
            facing = hit_normal.dot(n)
            if (surface and facing > 0.5) or (not surface and facing < 0.0):
                # Squishers on the other side of thin parts (e.g. fingers) are ignored
                through = self.body_bvh.ray_cast(v - n * 1e-4, -n, dist)
                if through[0] is not None and through[3] >= 0.002:
                    continue
                # Rays reaching far parts of the squishers (e.g. across folds or fingers) are
                # capped by the closest surface, at most twice as far with the facing above
                if surface:
                    near, near_normal, _, near_dist = bvh.find_nearest(v)
                    outside = (v - near).dot(near_normal) > 0.0
                    limit = 2.0 * near_dist if outside else 0.0
                    dist = min(dist, limit + settings.tightness + SQUISH_DEPTH_TOLERANCE)
                depth[i] = max(dist - eps + settings.offset, 0.0)
        return depth

    def bulge(self, depth, contact, weights, radius):
        """Bulge around the squished area, before the Bulge factor"""

        co = self.target.co
        bulge = np.zeros(self.target.n_verts)
        kd = kdtree(co[contact])

        bb_min = co[contact].min(axis=0) - radius
        bb_max = co[contact].max(axis=0) + radius
        near = np.all((co >= bb_min) & (co <= bb_max), axis=1) & (weights > 0.0) & (depth == 0.0)
        for i in np.nonzero(near & ~self._covered)[0]:
            hits = kd.find_n(co[i], 8)
            if hits[0][2] >= radius:
                continue
            # Rising from the squished area, peaking at a third of the radius
            t = hits[0][2] / radius
            pushed = sum(depth[contact[k]] for _, k, _ in hits) / len(hits)
            bulge[i] = pushed * 6.75 * t * (1.0 - t) ** 2

        # Evened out only in its band, cheap even on dense meshes
        band = bulge > 0.0
        edges = self.target.edges
        inside = edges[band[edges[:, 0]] & band[edges[:, 1]]]
        if len(inside):
            length = np.mean(np.linalg.norm(co[inside[:, 0]] - co[inside[:, 1]], axis=1))
            bulge = smooth_deformation(bulge[:, None], edges, max(length, 1e-6), radius / 3.0, band)
            bulge = bulge[:, 0]

        # Rolls rather than ridges
        return np.minimum(bulge, radius / 2.0)

    def solve(self, context, settings):
        """Return the Shape Key coordinates, the number of squished vertices and the error"""

        target = self.target
        self.disp = None
        self.debug = []
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
        smooth_distance = settings.smooth_distance

        # The slow steps are cached, for the settings changed after them
        key = (self._depth[0], smooth_distance)
        if self._smoothed[0] != key:
            smoothed = target.smooth(
                -normals * depth[:, None],
                smooth_distance,
                contact,
                -normals[contact],
                depth[contact],
            )
            self._smoothed = (key, smoothed)
        disp = self._smoothed[1].copy()

        # After the smoothing, which would flatten it
        if settings.bulge > 0.0 and settings.bulge_radius > 0.0:
            radius = settings.bulge_radius * BULGE_RANGE
            key = (self._depth[0], radius)
            if self._bulge[0] != key:
                self._bulge = (key, self.bulge(depth, contact, weights, radius))
            disp += normals * (self._bulge[1] * settings.bulge * BULGE_STRENGTH)[:, None]

        # Vertices covered by the squishers are only pushed inwards
        outwards = np.maximum(np.einsum("ij,ij->i", disp, normals), 0.0) * self._covered
        disp -= normals * outwards[:, None]

        self.influence = None
        if settings.auto_influence:
            self.influence = target.influence(self._depth[0], contact, settings.influence_radius)
            disp *= self.influence[:, None]

        # Push again under the squishers the vertices moved out of them by the smoothing
        bvh = self.squishers_bvh(context, settings)[0]
        moved = np.nonzero((np.linalg.norm(disp, axis=1) > 0.0) & (weights > 0.0))[0]
        pushed_again = np.zeros(target.n_verts)
        for _ in range(3):
            again = self.penetration(bvh, target.co + disp, moved, settings)
            # Rays from pushed vertices reach other layers: squished ones keep their depth,
            # the others stay within the deepest one
            pushed = -np.einsum("ij,ij->i", disp, normals)
            kept = np.maximum(depth + SQUISH_DEPTH_TOLERANCE - pushed, 0.0)
            again = np.minimum(again, np.where(depth > 0.0, kept, depth.max()))
            if not np.any(again > 0.0):
                break
            disp -= normals * again[:, None]
            pushed_again += again

        disp *= (settings.factor * weights)[:, None]

        if settings.rigid_group:
            islands = target.rigid_islands(settings.rigid_group, settings.invert_rigid_group)
            if islands is None:
                return target.basis, 0, "Rigid Vertex Group not found"
            disp = target.rigidify(disp, islands)

        self.disp = disp
        moved = np.linalg.norm(disp, axis=1)
        self.debug = [
            ("Max Depth", f"{depth.max() * 1000:.1f} mm"),
            (
                "Pushed Again",
                f"{np.count_nonzero(pushed_again)} ({pushed_again.max() * 1000:.1f} mm)",
            ),
            ("Moved Vertices", str(np.count_nonzero(moved > 1e-4))),
            ("Max Movement", f"{moved.max() * 1000:.1f} mm"),
            ("Left to Squish", "..."),
        ]
        return target.local(disp), len(contact), ""

    def check_steps(self, context, settings):
        """Count the vertices left to squish by the last squish, a bit at a time"""

        target = self.target
        co = target.co + self.disp
        bvh, squishers_co, _ = self.squishers_bvh(context, settings)
        near = np.all(
            (co >= squishers_co.min(axis=0) - 0.01) & (co <= squishers_co.max(axis=0) + 0.01),
            axis=1,
        )
        # Still out of the squishing surfaces, or inside the squishing volumes
        surface = settings.mode == "SURFACE"
        left = 0
        for k, i in enumerate(np.nonzero(near)[0]):
            if k % SQUISH_CHECK_CHUNK == 0:
                yield
            v = Vector(co[i])
            hit, normal, _, dist = bvh.find_nearest(v, 0.02)
            if hit is None or dist < 0.0005 or ((v - hit).dot(normal) > 0.0) != surface:
                continue
            left += not surface or normal.dot(Vector(target.normals[i])) > 0.5
        self.debug[-1] = ("Left to Squish", str(left))

    def overriding_modifiers(self):
        """Surface Deform modifiers of the body hiding the squish"""

        if self.disp is None:
            return []
        if self._overriding[0] is not self.disp:
            squished = np.linalg.norm(self.disp, axis=1) > 1e-5
            names = []
            for m in self.body.modifiers:
                if m.type != "SURFACE_DEFORM" or not m.show_viewport or m.target is None:
                    continue
                weights = self.target.weights(m.vertex_group, m.invert_vertex_group)
                if weights is None or np.any(weights[squished] > 0.0):
                    names.append(m.name)
            self._overriding = (self.disp, names)
        return self._overriding[1]


class MustardUI_ModelToolkit_Squish(ShapeKeyPreviewOperator, bpy.types.Operator):
    """Create a Shape Key on the Active Object squished by the other selected Objects (e.g. clothes, straps, hands), with a live preview.\nThe Rest Pose of the models is used"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_squish"
    bl_label = "Add Squish"
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
        return context.window_manager.MustardUI_ModelToolkit_SquishSettings

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

        return SquishSolver(body, squishers, name)

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
        if settings.outfit_property:
            squish_outfit_property(context, solver, sk.name, hidden=settings.custom_property_hidden)
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

    def preview_finish(self, context, session):
        message = super().preview_finish(context, session)
        if session.settings.outfit_property:
            name = session.settings.shape_key_name.strip() or session.key_name
            squish_outfit_property(
                context, session.solver, name, hidden=session.settings.outfit_property_hidden
            )
        return message


def squish_outfit(body, squishers):
    """Model and Outfit of the squishers, (None, None) if not in one"""

    arm = next(
        (
            x
            for x in bpy.data.armatures
            if x.MustardUI_created and x.MustardUI_RigSettings.model_body == body
        ),
        None,
    )
    if arm is None or not squishers:
        return None, None

    rig_settings = arm.MustardUI_RigSettings
    outfits = [x.collection for x in rig_settings.outfits_collections]
    for outfit in [*outfits, rig_settings.extras_collection]:
        if outfit is None:
            continue
        items = outfit.all_objects if rig_settings.outfit_config_subcollections else outfit.objects
        if set(squishers) <= set(items):
            return arm, outfit
    return None, None


def squish_outfit_property(context, solver, key_name, hidden=True):
    """Drive the Shape Key with a hidden Outfit custom property, on when the Outfit is shown"""

    arm, outfit = squish_outfit(solver.body, solver.squishers)
    if arm is None:
        return

    key = solver.body.data.shape_keys
    rna = f'bpy.data.shape_keys["{bpy.utils.escape_identifier(key.name)}"]'
    rna += f'.key_blocks["{bpy.utils.escape_identifier(key_name)}"]'
    if not mustardui_check_cp(arm, rna, "value"):
        return

    prop_name = key_name
    number = 1
    while prop_name in arm.keys():
        number += 1
        prop_name = f"{key_name} {number}"

    piece = solver.squishers[0] if len(solver.squishers) == 1 else None
    shown = any(not x.hide_viewport for x in solver.squishers)
    rna_idprop_ui_create(arm, prop_name, default=0.0, min=0.0, max=1.0, overridable=True)
    arm[prop_name] = 1.0 if shown else 0.0
    mustardui_add_driver(arm, rna, "value", prop_name, 0)

    cp = arm.MustardUI_CustomPropertiesOutfit.add()
    cp.rna = rna
    cp.path = "value"
    cp.name = "Squish"
    cp.prop_name = prop_name
    cp.type = "FLOAT"
    cp.subtype = key.key_blocks[key_name].bl_rna.properties["value"].subtype
    cp.icon = "SHAPEKEY_DATA"
    cp.is_animatable = True
    cp.hidden = hidden
    cp.cp_type = "OUTFIT"
    cp.outfit = outfit
    cp.outfit_piece = piece
    cp.outfit_enable_on_switch = True
    cp.outfit_enable_value = "MAX"
    cp.outfit_disable_on_switch = True
    cp.outfit_disable_value = "MIN"
    cp.min_float = 0.0
    cp.max_float = 1.0
    assign_ptr(cp, rna, context.preferences.addons[base_package].preferences)
    arm.update_tag()


def squish_draw_settings(layout, context):
    """Draw the settings of the running preview"""

    session = preview_session("SQUISH")
    if session is None:
        return
    settings = session.settings

    box = layout.box()
    preview_draw_presets(box, SquishPresetsMenu, SquishPresetAdd)
    col = box.column()
    col.use_property_split = True
    col.use_property_decorate = False
    col.prop(settings, "factor", text="Strength")

    col = preview_section(box, "mustardui_squish_output", "Output", "SHAPEKEY_DATA")
    if col is not None:
        col.prop(settings, "shape_key_name")
        row = col.row()
        row.enabled = squish_outfit(session.solver.body, session.solver.squishers)[0] is not None
        row.prop(settings, "outfit_property")

        row2 = row.row()
        row2.enabled = settings.outfit_property
        row2.prop(settings, "outfit_property_hidden")

    col = preview_section(box, "mustardui_squish_squishing", "Squishing", "MOD_SHRINKWRAP")
    if col is not None:
        col.prop(settings, "mode")
        col.prop(settings, "use_modifiers", text="Squishers Modifiers")

        col.separator()

        col.prop(settings, "tightness", text="Tightness (Pressure)")
        sub = col.column(align=True)
        sub.enabled = settings.tightness > 0.0
        sub.prop(settings, "move_squishers")
        row = sub.row(align=True)
        row.enabled = settings.move_squishers
        row.prop(settings, "squishers_movement", text="Movement")

        col.separator()

        col.prop(settings, "max_depth")
        col.prop(settings, "offset")

    col = preview_section(box, "mustardui_squish_shape", "Shape", "MOD_SMOOTH")
    if col is not None:
        sub = col.column(align=True)
        sub.prop(settings, "bulge")
        row = sub.row(align=True)
        row.enabled = settings.bulge > 0.0
        row.prop(settings, "bulge_radius", text="Radius")
        col.prop(settings, "smooth_distance")

    # The squishers rigid parts only matter when they are moved
    follower = next((x for x in session.solver.followers if isinstance(x, SquisherFollower)), None)
    moving = follower is not None and follower.enabled(settings)
    col = preview_draw_masks(
        box, session, "squish", moving and bool(settings.squishers_rigid_group)
    )
    if col is not None and follower is not None:
        sub = col.column()
        sub.enabled = moving
        preview_draw_vertex_group(
            sub,
            settings,
            "squishers_rigid_group",
            "invert_squishers_rigid_group",
            follower.obj,
            "Squishers",
        )

    rows = [("Squished Vertices", str(session.count)), ("Time", f"{session.elapsed:.2f} s")]
    preview_draw_debug(box, "squish", rows + session.solver.debug)

    overriding = session.solver.overriding_modifiers()
    if overriding:
        col = box.column(align=True)
        col.label(text="Hidden by Surface Deform modifiers:", icon="ERROR")
        for name in overriding:
            col.label(text=name, icon="MOD_MESHDEFORM")

    preview_draw_footer(box, session, info=False)


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_SquishSettings)
    bpy.utils.register_class(MustardUI_ModelToolkit_Squish)
    bpy.utils.register_class(SquishPresetsMenu)
    bpy.utils.register_class(SquishPresetAdd)

    bpy.types.WindowManager.MustardUI_ModelToolkit_SquishSettings = bpy.props.PointerProperty(
        type=MustardUI_ModelToolkit_SquishSettings
    )


def unregister():
    del bpy.types.WindowManager.MustardUI_ModelToolkit_SquishSettings

    bpy.utils.unregister_class(SquishPresetAdd)
    bpy.utils.unregister_class(SquishPresetsMenu)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_Squish)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_SquishSettings)
