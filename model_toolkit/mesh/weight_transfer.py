import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from ...misc.mesh_deform import NeighbourAverage, mesh_vertex_normals, triangle_barycentric

# Weights under this value are not written
MIN_WEIGHT = 1e-4
# Rings of copied weights around the filled ones smoothed with them, to soften the seam
SEAM_RINGS = 2
# Factor entries above which a region is not filled, about 200 MB
MAX_FACTOR_ENTRIES = 25_000_000


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


def concatenated_ranges(starts, counts):
    """Indices of the ranges with the given starts and counts, one after the other"""

    return np.repeat(starts - np.cumsum(counts) + counts, counts) + np.arange(counts.sum())


def inpainting_matrix(edges, weights, mass, unknown):
    """Entries (row, column, value) of -L + L M^-1 L on the rows of the unknown vertices"""

    n = len(mass)
    total = np.bincount(edges.ravel(), weights=np.repeat(weights, 2), minlength=n)
    # Laplacian entries with the diagonal, sorted by column
    rows = np.concatenate((edges[:, 0], edges[:, 1], np.arange(n)))
    cols = np.concatenate((edges[:, 1], edges[:, 0], np.arange(n)))
    vals = np.concatenate((weights, weights, -total))
    order = np.argsort(cols, kind="stable")
    rows, cols, vals = rows[order], cols[order], vals[order]
    counts = np.bincount(cols, minlength=n)
    starts = np.cumsum(counts) - counts

    # (L M^-1 L)_ik sums L_ij L_jk / m_j, pairing each entry of an unknown row with its column
    is_unknown = np.zeros(n, dtype=bool)
    is_unknown[unknown] = True
    own = np.nonzero(is_unknown[rows])[0]
    reps = counts[cols[own]]
    first = np.repeat(own, reps)
    second = concatenated_ranges(starts[cols[own]], reps)
    product = vals[first] * vals[second] / np.maximum(mass[cols[first]], 1e-30)
    return (
        np.concatenate((rows[first], rows[own])),
        np.concatenate((rows[second], cols[own])),
        np.concatenate((product, -vals[own])),
    )


def breadth_levels(start, adjacency, seen):
    """Breadth first levels of the graph from the start vertex, marking them as seen"""

    starts, counts, neighbours = adjacency
    levels = []
    current = np.array([start])
    seen[start] = True
    while len(current):
        levels.append(current)
        current = np.unique(neighbours[concatenated_ranges(starts[current], counts[current])])
        current = current[~seen[current]]
        seen[current] = True
    return levels


def solve_block_tridiagonal(diagonal, lower, b):
    """Solution of the block tridiagonal positive definite system, with a block Cholesky"""

    factors, coupling = [], [None]
    for k, block in enumerate(diagonal):
        if k:
            coupling.append(np.linalg.solve(factors[-1], lower[k].T).T)
        factors.append(np.linalg.cholesky(block - coupling[k] @ coupling[k].T if k else block))
    y = [None] * len(diagonal)
    for k in range(len(diagonal)):
        rhs = b[k] - coupling[k] @ y[k - 1] if k else b[k]
        y[k] = np.linalg.solve(factors[k], rhs)
    for k in reversed(range(len(diagonal))):
        if k + 1 < len(diagonal):
            y[k] = y[k] - coupling[k + 1].T @ y[k + 1]
        y[k] = np.linalg.solve(factors[k].T, y[k])
    return np.concatenate(y)


