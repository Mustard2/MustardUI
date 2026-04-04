from . import ops_hair_particles, ops_hair_visibility, ops_optimize


def register():
    ops_hair_visibility.register()
    ops_hair_particles.register()
    ops_optimize.register()


def unregister():
    ops_optimize.unregister()
    ops_hair_particles.unregister()
    ops_hair_visibility.unregister()
