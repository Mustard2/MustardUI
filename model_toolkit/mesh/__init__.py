from . import (
    ops_link_shape_keys,
    ops_select_preview_texture,
    ops_smooth_shape_key,
    ops_transfer_shape_keys,
    ops_transfer_vertex_groups,
    shape_key_preview,
)


def register():
    ops_link_shape_keys.register()
    ops_transfer_vertex_groups.register()
    ops_transfer_shape_keys.register()
    shape_key_preview.register()
    ops_smooth_shape_key.register()
    ops_select_preview_texture.register()


def unregister():
    ops_select_preview_texture.unregister()
    ops_smooth_shape_key.unregister()
    shape_key_preview.unregister()
    ops_transfer_shape_keys.unregister()
    ops_transfer_vertex_groups.unregister()
    ops_link_shape_keys.unregister()
