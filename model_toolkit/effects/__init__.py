from . import (
    ops_cloth_tear,
    ops_disintegration,
    ops_fireball,
    ops_hex_dissolve,
    ops_ripple,
    ops_squish,
    ops_sticky_liquid,
    ops_sticky_strands,
    ops_wet,
    ops_wrap,
)


def register():
    ops_squish.register()
    ops_disintegration.register()
    ops_ripple.register()
    ops_fireball.register()
    ops_hex_dissolve.register()
    ops_cloth_tear.register()
    ops_wrap.register()
    ops_sticky_strands.register()
    ops_sticky_liquid.register()
    ops_wet.register()


def unregister():
    ops_wet.unregister()
    ops_sticky_liquid.unregister()
    ops_sticky_strands.unregister()
    ops_wrap.unregister()
    ops_cloth_tear.unregister()
    ops_hex_dissolve.unregister()
    ops_fireball.unregister()
    ops_ripple.unregister()
    ops_disintegration.unregister()
    ops_squish.unregister()
