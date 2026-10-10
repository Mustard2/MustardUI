import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

# Triangles per leaf, and children per node, of the winding numbers tree
WINDING_LEAF = 4
WINDING_BRANCH = 4
# Nodes farther than this times their radius use the far field approximation
WINDING_BETA = 2.0


class MeshIntersectionChecker:
    """Intersection checks between objects, building each BVH tree once"""

    def __init__(self):
        self._cache = {}

    def _get(self, obj):
        """World bounding box and BVH tree of the evaluated mesh"""

        data = self._cache.get(obj.name)
        if data is None:
            # Hidden objects are not evaluated
            hide = obj.hide_viewport
            if hide:
                obj.hide_viewport = False
            eval_obj = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
            bm = bmesh.new()
            bm.from_mesh(eval_obj.to_mesh())
            bm.transform(obj.matrix_world)
            bm.normal_update()
            bvh = BVHTree.FromBMesh(bm)
            bm.free()
            eval_obj.to_mesh_clear()
            if hide:
                obj.hide_viewport = hide

            corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
            mins = [min(c[i] for c in corners) for i in range(3)]
            maxs = [max(c[i] for c in corners) for i in range(3)]
            data = (mins, maxs, bvh)
            self._cache[obj.name] = data
        return data

    def intersect(self, obj1, obj2):
        min1, max1, bvh1 = self._get(obj1)
        min2, max2, bvh2 = self._get(obj2)
        # Cheap bounding box test first
        if any(max1[i] < min2[i] or max2[i] < min1[i] for i in range(3)):
            return False
        return len(bvh1.overlap(bvh2)) > 0


def intersecting_triangles(bvh, other=None):
    """Pairs of intersecting triangles between the trees, or within the tree without other"""

    if other is not None:
        return np.array(bvh.overlap(other), dtype=np.int64).reshape(-1, 2)
    # The pairs are found in both orders, the triangles sharing an edge are skipped
    pairs = np.array(bvh.overlap(bvh), dtype=np.int64).reshape(-1, 2)
    return pairs[pairs[:, 0] < pairs[:, 1]]


