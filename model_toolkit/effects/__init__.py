from . import (
    ops_aura,
    ops_cloth_tear,
    ops_crush,
    ops_disintegration,
    ops_dust_motes,
    ops_dust_puff,
    ops_fireball,
    ops_foam,
    ops_hex_dissolve,
    ops_imprints,
    ops_jiggle,
    ops_marks,
    ops_ripple,
    ops_select_object,
    ops_shatter,
    ops_squish,
    ops_sticky_liquid,
    ops_sticky_strands,
    ops_wet,
    ops_wrap,
    settings,
    ui_list,
)


def register():
    ops_squish.register()
    ops_disintegration.register()
    ops_ripple.register()
    ops_jiggle.register()
    ops_fireball.register()
    ops_hex_dissolve.register()
    ops_cloth_tear.register()
    ops_shatter.register()
    ops_crush.register()
    ops_wrap.register()
    ops_sticky_strands.register()
    ops_sticky_liquid.register()
    ops_wet.register()
    ops_foam.register()
    ops_marks.register()
    ops_imprints.register()
    ops_dust_puff.register()
    ops_dust_motes.register()
    ops_aura.register()
    ops_select_object.register()
    settings.register()
    ui_list.register()


def unregister():
    ui_list.unregister()
    settings.unregister()
    ops_select_object.unregister()
    ops_aura.unregister()
    ops_dust_motes.unregister()
    ops_dust_puff.unregister()
    ops_imprints.unregister()
    ops_marks.unregister()
    ops_foam.unregister()
    ops_wet.unregister()
    ops_sticky_liquid.unregister()
    ops_sticky_strands.unregister()
    ops_wrap.unregister()
    ops_crush.unregister()
    ops_shatter.unregister()
    ops_cloth_tear.unregister()
    ops_hex_dissolve.unregister()
    ops_fireball.unregister()
    ops_jiggle.unregister()
    ops_ripple.unregister()
    ops_disintegration.unregister()
    ops_squish.unregister()
