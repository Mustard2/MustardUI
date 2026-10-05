from . import (
    definitions,
    ops_cleanmodel,
    ops_configuration,
    ops_quick_setup,
    ops_removearm,
    ops_removeui,
    ops_smartcheck,
    ops_version_date,
)


def register():
    definitions.register()
    ops_configuration.register()
    ops_version_date.register()
    ops_quick_setup.register()
    ops_smartcheck.register()
    ops_cleanmodel.register()
    ops_removeui.register()
    ops_removearm.register()


def unregister():
    ops_removearm.unregister()
    ops_removeui.unregister()
    ops_cleanmodel.unregister()
    ops_smartcheck.unregister()
    ops_quick_setup.unregister()
    ops_version_date.unregister()
    ops_configuration.unregister()
    definitions.unregister()
