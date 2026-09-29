from . import (
    ops_add_outfit,
    ops_add_outfit_from_file,
    ops_export_outfits,
    ops_naming,
    ops_rename,
    ops_rename_images,
)


def register():
    ops_rename.register()
    ops_rename_images.register()
    ops_naming.register()
    ops_add_outfit.register()
    ops_add_outfit_from_file.register()
    ops_export_outfits.register()


def unregister():
    ops_export_outfits.unregister()
    ops_add_outfit_from_file.unregister()
    ops_add_outfit.unregister()
    ops_naming.unregister()
    ops_rename_images.unregister()
    ops_rename.unregister()
