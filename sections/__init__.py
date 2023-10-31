from . import ops_add
from . import ops_assign
from . import ops_swap
from . import ui_list


def register():
    ops_add.register()
    ops_assign.register()
    ops_swap.register()
    ui_list.register()


def unregister():
    ops_add.unregister()
    ops_assign.unregister()
    ops_swap.unregister()
    ui_list.unregister()
