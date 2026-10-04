from . import ops_disintegration, ops_fireball, ops_hex_dissolve, ops_ripple


def register():
    ops_disintegration.register()
    ops_ripple.register()
    ops_fireball.register()
    ops_hex_dissolve.register()


def unregister():
    ops_hex_dissolve.unregister()
    ops_fireball.unregister()
    ops_ripple.unregister()
    ops_disintegration.unregister()
