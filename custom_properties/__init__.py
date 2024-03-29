from . import definitions
from . import ops_props
from . import ops_link
from . import menus
from . import ui_list
from . import ops_menu_settings
from . import ops_rebuild
from . import ops_smartcheck


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
