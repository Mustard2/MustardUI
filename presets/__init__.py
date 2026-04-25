from . import io, ops_apply, ops_create, ops_delete, ops_transfer, ui


def register():
    ops_apply.register()
    ops_create.register()
    ops_transfer.register()
    ops_delete.register()
    io.register()
    ui.register()


def unregister():
    ui.unregister()
    io.unregister()
    ops_delete.unregister()
    ops_transfer.unregister()
    ops_create.unregister()
    ops_apply.unregister()
