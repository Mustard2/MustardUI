from . import ops_transformations
from . import ops_hair_cage_add_cloth
from . import ops_hair_cage
from . import ops_collision_cage
from . import ops_spline_ik
from . import ops_jiggle


def register():
    ops_transformations.register()
    ops_hair_cage_add_cloth.register()
    ops_hair_cage.register()
    ops_collision_cage.register()
    ops_spline_ik.register()
    ops_jiggle.register()


def unregister():
    ops_jiggle.unregister()
    ops_spline_ik.unregister()
    ops_collision_cage.unregister()
    ops_hair_cage.unregister()
    ops_hair_cage_add_cloth.unregister()
    ops_transformations.unregister()
