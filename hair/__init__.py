from . import ops_hair_visibility
from . import ops_optimize


def register():
    ops_hair_visibility.register()
    ops_optimize.register()


def unregister():
    ops_optimize.unregister()
    ops_hair_visibility.unregister()
