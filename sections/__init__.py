from . import ops_add
from . import ops_delete
from . import ops_assign
from . import ops_swap
from . import ops_menu_settings


def register():
    ops_add.register()
    ops_delete.register()
    ops_assign.register()
    ops_swap.register()
    ops_menu_settings.register()


def unregister():
    ops_add.unregister()
    ops_delete.unregister()
    ops_assign.unregister()
    ops_swap.unregister()
    ops_menu_settings.unregister()
