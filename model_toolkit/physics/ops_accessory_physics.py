from collections import deque

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

from ...misc.move_modifier import move_modifier, move_modifier_after_armature
from ...misc.scene_state import execute_restoring_state
from ...model_selection.active_object import ModelMode, mustardui_active_object
from . import physics_presets

PIN_GROUP = "Accessory Pin"
RIGID_GROUP = "Accessory Rigid"
DEFORM_NAME = "Accessory Physics"
FOLLOWER_NODE_GROUP = "MustardUI Accessory Rigid Patch"

# Neighbouring voxels of a cell, the cell itself excluded
NEIGHBOURS = [
    (x, y, z) for x in (-1, 0, 1) for y in (-1, 0, 1) for z in (-1, 0, 1) if (x, y, z) != (0, 0, 0)
]


# ----------------------------------------------------------------------------
# Mesh data
# ----------------------------------------------------------------------------


def world_coordinates(obj):
    co = np.empty(len(obj.data.vertices) * 3)
    obj.data.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    mw = np.array(obj.matrix_world)
    return co @ mw[:3, :3].T + mw[:3, 3]


def group_weights(obj, name):
    weights = np.zeros(len(obj.data.vertices))
    group = obj.vertex_groups.get(name) if name else None
    if group is None:
        return weights
    for v in obj.data.vertices:
        for g in v.groups:
            if g.group == group.index:
                weights[v.index] = g.weight
                break
    return weights


