import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from ...misc.mesh_deform import NeighbourAverage, mesh_vertex_normals, triangle_barycentric

# Weights under this value are not written
MIN_WEIGHT = 1e-4
# Rings of copied weights around the filled ones smoothed with them, to soften the seam
SEAM_RINGS = 2
# Conjugate gradient tolerance and maximum iterations of the inpainting
SOLVE_TOLERANCE = 1e-7
SOLVE_ITERATIONS = 2000


def cotan_laplacian(co, tris):
    """Unique edges of the triangles with their cotangent weights, and the lumped vertex areas"""

    n = len(co)
    corners = co[tris]
    weights = []
    edges = []
    for k in range(3):
        a, b, c = k, (k + 1) % 3, (k + 2) % 3
        u = corners[:, b] - corners[:, a]
        v = corners[:, c] - corners[:, a]
        cross = np.maximum(np.linalg.norm(np.cross(u, v), axis=1), 1e-30)
        # The angle at a weights the opposite edge
        weights.append(0.5 * np.einsum("ij,ij->i", u, v) / cross)
        edges.append(tris[:, [b, c]])
    edges = np.sort(np.concatenate(edges), axis=1)
    keys, inverse = np.unique(edges[:, 0] * n + edges[:, 1], return_inverse=True)
    weights = np.bincount(inverse.ravel(), weights=np.concatenate(weights))
    # Obtuse triangles give negative weights, which would make the solve unstable
    weights = np.maximum(weights, 1e-8)
    edges = np.stack((keys // n, keys % n), axis=1)

    area = 0.5 * np.linalg.norm(
        np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]), axis=1
    )
    mass = np.bincount(tris.ravel(), weights=np.repeat(area / 3.0, 3), minlength=n)
    return edges, weights, mass


def grow(mask, edges, rings):
    """The vertices of the mask with the given rings of neighbours around them"""

    mask = mask.copy()
    for _ in range(rings):
        reached = mask[edges[:, 0]] | mask[edges[:, 1]]
        mask[edges[reached].ravel()] = True
    return mask


class RegionOperator:
    """The inpainting operator on the unknown vertices, with the known ones around them"""

    def __init__(self, edges, weights, mass, unknown):
        n = len(mass)
        # Unknown vertices and two rings around them, as the operator reaches that far
        region = np.zeros(n, dtype=bool)
        region[unknown] = True
        region = grow(region, edges, 2)
        self.index = np.nonzero(region)[0]
        local = np.full(n, -1, dtype=np.int64)
        local[self.index] = np.arange(len(self.index))
        inside = region[edges[:, 0]] & region[edges[:, 1]]
        e = local[edges[inside]]
        w = weights[inside]

        # Directed edges sorted by their first vertex, to sum over the neighbours quickly
        src = np.concatenate((e[:, 0], e[:, 1]))
        dst = np.concatenate((e[:, 1], e[:, 0]))
        order = np.argsort(src, kind="stable")
        self.src, self.dst, self.w = src[order], dst[order], np.concatenate((w, w))[order]
        m = len(self.index)
        counts = np.bincount(self.src, minlength=m)
        # Vertices without neighbours have no range to sum, and would end past the last one
        self.connected = counts > 0
        self.starts = (np.cumsum(counts) - counts)[self.connected]
        self.total = np.bincount(self.src, weights=self.w, minlength=m)
        self.mass = np.maximum(mass[self.index], 1e-30)
        self.unknown = local[unknown]

        # Diagonal of the operator on the unknown vertices, for the preconditioner
        u = self.unknown
        squares = np.bincount(self.src, weights=self.w**2 / self.mass[self.dst], minlength=m)
        self.diagonal = self.total[u] + self.total[u] ** 2 / self.mass[u] + squares[u]

    def laplacian(self, x):
        """Cotangent laplacian of the columns"""

        if not len(self.src):
            return np.zeros_like(x)
        sums = np.zeros_like(x)
        sums[self.connected] = np.add.reduceat(self.w[:, None] * x[self.dst], self.starts, axis=0)
        return sums - self.total[:, None] * x

    def apply(self, x):
        """Operator of the paper, -L + L M^-1 L, on the unknown rows"""

        lx = self.laplacian(x)
        return (-lx + self.laplacian(lx / self.mass[:, None]))[self.unknown]

    def solve(self, known, guess):
        """Columns on the unknown vertices minimizing the operator energy, with the known values
        fixed on the other vertices of the region, starting from the guess"""

        x = known[self.index].copy()
        x[self.unknown] = 0.0
        b = -self.apply(x)

        def product(y, columns):
            z = np.zeros((len(x), len(columns)))
            z[self.unknown] = y
            return self.apply(z)

        # Preconditioned conjugate gradient, all the columns at once until they converge
        y = guess.copy()
        r = b - product(y, np.arange(b.shape[1]))
        z = r / self.diagonal[:, None]
        p = z.copy()
        rz = np.einsum("ij,ij->j", r, z)
        limit = SOLVE_TOLERANCE**2 * np.maximum(np.einsum("ij,ij->j", b, b), 1e-30)
        active = np.arange(b.shape[1])
        for _ in range(SOLVE_ITERATIONS):
            active = active[np.einsum("ij,ij->j", r[:, active], r[:, active]) > limit[active]]
            if not len(active):
                break
            ap = product(p[:, active], active)
            alpha = rz[active] / np.maximum(np.einsum("ij,ij->j", p[:, active], ap), 1e-30)
            y[:, active] += alpha * p[:, active]
            r[:, active] -= alpha * ap
            z = r[:, active] / self.diagonal[:, None]
            rz_new = np.einsum("ij,ij->j", r[:, active], z)
            p[:, active] = z + (rz_new / np.maximum(rz[active], 1e-30)) * p[:, active]
            rz[active] = rz_new
        return y


