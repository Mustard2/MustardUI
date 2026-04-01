from . import settings_item
from . import settings
from . import ops_cache
from . import menu
from . import ops_setup
from . import ops_mirror
from . import ops_add
from . import ops_remove
from . import ops_delete
from . import ops_rebind
from . import ui_list
from . import ui_list_outfits
from . import ui_list_menu
from . import settings_presets
from . import ops_presets_io
from . import ui_presets


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
