from . import ops_configuration
from . import ops_smartcheck
from . import ops_cleanmodel
from . import ops_debug
from . import ops_removeui


def register():
    ops_configuration.register()
    ops_smartcheck.register()
    ops_cleanmodel.register()
    ops_debug.register()
    ops_removeui.register()


def unregister():
    ops_configuration.unregister()
    ops_smartcheck.unregister()
    ops_cleanmodel.unregister()
    ops_debug.unregister()
    ops_removeui.unregister()
