from . import ops_fix_old_UI
from . import ops_fix_eevee_normals


def register():
    ops_fix_old_UI.register()
    ops_fix_eevee_normals.register()


def unregister():
    ops_fix_old_UI.unregister()
    ops_fix_eevee_normals.unregister()
