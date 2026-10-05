from typing import NamedTuple

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from ...misc.mesh_deform import (
    NeighbourAverage,
    mesh_vertex_normals,
    triangle_barycentric,
)
from ...misc.mesh_intersection import intersecting_triangles

# Maximum movement of a vertex in one iteration, relative to the median edge length
MAX_STEP = 0.5
# Directions kept by the L-BFGS optimizer
HISTORY = 8
# Passes spreading the descent direction to the neighbour vertices
SMOOTHING_PASSES = 10
# Size of the patches spreading it over larger areas at once, relative to the median edge
# length, and their weight
COARSE_SIZE = 3.0
COARSE_WEIGHT = 2.0
# Weight of the repulsion between the outfit parts, relative to the shape preservation
REPULSION_WEIGHT = 100.0
# Weight of the repulsion from the body, stiffer so that the layers push each other outwards
BODY_WEIGHT = 1000.0
# Weight of the pull towards the body, and of the edge lengths relative to the shape
PULL_WEIGHT = 1.0
STRETCH_WEIGHT = 1.0
# Search radius of the self pairs, relative to the median edge length of the outfit
SELF_SEARCH = 3.0
# Height over the outfit triangles of the body vertices checked, relative to the median edge
BODY_POKE = 2.0
# Body vertices under an outfit triangle have normals at least this aligned with it
FACING = 0.3
# Barycentric tolerance of the body vertices over the outfit triangles
BORDER_TOLERANCE = 0.05
# Triangles are kept at least this fraction of their rest area, along their rest normal
MIN_AREA = 0.25
# Iterations between the updates of the body planes and the checks of the intersections
REFRESH_EVERY = 10
# The optimization stops when the energy decreases less than this between the checks
ENERGY_TOLERANCE = 0.02
# Movement after which the pairs of a vertex are searched again, relative to the median edge
REQUERY_DISTANCE = 0.2


class FitMetrics(NamedTuple):
    """Outfit vertices inside the body, triangles through it, and self intersecting pairs"""

    buried: int
    through: int
    crossing: int


def outfit_metrics(co, tris, body_bvh, buried):
    """Metrics of the outfit with the given coordinates and number of buried vertices"""

    bvh = BVHTree.FromPolygons(co.tolist(), tris.tolist())
    return FitMetrics(
        buried,
        len(np.unique(intersecting_triangles(bvh, body_bvh)[:, 0])),
        len(intersecting_triangles(bvh)),
    )


def triangle_normals(corners):
    """Unit normals of the triangles with the given corner coordinates"""

    normal = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    return normal / np.maximum(np.linalg.norm(normal, axis=1), 1e-30)[:, None]


def scatter(grad, index, values):
    for k in range(3):
        grad[:, k] += np.bincount(index, weights=values[:, k], minlength=len(grad))


class QueryCache:
    """Query results for moving points, queried again only when they moved"""

    def __init__(self, query, count, tolerance, tris=None):
        self.query = query
        self.tolerance = tolerance
        self.tris = tris
        self.queried = np.zeros(count, dtype=bool)
        self.where = np.zeros((count, 3))
        self.results = None

    def __call__(self, co, candidates):
        moved = ~self.queried | (np.linalg.norm(co - self.where, axis=1) > self.tolerance)
        if self.results is not None and self.tris is not None:
            # Pairs with a moved triangle
            points, faces = self.results[:2]
            moved[points[np.any(moved[self.tris[faces]], axis=1)]] = True
        stale = candidates[moved[candidates]]
        fresh = self.query(co, stale)
        self.queried[stale] = True
        self.where[stale] = co[stale]
        if self.results is not None:
            keep = ~np.isin(self.results[0], stale)
            fresh = tuple(
                np.concatenate((old[keep], new))
                for old, new in zip(self.results, fresh, strict=True)
            )
        self.results = fresh
        keep = np.isin(fresh[0], candidates)
        return tuple(x[keep] for x in fresh)


