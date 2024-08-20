from . import definitions
from . import ops_smartcheck
from . import ops_reset
from . import ui_list


def register():
    definitions.register()
    ops_smartcheck.register()
    ops_reset.register()
    ui_list.register()


def unregister():
    ui_list.unregister()
    ops_reset.unregister()
    ops_smartcheck.unregister()
    definitions.unregister()
