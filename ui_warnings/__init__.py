from . import ops_fix_eevee_normals, ops_remove_old_UI, ops_update_ui


def register():
    ops_remove_old_UI.register()
    ops_fix_eevee_normals.register()
    ops_update_ui.register()


def unregister():
    ops_update_ui.unregister()
    ops_fix_eevee_normals.unregister()
    ops_remove_old_UI.unregister()
