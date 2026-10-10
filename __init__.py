# MustardUI addon
# GitHub page: https://github.com/Mustard2/MustardUI

# Add-on information
bl_info = {
    "name": "MustardUI",
    "description": "Easy-to-use UI for human characters.",
    "author": "Mustard",
    "version": (2026, 10, 0),
    "blender": (4, 2, 0),
    "warning": "",
    "doc_url": "https://github.com/Mustard2/MustardUI/wiki",
    "category": "User Interface",
}

from . import (  # noqa: E402
    armature,
    configuration,
    custom_properties,
    hair,
    links,
    menu,
    misc,
    model_selection,
    model_toolkit,
    morphs,
    outfits,
    physics,
    presets,
    sections,
    settings,
    text_storage,
    tools,
    warnings,
)


def register():
    outfits.register()
    hair.register()
    sections.register()
    settings.register()
    misc.register()
    model_selection.register()
    presets.register()
    warnings.register()
    armature.register()
    tools.register()
    model_toolkit.register()
    custom_properties.register()
    physics.register()
    morphs.register()
    configuration.register()
    links.register()
    menu.register()
    text_storage.register()


def unregister():
    text_storage.unregister()
    menu.unregister()
    links.unregister()
    configuration.unregister()
    morphs.unregister()
    physics.unregister()
    custom_properties.unregister()
    model_toolkit.unregister()
    tools.unregister()
    armature.unregister()
    warnings.unregister()
    presets.unregister()
    model_selection.unregister()
    misc.unregister()
    settings.unregister()
    sections.unregister()
    hair.unregister()
    outfits.unregister()
