import bpy
from bpy.props import BoolProperty

from . import (
    ops_bone_physics,
    ops_collision_cage,
    ops_face_controller,
    ops_hair_cage,
    ops_hair_cage_add_cloth,
    ops_jiggle,
    ops_link_shape_keys,
    ops_rename,
    ops_spline_ik,
    ops_transfer_vertex_groups,
    ops_transformations,
)


def register():
    bpy.types.Object.MustardUI_tools_creators_is_created = BoolProperty(default=False)

    ops_transformations.register()
    ops_hair_cage_add_cloth.register()
    ops_hair_cage.register()
    ops_collision_cage.register()
    ops_spline_ik.register()
    ops_jiggle.register()
    ops_bone_physics.register()
    ops_face_controller.register()
    ops_rename.register()
    ops_link_shape_keys.register()
    ops_transfer_vertex_groups.register()


def unregister():
    ops_transfer_vertex_groups.unregister()
    ops_link_shape_keys.unregister()
    ops_rename.unregister()
    ops_face_controller.unregister()
    ops_bone_physics.unregister()
    ops_jiggle.unregister()
    ops_spline_ik.unregister()
    ops_collision_cage.unregister()
    ops_hair_cage.unregister()
    ops_hair_cage_add_cloth.unregister()
    ops_transformations.unregister()

    del bpy.types.Object.MustardUI_tools_creators_is_created
