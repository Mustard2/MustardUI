from . import ops_checkmorphs
from . import ops_clearpose
from . import ops_defvalue
from . import ops_drivers


def register():
    ops_checkmorphs.register()
    ops_clearpose.register()
    ops_defvalue.register()
    ops_drivers.register()


def unregister():
    ops_drivers.unregister()
    ops_defvalue.unregister()
    ops_clearpose.unregister()
    ops_checkmorphs.unregister()
