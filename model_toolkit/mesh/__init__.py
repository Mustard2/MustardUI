from . import (
    ops_fix_clipping,
    ops_link_shape_keys,
    ops_squish,
    ops_transfer_vertex_groups,
    shape_key_preview,
)


def register():
    ops_link_shape_keys.register()
    ops_transfer_vertex_groups.register()
    shape_key_preview.register()
    ops_squish.register()
    ops_fix_clipping.register()


def unregister():
    ops_fix_clipping.unregister()
    ops_squish.unregister()
    shape_key_preview.unregister()
    ops_transfer_vertex_groups.unregister()
    ops_link_shape_keys.unregister()
