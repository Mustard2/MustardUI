from . import definitions
from . import ops_add
from . import ops_delete
from . import ops_remove
from . import ops_optimize
from . import ops_smartcheck
from . import ops_visibility
from . import ops_rename_outfit
from . import menu
from . import ui_list


def register():
    definitions.register()
    ops_add.register()
    ops_delete.register()
    ops_remove.register()
    ops_optimize.register()
    ops_smartcheck.register()
    ops_visibility.register()
    ops_rename_outfit.register()
    ui_list.register()
    menu.register()


def unregister():
    menu.unregister()
    ui_list.unregister()
    ops_rename_outfit.unregister()
    ops_visibility.unregister()
    ops_smartcheck.unregister()
    ops_optimize.unregister()
    ops_remove.unregister()
    ops_delete.unregister()
    ops_add.unregister()
    definitions.unregister()