def inpaint(edges, weights, mass, unknown, values):
    """Unknown values minimizing -L + L M^-1 L, and if no region kept its closest values"""

    m = len(unknown)
    # The closest values are kept by the regions too large or degenerate to solve
    result = values[unknown]
    if not values.shape[1]:
        return result, True
    local = np.full(len(mass), -1, dtype=np.int64)
    local[unknown] = np.arange(m)
    rows, cols, vals = inpainting_matrix(edges, weights, mass, unknown)

    # The known values move to the right side
    known = local[cols] < 0
    b = np.zeros((m, values.shape[1]))
    np.add.at(b, local[rows[known]], -vals[known, None] * values[cols[known]])
    touched = np.zeros(m, dtype=bool)
    touched[local[rows[known]]] = True
    rows, cols, vals = local[rows[~known]], local[cols[~known]], vals[~known]
    order = np.argsort(rows, kind="stable")
    rows, cols, vals = rows[order], cols[order], vals[order]
    counts = np.bincount(rows, minlength=m)
    starts = np.cumsum(counts) - counts
    adjacency = (starts, counts, cols)

    solved = True
    seen = np.zeros(m, dtype=bool)
    level = np.empty(m, dtype=np.int64)
    position = np.empty(m, dtype=np.int64)
    for start in range(m):
        if seen[start]:
            continue
        # Levels from a far vertex, as they are narrower: the matrix is block tridiagonal
        levels = breadth_levels(start, adjacency, seen)
        seen[np.concatenate(levels)] = False
        levels = breadth_levels(levels[-1][0], adjacency, seen)
        region = np.concatenate(levels)
        # Regions without known vertices around keep the closest values
        if not np.any(touched[region]):
            continue
        sizes = np.array([len(x) for x in levels])
        if np.sum(sizes**2) + np.sum(sizes[1:] * sizes[:-1]) > MAX_FACTOR_ENTRIES:
            solved = False
            continue

        for k, x in enumerate(levels):
            level[x] = k
            position[x] = np.arange(len(x))
        # Entries of the region rows, in the order of the levels
        entries = concatenated_ranges(starts[region], counts[region])
        r, c, v = rows[entries], cols[entries], vals[entries]
        bounds = np.searchsorted(level[r], np.arange(len(sizes) + 1))
        diagonal, lower = [], []
        for k, size in enumerate(sizes):
            at = slice(bounds[k], bounds[k + 1])
            rk, ck, vk = position[r[at]], c[at], v[at]
            # Columns of the previous level and of this one, as the matrix is symmetric
            previous = sizes[k - 1] if k else 0
            keep = level[ck] <= k
            columns = position[ck] + np.where(level[ck] == k, previous, 0)
            block = np.zeros((size, previous + size))
            np.add.at(block, (rk[keep], columns[keep]), vk[keep])
            lower.append(block[:, :previous])
            diagonal.append(block[:, previous:])
        try:
            y = solve_block_tridiagonal(diagonal, lower, [b[x] for x in levels])
        except np.linalg.LinAlgError:
            y = None
        if y is None or not np.all(np.isfinite(y)):
            solved = False
            continue
        result[region] = y
    return result, solved


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
    """Average the weights of the masked vertices with their neighbours"""

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
    """Robust weight transfer from the source to the target (Abdrashitov et al. 2023)"""

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
        return weights, np.ones(n, dtype=bool), np.zeros(n, dtype=bool), True

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
    solved = True
    if len(unknown):
        lap_edges, lap_weights, mass = cotan_laplacian(co, tris)
        # Only the columns with weights within the operator reach of the unknown vertices
        around = np.zeros(n, dtype=bool)
        around[unknown] = True
        around = grow(around, lap_edges, 2)
        columns = np.nonzero(np.any(weights[around] > 0.0, axis=0))[0]
        values, solved = inpaint(lap_edges, lap_weights, mass, unknown, weights[:, columns])
        weights[unknown] = 0.0
        weights[np.ix_(unknown, columns)] = values

    weights = np.clip(weights, 0.0, 1.0)
    filled = np.zeros(n, dtype=bool)
    filled[unknown] = True
    if settings.smooth_all:
        smoothed = np.ones(n, dtype=bool)
    else:
        smoothed = grow(filled, edges, SEAM_RINGS) if len(edges) else filled
    weights = smooth_weights(weights, edges, smoothed, settings.smooth)
    weights = limit_influences(weights, settings.limit_influences)
    return weights, matched, filled, solved
