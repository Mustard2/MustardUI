from . import addon_prefs
from . import addon
from . import outfit
from . import daz_morph
from . import section
from . import rig


def register():
    addon_prefs.register()
    addon.register()
    outfit.register()
    daz_morph.register()
    section.register()
    rig.register()


def unregister():
    addon_prefs.unregister()
    addon.unregister()
    outfit.unregister()
    daz_morph.unregister()
    section.unregister()
    rig.unregister()