class FitOptimizer:
    """Outfit fit as the minimum of an energy, found with L-BFGS"""

    def __init__(self, target, body_co, body_tris, body_normals, body_bvh, winding):
        self.target = target
        self.body_co = body_co
        self.body_normals = body_normals
        self.body_bvh = body_bvh
        # Planes of the body faces, oriented as the vertex normals
        corners = body_co[body_tris]
        normals = triangle_normals(corners)
        outward = np.sign(np.einsum("ij,ij->i", normals, body_normals[body_tris].sum(axis=1)))
        self.face_normals = normals * np.where(outward == 0.0, 1.0, outward)[:, None]

        edges = target.edges
        self.edge = float(np.median(target.edge_lengths)) if len(edges) else 1e-3
        self.degree = np.maximum(np.bincount(edges.ravel(), minlength=target.n_verts), 1)
        self.history = []
        # Winding numbers of the body, shared with the metrics
        self.winding = winding
        self.set_rest(target.co)
        # Average of the neighbour vertices, for the preconditioning
        self.average = NeighbourAverage(edges, target.n_verts)
        # Patches grown along the edges from seeds spread in space, never across the pieces
        cells = np.floor((target.co - target.co.min(axis=0)) / (COARSE_SIZE * self.edge))
        _, seeds = np.unique(cells.astype(np.int64), axis=0, return_index=True)
        patch = np.full(target.n_verts, -1, dtype=np.int64)
        patch[seeds] = np.arange(len(seeds))
        while len(edges):
            reached = (patch[edges[:, 0]] >= 0) != (patch[edges[:, 1]] >= 0)
            if not np.any(reached):
                break
            pairs = edges[reached]
            new = np.where(patch[pairs[:, 0]] >= 0, pairs[:, 1], pairs[:, 0])
            patch[new] = np.maximum(patch[pairs[:, 0]], patch[pairs[:, 1]])
        # Pieces without a seed keep their vertices alone
        alone = np.nonzero(patch < 0)[0]
        patch[alone] = len(seeds) + np.arange(len(alone))
        self.patch = patch
        self.patch_size = np.bincount(patch).astype(np.float64)

    def set_rest(self, rest):
        """Shape kept by the optimization"""

        self.rest = rest
        edges = self.target.edges
        self.rest_lengths = np.linalg.norm(rest[edges[:, 0]] - rest[edges[:, 1]], axis=1)
        corners = rest[self.target.tris]
        self.rest_normals = triangle_normals(corners)
        self.rest_areas = 0.5 * np.linalg.norm(
            np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]), axis=1
        )

    def body_points(self, co, planes, gap):
        """Body vertices through or under the outfit triangles"""

        target = self.target
        tris = target.tris
        normals = triangle_normals(co[tris])
        # Outward side of the triangles from the body normals under their vertices
        under = np.zeros_like(co)
        i, _, under[i] = planes
        facing = np.einsum("ij,ij->i", normals, under[tris].sum(axis=1))
        outward = normals * np.sign(facing)[:, None]

        band = gap + BODY_POKE * self.edge
        inside = np.all((self.body_co >= co.min(axis=0) - band), axis=1)
        inside &= np.all((self.body_co <= co.max(axis=0) + band), axis=1)
        bvh = BVHTree.FromPolygons(co.tolist(), tris.tolist())
        found = []
        faces = []
        for b in np.nonzero(inside)[0]:
            face = bvh.find_nearest(Vector(self.body_co[b]), band)[2]
            if face is not None:
                found.append(b)
                faces.append(face)
        found = np.array(found, dtype=np.int64)
        faces = np.array(faces, dtype=np.int64)

        # Only the body surface under the triangles, facing the same way
        direction = outward[faces]
        keep = facing[faces] != 0.0
        keep &= np.einsum("ij,ij->i", self.body_normals[found], direction) > FACING
        height = np.einsum("ij,ij->i", self.body_co[found] - co[tris[faces, 0]], direction)
        keep &= height > -gap
        # Only the body vertices over the triangles, not beside their borders
        corners = tris[faces]
        bary = triangle_barycentric(self.body_co[found], co[corners], clamp=False)
        keep &= np.all(bary >= -BORDER_TOLERANCE, axis=1)
        bary = np.clip(bary[keep], 0.0, None)
        bary /= np.maximum(bary.sum(axis=1), 1e-12)[:, None]
        return found[keep], corners[keep], bary, direction[keep]

    def layer_rays(self, co, points, band):
        """Outfit triangles over and under the points"""

        tris = self.target.tris
        normals = mesh_vertex_normals(co, tris)
        bvh = BVHTree.FromPolygons(co.tolist(), tris.tolist())
        eps = 1e-4 * self.edge
        found = []
        faces = []
        locations = []
        for i in points:
            v = Vector(co[i])
            for d in (Vector(normals[i]), -Vector(normals[i])):
                hit, _, face, _ = bvh.ray_cast(v + d * eps, d, band)
                if hit is not None:
                    found.append(i)
                    faces.append(face)
                    locations.append(hit)
        found = np.array(found, dtype=np.int64)
        faces = np.array(faces, dtype=np.int64)
        locations = np.array(locations, dtype=np.float64).reshape(-1, 3)
        keep = ~np.any(tris[faces] == found[:, None], axis=1)
        found, faces = found[keep], faces[keep]
        return found, faces, triangle_barycentric(locations[keep], co[tris[faces]])

    def layer_faces(self, co, gap, rays):
        """Outfit vertices over or under an outfit triangle, keeping their side"""

        target = self.target
        found, faces, bary = rays
        corners = target.tris[faces]
        band = gap + SELF_SEARCH * self.edge
        normal = triangle_normals(co[corners])
        height = np.einsum(
            "ij,ij->i", co[found] - np.einsum("ij,ijk->ik", bary, co[corners]), normal
        )
        # Side at rest, when the vertex was over the same point of the triangle
        rest = self.rest
        rest_offset = rest[found] - np.einsum("ij,ijk->ik", bary, rest[corners])
        rest_normal = triangle_normals(rest[corners])
        rest_height = np.einsum("ij,ij->i", rest_offset, rest_normal)
        tangential = np.linalg.norm(rest_offset - rest_height[:, None] * rest_normal, axis=1)
        at_rest = (np.abs(rest_height) < band) & (tangential < self.edge)
        at_rest &= np.abs(rest_height) > 1e-7
        side = np.where(at_rest, np.sign(rest_height), np.sign(height))
        min_height = np.where(at_rest, np.minimum(np.abs(rest_height), gap), gap)
        return found, corners, bary, normal * side[:, None], min_height

    def body_planes(self, co, points, reach):
        """Outfit points near the body, with the plane through their nearest body point"""

        found = []
        faces = []
        origins = []
        for i in points:
            loc, _, face, _ = self.body_bvh.find_nearest(Vector(co[i]), reach)
            if loc is not None:
                found.append(i)
                faces.append(face)
                origins.append(loc)
        found = np.array(found, dtype=np.int64)
        origins = np.array(origins, dtype=np.float64).reshape(-1, 3)
        face_normals = self.face_normals[np.array(faces, dtype=np.int64)]
        offset = co[found] - origins
        distance = np.linalg.norm(offset, axis=1)
        # Towards the point, flipped when inside the body, the face normal on the surface
        side = np.where(np.einsum("ij,ij->i", offset, face_normals) < 0.0, -1.0, 1.0)
        normals = offset / np.maximum(distance, 1e-12)[:, None] * side[:, None]
        normals = np.where(distance[:, None] > 1e-9, normals, face_normals)
        return found, origins, normals

    @staticmethod
    def plane_heights(points, origins, normals):
        """Height of the points over the planes"""

        return np.einsum("ij,ij->i", points - origins, normals)

    def check(self, co, planes, gap):
        """Number of intersections and flipped triangles of the outfit"""

        # Only the vertices sunk under the body planes can be inside it
        i, origins, normals = planes
        sunk = i[self.plane_heights(co[i], origins, normals) < 0.5 * gap]
        buried = 0
        if len(sunk):
            buried = int(np.count_nonzero(np.abs(self.winding()(co[sunk])) > 0.5))

        tris = self.target.tris
        metrics = outfit_metrics(co, tris, self.body_bvh, buried)
        flipped = np.einsum("ij,ij->i", triangle_normals(co[tris]), self.rest_normals) < 0.0
        return sum(metrics) + int(np.count_nonzero(flipped))

    def energy(self, co, terms, pull, gap, stiffness):
        """Energy of the outfit coordinates and its gradient, with the pairs of the terms"""

        target = self.target
        grad = np.zeros_like(co)
        energy = 0.0

        # Signed repulsion from the planes of the body faces under the outfit, and pull
        i, origin, normal = terms["planes"]
        height = self.plane_heights(co[i], origin, normal) - gap
        missing = np.maximum(-height, 0.0)
        above = np.where(pull[i] > 0.0, np.maximum(height, 0.0), 0.0)
        energy += BODY_WEIGHT * np.dot(missing, missing)
        energy += PULL_WEIGHT * np.dot(pull[i], above**2)
        force = 2.0 * (PULL_WEIGHT * pull[i] * above - BODY_WEIGHT * missing)
        grad[i] += force[:, None] * normal

        # Centers of the outfit triangles under the body push their corners out
        if "centers" in terms and len(terms["centers"][0]):
            f, origin, normal = terms["centers"]
            corners = target.tris[f]
            height = self.plane_heights(co[corners].mean(axis=1), origin, normal) - gap
            missing = np.maximum(-height, 0.0)
            energy += BODY_WEIGHT * np.dot(missing, missing)
            push = (-2.0 * BODY_WEIGHT * missing / 3.0)[:, None] * normal
            for k in range(3):
                scatter(grad, corners[:, k], push)

        # Body vertices through the outfit triangles push them out
        if "body_points" in terms and len(terms["body_points"][0]):
            b, corners, bary, direction = terms["body_points"]
            point = np.einsum("ij,ijk->ik", bary, co[corners])
            missing = np.einsum("ij,ij->i", self.body_co[b] - point, direction) + gap
            missing = np.maximum(missing, 0.0)
            energy += BODY_WEIGHT * np.dot(missing, missing)
            for k in range(3):
                push = (-2.0 * BODY_WEIGHT * missing * bary[:, k])[:, None] * direction
                scatter(grad, corners[:, k], push)

        # Outfit vertices and triangles over each other keep their side
        if "faces" in terms and len(terms["faces"][0]):
            i, corners, bary, direction, min_height = terms["faces"]
            point = np.einsum("ij,ijk->ik", bary, co[corners])
            missing = min_height - np.einsum("ij,ij->i", co[i] - point, direction)
            missing = np.maximum(missing, 0.0)
            energy += REPULSION_WEIGHT * np.dot(missing, missing)
            push = (2.0 * REPULSION_WEIGHT * missing)[:, None] * direction
            scatter(grad, i, -push)
            for k in range(3):
                scatter(grad, corners[:, k], push * bary[:, k, None])

        # Triangles shrinking or flipping over
        tris = target.tris
        e1 = co[tris[:, 1]] - co[tris[:, 0]]
        e2 = co[tris[:, 2]] - co[tris[:, 0]]
        normal = self.rest_normals
        area = 0.5 * np.einsum("ij,ij->i", np.cross(e1, e2), normal)
        missing = np.maximum(MIN_AREA * self.rest_areas - area, 0.0)
        shrunk = np.nonzero(missing > 0.0)[0]
        if len(shrunk):
            scale = 1.0 / np.maximum(self.rest_areas[shrunk], 1e-30)
            energy += REPULSION_WEIGHT * np.dot(missing[shrunk] ** 2, scale)
            factor = (-2.0 * REPULSION_WEIGHT * missing[shrunk] * scale)[:, None]
            d1 = factor * 0.5 * np.cross(e2[shrunk], normal[shrunk])
            d2 = factor * 0.5 * np.cross(normal[shrunk], e1[shrunk])
            scatter(grad, tris[shrunk, 1], d1)
            scatter(grad, tris[shrunk, 2], d2)
            scatter(grad, tris[shrunk, 0], -(d1 + d2))

        # Smooth displacement, keeping the details of the outfit
        edges = target.edges
        disp = co - self.rest
        lap = self.average(disp) - disp
        back = self.degree[:, None] * self.average(lap / self.degree[:, None])
        energy += stiffness * np.einsum("ij,ij->", lap, lap)
        grad += 2.0 * stiffness * (back - lap)

        # Edge lengths
        vec = co[edges[:, 0]] - co[edges[:, 1]]
        length = np.maximum(np.linalg.norm(vec, axis=1), 1e-12)
        stretch = length - self.rest_lengths
        energy += STRETCH_WEIGHT * stiffness * np.dot(stretch, stretch)
        force = (2.0 * STRETCH_WEIGHT * stiffness * stretch / length)[:, None] * vec
        scatter(grad, edges[:, 0], force)
        scatter(grad, edges[:, 1], -force)
        return energy, grad

    def run(self, co, free, settings, rest):
        """Optimize the outfit keeping the rest shape, yielding the progress"""

        gap = settings.offset
        reach = gap + max(settings.max_depth, settings.fit_distance)
        max_step = MAX_STEP * self.edge
        points = np.nonzero(free)[0]
        target = self.target
        self.set_rest(rest)

        # Pull of the outfit vertices near the body at rest, fading out with the distance
        distance = settings.fit_distance
        pull = np.zeros(target.n_verts)
        if distance > 0.0:
            i, origins, normals = self.body_planes(rest, range(target.n_verts), gap + distance)
            height = self.plane_heights(rest[i], origins, normals) - gap
            # Full pull up to half the distance, then fading out
            t = np.clip(2.0 * height / distance - 1.0, 0.0, 1.0)
            near = (height > 0.0) & (height < distance)
            pull[i] = np.where(near, 1.0 - t * t * (3.0 - 2.0 * t), 0.0)

        def evaluate(x):
            energy, grad = self.energy(x, terms, pull, gap, settings.stiffness)
            grad[~free] = 0.0
            return energy, grad

        tolerance = REQUERY_DISTANCE * self.edge
        planes_cache = QueryCache(
            lambda co, stale: self.body_planes(co, stale, reach), target.n_verts, tolerance
        )
        corners = rest[target.tris]
        size = np.linalg.norm(corners - corners.mean(axis=1, keepdims=True), axis=2).max()
        centers_cache = QueryCache(
            lambda co, stale: self.body_planes(co, stale, gap + size), len(target.tris), tolerance
        )
        band = gap + SELF_SEARCH * self.edge
        rays_cache = QueryCache(
            lambda co, stale: self.layer_rays(co, stale, band),
            target.n_verts,
            tolerance,
            target.tris,
        )

        def refresh(x):
            terms = {"planes": planes_cache(x, points)}
            terms["body_points"] = self.body_points(x, terms["planes"], gap)
            # Triangles near the body, with the body face under their center, which sags under
            # the body when the triangles are larger than its details
            height = np.full(target.n_verts, np.inf)
            i, origins, normals = terms["planes"]
            height[i] = self.plane_heights(x[i], origins, normals)
            corners = x[target.tris]
            radius = corners - corners.mean(axis=1, keepdims=True)
            size = np.linalg.norm(radius, axis=2).max(axis=1)
            near = np.nonzero(height[target.tris].min(axis=1) < gap + size)[0]
            terms["centers"] = centers_cache(corners.mean(axis=1), near)
            if settings.self_collisions:
                rays = rays_cache(x, np.arange(target.n_verts))
                terms["faces"] = self.layer_faces(x, gap, rays)
            return terms

        x = co.copy()
        # The pairs and their normals are updated every few iterations
        terms = refresh(x)
        energy, grad = evaluate(x)
        # Smoothed gradient, and the directions with their smoothed gradient changes
        smoothed = self.precondition(grad, free)
        history = []
        self.history = [(0, energy, self.check(x, terms["planes"], gap))]
        # Only the optimized coordinates, the starting ones ignore the pull
        best = (np.inf, x)
        iterations = settings.iterations
        done = 0
        for it in range(iterations):
            yield it / iterations, f"Optimize {it + 1}/{iterations}"

            direction = self.direction(grad, smoothed, history, max_step)
            slope = np.vdot(grad, direction)
            if slope >= 0.0:
                history = []
                direction = self.direction(grad, smoothed, history, max_step)
                slope = np.vdot(grad, direction)
            if slope >= 0.0:
                break

            # Backtracking until the energy decreases enough
            t = 1.0
            while True:
                x_new = x + t * direction
                energy_new, grad_new = evaluate(x_new)
                if energy_new <= energy + 1e-4 * t * slope or t < 1e-3:
                    break
                t *= 0.5
            if energy_new >= energy:
                break

            smoothed_new = self.precondition(grad_new, free)
            step = x_new - x
            change = grad_new - grad
            if np.vdot(step, change) > 1e-30:
                history.append((step, change, smoothed_new - smoothed))
                del history[:-HISTORY]
            x, energy, grad, smoothed = x_new, energy_new, grad_new, smoothed_new
            done = it + 1

            # Keep the coordinates with less intersections, update the planes under the moved
            # vertices, and stop when converged
            if done % REFRESH_EVERY == 0:
                score = self.check(x, terms["planes"], gap)
                previous = self.history[-1][1]
                self.history.append((done, energy, score))
                if score <= best[0]:
                    best = (score, x.copy())
                # Net progress over a whole cycle, as each refresh raises the energy again
                if previous - energy < ENERGY_TOLERANCE * previous:
                    break
                terms = refresh(x)
                energy, grad = evaluate(x)
                smoothed = self.precondition(grad, free)
                history = []

        if self.check(x, terms["planes"], gap) <= best[0]:
            return x, done
        return best[1], done

    def precondition(self, q, free):
        """Spread the vector to the neighbour vertices, so that whole areas move together"""

        # Average of each patch, moving it as a whole
        means = np.stack([np.bincount(self.patch, weights=q[:, k]) for k in range(3)], axis=1)
        q = q + COARSE_WEIGHT * (means / self.patch_size[:, None])[self.patch]
        for _ in range(SMOOTHING_PASSES):
            q = 0.5 * q + 0.5 * self.average(q)
        q[~free] = 0.0
        return q

    @staticmethod
    def direction(grad, smoothed, history, max_step):
        """Preconditioned L-BFGS descent direction"""

        q = grad.copy()
        pq = smoothed.copy()
        factors = []
        for step, change, smoothed_change in reversed(history):
            rho = 1.0 / np.vdot(change, step)
            alpha = rho * np.vdot(step, q)
            q -= alpha * change
            pq -= alpha * smoothed_change
            factors.append((rho, alpha, step, change))
        if history:
            step, change, smoothed_change = history[-1]
            pq *= np.vdot(step, change) / max(np.vdot(change, smoothed_change), 1e-30)
        else:
            # Steepest descent moving the vertices up to the maximum step
            pq *= max_step / max(np.linalg.norm(pq, axis=1).max(), 1e-30)
        for rho, alpha, step, change in reversed(factors):
            beta = rho * np.vdot(change, pq)
            pq += step * (alpha - beta)
        direction = -pq
        longest = np.linalg.norm(direction, axis=1).max()
        if longest > max_step:
            direction *= max_step / longest
        return direction
