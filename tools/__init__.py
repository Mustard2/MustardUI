from . import settings
from . import eevee_normals
from . import auto_eyelid
from . import auto_breath
from . import simplify


def register():
    settings.register()
    eevee_normals.register()
    auto_eyelid.register()
    auto_breath.register()
    simplify.register()


def unregister():
    simplify.unregister()
    auto_breath.unregister()
    auto_eyelid.unregister()
    eevee_normals.unregister()
    settings.unregister()
