import bpy
import bmesh
from mathutils.bvhtree import BVHTree


def check_mesh_intersection(obj1, obj2):
    def get_bvh_tree(obj):
        # Ensure the object is a mesh and up to date
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
        return bvh

    hide_viewport1 = obj1.hide_viewport
    obj1.hide_viewport = False
    hide_viewport2 = obj2.hide_viewport
    obj2.hide_viewport = False

    bvh1 = get_bvh_tree(obj1)
    bvh2 = get_bvh_tree(obj2)

    # Check for overlaps between two BVH trees
    overlap = bvh1.overlap(bvh2)

    obj1.hide_viewport = hide_viewport1
    obj2.hide_viewport = hide_viewport2

    return len(overlap) > 0
