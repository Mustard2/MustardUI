import numpy as np
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

from .scene_state import SceneState


def kdtree(points):
    """KDTree of the points, found by their index"""

    kd = KDTree(len(points))
    for i, co in enumerate(points):
        kd.insert(co, i)
    kd.balance()
    return kd


def mesh_triangles(mesh):
    mesh.calc_loop_triangles()
    tris = np.empty(len(mesh.loop_triangles) * 3, dtype=np.int64)
    mesh.loop_triangles.foreach_get("vertices", tris)
    return tris.reshape(-1, 3)


def mesh_vertex_normals(co, tris):
    """Area weighted vertex normals of the mesh with the given coordinates"""

    face_normals = np.cross(co[tris[:, 1]] - co[tris[:, 0]], co[tris[:, 2]] - co[tris[:, 0]])
    normals = np.zeros_like(co)
    for i in range(3):
        for k in range(3):
            normals[:, i] += np.bincount(tris[:, k], weights=face_normals[:, i], minlength=len(co))
    normals /= np.maximum(np.linalg.norm(normals, axis=1), 1e-12)[:, None]
    return normals


def mesh_laplacian(values, edges, n_verts):
    """Average of the neighbours values for each vertex"""

    count = np.bincount(edges.ravel(), minlength=n_verts).astype(np.float64)
    count[count == 0] = 1.0
    avg = np.empty_like(values)
    for i in range(values.shape[1]):
        acc = np.bincount(edges[:, 0], weights=values[edges[:, 1], i], minlength=n_verts)
        acc += np.bincount(edges[:, 1], weights=values[edges[:, 0], i], minlength=n_verts)
        avg[:, i] = acc / count
    return avg


class NeighbourAverage:
    """Average of the neighbours values of each vertex"""

    def __init__(self, edges, n):
        linked = np.concatenate((edges, edges[:, ::-1]))
        order = np.argsort(linked[:, 0], kind="stable")
        self.neighbours = linked[order, 1]
        self.counts = np.bincount(linked[:, 0], minlength=n)
        self.connected = self.counts > 0
        # Vertices without neighbours have no range to sum, and would end past the last one
        self.starts = (np.cumsum(self.counts) - self.counts)[self.connected]

    def __call__(self, values):
        average = values.copy()
        if len(self.neighbours):
            sums = np.add.reduceat(values[self.neighbours], self.starts, axis=0)
            average[self.connected] = sums / self.counts[self.connected, None]
        return average


def smooth_deformation(delta, edges, length, distance, area=None):
    """Smooth the displacement of the vertices over the distance, keeping its size"""

    iterations = int(np.ceil(2.0 * (distance / length) ** 2)) if distance > 0.0 else 0
    if not iterations:
        return delta

    if area is None:
        # Only the deformed area, with the vertices the smoothing can reach
        region = np.linalg.norm(delta, axis=1) > 1e-5
        rings = int(np.ceil(3.0 * distance / length))
    else:
        region = area.copy()
        rings = 1
    for _ in range(rings):
        grow = edges[region[edges[:, 0]] | region[edges[:, 1]]].ravel()
        if np.all(region[grow]):
            break
        region[grow] = True
    indices = np.nonzero(region)[0]
    free = np.ones(len(indices), dtype=bool) if area is None else area[indices]
    remap = np.full(len(region), -1, dtype=np.int64)
    remap[indices] = np.arange(len(indices))
    sub_edges = remap[edges[region[edges[:, 0]] & region[edges[:, 1]]]]

    # Smoothing and the opposite step, removing the details but keeping the size of the
    # deformation. A larger opposite step (Taubin) enlarges it after many iterations
    sub = delta[indices].copy()
    for _ in range(min(iterations, 2000)):
        sub[free] += 0.5 * (mesh_laplacian(sub, sub_edges, len(sub)) - sub)[free]
        sub[free] -= 0.5 * (mesh_laplacian(sub, sub_edges, len(sub)) - sub)[free]
    smoothed = delta.copy()
    smoothed[indices] = sub
    return smoothed


def shape_key_mix(obj, exclude_name=""):
    """Current Shape Keys mix of the object, without the excluded Shape Key"""

    sks = obj.data.shape_keys
    if sks is None:
        return None

    excluded = sks.key_blocks.get(exclude_name) if exclude_name else None
    mute = excluded.mute if excluded is not None else False
    if excluded is not None:
        excluded.mute = True
    active_index = obj.active_shape_key_index

    tmp = obj.shape_key_add(name="MustardUI_Mix", from_mix=True)
    mix = np.empty(len(tmp.data) * 3, dtype=np.float64)
    tmp.data.foreach_get("co", mix)
    obj.shape_key_remove(tmp)

    if excluded is not None:
        excluded.mute = mute
    obj.active_shape_key_index = active_index

    return mix.reshape(-1, 3)


