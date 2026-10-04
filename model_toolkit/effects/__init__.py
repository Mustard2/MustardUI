from . import (
    ops_disintegration,
    ops_fireball,
    ops_hex_dissolve,
    ops_ripple,
    ops_squish,
    ops_sticky_strands,
    ops_wrap,
)


def register():
    ops_squish.register()
    ops_disintegration.register()
    ops_ripple.register()
    ops_fireball.register()
    ops_hex_dissolve.register()
    ops_wrap.register()
    ops_sticky_strands.register()


def unregister():
    ops_sticky_strands.unregister()
    ops_wrap.unregister()
    ops_hex_dissolve.unregister()
    ops_fireball.unregister()
    ops_ripple.unregister()
    ops_disintegration.unregister()
    ops_squish.unregister()
