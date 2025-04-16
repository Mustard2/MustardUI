import bpy
from . import ops_transformations
from . import ops_hair_cage_add_cloth
from . import ops_hair_cage
from . import ops_collision_cage
from . import ops_spline_ik
from . import ops_jiggle
from . import ops_bone_physics
from . import ops_rename


def register():
    bpy.types.Object.MustardUI_tools_creators_is_created = bpy.props.BoolProperty(default=False)

    ops_transformations.register()
    ops_hair_cage_add_cloth.register()
    ops_hair_cage.register()
    ops_collision_cage.register()
    ops_spline_ik.register()
    ops_jiggle.register()
    ops_bone_physics.register()
    ops_rename.register()


def unregister():
    ops_rename.unregister()
    ops_bone_physics.unregister()
    ops_jiggle.unregister()
    ops_spline_ik.unregister()
    ops_collision_cage.unregister()
    ops_hair_cage.unregister()
    ops_hair_cage_add_cloth.unregister()
    ops_transformations.unregister()

    del bpy.types.Object.MustardUI_tools_creators_is_created
