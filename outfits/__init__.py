from . import (
    definitions,
    menu,
    ops_add,
    ops_delete,
    ops_optimize,
    ops_remove,
    ops_rename_outfit,
    ops_select_config,
    ops_smartcheck,
    ops_visibility,
    ops_visibility_extras,
    ops_visibility_full,
    ui_list,
)


def register():
    definitions.register()
    ops_add.register()
    ops_delete.register()
    ops_remove.register()
    ops_optimize.register()
    ops_smartcheck.register()
    ops_visibility.register()
    ops_visibility_full.register()
    ops_visibility_extras.register()
    ops_rename_outfit.register()
    ops_select_config.register()
    ui_list.register()
    menu.register()


def unregister():
    menu.unregister()
    ui_list.unregister()
    ops_select_config.unregister()
    ops_rename_outfit.unregister()
    ops_visibility_extras.unregister()
    ops_visibility_full.unregister()
    ops_visibility.unregister()
    ops_smartcheck.unregister()
    ops_optimize.unregister()
    ops_remove.unregister()
    ops_delete.unregister()
    ops_add.unregister()
    definitions.unregister()
