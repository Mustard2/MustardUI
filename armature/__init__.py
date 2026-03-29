from . import definitions
from . import ops_smartcheck
from . import ops_clearpose
from . import ops_reset
from . import ops_transfer_animation
from . import ui_list
from . import external


def register():
    definitions.register()
    ops_smartcheck.register()
    ops_clearpose.register()
    ops_reset.register()
    ops_transfer_animation.register()
    ui_list.register()
    external.register()


def unregister():
    external.unregister()
    ui_list.unregister()
    ops_transfer_animation.unregister()
    ops_reset.unregister()
    ops_clearpose.unregister()
    ops_smartcheck.unregister()
    definitions.unregister()