def triangle_barycentric(points, corners, clamp=True):
    """Barycentric coordinates of the points projected on the triangles, clamped inside them"""

    e1 = corners[:, 1] - corners[:, 0]
    e2 = corners[:, 2] - corners[:, 0]
    v = points - corners[:, 0]
    d11 = np.einsum("ij,ij->i", e1, e1)
    d12 = np.einsum("ij,ij->i", e1, e2)
    d22 = np.einsum("ij,ij->i", e2, e2)
    v1 = np.einsum("ij,ij->i", v, e1)
    v2 = np.einsum("ij,ij->i", v, e2)
    det = np.maximum(d11 * d22 - d12 * d12, 1e-30)
    b1 = (d22 * v1 - d12 * v2) / det
    b2 = (d11 * v2 - d12 * v1) / det
    bary = np.stack((1.0 - b1 - b2, b1, b2), axis=1)
    if not clamp:
        return bary
    bary = np.clip(bary, 0.0, None)
    return bary / np.maximum(bary.sum(axis=1), 1e-12)[:, None]


def read_weights(obj, names):
    """Weights of the Vertex Groups for each vertex, as columns"""

    weights = np.zeros((len(obj.data.vertices), len(names)))
    columns = {obj.vertex_groups[name].index: k for k, name in enumerate(names)}
    for v in obj.data.vertices:
        for g in v.groups:
            k = columns.get(g.group)
            if k is not None:
                weights[v.index, k] = g.weight
    return weights


def write_weights(obj, names, weights, min_weight=0.0):
    """Replace the Vertex Groups with the weights columns"""

    everything = list(range(len(obj.data.vertices)))
    groups = []
    for k, name in enumerate(names):
        vg = obj.vertex_groups.get(name)
        if vg is None:
            vg = obj.vertex_groups.new(name=name)
        vg.remove(everything)
        for i in np.nonzero((weights[:, k] > 0.0) & (weights[:, k] >= min_weight))[0]:
            vg.add([int(i)], float(weights[i, k]), "REPLACE")
        groups.append(vg)
    return groups


def vertex_group_weights(obj, name):
    """Weights of the Vertex Group for each vertex, None if not found"""

    if not name:
        return np.ones(len(obj.data.vertices))
    if obj.vertex_groups.get(name) is None:
        return None
    return read_weights(obj, [name])[:, 0]


def write_vertex_group(obj, name, weights):
    """Create or replace the Vertex Group with the given weights"""

    return write_weights(obj, [name], weights[:, None])[0]


def rest_geometry(
    context, objects, rest_objects, use_modifiers, exclude_key="", faces_only=True, basis=False
):
    """World coordinates and triangles of the objects in Rest Pose"""

    geometry = []
    state = SceneState(context)
    muted = []
    try:
        # Armatures deforming or parenting the objects
        for obj in [*objects, *rest_objects]:
            armatures = [obj.parent] + [m.object for m in obj.modifiers if m.type == "ARMATURE"]
            armatures += [getattr(c, "target", None) for c in obj.constraints]
            for arm in armatures:
                if arm is not None and arm.type == "ARMATURE":
                    arm.data.pose_position = "REST"
        for obj in objects:
            sks = getattr(obj.data, "shape_keys", None)
            if sks is None:
                continue
            if basis:
                excluded = [sk for sk in sks.key_blocks if sk != sks.reference_key]
            else:
                excluded = [sks.key_blocks.get(exclude_key)] if exclude_key else []
            for sk in excluded:
                if sk is not None and not sk.mute:
                    sk.mute = True
                    muted.append(sk)
        depsgraph = context.evaluated_depsgraph_get()

        for obj in objects:
            eval_obj = obj.evaluated_get(depsgraph) if use_modifiers else obj
            mesh = eval_obj.to_mesh()

            co = None
            if not use_modifiers and obj.type == "MESH":
                co = shape_key_mix(obj, exclude_key)
            if co is None:
                co = np.empty(len(mesh.vertices) * 3, dtype=np.float64)
                mesh.vertices.foreach_get("co", co)
                co = co.reshape(-1, 3)
            mat = np.array(obj.matrix_world, dtype=np.float64)
            co = co @ mat[:3, :3].T + mat[:3, 3]

            tri = mesh_triangles(mesh)
            eval_obj.to_mesh_clear()
            if len(tri) or not faces_only:
                geometry.append((co, tri))
    finally:
        for sk in muted:
            sk.mute = False
        state.restore_poses_and_frame(context)

    return geometry


