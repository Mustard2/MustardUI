from . import addon_prefs
from . import addon
from . import outfit
from . import section
from . import rig
from . import geometry_nodes


def register():
    addon_prefs.register()
    addon.register()
    outfit.register()
    section.register()
    rig.register()
    geometry_nodes.register()


def unregister():
    geometry_nodes.unregister()
    rig.unregister()
    section.unregister()
    outfit.unregister()
    addon.unregister()
    addon_prefs.unregister()
