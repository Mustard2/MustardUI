from . import ops_delete, ops_transfer


def register():
    ops_transfer.register()
    ops_delete.register()


def unregister():
    ops_delete.unregister()
    ops_transfer.unregister()
