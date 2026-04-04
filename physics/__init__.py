from . import (
    menu,
    ops_add,
    ops_cache,
    ops_delete,
    ops_mirror,
    ops_presets_io,
    ops_rebind,
    ops_remove,
    ops_setup,
    settings,
    settings_item,
    settings_presets,
    ui_list,
    ui_list_menu,
    ui_list_outfits,
    ui_presets,
)


def register():
    settings_item.register()
    settings_presets.register()
    settings.register()
    ops_cache.register()
    menu.register()
    ops_setup.register()
    ops_mirror.register()
    ops_add.register()
    ops_remove.register()
    ops_delete.register()
    ops_rebind.register()
    ui_list.register()
    ui_list_outfits.register()
    ui_list_menu.register()
    ops_presets_io.register()
    ui_presets.register()


def unregister():
    ui_presets.unregister()
    ops_presets_io.unregister()
    ui_list_menu.unregister()
    ui_list_outfits.unregister()
    ui_list.unregister()
    ops_rebind.unregister()
    ops_delete.unregister()
    ops_remove.unregister()
    ops_add.unregister()
    ops_mirror.unregister()
    ops_setup.unregister()
    menu.unregister()
    ops_cache.unregister()
    settings.unregister()
    settings_presets.unregister()
    settings_item.unregister()
