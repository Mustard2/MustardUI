from . import settings
from . import lattice
from . import physics
from . import eevee_normals
from . import childof
from . import auto_eyelid
from . import auto_breath


def register():
    settings.register()
    lattice.register()
    physics.register()
    eevee_normals.register()
    childof.register()
    auto_eyelid.register()
    auto_breath.register()


def unregister():
    auto_breath.unregister()
    auto_eyelid.unregister()
    childof.unregister()
    eevee_normals.unregister()
    physics.unregister()
    lattice.unregister()
    settings.unregister()
