from . import (
    ops_add_outfit,
    ops_naming,
    ops_rename,
    ops_rename_images,
)


def register():
    ops_rename.register()
    ops_rename_images.register()
    ops_naming.register()
    ops_add_outfit.register()


def unregister():
    ops_add_outfit.unregister()
    ops_naming.unregister()
    ops_rename_images.unregister()
    ops_rename.unregister()
