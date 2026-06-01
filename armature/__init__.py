from . import (
    definitions,
    external,
    ops_clearpose,
    ops_reset,
    ops_select_armature,
    ops_smartcheck,
    ops_transfer_animation,
    ik_fk_snapper,
    ui_list,
)


def register():
    definitions.register()
    ops_smartcheck.register()
    ops_clearpose.register()
    ops_reset.register()
    ops_transfer_animation.register()
    ops_select_armature.register()
    ui_list.register()
    ik_fk_snapper.register()
    external.register()


def unregister():
    external.unregister()
    ik_fk_snapper.unregister()
    ui_list.unregister()
    ops_select_armature.unregister()
    ops_transfer_animation.unregister()
    ops_reset.unregister()
    ops_clearpose.unregister()
    ops_smartcheck.unregister()
    definitions.unregister()
