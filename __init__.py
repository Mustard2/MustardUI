# MustardUI addon
# GitHub page: https://github.com/Mustard2/MustardUI

from . import (
    armature,
    configuration,
    custom_properties,
    links,
    menu,
    misc,
    model_selection,
    morphs,
    outfits,
    physics,
    sections,
    settings,
    tools,
    tools_creators,
    viewport_panel,
    warnings,
)

# Add-on information
bl_info = {
    "name": "MustardUI",
    "description": "Easy-to-use UI for human characters.",
    "author": "Mustard",
    "version": (2025, 8, 2),
    "blender": (5, 0, 0),
    "warning": "",
    "doc_url": "https://github.com/Mustard2/MustardUI/wiki",
    "category": "User Interface",
}


def register():
    outfits.register()
    sections.register()
    settings.register()
    misc.register()
    model_selection.register()
    warnings.register()
    armature.register()
    tools.register()
    tools_creators.register()
    custom_properties.register()
    physics.register()
    morphs.register()
    configuration.register()
    links.register()
    menu.register()
    viewport_panel.register()


def unregister():
    viewport_panel.unregister()
    menu.unregister()
    links.unregister()
    configuration.unregister()
    morphs.unregister()
    physics.unregister()
    custom_properties.unregister()
    tools_creators.unregister()
    tools.unregister()
    armature.unregister()
    warnings.unregister()
    model_selection.unregister()
    misc.unregister()
    settings.unregister()
    sections.unregister()
    outfits.unregister()
