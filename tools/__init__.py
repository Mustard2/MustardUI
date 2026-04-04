from . import (
    auto_breath,
    auto_eyelid,
    bone_shrinkwrap,
    eevee_normals,
    settings,
    simplify,
)


def register():
    settings.register()
    eevee_normals.register()
    auto_eyelid.register()
    auto_breath.register()
    bone_shrinkwrap.register()
    simplify.register()


def unregister():
    simplify.unregister()
    bone_shrinkwrap.unregister()
    auto_breath.unregister()
    auto_eyelid.unregister()
    eevee_normals.unregister()
    settings.unregister()
