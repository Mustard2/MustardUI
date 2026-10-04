from . import ops_disintegration, ops_ripple


def register():
    ops_disintegration.register()
    ops_ripple.register()


def unregister():
    ops_ripple.unregister()
    ops_disintegration.unregister()