def geometry_bvh(geometry, flipped=None):
    """BVHTree of the geometry, with its vertices and triangles"""

    verts = []
    tris = []
    offset = 0
    for k, (co, tri) in enumerate(geometry):
        flip = flipped is not None and flipped[k]
        tris.append((tri[:, ::-1] if flip else tri) + offset)
        verts.append(co)
        offset += len(co)

    if not tris:
        return None, None, None

    verts = np.concatenate(verts)
    tris = np.concatenate(tris)
    return BVHTree.FromPolygons(verts.tolist(), tris.tolist()), verts, tris


def rest_coordinates(obj, key_name):
    """Basis coordinates and world coordinates of the Shape Keys mix"""

    mesh = obj.data
    basis = np.empty(len(mesh.vertices) * 3, dtype=np.float64)
    if mesh.shape_keys is not None:
        mesh.shape_keys.reference_key.data.foreach_get("co", basis)
    else:
        mesh.vertices.foreach_get("co", basis)
    basis = basis.reshape(-1, 3)
    mix = shape_key_mix(obj, key_name)
    if mix is None:
        mix = basis

    mat = np.array(obj.matrix_world, dtype=np.float64)
    return basis, mix @ mat[:3, :3].T + mat[:3, 3], np.linalg.inv(mat[:3, :3])


def rigid_translation(moves):
    """Single translation covering the moves along their average direction"""

    mean = moves.mean(axis=0)
    length = np.linalg.norm(mean)
    if length < 1e-9:
        return np.zeros(3)
    direction = mean / length
    return direction * max((moves @ direction).max(), 0.0)


class RigidChild:
    """Child object moved rigidly with the surface of its parent under it"""

    def __init__(self, obj, target, key_name):
        self.obj = obj
        self.basis, co, self.mat3_inv = rest_coordinates(obj, key_name)
        kd = target.kdtree()
        self.anchors = np.array([kd.find(c)[1] for c in co], dtype=np.int64)

    def enabled(self, settings):
        return settings.move_children

    def shape(self, solver, settings):
        if not self.enabled(settings) or solver.disp is None or not len(self.anchors):
            return self.basis
        return self.basis + rigid_translation(solver.disp[self.anchors]) @ self.mat3_inv.T


