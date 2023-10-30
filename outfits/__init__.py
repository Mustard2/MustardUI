from . import ops_add
from . import ops_delete
from . import ops_remove
from . import ops_optimize
from . import ops_smartcheck
from . import ops_visibility
from . import menu


def register():
    ops_add.register()
    ops_delete.register()
    ops_remove.register()
    ops_optimize.register()
    ops_smartcheck.register()
    ops_visibility.register()
    menu.register()


def unregister():
    ops_add.unregister()
    ops_delete.unregister()
    ops_remove.unregister()
    ops_optimize.unregister()
    ops_smartcheck.unregister()
    ops_visibility.unregister()
    menu.unregister()
