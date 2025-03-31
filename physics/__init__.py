from . import settings_item
from . import settings
from . import ops_cache
from . import menu
from . import ops_mirror
from . import ops_add
from . import ops_remove
from . import ops_rebind
from . import ui_list
from . import ui_list_menu
from . import ops_hair_particles


def register():
    settings_item.register()
    settings.register()
    ops_cache.register()
    menu.register()
    ops_mirror.register()
    ops_add.register()
    ops_remove.register()
    ops_rebind.register()
    ui_list.register()
    ui_list_menu.register()
    ops_hair_particles.register()


def unregister():
    ops_hair_particles.unregister()
    ui_list_menu.unregister()
    ui_list.unregister()
    ops_rebind.unregister()
    ops_remove.unregister()
    ops_add.unregister()
    ops_mirror.unregister()
    menu.unregister()
    ops_cache.unregister()
    settings.unregister()
    settings_item.unregister()
