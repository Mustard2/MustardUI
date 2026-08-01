import bpy
from bpy.props import BoolProperty

from . import (
    ops_bone_physics,
    ops_jiggle_accurate,
    ops_collision_cage,
    ops_face_controller,
    ops_hair_cage,
    ops_jiggle,
    ops_link_shape_keys,
    ops_naming,
    ops_optimize_mods,
    ops_optimize_shaders,
    ops_optimize_sk,
    ops_pack_rgba,
    ops_physics_assign,
    ops_rename,
    ops_rename_images,
    ops_select_preview_texture,
    ops_spline_ik,
    ops_transfer_vertex_groups,
    ops_transformations,
    physics_presets,
)


def register():
    bpy.types.Object.MustardUI_tools_creators_is_created = BoolProperty(default=False)

    physics_presets.register()

    ops_transformations.register()
    ops_hair_cage.register()
    ops_collision_cage.register()
    ops_jiggle_accurate.register()
    ops_spline_ik.register()
    ops_jiggle.register()
    ops_bone_physics.register()
    ops_face_controller.register()
    ops_rename.register()
    ops_rename_images.register()
    ops_naming.register()
    ops_link_shape_keys.register()
    ops_transfer_vertex_groups.register()
    ops_pack_rgba.register()
    ops_physics_assign.register()
    ops_optimize_mods.register()
    ops_optimize_shaders.register()
    ops_select_preview_texture.register()
    ops_optimize_sk.register()


def unregister():
    ops_optimize_sk.unregister()
    ops_select_preview_texture.unregister()
    ops_optimize_shaders.unregister()
    ops_optimize_mods.unregister()
    ops_physics_assign.unregister()
    ops_pack_rgba.unregister()
    ops_transfer_vertex_groups.unregister()
    ops_link_shape_keys.unregister()
    ops_naming.unregister()
    ops_rename_images.unregister()
    ops_rename.unregister()
    ops_face_controller.unregister()
    ops_bone_physics.unregister()
    ops_jiggle.unregister()
    ops_spline_ik.unregister()
    ops_jiggle_accurate.unregister()
    ops_collision_cage.unregister()
    ops_hair_cage.unregister()
    ops_transformations.unregister()

    physics_presets.unregister()

    del bpy.types.Object.MustardUI_tools_creators_is_created
