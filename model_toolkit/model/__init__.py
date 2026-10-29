from . import (
    ops_naming,
    ops_rename,
    ops_rename_images,
    ops_scale_character,
)


def register():
    ops_rename.register()
    ops_rename_images.register()
    ops_naming.register()
    ops_scale_character.register()


def unregister():
    ops_scale_character.unregister()
    ops_naming.unregister()
    ops_rename_images.unregister()
    ops_rename.unregister()
