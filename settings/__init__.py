from . import addon, addon_prefs, rig


def register():
    addon_prefs.register()
    addon.register()
    rig.register()


def unregister():
    rig.unregister()
    addon.unregister()
    addon_prefs.unregister()
