from . import ops_select, ops_vms


def register():
    ops_select.register()
    ops_vms.register()


def unregister():
    ops_vms.unregister()
    ops_select.unregister()
