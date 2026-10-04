from . import (
    ops_naming,
    ops_rename,
    ops_rename_images,
)


def register():
    ops_rename.register()
    ops_rename_images.register()
    ops_naming.register()


def unregister():
    ops_naming.unregister()
    ops_rename_images.unregister()
    ops_rename.unregister()
