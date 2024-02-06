from . import ops_assign
from . import ui_list


def register():
    ops_assign.register()
    ui_list.register()


def unregister():
    ops_assign.unregister()
    ui_list.unregister()
