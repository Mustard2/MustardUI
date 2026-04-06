from . import (
    definitions,
    external,
    ops_clearpose,
    ops_reset,
    ops_smartcheck,
    ops_transfer_animation,
    ui_list,
)


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
