from . import settings
from . import eevee_normals
from . import auto_eyelid
from . import auto_breath


def register():
    settings.register()
    eevee_normals.register()
    auto_eyelid.register()
    auto_breath.register()


def unregister():
    auto_breath.unregister()
    auto_eyelid.unregister()
    eevee_normals.unregister()
    settings.unregister()