def smooth_step(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def evaluated_bvh(obj, depsgraph):
    """BVH of the evaluated mesh in world space."""
    eval_obj = obj.evaluated_get(depsgraph)
    mesh = eval_obj.to_mesh()
    mw = eval_obj.matrix_world
    bvh = BVHTree.FromPolygons(
        [mw @ v.co for v in mesh.vertices], [p.vertices[:] for p in mesh.polygons]
    )
    eval_obj.to_mesh_clear()
    return bvh


def deform_weights_kdtree(source, armature):
    """KD-Tree of the source vertices with their deform weights."""
    coordinates = world_coordinates(source)
    kd = KDTree(len(coordinates))
    for i, co in enumerate(coordinates):
        kd.insert(co, i)
    kd.balance()

    deform = {
        g.index: g.name
        for g in source.vertex_groups
        if g.name in armature.data.bones and armature.data.bones[g.name].use_deform
    }
    weights = [
        {deform[g.group]: g.weight for g in v.groups if g.group in deform and g.weight > 0}
        for v in source.data.vertices
    ]
    return kd, weights


def transfer_deform_weights(target, kd, weights, points):
    """Weights of the nearest source vertices, normalized, on the target vertices."""
    groups = {}
    for index, co in enumerate(points):
        accumulated = {}
        total = 0.0
        for _, i, distance in kd.find_n(co, 4):
            factor = 1.0 / max(distance, 1e-5)
            total += factor
            for name, weight in weights[i].items():
                accumulated[name] = accumulated.get(name, 0.0) + weight * factor
        norm = sum(accumulated.values())
        for name, weight in accumulated.items():
            if name not in groups:
                groups[name] = target.vertex_groups.get(name) or target.vertex_groups.new(name=name)
            groups[name].add([index], weight / norm if norm > 0 else 0.0, "REPLACE")


# ----------------------------------------------------------------------------
# Skeleton of the flexible part
# ----------------------------------------------------------------------------


def voxel_cells(points, size):
    cells = {}
    for i, co in enumerate(points):
        cells.setdefault(tuple(np.floor(co / size).astype(int)), []).append(i)
    return cells


def cell_components(cells):
    """Groups of touching cells."""
    seen = set()
    components = []
    for start in cells:
        if start in seen:
            continue
        seen.add(start)
        queue = deque([start])
        component = []
        while queue:
            cell = queue.popleft()
            component.append(cell)
            for d in NEIGHBOURS:
                other = (cell[0] + d[0], cell[1] + d[1], cell[2] + d[2])
                if other in cells and other not in seen:
                    seen.add(other)
                    queue.append(other)
        components.append(component)
    return components


def hops_within(adjacency, a, b, limit):
    """True if b can be reached from a in at most limit steps."""
    seen = {a}
    frontier = [a]
    for _ in range(limit):
        next_frontier = []
        for node in frontier:
            for other in adjacency[node]:
                if other == b:
                    return True
                if other not in seen:
                    seen.add(other)
                    next_frontier.append(other)
        frontier = next_frontier
    return False


def skeleton(points, size, loop_hops=8, spur_length=2):
    """Graph following the strands of the points: nodes positions and adjacency.

    The voxel centroids are joined by a minimum spanning tree, and the edges closing
    long loops (e.g. the ring of a necklace) are added back. Short spurs left by the
    thickness of the strands are pruned.
    """
    cells = voxel_cells(points, size)
    keys = list(cells)
    index = {k: i for i, k in enumerate(keys)}
    positions = [Vector(points[cells[k]].mean(axis=0)) for k in keys]

    edges = []
    for k in keys:
        for d in NEIGHBOURS:
            other = (k[0] + d[0], k[1] + d[1], k[2] + d[2])
            if other in index and index[k] < index[other]:
                a, b = index[k], index[other]
                edges.append(((positions[a] - positions[b]).length, a, b))
    edges.sort()

    parent = list(range(len(keys)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    adjacency = {i: set() for i in range(len(keys))}
    others = []
    for _, a, b in edges:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
            adjacency[a].add(b)
            adjacency[b].add(a)
        else:
            others.append((a, b))
    for a, b in others:
        if not hops_within(adjacency, a, b, loop_hops):
            adjacency[a].add(b)
            adjacency[b].add(a)

    # Prune the short branches ending in a junction
    for _ in range(2):
        for leaf in [n for n, adj in adjacency.items() if len(adj) == 1]:
            if leaf not in adjacency or len(adjacency[leaf]) != 1:
                continue
            branch = [leaf]
            previous, current = leaf, next(iter(adjacency[leaf]))
            while len(adjacency[current]) == 2 and len(branch) <= spur_length:
                branch.append(current)
                previous, current = current, next(x for x in adjacency[current] if x != previous)
            if len(adjacency[current]) >= 3 and len(branch) <= spur_length:
                for node in branch:
                    for other in adjacency.pop(node):
                        if other in adjacency:
                            adjacency[other].discard(node)

    return positions, adjacency


def polylines(adjacency):
    """Split the graph in polylines between the nodes which are not in the middle of a
    strand. Returns (nodes, closed) tuples."""
    ends = {n for n, adj in adjacency.items() if len(adj) != 2}
    visited = set()
    lines = []
    for start in ends:
        for first in adjacency[start]:
            if (start, first) in visited:
                continue
            line = [start]
            previous, current = start, first
            while True:
                visited.add((previous, current))
                visited.add((current, previous))
                line.append(current)
                if current in ends:
                    break
                previous, current = current, next(x for x in adjacency[current] if x != previous)
            lines.append((line, False))

    # Closed loops without junctions
    for start, adj in adjacency.items():
        if len(adj) != 2 or any((start, x) in visited for x in adj):
            continue
        line = [start]
        previous, current = start, next(iter(adj))
        while current != start:
            visited.add((previous, current))
            visited.add((current, previous))
            line.append(current)
            previous, current = current, next(x for x in adjacency[current] if x != previous)
        visited.add((previous, current))
        visited.add((current, previous))
        lines.append((line, True))
    return lines


# ----------------------------------------------------------------------------
# Proxy
# ----------------------------------------------------------------------------


class ProxyBuilder:
    """Low poly mesh driving the accessory: ribbons along the strands and a stiff patch
    for every rigid part."""

    def __init__(self, surface_normal, width):
        self.bm = bmesh.new()
        self.surface_normal = surface_normal
        self.width = width
        self.rigid = set()
        self.patches = []
        # Proxy vertices of each skeleton node, to attach the rigid parts
        self.node_vertices = {}

    def section(self, point, tangent):
        normal = self.surface_normal(point)
        side = tangent.cross(normal)
        if side.length < 1e-6:
            side = tangent.orthogonal()
        side.normalize()
        w = self.width / 2
        return [self.bm.verts.new(point + side * w), self.bm.verts.new(point - side * w)]

    def ribbon(self, positions, adjacency, line, closed):
        points = [positions[n].copy() for n in line]

        # Smooth the voxel steps, keeping the ends in place
        for _ in range(2):
            smoothed = list(points)
            count = len(points)
            for i in range(count):
                if not closed and i in (0, count - 1):
                    continue
                smoothed[i] = (points[i - 1] + points[i] * 2 + points[(i + 1) % count]) / 4
            points = smoothed

        # The junctions are shared vertices, the other nodes get a cross section
        hubs = {}
        if not closed:
            for i in (0, len(line) - 1):
                node = line[i]
                if len(adjacency[node]) >= 3:
                    if node not in self.node_vertices:
                        self.node_vertices[node] = [self.bm.verts.new(positions[node])]
                    hubs[i] = self.node_vertices[node][0]

        body = [i for i in range(len(line)) if i not in hubs]
        if not body:
            # Two junctions next to each other: a section in the middle joins them
            middle = (points[0] + points[-1]) / 2
            sections = [self.section(middle, (points[-1] - points[0]).normalized())]
        else:
            sections = []
            for i in body:
                a = points[i - 1] if (closed or i > 0) else points[i]
                b = points[(i + 1) % len(points)] if (closed or i < len(points) - 1) else points[i]
                tangent = (b - a).normalized() if (b - a).length > 1e-6 else Vector((0, 0, 1))
                section = self.section(points[i], tangent)
                sections.append(section)
                self.node_vertices[line[i]] = section

        for i in range(len(sections) if closed else len(sections) - 1):
            a, b = sections[i], sections[(i + 1) % len(sections)]
            self.bm.faces.new((a[0], b[0], b[1], a[1]))
        if 0 in hubs:
            self.bm.faces.new((hubs[0], sections[0][0], sections[0][1]))
        if len(line) - 1 in hubs:
            self.bm.faces.new((hubs[len(line) - 1], sections[-1][1], sections[-1][0]))

    def rigid_patch(self, points, size):
        """Grid on the main plane of the points, returns its perimeter."""
        center = points.mean(axis=0)
        _, _, axes = np.linalg.svd(points - center, full_matrices=False)
        u, v = Vector(axes[0]), Vector(axes[1])
        pu = (points - center) @ axes[0]
        pv = (points - center) @ axes[1]
        # Thin parts still get a patch wide enough to hold the shape
        extent_u = max(pu.max() - pu.min(), self.width)
        extent_v = max(pv.max() - pv.min(), self.width)
        nu = int(np.clip(np.ceil(extent_u / size) + 1, 2, 8))
        nv = int(np.clip(np.ceil(extent_v / size) + 1, 2, 8))
        origin = Vector(center) + u * (pu.max() + pu.min()) / 2 + v * (pv.max() + pv.min()) / 2

        grid = []
        for i in range(nu):
            row = []
            for j in range(nv):
                co = (
                    origin
                    + u * extent_u * (i / (nu - 1) - 0.5)
                    + v * extent_v * (j / (nv - 1) - 0.5)
                )
                vert = self.bm.verts.new(co)
                self.rigid.add(vert)
                row.append(vert)
            grid.append(row)
        self.patches.append([vert for row in grid for vert in row])
        for i in range(nu - 1):
            for j in range(nv - 1):
                self.bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
        # Perimeter in order, to hinge the patch on one of its boundary edges
        return (
            [grid[i][0] for i in range(nu)]
            + [grid[nu - 1][j] for j in range(1, nv)]
            + [grid[i][nv - 1] for i in range(nu - 2, -1, -1)]
            + [grid[0][j] for j in range(nv - 2, 0, -1)]
        )

    def attach(self, perimeter, positions, adjacency):
        """Tie the patch to the nearest strand node and to its neighbours with springs, so
        that it swings around the strand but does not spin around a single point."""
        if not self.node_vertices:
            return
        node = min(
            self.node_vertices,
            key=lambda n: min((positions[n] - v.co).length for v in perimeter),
        )
        # The node and its neighbours up to two steps along the strands
        anchors = {node}
        for _ in range(2):
            anchors |= {n for a in anchors for n in adjacency.get(a, ())}
        anchors = [n for n in anchors if n in self.node_vertices]
        for anchor in [v for n in anchors for v in self.node_vertices[n]]:
            for vert in sorted(perimeter, key=lambda v: (v.co - anchor.co).length)[:2]:
                if self.bm.edges.get((anchor, vert)) is None:
                    self.bm.edges.new((anchor, vert))

    def to_object(self, name):
        bmesh.ops.remove_doubles(self.bm, verts=self.bm.verts[:], dist=1e-5)
        self.bm.verts.index_update()
        patches = [[v.index for v in patch if v.is_valid] for patch in self.patches]
        mesh = bpy.data.meshes.new(name)
        self.bm.to_mesh(mesh)
        self.bm.free()
        return bpy.data.objects.new(name, mesh), patches


# ----------------------------------------------------------------------------
# Collider
# ----------------------------------------------------------------------------


def copy_driver(source_fcurve, target_id, data_path):
    fcurve = target_id.driver_add(data_path)
    source, driver = source_fcurve.driver, fcurve.driver
    driver.type = source.type
    driver.expression = source.expression
    driver.use_self = source.use_self
    for variable in source.variables:
        new = driver.variables.new()
        new.name = variable.name
        new.type = variable.type
        for t_src, t_dst in zip(variable.targets, new.targets, strict=True):
            if variable.type == "SINGLE_PROP":
                t_dst.id_type = t_src.id_type
            t_dst.id = t_src.id
            t_dst.data_path = t_src.data_path
            t_dst.bone_target = t_src.bone_target
            t_dst.transform_type = t_src.transform_type
            t_dst.transform_space = t_src.transform_space
            t_dst.rotation_mode = t_src.rotation_mode
    # Curve mapping: keyframes, or the default Generator modifier
    for point in source_fcurve.keyframe_points:
        new_point = fcurve.keyframe_points.insert(point.co[0], point.co[1])
        new_point.interpolation = point.interpolation
    if not any(m.type == "GENERATOR" for m in source_fcurve.modifiers):
        for modifier in [m for m in fcurve.modifiers if m.type == "GENERATOR"]:
            fcurve.modifiers.remove(modifier)
    return fcurve


def create_collider(source, armature, box_min, box_max, name):
    """Copy of the source mesh around the box, deformed by the armature, keeping only the
    Shape Keys (and their drivers) which move that region."""
    mw = source.matrix_world
    co = world_coordinates(source)
    inside = np.all((co >= box_min) & (co <= box_max), axis=1)

    polygons = [p.vertices[:] for p in source.data.polygons if all(inside[i] for i in p.vertices)]
    used = sorted({i for p in polygons for i in p})
    remap = {old: new for new, old in enumerate(used)}

    local = np.empty(len(source.data.vertices) * 3)
    source.data.vertices.foreach_get("co", local)
    local = local.reshape(-1, 3)

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(local[used].tolist(), [], [[remap[i] for i in p] for p in polygons])
    mesh.update()
    collider = bpy.data.objects.new(name, mesh)
    collider.matrix_world = mw.copy()

    # Deform weights
    deform = {
        g.index: g.name
        for g in source.vertex_groups
        if g.name in armature.data.bones and armature.data.bones[g.name].use_deform
    }
    groups = {}
    for old in used:
        for g in source.data.vertices[old].groups:
            if g.group in deform and g.weight > 0:
                name_g = deform[g.group]
                if name_g not in groups:
                    groups[name_g] = collider.vertex_groups.new(name=name_g)
                groups[name_g].add([remap[old]], g.weight, "REPLACE")

    # Shape Keys moving the region
    keys = source.data.shape_keys
    if keys is not None and len(keys.key_blocks) > 1:
        data = {}
        buffer = np.empty(len(source.data.vertices) * 3)
        for kb in keys.key_blocks:
            kb.data.foreach_get("co", buffer)
            data[kb.name] = buffer.reshape(-1, 3)[used].copy()
        driven = set()
        if keys.animation_data is not None:
            driven = {
                f.data_path.split('"')[1]
                for f in keys.animation_data.drivers
                if f.data_path.startswith('key_blocks["')
            }
        # Only the Shape Keys which can be active and noticeably move the region
        keep = [keys.key_blocks[0]] + [
            kb
            for kb in keys.key_blocks[1:]
            if (kb.name in driven or abs(kb.value) > 1e-4)
            and np.abs(data[kb.name] - data[kb.relative_key.name]).max() > 5e-4
        ]
        for kb in keep:
            new = collider.shape_key_add(name=kb.name, from_mix=False)
            new.data.foreach_set("co", data[kb.name].ravel())
            new.slider_min, new.slider_max = kb.slider_min, kb.slider_max
            new.value = kb.value
            new.mute = kb.mute
        new_keys = collider.data.shape_keys
        for kb in keep[1:]:
            relative = kb.relative_key.name
            new_keys.key_blocks[kb.name].relative_key = new_keys.key_blocks.get(
                relative, new_keys.key_blocks[0]
            )
        if keys.animation_data is not None:
            kept = {kb.name for kb in keep}
            for fcurve in keys.animation_data.drivers:
                path = fcurve.data_path
                if path.startswith('key_blocks["') and path.split('"')[1] in kept:
                    copy_driver(fcurve, new_keys, path)

    modifier = collider.modifiers.new("Armature", "ARMATURE")
    modifier.object = armature
    collider.modifiers.new("Collision", "COLLISION")
    collider.collision.thickness_outer = 0.001
    collider.collision.cloth_friction = 5.0
    return collider


def rigid_patch_node_group():
    """Geometry Nodes keeping one Vertex Group of an object, with its modifiers evaluated."""
    node_group = bpy.data.node_groups.get(FOLLOWER_NODE_GROUP)
    if node_group is not None:
        return node_group

    node_group = bpy.data.node_groups.new(FOLLOWER_NODE_GROUP, "GeometryNodeTree")
    interface = node_group.interface
    interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    interface.new_socket("Object", in_out="INPUT", socket_type="NodeSocketObject")
    interface.new_socket("Group", in_out="INPUT", socket_type="NodeSocketString")
    interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")

    nodes, links = node_group.nodes, node_group.links
    group_in = nodes.new("NodeGroupInput")
    group_out = nodes.new("NodeGroupOutput")
    info = nodes.new("GeometryNodeObjectInfo")
    info.transform_space = "RELATIVE"
    attribute = nodes.new("GeometryNodeInputNamedAttribute")
    attribute.data_type = "FLOAT"
    compare = nodes.new("FunctionNodeCompare")
    compare.data_type = "FLOAT"
    compare.operation = "LESS_THAN"
    compare.inputs[1].default_value = 0.5
    delete = nodes.new("GeometryNodeDeleteGeometry")
    delete.domain = "POINT"

    links.new(group_in.outputs["Object"], info.inputs["Object"])
    links.new(group_in.outputs["Group"], attribute.inputs["Name"])
    links.new(attribute.outputs["Attribute"], compare.inputs[0])
    links.new(info.outputs["Geometry"], delete.inputs["Geometry"])
    links.new(compare.outputs["Result"], delete.inputs["Selection"])
    links.new(delete.outputs["Geometry"], group_out.inputs["Geometry"])
    return node_group


def rigid_follower(name, proxy, group_name, collection):
    """Mesh made of one rigid patch of the simulated proxy.

    Geometry Nodes are used and not a Vertex Parent, as the transform of a hidden object
    is not updated, while its geometry is evaluated when another object depends on it.
    """
    obj = bpy.data.objects.new(name, bpy.data.meshes.new(name))
    collection.objects.link(obj)
    modifier = obj.modifiers.new("Rigid Patch", "NODES")
    modifier.node_group = rigid_patch_node_group()
    for item in modifier.node_group.interface.items_tree:
        if getattr(item, "in_out", None) != "INPUT":
            continue
        if item.socket_type == "NodeSocketObject":
            set_modifier_input(modifier, item.identifier, proxy)
        elif item.socket_type == "NodeSocketString":
            set_modifier_input(modifier, item.identifier, group_name)
    return obj


def set_modifier_input(modifier, identifier, value):
    # Blender 5.2 exposes the inputs as properties, the previous versions as ID properties
    properties = getattr(modifier, "properties", None)
    if properties is not None and hasattr(properties, "inputs"):
        getattr(properties.inputs, identifier).value = value
    else:
        modifier[identifier] = value


def bind_surface_deform(context, obj, modifier):
    hidden = obj.hide_viewport
    obj.hide_viewport = False
    context.view_layer.update()
    with context.temp_override(object=obj, active_object=obj):
        bpy.ops.object.surfacedeform_bind(modifier=modifier.name)
    obj.hide_viewport = hidden
    return modifier.is_bound


class CreatedData:
    """Data created by the tool, to remove it if the tool fails"""

    def __init__(self, target):
        self.target = target
        self.modifiers = set(target.modifiers.keys())
        self.groups = set(target.vertex_groups.keys())
        self.data = {
            name: set(getattr(bpy.data, name).keys())
            for name in ("objects", "meshes", "collections")
        }

    def remove(self):
        target = self.target
        for modifier in [m for m in target.modifiers if m.name not in self.modifiers]:
            target.modifiers.remove(modifier)
        for group in [g for g in target.vertex_groups if g.name not in self.groups]:
            target.vertex_groups.remove(group)
        for name, existing in self.data.items():
            collection = getattr(bpy.data, name)
            for datablock in [x for x in collection if x.name not in existing]:
                collection.remove(datablock)


def binary_group(obj, name, indices):
    group = obj.vertex_groups.get(name)
    if group is not None:
        obj.vertex_groups.remove(group)
    group = obj.vertex_groups.new(name=name)
    group.add(indices, 1.0, "REPLACE")
    return group.name


def hide_from_render(obj):
    obj.display_type = "WIRE"
    obj.hide_render = True
    obj.visible_camera = False
    obj.visible_shadow = False
    obj.visible_diffuse = False
    obj.visible_glossy = False
    obj.visible_transmission = False
    obj.visible_volume_scatter = False


# ----------------------------------------------------------------------------
# Operator
# ----------------------------------------------------------------------------


class MustardUI_ModelToolkit_AccessoryPhysics(bpy.types.Operator):
    """Add physics with collisions to an accessory (necklaces, chains, pendants, earrings).\nA low poly proxy is generated along the accessory and simulated with Cloth, and the accessory follows it with a Surface Deform modifier.\nUse Fit to Body first if the accessory intersects the body"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_accessory_physics"
    bl_label = "Accessory Physics"
    bl_options = {"REGISTER", "UNDO"}

    pin_group: bpy.props.StringProperty(
        name="Pin Group",
        description="Vertex Group of the parts following the armature (e.g. the back of "
        "a necklace).\nIf empty, the highest part of the accessory is pinned",
    )
    auto_pin: bpy.props.FloatProperty(
        name="Auto Pin Height",
        description="Fraction of the height of the accessory pinned, from the top, if "
        "no Pin Group is set",
        default=0.25,
        min=0.0,
        max=1.0,
        subtype="FACTOR",
    )
    rigid_group: bpy.props.StringProperty(
        name="Rigid Group",
        description="Vertex Group of the parts moving without deforming (e.g. a pendant)",
    )
    resolution: bpy.props.FloatProperty(
        name="Resolution",
        description="Distance between the proxy vertices.\nSmaller values follow the "
        "accessory more closely, but the simulation is slower",
        default=0.01,
        min=0.002,
        soft_max=0.05,
        subtype="DISTANCE",
    )
    width: bpy.props.FloatProperty(
        name="Strand Width",
        description="Width of the proxy along the strands (e.g. the chain)",
        default=0.004,
        min=0.0005,
        soft_max=0.02,
        subtype="DISTANCE",
    )
    collisions: bpy.props.BoolProperty(
        name="Collisions",
        description="Collide with the body",
        default=True,
    )
    collision_object: bpy.props.StringProperty(
        name="Collision Object",
        description="Mesh used for the collisions.\nIf empty, a collision mesh is "
        "generated around the accessory from the Collision item of the Physics panel, "
        "or from the Body",
    )
    collision_margin: bpy.props.FloatProperty(
        name="Collision Margin",
        description="Distance around the accessory covered by the generated collision mesh",
        default=0.1,
        min=0.01,
        soft_max=0.5,
        subtype="DISTANCE",
    )
    add_to_panel: bpy.props.BoolProperty(
        name="Add to Physics Panel",
        description="Add the proxy and the collision mesh to the Physics Panel",
        default=True,
    )

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=ModelMode.MODEL_TOOLKIT)
        obj = context.active_object
        if not res or obj is None or obj.type != "MESH":
            return False
        return obj != arm.MustardUI_RigSettings.model_body

    def execute(self, context):
        return execute_restoring_state(self, context)

    def _execute(self, context):
        res, arm = mustardui_active_object(context, config=ModelMode.MODEL_TOOLKIT)
        rig_settings = arm.MustardUI_RigSettings
        body = rig_settings.model_body
        target = context.active_object

        if context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        armature = next(
            (m.object for m in target.modifiers if m.type == "ARMATURE" and m.object),
            rig_settings.model_armature_object,
        )
        if armature is None:
            self.report({"ERROR"}, "MustardUI - No armature found for the accessory.")
            return {"CANCELLED"}
        if any(
            m.type == "SURFACE_DEFORM" and m.name.startswith(DEFORM_NAME) for m in target.modifiers
        ):
            self.report(
                {"ERROR"},
                "MustardUI - The accessory already has physics: remove the "
                f"'{DEFORM_NAME}' modifier first.",
            )
            return {"CANCELLED"}

        if body is None and not any(m.type == "ARMATURE" for m in target.modifiers):
            self.report({"ERROR"}, "MustardUI - The accessory has no Armature modifier.")
            return {"CANCELLED"}

        created = CreatedData(target)
        try:
            return self.build(context, arm, target, armature)
        except Exception:
            created.remove()
            raise

    def build(self, context, arm, target, armature):
        rig_settings = arm.MustardUI_RigSettings
        physics_settings = arm.MustardUI_PhysicsSettings
        body = rig_settings.model_body

        # Everything is computed in rest pose, on the first frame
        context.scene.frame_set(context.scene.frame_start)
        for obj in [x for x in bpy.data.objects if x.type == "ARMATURE"]:
            obj.data.pose_position = "REST"
        context.view_layer.update()
        depsgraph = context.evaluated_depsgraph_get()

        body_bvh = evaluated_bvh(body, depsgraph) if body is not None else None
        points = world_coordinates(target)
        center = Vector(points.mean(axis=0))

        def surface_normal(co):
            if body_bvh is not None:
                location, normal, _, _ = body_bvh.find_nearest(co)
                if location is not None:
                    return normal
            direction = co - center
            return direction.normalized() if direction.length > 1e-6 else Vector((0, -1, 0))

        # Proxy: strands and rigid parts
        rigid_weights = group_weights(target, self.rigid_group)
        rigid_mask = rigid_weights > 0.5
        builder = ProxyBuilder(surface_normal, self.width)

        flexible = points[~rigid_mask]
        positions, adjacency = [], {}
        if len(flexible):
            positions, adjacency = skeleton(flexible, self.resolution)
            for line, closed in polylines(adjacency):
                builder.ribbon(positions, adjacency, line, closed)

        # Rigid parts, as indices of the accessory vertices
        rigid_parts = []
        rigid_all = np.nonzero(rigid_mask)[0]
        if len(rigid_all):
            cells = voxel_cells(points[rigid_all], self.resolution)
            for component in cell_components(cells):
                indices = rigid_all[[i for cell in component for i in cells[cell]]]
                rigid_parts.append(indices.tolist())
                perimeter = builder.rigid_patch(points[indices], self.resolution)
                builder.attach(perimeter, positions, adjacency)

        if not builder.bm.verts:
            builder.bm.free()
            self.report({"ERROR"}, "MustardUI - The proxy could not be generated.")
            return {"CANCELLED"}

        proxy, patches = builder.to_object(f"{target.name} Physics Proxy")
        bmesh_tri = bmesh.new()
        bmesh_tri.from_mesh(proxy.data)
        bmesh.ops.triangulate(bmesh_tri, faces=bmesh_tri.faces[:])
        bmesh_tri.to_mesh(proxy.data)
        bmesh_tri.free()

        collection = bpy.data.collections.new(f"{target.name} Physics")
        # Next to the armature, as the collection of the accessory might be hidden
        parent_collection = (
            armature.users_collection[0] if armature.users_collection else context.scene.collection
        )
        parent_collection.children.link(collection)
        collection.objects.link(proxy)
        proxy.parent = armature
        proxy.matrix_parent_inverse = armature.matrix_world.inverted()
        proxy.matrix_world = Matrix.Identity(4)
        proxy_points = [v.co.copy() for v in proxy.data.vertices]

        # Pin weights from the accessory
        pin_weights = group_weights(target, self.pin_group)
        if not self.pin_group or target.vertex_groups.get(self.pin_group) is None:
            z = points[:, 2]
            top = z.max() - self.auto_pin * (z.max() - z.min())
            blend = max(0.1 * (z.max() - z.min()), 1e-4)
            pin_weights = smooth_step(top - blend, top, z)
        kd = KDTree(len(points))
        for i, co in enumerate(points):
            kd.insert(co, i)
        kd.balance()
        pin = proxy.vertex_groups.new(name=PIN_GROUP)
        for v in proxy.data.vertices:
            weight = np.mean([pin_weights[i] for _, i, _ in kd.find_n(proxy_points[v.index], 3)])
            if weight > 0.001:
                pin.add([v.index], float(min(weight, 1.0)), "REPLACE")
        rigid_group = proxy.vertex_groups.new(name=RIGID_GROUP)
        for k, patch in enumerate(patches):
            rigid_group.add(patch, 1.0, "REPLACE")
            proxy.vertex_groups.new(name=f"{RIGID_GROUP} {k + 1}").add(patch, 1.0, "REPLACE")

        # Accessories without an Armature modifier get one, with the body weights
        if not any(m.type == "ARMATURE" for m in target.modifiers):
            body_kd, body_weights = deform_weights_kdtree(body, armature)
            transfer_deform_weights(target, body_kd, body_weights, [Vector(p) for p in points])
            modifier = target.modifiers.new("Accessory Physics Armature", "ARMATURE")
            modifier.object = armature
            move_modifier(target, modifier, 0)

        # The proxy follows the armature as the accessory does, so that it does not move
        # when the physics is disabled
        skin_kd, skin_weights = deform_weights_kdtree(target, armature)
        transfer_deform_weights(proxy, skin_kd, skin_weights, proxy_points)
        proxy_armature = proxy.modifiers.new("Armature", "ARMATURE")
        proxy_armature.object = armature

        # The rigid parts follow a copy of their patch, so that they are only moved and
        # rotated, while the rest follows the proxy
        followers = []
        for k in range(len(patches)):
            follower = rigid_follower(
                f"{proxy.name} Rigid {k + 1}", proxy, f"{RIGID_GROUP} {k + 1}", collection
            )
            hide_from_render(follower)
            followers.append(follower)

        deform = target.modifiers.new(DEFORM_NAME, "SURFACE_DEFORM")
        deform.target = proxy
        deform.falloff = 4.0
        if rigid_parts:
            deform.vertex_group = binary_group(
                target, f"{DEFORM_NAME} Rigid", [i for part in rigid_parts for i in part]
            )
            deform.invert_vertex_group = True
            deform.use_sparse_bind = True
        move_modifier_after_armature(target, deform)
        bound = bind_surface_deform(context, target, deform)

        # Named after the proxy, so that the Physics panel enables them with it
        for k, (part, follower) in enumerate(zip(rigid_parts, followers, strict=True)):
            rigid_deform = target.modifiers.new(follower.name, "SURFACE_DEFORM")
            rigid_deform.target = follower
            rigid_deform.vertex_group = binary_group(target, f"{DEFORM_NAME} Rigid {k + 1}", part)
            rigid_deform.use_sparse_bind = True
            move_modifier_after_armature(target, rigid_deform)
            bound = bind_surface_deform(context, target, rigid_deform) and bound
            follower.hide_viewport = True

        if not bound:
            self.report({"WARNING"}, "MustardUI - The Surface Deform modifier could not be bound.")

        # Physics
        cloth = physics_presets.apply_physics(
            proxy,
            engine="CLOTH",
            preset="ACCESSORY",
            pin_group_name=PIN_GROUP,
            structural_group_name=RIGID_GROUP,
        )
        cloth.settings.vertex_group_shear_stiffness = RIGID_GROUP
        cloth.settings.vertex_group_bending = RIGID_GROUP
        cloth.collision_settings.use_collision = self.collisions

        collider = None
        if self.collisions:
            collider = (
                bpy.data.objects.get(self.collision_object) if self.collision_object else None
            )
            if collider is not None:
                if not any(m.type == "COLLISION" for m in collider.modifiers):
                    collider.modifiers.new("Collision", "COLLISION")
                cloth.collision_settings.collection = None
            else:
                source = next(
                    (
                        x.object
                        for x in physics_settings.items
                        if x.type == "COLLISION" and x.object and x.object.type == "MESH"
                    ),
                    body,
                )
                if source is not None:
                    margin = self.collision_margin
                    collider = create_collider(
                        source,
                        armature,
                        points.min(axis=0) - margin,
                        points.max(axis=0) + margin,
                        f"{target.name} Collision",
                    )
                    collection.objects.link(collider)
                    collider.parent = armature
                    collider.matrix_parent_inverse = armature.matrix_world.inverted()
                    collider.matrix_world = source.matrix_world.copy()
                    hide_from_render(collider)
                    cloth.collision_settings.collection = collection

        hide_from_render(proxy)

        # The simulation cannot start inside the body
        clipping = 0
        if body_bvh is not None:
            for co in proxy_points:
                location, normal, _, _ = body_bvh.find_nearest(co)
                if location is not None and (co - location).dot(normal) < -0.002:
                    clipping += 1

        if self.add_to_panel:
            item = physics_settings.items.add()
            item.object = proxy
            item.type = "CAGE"
            outfits = [x.collection for x in rig_settings.outfits_collections if x.collection]
            if rig_settings.extras_collection is not None:
                outfits.append(rig_settings.extras_collection)
            outfit_collection = next((x for x in outfits if target.name in x.all_objects), None)
            if outfit_collection is not None:
                item.outfit_enable = True
                item.outfit_collection = outfit_collection
                item.outfit_object = target
            if collider is not None and collider.name in collection.objects:
                item = physics_settings.items.add()
                item.object = collider
                item.type = "COLLISION"

        proxy.MustardUI_tools_creators_is_created = True
        for obj in [proxy, *followers] + (
            [collider] if collider and collider.name in collection.objects else []
        ):
            obj.MustardUI_tools_creators_type = "ACCESSORY"

        if clipping:
            self.report(
                {"WARNING"},
                f"MustardUI - Accessory Physics created, but {clipping} proxy vertices are "
                "inside the body: use Fit to Body on the accessory, then create it again.",
            )
        else:
            self.report({"INFO"}, "MustardUI - Accessory Physics created.")

        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        box = layout.box()
        col = box.column()
        col.prop_search(self, "pin_group", obj, "vertex_groups")
        row = col.row()
        row.enabled = not self.pin_group
        row.prop(self, "auto_pin")
        col.prop_search(self, "rigid_group", obj, "vertex_groups")

        box = layout.box()
        col = box.column(align=True)
        col.prop(self, "resolution")
        col.prop(self, "width")

        box = layout.box()
        box.prop(self, "collisions")
        col = box.column()
        col.enabled = self.collisions
        col.prop_search(self, "collision_object", bpy.data, "objects")
        row = col.row()
        row.enabled = not self.collision_object
        row.prop(self, "collision_margin")

        layout.prop(self, "add_to_panel")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=320)


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_AccessoryPhysics)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_AccessoryPhysics)
