from . import (
    auto_breath,
    auto_eyelid,
    bone_shrinkwrap,
    eevee_normals,
    lipsync,
    settings,
    simplify,
)


def register():
    settings.register()
    eevee_normals.register()
    auto_eyelid.register()
    auto_breath.register()
    lipsync.register()
    bone_shrinkwrap.register()
    simplify.register()


def unregister():
    simplify.unregister()
    bone_shrinkwrap.unregister()
    lipsync.unregister()
    auto_breath.unregister()
    auto_eyelid.unregister()
    eevee_normals.unregister()
    settings.unregister()
