from . import (
    ops_optimize_mods,
    ops_optimize_shaders,
    ops_optimize_sk,
    ops_select_preview_texture,
)


def register():
    ops_optimize_mods.register()
    ops_optimize_shaders.register()
    ops_select_preview_texture.register()
    ops_optimize_sk.register()


def unregister():
    ops_optimize_sk.unregister()
    ops_select_preview_texture.unregister()
    ops_optimize_shaders.unregister()
    ops_optimize_mods.unregister()