def limit_influences(weights, count):
    """Keep the largest weights of each vertex, keeping their sum up to 1"""

    if count <= 0 or weights.shape[1] <= count:
        return weights
    total = weights.sum(axis=1)
    cut = np.partition(weights, -count, axis=1)[:, -count][:, None]
    limited = np.where(weights >= cut, weights, 0.0)
    # Ties at the cut might keep more than the count
    order = np.argsort(-limited, axis=1, kind="stable")
    limited[np.arange(len(weights))[:, None], order[:, count:]] = 0.0
    scale = np.minimum(total, 1.0) / np.maximum(limited.sum(axis=1), 1e-30)
    return limited * scale[:, None]


def smooth_weights(weights, edges, mask, iterations):
    """Average the weights of the masked vertices with their neighbours. Only the Vertex Groups
    with weights around them can change"""

    if iterations <= 0 or not np.any(mask) or not len(edges):
        return weights
    columns = np.nonzero(np.any(weights[grow(mask, edges, 1)] > 0.0, axis=0))[0]
    if not len(columns):
        return weights

    average = NeighbourAverage(edges, len(weights))
    values = weights[:, columns]
    for _ in range(iterations):
        values = np.where(mask[:, None], 0.5 * values + 0.5 * average(values), values)
    weights = weights.copy()
    weights[:, columns] = values
    return weights


def transfer_weights(source, target, settings):
    """Weights of the target vertices from the source ones (Abdrashitov et al. 2023): the
    closest points within the distance and the normal angle copy the source weights, the
    others are inpainted smoothly from them. The pieces without matches copy the weights of
    their closest point, as rigid parts.
    Source and target are (coordinates, triangles, edges), the source with the weights too.
    Returns the weights, the matched vertices and the filled ones"""

    source_co, source_tris, source_weights = source
    co, tris, edges = target
    n = len(co)
    # Closest points of the source
    bvh = BVHTree.FromPolygons(source_co.tolist(), source_tris.tolist())
    faces = np.empty(n, dtype=np.int64)
    locations = np.empty((n, 3))
    for i, p in enumerate(co):
        loc, _, faces[i], _ = bvh.find_nearest(Vector(p))
        locations[i] = loc
    corners = source_tris[faces]
    bary = triangle_barycentric(locations, source_co[corners])
    distance = np.linalg.norm(co - locations, axis=1)
    closest = np.einsum("ij,ijk->ik", bary, source_weights[corners])
    # Meshes without faces (e.g. wires) copy the closest weights
    if not len(tris):
        weights = limit_influences(np.clip(closest, 0.0, 1.0), settings.limit_influences)
        return weights, np.ones(n, dtype=bool), np.zeros(n, dtype=bool)

    source_normals = mesh_vertex_normals(source_co, source_tris)
    normals = mesh_vertex_normals(co, tris)
    closest_normals = np.einsum("ij,ijk->ik", bary, source_normals[corners])
    closest_normals /= np.maximum(np.linalg.norm(closest_normals, axis=1), 1e-12)[:, None]
    alignment = np.einsum("ij,ij->i", normals, closest_normals)
    near = distance <= settings.max_distance
    # Outfits with normals towards the body
    if np.any(near) and np.median(alignment[near]) < 0.0:
        alignment = -alignment
    if settings.both_sides:
        alignment = np.abs(alignment)
    matched = near & (alignment >= np.cos(settings.max_angle))
    # Vertices without faces can not be inpainted
    in_faces = np.zeros(n, dtype=bool)
    in_faces[tris.ravel()] = True

    weights = closest.copy()
    # Connected pieces, pointer jumping until every vertex points to the smallest of its piece
    component = np.arange(n)
    while len(edges):
        low = np.minimum(component[edges[:, 0]], component[edges[:, 1]])
        updated = component.copy()
        np.minimum.at(updated, component[edges[:, 0]], low)
        np.minimum.at(updated, component[edges[:, 1]], low)
        updated = updated[updated]
        if np.array_equal(updated, component):
            break
        component = updated
    has_match = np.zeros(n, dtype=bool)
    has_match[component[matched & in_faces]] = True
    # Pieces without matches move rigidly with the closest point of their closest vertex
    rigid = ~has_match[component]
    if np.any(rigid):
        pieces = np.nonzero(rigid)[0]
        order = pieces[np.lexsort((distance[pieces], component[pieces]))]
        roots, first = np.unique(component[order], return_index=True)
        best = np.zeros(n, dtype=np.int64)
        best[roots] = order[first]
        weights[pieces] = closest[best[component[pieces]]]

    unknown = np.nonzero(~matched & ~rigid & in_faces)[0]
    if len(unknown):
        lap_edges, lap_weights, mass = cotan_laplacian(co, tris)
        # Only the columns with weights around the unknown vertices
        operator = RegionOperator(lap_edges, lap_weights, mass, unknown)
        columns = np.nonzero(np.any(weights[operator.index] > 0.0, axis=0))[0]
        if len(columns):
            # The closest weights are a good start
            guess = weights[np.ix_(unknown, columns)]
            solved = operator.solve(weights[:, columns], guess)
            weights[unknown] = 0.0
            weights[np.ix_(unknown, columns)] = solved
        else:
            weights[unknown] = 0.0

    weights = np.clip(weights, 0.0, 1.0)
    filled = np.zeros(n, dtype=bool)
    filled[unknown] = True
    if settings.smooth_all:
        smoothed = np.ones(n, dtype=bool)
    else:
        smoothed = grow(filled, edges, SEAM_RINGS) if len(edges) else filled
    weights = smooth_weights(weights, edges, smoothed, settings.smooth)
    weights = limit_influences(weights, settings.limit_influences)
    return weights, matched, filled
