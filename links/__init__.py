from . import ops_link
from . import ui_list
from . import definitions


def register():
    definitions.register()
    ops_link.register()
    ui_list.register()


def unregister():
    definitions.unregister()
    ops_link.unregister()
    ui_list.unregister()
