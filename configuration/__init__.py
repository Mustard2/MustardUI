from . import (
    ops_cleanmodel,
    ops_configuration,
    ops_debug,
    ops_removearm,
    ops_removeui,
    ops_smartcheck,
)


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
