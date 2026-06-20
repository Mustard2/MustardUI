import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def build_bvh(obj):
    """Build a world-space BVHTree from an object's evaluated mesh."""
    # hide_viewport excludes the object from depsgraph evaluation, so toggle it
    # off (only when needed) to get an up-to-date evaluated mesh.
    hide = obj.hide_viewport
    if hide:
        obj.hide_viewport = False

    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(depsgraph)
    mesh = eval_obj.to_mesh()

    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.transform(obj.matrix_world)
    bm.normal_update()

    bvh = BVHTree.FromBMesh(bm)

    bm.free()
    eval_obj.to_mesh_clear()

    if hide:
        obj.hide_viewport = hide

    return bvh


def world_aabb(obj):
    """Return (min_corner, max_corner) of an object's world-space bounding box."""
    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    mins = Vector([min(c[i] for c in corners) for i in range(3)])
    maxs = Vector([max(c[i] for c in corners) for i in range(3)])
    return mins, maxs


def aabb_overlap(aabb1, aabb2):
    """Cheap axis-aligned bounding box overlap test in world space."""
    min1, max1 = aabb1
    min2, max2 = aabb2
    for i in range(3):
        if max1[i] < min2[i] or max2[i] < min1[i]:
            return False
    return True


class MeshIntersectionChecker:
    """Caches per-object BVH trees and bounding boxes so repeated intersection
    checks (e.g. one cage against many outfit objects) only build each tree once.

    The cache is keyed by object name and is only valid while geometry and
    transforms remain unchanged, so create a fresh checker per batch/operator run.
    """

    def __init__(self):
        self._cache = {}

    def _get(self, obj):
        data = self._cache.get(obj.name)
        if data is None:
            data = (world_aabb(obj), build_bvh(obj))
            self._cache[obj.name] = data
        return data

    def intersect(self, obj1, obj2):
        aabb1, bvh1 = self._get(obj1)
        aabb2, bvh2 = self._get(obj2)

        # Reject non-overlapping pairs with a cheap bounding box test before
        # running the full BVH overlap.
        if not aabb_overlap(aabb1, aabb2):
            return False

        return len(bvh1.overlap(bvh2)) > 0


def check_mesh_intersection(obj1, obj2):
    """One-shot intersection test. Prefer MeshIntersectionChecker when testing
    the same objects repeatedly."""
    if not aabb_overlap(world_aabb(obj1), world_aabb(obj2)):
        return False
    return len(build_bvh(obj1).overlap(build_bvh(obj2))) > 0
