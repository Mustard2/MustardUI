from . import (
    definitions,
    menus,
    ops_link,
    ops_menu_settings,
    ops_props,
    ops_rebuild,
    ops_smartcheck,
    ui_list,
)


def register():
    definitions.register()
    ops_props.register()
    ops_link.register()
    menus.register()
    ui_list.register()
    ops_menu_settings.register()
    ops_rebuild.register()
    ops_smartcheck.register()


def unregister():
    ops_smartcheck.unregister()
    ops_rebuild.unregister()
    ops_menu_settings.unregister()
    ui_list.unregister()
    menus.unregister()
    ops_link.unregister()
    ops_props.unregister()
    definitions.unregister()
