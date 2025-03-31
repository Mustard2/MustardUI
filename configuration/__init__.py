from . import ops_configuration
from . import ops_smartcheck
from . import ops_cleanmodel
from . import ops_debug
from . import ops_removeui
from . import ops_removearm


def register():
    ops_configuration.register()
    ops_smartcheck.register()
    ops_cleanmodel.register()
    ops_debug.register()
    ops_removeui.register()
    ops_removearm.register()


def unregister():
    ops_removearm.unregister()
    ops_removeui.unregister()
    ops_debug.unregister()
    ops_cleanmodel.unregister()
    ops_smartcheck.unregister()
    ops_configuration.unregister()
