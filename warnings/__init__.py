from . import ops_fix_old_UI
from . import ops_fix_eevee_normals
from . import ops_fix_old_morphs


def register():
    ops_fix_old_UI.register()
    ops_fix_eevee_normals.register()
    ops_fix_old_morphs.register()


def unregister():
    ops_fix_old_morphs.unregister()
    ops_fix_eevee_normals.unregister()
    ops_fix_old_UI.unregister()
