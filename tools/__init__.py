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
    settings.unregister()
    lattice.unregister()
    physics.unregister()
    eevee_normals.unregister()
    childof.unregister()
    auto_eyelid.unregister()
    auto_breath.unregister()
