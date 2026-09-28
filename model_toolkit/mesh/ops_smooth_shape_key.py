import bpy
import numpy as np
from mathutils.kdtree import KDTree

from ...misc.mesh_deform import mesh_triangles, smooth_deformation, vertex_group_weights
from .shape_key_preview import (
    ShapeKeyPreviewOperator,
    preview_draw_footer,
    preview_draw_vertex_group,
    preview_running,
    preview_session,
    preview_settings_update,
    preview_show_result,
)


class MustardUI_ModelToolkit_SmoothShapeKeySettings(bpy.types.PropertyGroup):
    mode: bpy.props.EnumProperty(
        name="Mode",
        items=(
            (
                "DEFORMATION",
                "Deformation",
                "Smooth the movement of the Shape Key, keeping the details of the mesh",
            ),
            (
                "SHAPE",
                "Shape",
                "Smooth the shape of the mesh where the Shape Key moves it, removing the "
                "roughness of the mesh (e.g. irregular topology), but also its details",
            ),
        ),
        default="DEFORMATION",
        update=preview_settings_update,
    )

    smooth_distance: bpy.props.FloatProperty(
        name="Smooth",
        default=0.03,
        min=0.0,
        max=1.0,
        soft_max=0.1,
        subtype="DISTANCE",
        description="Distance the Shape Key deformation is smoothed over.\nIt does not depend "
        "on the mesh density",
        update=preview_settings_update,
    )

    factor: bpy.props.FloatProperty(
        name="Strength",
        default=1.0,
        min=0.0,
        max=1.0,
        subtype="FACTOR",
        description="Blend between the original and the smoothed Shape Key",
        update=preview_settings_update,
    )

    keep_borders: bpy.props.BoolProperty(
        name="Keep Borders",
        default=True,
        description="Do not change the Shape Key on the open borders of the mesh (e.g. the "
        "hems of the clothes), fading in the smoothing from them",
        update=preview_settings_update,
    )

    border_distance: bpy.props.FloatProperty(
        name="Border Distance",
        default=0.01,
        min=0.0,
        soft_max=0.05,
        subtype="DISTANCE",
        description="Distance from the borders where the smoothing fades in",
        update=preview_settings_update,
    )

    vertex_group: bpy.props.StringProperty(
        name="Vertex Group",
        description="Restrict the smoothing to this Vertex Group",
        update=preview_settings_update,
    )

    invert_vertex_group: bpy.props.BoolProperty(
        name="Invert",
        default=False,
        description="Invert the Vertex Group weights",
        update=preview_settings_update,
    )


class SmoothShapeKeySolver:
    """Smooth the deformation of a Shape Key, relative to its reference Shape Key"""

    def __init__(self, obj, key_name):
        self.obj = obj
        self.followers = []
        self.children = []
        self.influence = None
        self.disp = None

        key = obj.data.shape_keys.key_blocks[key_name]
        coordinates = []
        for sk in (key.relative_key, key):
            co = np.empty(len(sk.data) * 3, dtype=np.float32)
            sk.data.foreach_get("co", co)
            coordinates.append(co.reshape(-1, 3).astype(np.float64))
        self.relative = coordinates[0]
        self.delta = coordinates[1] - coordinates[0]
        # Shown when the result is hidden in the preview
        self.original = coordinates[1]

        edges = np.empty(len(obj.data.edges) * 2, dtype=np.int64)
        obj.data.edges.foreach_get("vertices", edges)
        self.edges = edges.reshape(-1, 2)

        # Edge length in world space, in the deformed area
        world = self.relative @ np.array(obj.matrix_world, dtype=np.float64)[:3, :3].T
        # Imported Shape Keys often move all the vertices by tiny amounts
        moving = np.linalg.norm(self.delta, axis=1) > 1e-5
        self.moving = moving
        edges = self.edges[moving[self.edges[:, 0]] | moving[self.edges[:, 1]]]
        lengths = np.linalg.norm(world[edges[:, 0]] - world[edges[:, 1]], axis=1)
        self.length = max(float(np.median(lengths)), 1e-6) if len(lengths) else 1e-6

        # Distance from the open borders, the edges of a single face
        tris = mesh_triangles(obj.data)
        pairs = np.sort(np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]]), axis=1)
        pairs, counts = np.unique(pairs, axis=0, return_counts=True)
        border = np.unique(pairs[counts == 1])
        self.border_distance = np.full(len(world), np.inf)
        if len(border):
            kd = KDTree(len(border))
            for k, i in enumerate(border):
                kd.insert(world[i], k)
            kd.balance()
            self.border_distance = np.array([kd.find(c)[2] for c in world])

    def solve(self, context, settings):
        """Return the Shape Key coordinates, the number of changed vertices and the error"""

        weights = vertex_group_weights(self.obj, settings.vertex_group)
        if weights is None:
            return self.relative + self.delta, 0, "Vertex Group not found"
        if settings.vertex_group and settings.invert_vertex_group:
            weights = 1.0 - weights

        distance = settings.smooth_distance
        if settings.mode == "SHAPE":
            # The deformed shape, only where the Shape Key moves it
            shape = smooth_deformation(
                self.original, self.edges, self.length, distance, self.moving
            )
            smoothed = shape - self.relative
        else:
            smoothed = smooth_deformation(self.delta, self.edges, self.length, distance)

        blend = settings.factor * weights
        if settings.keep_borders:
            radius = max(settings.border_distance, 1e-6)
            t = np.clip(self.border_distance / radius, 0.0, 1.0)
            blend = blend * t * t * (3.0 - 2.0 * t)
        delta = self.delta + (smoothed - self.delta) * blend[:, None]
        count = int(np.count_nonzero(np.abs(delta - self.delta).max(axis=1) > 1e-7))
        return self.relative + delta, count, ""


