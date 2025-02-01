from . import settings_item
from . import settings
from . import ops_cache
from . import menu
from . import ops_mirror
from . import ops_add
from . import ops_remove
from . import ui_list


def register():
    settings_item.register()
    settings.register()
    ops_cache.register()
    menu.register()
    ops_mirror.register()
    ops_add.register()
    ops_remove.register()
    ui_list.register()


def unregister():
    ui_list.unregister()
    ops_remove.unregister()
    ops_add.unregister()
    ops_mirror.unregister()
    menu.unregister()
    ops_cache.unregister()
    settings.unregister()
    settings_item.unregister()
