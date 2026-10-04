from . import (
    ops_accessory_physics,
    ops_bone_physics,
    ops_collision_cage,
    ops_hair_cage,
    ops_jiggle,
    ops_jiggle_accurate,
    ops_physics_assign,
    ops_remove_physics,
    physics_presets,
)


def register():
    physics_presets.register()
    ops_hair_cage.register()
    ops_collision_cage.register()
    ops_jiggle_accurate.register()
    ops_jiggle.register()
    ops_bone_physics.register()
    ops_physics_assign.register()
    ops_accessory_physics.register()
    ops_remove_physics.register()


def unregister():
    ops_remove_physics.unregister()
    ops_accessory_physics.unregister()
    ops_physics_assign.unregister()
    ops_bone_physics.unregister()
    ops_jiggle.unregister()
    ops_jiggle_accurate.unregister()
    ops_collision_cage.unregister()
    ops_hair_cage.unregister()
    physics_presets.unregister()
