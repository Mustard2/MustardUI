from . import (
    ops_add_outfit,
    ops_add_outfit_from_file,
    ops_export_outfits,
)


def register():
    ops_add_outfit.register()
    ops_add_outfit_from_file.register()
    ops_export_outfits.register()


def unregister():
    ops_export_outfits.unregister()
    ops_add_outfit_from_file.unregister()
    ops_add_outfit.unregister()
