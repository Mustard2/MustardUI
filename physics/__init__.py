from . import (
    menu,
    ops_add,
    ops_cache,
    ops_hair_particles,
    ops_mirror,
    ops_rebind,
    ops_remove,
    ops_setup,
    settings,
    settings_item,
    ui_list,
    ui_list_menu,
    ui_list_outfits,
)


def register():
    settings_item.register()
    settings.register()
    ops_cache.register()
    menu.register()
    ops_setup.register()
    ops_mirror.register()
    ops_add.register()
    ops_remove.register()
    ops_rebind.register()
    ui_list.register()
    ui_list_outfits.register()
    ui_list_menu.register()
    ops_hair_particles.register()


def unregister():
    ops_hair_particles.unregister()
    ui_list_menu.unregister()
    ui_list_outfits.unregister()
    ui_list.unregister()
    ops_rebind.unregister()
    ops_remove.unregister()
    ops_add.unregister()
    ops_mirror.unregister()
    ops_setup.unregister()
    menu.unregister()
    ops_cache.unregister()
    settings.unregister()
    settings_item.unregister()