class DeformTarget:
    """Rest data of the object receiving the Shape Key"""

    def __init__(self, obj, key_name):
        self.obj = obj
        self.key_name = key_name
        mesh = obj.data
        self.n_verts = len(mesh.vertices)

        # Rest coordinates, and the current Shape Keys mix the other objects are fitted on
        self.basis, self.co, self.mat3_inv = rest_coordinates(obj, key_name)
        self.tris = mesh_triangles(mesh)
        self.normals = mesh_vertex_normals(self.co, self.tris)

        edges = np.empty(len(mesh.edges) * 2, dtype=np.int64)
        mesh.edges.foreach_get("vertices", edges)
        self.edges = edges.reshape(-1, 2)

        self._weights = {}
        self._influence = (None, None)
        self._islands = {}
        self._kdtree = None

    def kdtree(self):
        if self._kdtree is None:
            self._kdtree = kdtree(self.co)
        return self._kdtree

    def rigid_children(self, exclude):
        """Mesh objects parented to the object, moved rigidly with it"""

        def object_parented(child):
            # Vertex parented children already follow the parent vertices
            while child is not None and child != self.obj:
                if child.parent_type != "OBJECT":
                    return False
                child = child.parent
            return child == self.obj

        return [
            RigidChild(child, self, self.key_name)
            for child in self.obj.children_recursive
            if child.type == "MESH"
            and child not in exclude
            and len(child.data.vertices)
            and object_parented(child)
        ]

    def weights(self, vertex_group, invert=False):
        key = (vertex_group, invert)
        if key not in self._weights:
            weights = vertex_group_weights(self.obj, vertex_group)
            if weights is not None and vertex_group and invert:
                weights = 1.0 - weights
            self._weights[key] = weights
        return self._weights[key]

    def rigid_islands(self, vertex_group, invert=False):
        """Connected parts of the Vertex Group vertices, None if not found"""

        key = (vertex_group, invert)
        if key not in self._islands:
            weights = self.weights(vertex_group, invert)
            if weights is None:
                return None

            rigid = weights > 0.0
            neighbours = {int(i): [] for i in np.nonzero(rigid)[0]}
            for a, b in self.edges[rigid[self.edges[:, 0]] & rigid[self.edges[:, 1]]]:
                neighbours[int(a)].append(int(b))
                neighbours[int(b)].append(int(a))

            islands = []
            visited = set()
            for start in neighbours:
                if start in visited:
                    continue
                island = [start]
                visited.add(start)
                for i in island:
                    for j in neighbours[i]:
                        if j not in visited:
                            visited.add(j)
                            island.append(j)
                islands.append(np.array(island))

            # Closest non rigid vertices, to follow the surface under the rigid parts
            free = np.nonzero(~rigid)[0]
            if len(free):
                kd = kdtree(self.co[free])
                islands = [
                    (island, np.array([free[kd.find(self.co[i])[1]] for i in island]))
                    for island in islands
                ]
            else:
                islands = [(island, island[:0]) for island in islands]
            self._islands[key] = islands
        return self._islands[key]

    def rigidify(self, disp, islands):
        """Move each rigid island with a single translation"""

        for island, anchors in islands:
            disp[island] = rigid_translation(np.concatenate((disp[island], disp[anchors])))
        return disp

    def influence(self, key, contact, radius):
        """Weights fading from the contact vertices to 0 at the radius, cached by key"""

        if self._influence[0] == (key, radius):
            return self._influence[1]

        co = self.co
        weights = np.zeros(self.n_verts)
        weights[contact] = 1.0
        if radius > 0.0:
            kd = kdtree(co[contact])
            bb_min = co[contact].min(axis=0) - radius
            bb_max = co[contact].max(axis=0) + radius
            near = np.all((co >= bb_min) & (co <= bb_max), axis=1) & (weights == 0.0)
            for i in np.nonzero(near)[0]:
                d = kd.find(co[i])[2]
                if d < radius:
                    t = 1.0 - d / radius
                    weights[i] = t * t * (3.0 - 2.0 * t)

        self._influence = ((key, radius), weights)
        return weights

    def smooth(self, disp, distance, contact, directions, required, min_iterations=0):
        """Smooth the displacement, keeping the required one along the directions"""

        moving = np.linalg.norm(disp, axis=1) > 0.0
        if not np.any(moving):
            return disp
        edges = self.edges
        touching = moving[edges[:, 0]] | moving[edges[:, 1]]
        # Only loose vertices move: nothing to smooth
        if not np.any(touching):
            return disp
        length = np.median(
            np.linalg.norm(self.co[edges[touching, 0]] - self.co[edges[touching, 1]], axis=1)
        )
        length = max(length, 1e-6)

        # Iterations spreading the displacement over the distance, whatever the mesh density
        iterations = int(np.ceil(2.0 * (distance / length) ** 2)) if distance > 0.0 else 0
        iterations = min(max(iterations, min_iterations), 2000)
        if not iterations:
            return disp

        # Only the vertices the smoothing can reach
        region = moving.copy()
        for _ in range(
            int(np.ceil(3.0 * max(distance, length * np.sqrt(iterations / 2.0)) / length))
        ):
            grow = region[edges[:, 0]] | region[edges[:, 1]]
            if np.all(region[edges[grow].ravel()]):
                break
            region[edges[grow].ravel()] = True
        indices = np.nonzero(region)[0]
        remap = np.full(self.n_verts, -1, dtype=np.int64)
        remap[indices] = np.arange(len(indices))
        sub_edges = remap[edges[region[edges[:, 0]] & region[edges[:, 1]]]]
        sub = disp[indices]
        sub_contact = remap[contact]

        for _ in range(iterations):
            sub = 0.5 * sub + 0.5 * mesh_laplacian(sub, sub_edges, len(indices))
            pushed = np.einsum("ij,ij->i", sub[sub_contact], directions)
            missing = np.maximum(required - pushed, 0.0)
            sub[sub_contact] += directions * missing[:, None]

        disp = disp.copy()
        disp[indices] = sub
        return disp

    def local(self, disp):
        """Shape Key coordinates from the world space displacement"""

        return self.basis + disp @ self.mat3_inv.T
