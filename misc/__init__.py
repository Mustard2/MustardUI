from . import addon_prefs


def register():
    addon_prefs.register()


def unregister():
    addon_prefs.unregister()