class WindingNumbers:
    """Generalized winding numbers of a triangle mesh (Jacobson et al. 2013)"""

    def __init__(self, co, tris, leaf=WINDING_LEAF, branch=WINDING_BRANCH, beta=WINDING_BETA):
        self.leaf = leaf
        self.branch = branch
        self.beta = beta
        a, b, c = co[tris[:, 0]], co[tris[:, 1]], co[tris[:, 2]]
        # Triangles sorted along a Morton curve, so that the close ones share the tree nodes
        centers = (a + b + c) / 3.0
        lo = centers.min(axis=0)
        span = max(float((centers.max(axis=0) - lo).max()), 1e-12)
        cells = np.minimum((centers - lo) * (1024.0 / span), 1023.0).astype(np.uint64)
        code = np.zeros(len(centers), dtype=np.uint64)
        for axis in range(3):
            x = cells[:, axis]
            for shift, mask in (
                (16, 0x030000FF),
                (8, 0x0300F00F),
                (4, 0x030C30C3),
                (2, 0x09249249),
            ):
                x = (x | (x << np.uint64(shift))) & np.uint64(mask)
            code |= x << np.uint64(axis)
        order = np.argsort(code, kind="stable")
        n_leaves = max(-(-len(order) // leaf), 1)
        # Leaves padded with degenerate triangles, having no solid angle
        valid = np.zeros(n_leaves * leaf, dtype=bool)
        valid[: len(order)] = True
        order = np.concatenate((order, np.full(len(valid) - len(order), order[-1])))
        a, b, c = a[order], b[order], c[order]
        b[~valid] = a[~valid]
        c[~valid] = a[~valid]
        shape = (n_leaves, leaf, 3)
        self.a, self.b, self.c = a.reshape(shape), b.reshape(shape), c.reshape(shape)

        # Leaves, then the parents of the nodes close along the Morton curve, up to the root
        dipole = 0.5 * np.cross(self.b - self.a, self.c - self.a)
        size = np.linalg.norm(dipole, axis=-1)
        center = self._center(size, (self.a + self.b + self.c) / 3.0)
        corners = np.concatenate((self.a, self.b, self.c), axis=1) - center[:, None]
        radius = np.linalg.norm(corners, axis=-1).max(axis=1)
        self.levels = [(center, dipole.sum(axis=1), radius, size.sum(axis=1))]
        while len(self.levels[-1][0]) > 1:
            center, dipole, radius, size = self.levels[-1]
            n = -(-len(center) // branch)
            pad = n * branch - len(center)
            # Padding children with no area, never visited
            center = np.concatenate((center, np.repeat(center[-1:], pad, axis=0)))
            radius = np.concatenate((radius, np.repeat(radius[-1:], pad)))
            dipole = np.concatenate((dipole, np.zeros((pad, 3))))
            size = np.concatenate((size, np.zeros(pad)))
            children = center.reshape(n, branch, 3)
            parent = self._center(size.reshape(n, branch), children)
            spread = np.linalg.norm(children - parent[:, None], axis=-1) + radius.reshape(n, branch)
            self.levels.append(
                (
                    parent,
                    dipole.reshape(n, branch, 3).sum(axis=1),
                    spread.max(axis=1),
                    size.reshape(n, branch).sum(axis=1),
                )
            )

    @staticmethod
    def _center(size, centers):
        """Area weighted center of the children, their average without area"""

        total = size.sum(axis=1)
        weighted = np.einsum("ij,ijk->ik", size, centers) / np.maximum(total, 1e-30)[:, None]
        return np.where(total[:, None] > 0.0, weighted, centers.mean(axis=1))

    def __call__(self, points, chunk=4096):
        points = np.asarray(points, dtype=np.float64).reshape(-1, 3)
        winding = np.zeros(len(points))
        for start in range(0, len(points), chunk):
            q = points[start : start + chunk]
            total = np.zeros(len(q))
            # Pairs of points and nodes still to visit, from the root
            qi = np.arange(len(q))
            ni = np.zeros(len(q), dtype=np.int64)
            for depth in range(len(self.levels) - 1, -1, -1):
                center, dipole, radius, _ = self.levels[depth]
                d = center[ni] - q[qi]
                dist = np.linalg.norm(d, axis=1)
                near = dist <= self.beta * radius[ni]
                far = ~near
                flux = np.einsum("ij,ij->i", d[far], dipole[ni[far]]) / dist[far] ** 3
                total += np.bincount(qi[far], weights=flux, minlength=len(q))
                qi, ni = qi[near], ni[near]
                if depth:
                    # Children of the near nodes
                    n_children = len(self.levels[depth - 1][0])
                    qi = np.repeat(qi, self.branch)
                    ni = (ni[:, None] * self.branch + np.arange(self.branch)).ravel()
                    keep = ni < n_children
                    qi, ni = qi[keep], ni[keep]

            # Exact solid angles of the triangles of the near leaves (Van Oosterom & Strackee)
            for k in range(0, len(qi), 16384):
                bq, bn = qi[k : k + 16384], ni[k : k + 16384]
                p = q[bq][:, None]
                a, b, c = self.a[bn] - p, self.b[bn] - p, self.c[bn] - p
                la, lb, lc = (np.linalg.norm(x, axis=-1) for x in (a, b, c))
                det = np.einsum("...i,...i->...", a, np.cross(b, c))
                div = la * lb * lc
                div += np.einsum("...i,...i->...", a, b) * lc
                div += np.einsum("...i,...i->...", b, c) * la
                div += np.einsum("...i,...i->...", c, a) * lb
                angles = 2.0 * np.arctan2(det, div)
                total += np.bincount(bq, weights=angles.sum(axis=1), minlength=len(q))
            winding[start : start + len(q)] = total / (4.0 * np.pi)
        return winding