class MustardUI_ModelToolkit_SmoothShapeKey(ShapeKeyPreviewOperator, bpy.types.Operator):
    """Smooth the active Shape Key of the Active Object, with a live preview"""

    bl_idname = "mustardui.model_toolkit_smooth_shape_key"
    bl_label = "Smooth Shape Key"
    bl_options = {"REGISTER", "UNDO"}

    preview_tool = "SMOOTH_SHAPE_KEY"
    preview_verb = "smoothed"

    @classmethod
    def poll(cls, context):
        if preview_running():
            return False
        obj = context.active_object
        if obj is None or obj.type != "MESH" or obj.mode != "OBJECT":
            return False
        # Not the Basis Shape Key
        return obj.data.shape_keys is not None and obj.active_shape_key_index > 0

    def preview_settings(self, context):
        return context.window_manager.MustardUI_ModelToolkit_SmoothShapeKeySettings

    def execute(self, context):
        obj = context.active_object
        sk = obj.active_shape_key
        co, count, error = SmoothShapeKeySolver(obj, sk.name).solve(
            context, self.preview_settings(context)
        )
        if error:
            self.report({"ERROR"}, f"MustardUI - {error}")
            return {"CANCELLED"}

        sk.data.foreach_set("co", co.ravel())
        obj.data.update()
        self.report({"INFO"}, f"MustardUI - Shape Key '{sk.name}' smoothed ({count} vertices)")
        return {"FINISHED"}

    def invoke(self, context, event):
        obj = context.active_object
        sk = obj.active_shape_key
        return self.preview_start(context, obj, sk.name, SmoothShapeKeySolver(obj, sk.name))

    def preview_finish(self, context, session):
        # Keep the smoothed Shape Key, even if hidden, at its original value
        preview_show_result(session, True)
        sk = session.obj.data.shape_keys.key_blocks[session.key_name]
        sk.value = session.backup.backup[1]
        return f"Shape Key '{sk.name}' smoothed ({session.count} vertices)"


def smooth_shape_key_draw_settings(layout, context):
    """Draw the settings of the running preview"""

    session = preview_session("SMOOTH_SHAPE_KEY")
    if session is None:
        return
    settings = session.settings

    box = layout.box()
    col = box.column()
    col.use_property_split = True
    col.use_property_decorate = False
    col.label(text=session.key_name, icon="SHAPEKEY_DATA")
    col.row().prop(settings, "mode", expand=True)
    col.prop(settings, "smooth_distance")
    col.prop(settings, "factor")
    row = col.row(heading="Keep Borders", align=True)
    row.prop(settings, "keep_borders", text="")
    sub = row.row(align=True)
    sub.enabled = settings.keep_borders
    sub.prop(settings, "border_distance", text="")
    preview_draw_vertex_group(
        col, settings, "vertex_group", "invert_vertex_group", session.obj, "Vertex Group"
    )
    preview_draw_footer(box, session)


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_SmoothShapeKeySettings)
    bpy.utils.register_class(MustardUI_ModelToolkit_SmoothShapeKey)

    bpy.types.WindowManager.MustardUI_ModelToolkit_SmoothShapeKeySettings = (
        bpy.props.PointerProperty(type=MustardUI_ModelToolkit_SmoothShapeKeySettings)
    )


def unregister():
    del bpy.types.WindowManager.MustardUI_ModelToolkit_SmoothShapeKeySettings

    bpy.utils.unregister_class(MustardUI_ModelToolkit_SmoothShapeKey)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_SmoothShapeKeySettings)
