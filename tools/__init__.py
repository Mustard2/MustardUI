from . import auto_breath, auto_eyelid, eevee_normals, settings, simplify


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
