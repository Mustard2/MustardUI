from . import addon_prefs
from . import addon
from . import rig
from . import geometry_nodes


def register():
    addon_prefs.register()
    addon.register()
    rig.register()
    geometry_nodes.register()


def unregister():
    geometry_nodes.unregister()
    rig.unregister()
    addon.unregister()
    addon_prefs.unregister()
