import bpy
import numpy as np
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

from ...misc.mesh_deform import mesh_triangles, smooth_deformation, vertex_group_weights
from .shape_key_preview import link_shape_key_driver


class MustardUI_ModelToolkit_TransferShapeKeys_Item(bpy.types.PropertyGroup):
    use: bpy.props.BoolProperty(name="Transfer", default=True)


class MUSTARDUI_UL_ModelToolkit_UIList_TransferShapeKeys(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.prop(item, "use", text="")
        row.label(text=item.name, icon="SHAPEKEY_DATA")


class MustardUI_ModelToolkit_TransferShapeKeys_Select(bpy.types.Operator):
    """Select or deselect all the Shape Keys in the list"""

    bl_idname = "mustardui.model_toolkit_transfer_shape_keys_select"
    bl_label = "Select Shape Keys"

    use: bpy.props.BoolProperty(default=True)

    def execute(self, context):
        for item in context.window_manager.MustardUI_ModelToolkit_TransferShapeKeys_Items:
            item.use = self.use
        return {"FINISHED"}


def transfer_targets(context):
    source = context.active_object
    return [
        o
        for o in context.selected_objects
        if o != source and o.type == "MESH" and source is not None and o.data != source.data
    ]


# Keep the Enum strings alive, as Blender does not store them
VERTEX_GROUP_ITEMS = []


def vertex_group_items(self, context):
    names = sorted({vg.name for o in transfer_targets(context) for vg in o.vertex_groups})
    VERTEX_GROUP_ITEMS[:] = [("NONE", "None", "Transfer to all the vertices")] + [
        (n, n, "") for n in names
    ]
    return VERTEX_GROUP_ITEMS


def mesh_rest_coordinates(obj):
    """Basis coordinates of the mesh, in local space"""

    mesh = obj.data
    # Read as float32, the fast path of foreach_get
    co = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    if mesh.shape_keys is not None:
        mesh.shape_keys.reference_key.data.foreach_get("co", co)
    else:
        mesh.vertices.foreach_get("co", co)
    return co.reshape(-1, 3).astype(np.float64)


def shape_key_coordinates(sk):
    co = np.empty(len(sk.data) * 3, dtype=np.float32)
    sk.data.foreach_get("co", co)
    return co.reshape(-1, 3).astype(np.float64)


def transfer_mapping(source_co, source_tris, target_co, method, max_distance):
    """Source vertex indices and weights for each target vertex, in world space"""

    n = len(target_co)
    indices = np.zeros((n, 3), dtype=np.int64)
    weights = np.zeros((n, 3), dtype=np.float64)
    distances = np.empty(n, dtype=np.float64)

    if method == "SURFACE" and len(source_tris):
        bvh = BVHTree.FromPolygons(source_co.tolist(), source_tris.tolist())
        locations = np.empty((n, 3), dtype=np.float64)
        faces = np.zeros(n, dtype=np.int64)
        for i, co in enumerate(target_co):
            loc, _, face, dist = bvh.find_nearest(co)
            locations[i] = loc
            faces[i] = face
            distances[i] = dist
        indices = source_tris[faces]

        # Barycentric weights of the closest points on the triangles
        a = source_co[indices[:, 0]]
        v0 = source_co[indices[:, 1]] - a
        v1 = source_co[indices[:, 2]] - a
        v2 = locations - a
        d00 = np.einsum("ij,ij->i", v0, v0)
        d01 = np.einsum("ij,ij->i", v0, v1)
        d11 = np.einsum("ij,ij->i", v1, v1)
        d20 = np.einsum("ij,ij->i", v2, v0)
        d21 = np.einsum("ij,ij->i", v2, v1)
        denom = d00 * d11 - d01 * d01
        degenerate = np.abs(denom) < 1e-20
        denom[degenerate] = 1.0
        v = (d11 * d20 - d01 * d21) / denom
        w = (d00 * d21 - d01 * d20) / denom
        weights = np.clip(np.stack([1.0 - v - w, v, w], axis=1), 0.0, 1.0)
        weights[degenerate] = 1.0 / 3.0
        weights /= np.maximum(weights.sum(axis=1), 1e-12)[:, None]
    else:
        kd = KDTree(len(source_co))
        for i, co in enumerate(source_co):
            kd.insert(co, i)
        kd.balance()
        for i, co in enumerate(target_co):
            _, index, dist = kd.find(co)
            indices[i, 0] = index
            distances[i] = dist
        weights[:, 0] = 1.0

    if max_distance > 0.0:
        weights[distances > max_distance] = 0.0

    return indices, weights


def transfer_shape_keys(source, targets, keys, **kwargs):
    """Transfer the Shape Keys of the source to the targets, returning the number of the
    Shape Keys written"""

    steps = transfer_shape_keys_steps(source, targets, keys, **kwargs)
    while True:
        try:
            next(steps)
        except StopIteration as stop:
            return stop.value


def transfer_shape_keys_steps(
    source,
    targets,
    keys,
    method="SURFACE",
    max_distance=0.0,
    smooth=0.0,
    threshold=0.0001,
    overwrite=False,
    vertex_group="NONE",
    invert_vertex_group=False,
    link=True,
):
    """Transfer the Shape Keys like transfer_shape_keys, yielding the fraction of the Shape
    Keys done"""

    source_sks = source.data.shape_keys
    source_mat = np.array(source.matrix_world, dtype=np.float64)
    source_basis = mesh_rest_coordinates(source)
    source_co = source_basis @ source_mat[:3, :3].T + source_mat[:3, 3]
    source_tris = mesh_triangles(source.data)

    # Source points for each target vertex
    mappings = []
    for target in targets:
        mesh = target.data
        if len(mesh.vertices) == 0:
            continue

        target_mat = np.array(target.matrix_world, dtype=np.float64)
        target_basis = mesh_rest_coordinates(target)
        target_co = target_basis @ target_mat[:3, :3].T + target_mat[:3, 3]
        to_local = np.linalg.inv(target_mat[:3, :3]).T

        indices, weights = transfer_mapping(source_co, source_tris, target_co, method, max_distance)

        edges = np.empty(len(mesh.edges) * 2, dtype=np.int64)
        mesh.edges.foreach_get("vertices", edges)
        edges = edges.reshape(-1, 2)
        lengths = np.linalg.norm(target_co[edges[:, 0]] - target_co[edges[:, 1]], axis=1)
        length = max(float(np.median(lengths)), 1e-6) if len(lengths) else 1e-6

        mask = None
        if vertex_group != "NONE" and vertex_group in target.vertex_groups:
            mask = vertex_group_weights(target, vertex_group)
            if invert_vertex_group:
                mask = 1.0 - mask

        mappings.append((target, target_basis, to_local, indices, weights, edges, length, mask))

    created = 0
    for index, sk in enumerate(keys):
        yield index / len(keys)
        relative = sk.relative_key
        if relative is None or relative == source_sks.reference_key:
            relative_co = source_basis
        else:
            relative_co = shape_key_coordinates(relative)
        source_delta = (shape_key_coordinates(sk) - relative_co) @ source_mat[:3, :3].T

        for target, target_basis, to_local, indices, weights, edges, length, mask in mappings:
            mesh = target.data
            existing = mesh.shape_keys.key_blocks.get(sk.name) if mesh.shape_keys else None
            if existing is not None and (
                not overwrite or existing == mesh.shape_keys.reference_key
            ):
                continue

            delta = np.einsum("ij,ijk->ik", weights, source_delta[indices])
            delta = smooth_deformation(delta, edges, length, smooth)
            if mask is not None:
                delta *= mask[:, None]

            # In world space, whatever the scale of the target
            if np.abs(delta).max() < threshold:
                # The overwritten key would keep a stale deformation
                if existing is not None:
                    existing.relative_key = mesh.shape_keys.reference_key
                    existing.data.foreach_set("co", target_basis.ravel())
                continue
            delta = delta @ to_local

            if mesh.shape_keys is None:
                target.shape_key_add(name="Basis", from_mix=False)
            new_sk = existing
            if new_sk is None:
                new_sk = target.shape_key_add(name=sk.name, from_mix=False)
            new_sk.relative_key = mesh.shape_keys.reference_key
            new_sk.data.foreach_set("co", (target_basis + delta).ravel())
            new_sk.slider_min = sk.slider_min
            new_sk.slider_max = sk.slider_max
            new_sk.interpolation = sk.interpolation
            if sk.vertex_group in target.vertex_groups:
                new_sk.vertex_group = sk.vertex_group

            new_sk.value = sk.value
            if link:
                link_shape_key_driver(target, new_sk.name, source, sk.name)

            created += 1

    for target, *_ in mappings:
        target.data.update()

    return created


class MustardUI_ModelToolkit_TransferShapeKeys(bpy.types.Operator):
    """Transfer the Shape Keys from the Active Object to the other selected Objects, using the closest points on its surface"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_transfer_shape_keys"
    bl_label = "Transfer Shape Keys"
    bl_options = {"UNDO"}

    method: bpy.props.EnumProperty(
        name="Method",
        items=(
            (
                "SURFACE",
                "Nearest Surface",
                "Interpolate the Shape Keys on the closest point of the source surface",
            ),
            (
                "VERTEX",
                "Nearest Vertex",
                "Copy the Shape Keys from the closest source vertex.\nUseful when the meshes "
                "share the same vertices",
            ),
        ),
        default="SURFACE",
    )

    max_distance: bpy.props.FloatProperty(
        name="Max Distance",
        default=0.0,
        min=0.0,
        soft_max=0.2,
        subtype="DISTANCE",
        description="Vertices farther than this from the source are not affected.\nSet to 0 "
        "to disable",
    )

    smooth: bpy.props.FloatProperty(
        name="Smooth",
        default=0.0,
        min=0.0,
        max=1.0,
        soft_max=0.1,
        subtype="DISTANCE",
        description="Distance the transferred Shape Keys are smoothed over, to reduce the "
        "artifacts on loose meshes (e.g. skirts).\nSet to 0 to disable",
    )

    threshold: bpy.props.FloatProperty(
        name="Threshold",
        default=0.0001,
        min=0.0,
        soft_max=0.001,
        step=0.001,
        precision=5,
        subtype="DISTANCE",
        description="Shape Keys moving the target less than this are not created",
    )

    overwrite: bpy.props.BoolProperty(
        name="Overwrite",
        default=False,
        description="Overwrite the Shape Keys already on the targets, resetting the ones below "
        "the threshold.\nIf disabled, they are skipped",
    )

    vertex_group: bpy.props.EnumProperty(
        name="Vertex Group",
        items=vertex_group_items,
        description="Restrict the Shape Keys to this Vertex Group of the targets.\nTargets "
        "without it are not restricted",
    )

    invert_vertex_group: bpy.props.BoolProperty(
        name="Invert",
        default=False,
        description="Invert the Vertex Group weights",
    )

    link: bpy.props.BoolProperty(
        name="Link to Source",
        default=True,
        description="Drive the values of the new Shape Keys with the source ones",
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj is None or obj.type != "MESH" or context.mode != "OBJECT":
            return False
        selected_objs = [x for x in context.selected_objects if x.type == "MESH"]
        return len(selected_objs) > 1

    def draw(self, context):
        wm = context.window_manager
        layout = self.layout

        row = layout.row()
        row.template_list(
            "MUSTARDUI_UL_ModelToolkit_UIList_TransferShapeKeys",
            "",
            wm,
            "MustardUI_ModelToolkit_TransferShapeKeys_Items",
            wm,
            "MustardUI_ModelToolkit_TransferShapeKeys_ItemIndex",
            rows=8,
        )

        row = layout.row(align=True)
        row.operator(
            "mustardui.model_toolkit_transfer_shape_keys_select",
            text="All",
            icon="CHECKBOX_HLT",
        ).use = True
        row.operator(
            "mustardui.model_toolkit_transfer_shape_keys_select",
            text="None",
            icon="CHECKBOX_DEHLT",
        ).use = False

        layout.separator()

        col = layout.column()
        col.use_property_split = True
        col.use_property_decorate = False
        col.prop(self, "method")
        col.prop(self, "max_distance")
        col.prop(self, "smooth")
        col.prop(self, "threshold")
        col.prop(self, "overwrite")
        row = col.row(align=True)
        row.prop(self, "vertex_group")
        row.prop(self, "invert_vertex_group", text="", icon="ARROW_LEFTRIGHT")
        col.prop(self, "link")

    def invoke(self, context, event):
        wm = context.window_manager
        source = context.active_object
        items = wm.MustardUI_ModelToolkit_TransferShapeKeys_Items

        sks = source.data.shape_keys
        if sks is None or len(sks.key_blocks) < 2:
            self.report({"ERROR"}, "MustardUI - Active Object has no Shape Keys")
            return {"CANCELLED"}

        # Keep the previous choices for the Shape Keys still there
        previous = {item.name: item.use for item in items}
        items.clear()
        for sk in sks.key_blocks:
            if sk == sks.reference_key:
                continue
            item = items.add()
            item.name = sk.name
            item.use = previous.get(sk.name, True)
        wm.MustardUI_ModelToolkit_TransferShapeKeys_ItemIndex = 0

        return context.window_manager.invoke_props_dialog(self, width=350)

    def execute(self, context):
        wm = context.window_manager
        source = context.active_object

        if source is None or source.type != "MESH" or source.data.shape_keys is None:
            self.report({"ERROR"}, "MustardUI - Active Object has no Shape Keys")
            return {"CANCELLED"}

        source_sks = source.data.shape_keys
        if not source_sks.use_relative:
            self.report({"ERROR"}, "MustardUI - Absolute Shape Keys are not supported")
            return {"CANCELLED"}

        items = wm.MustardUI_ModelToolkit_TransferShapeKeys_Items
        names = [item.name for item in items if item.use]
        # Transfer all the Shape Keys when called from scripts
        if not len(items):
            names = [sk.name for sk in source_sks.key_blocks if sk != source_sks.reference_key]
        keys = [source_sks.key_blocks[n] for n in names if n in source_sks.key_blocks]
        if not keys:
            self.report({"ERROR"}, "MustardUI - No Shape Keys to transfer")
            return {"CANCELLED"}

        targets = transfer_targets(context)
        if not targets:
            self.report({"ERROR"}, "MustardUI - Select at least one other Mesh")
            return {"CANCELLED"}

        created = transfer_shape_keys(
            source,
            targets,
            keys,
            method=self.method,
            max_distance=self.max_distance,
            smooth=self.smooth,
            threshold=self.threshold,
            overwrite=self.overwrite,
            vertex_group=self.vertex_group,
            invert_vertex_group=self.invert_vertex_group,
            link=self.link,
        )

        self.report(
            {"INFO"},
            f"MustardUI - {created} Shape Keys transferred to {len(targets)} Objects",
        )

        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_TransferShapeKeys_Item)
    bpy.utils.register_class(MUSTARDUI_UL_ModelToolkit_UIList_TransferShapeKeys)
    bpy.utils.register_class(MustardUI_ModelToolkit_TransferShapeKeys_Select)
    bpy.utils.register_class(MustardUI_ModelToolkit_TransferShapeKeys)

    bpy.types.WindowManager.MustardUI_ModelToolkit_TransferShapeKeys_Items = (
        bpy.props.CollectionProperty(type=MustardUI_ModelToolkit_TransferShapeKeys_Item)
    )
    bpy.types.WindowManager.MustardUI_ModelToolkit_TransferShapeKeys_ItemIndex = (
        bpy.props.IntProperty(default=0, name="")
    )


def unregister():
    del bpy.types.WindowManager.MustardUI_ModelToolkit_TransferShapeKeys_ItemIndex
    del bpy.types.WindowManager.MustardUI_ModelToolkit_TransferShapeKeys_Items

    bpy.utils.unregister_class(MustardUI_ModelToolkit_TransferShapeKeys)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_TransferShapeKeys_Select)
    bpy.utils.unregister_class(MUSTARDUI_UL_ModelToolkit_UIList_TransferShapeKeys)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_TransferShapeKeys_Item)
