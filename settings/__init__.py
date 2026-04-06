from . import addon, addon_prefs, geometry_nodes, rig


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
