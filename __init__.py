# MustardUI addon
# GitHub page: https://github.com/Mustard2/MustardUI

# Add-on information
bl_info = {
    "name": "MustardUI",
    "description": "Easy-to-use UI for human characters.",
    "author": "Mustard",
    "version": (2026, 1, 0),
    "blender": (4, 2, 0),
    "warning": "",
    "doc_url": "https://github.com/Mustard2/MustardUI/wiki",
    "category": "User Interface",
}

from . import settings
from . import misc
from . import model_selection
from . import warnings
from . import armature
from . import tools
from . import tools_creators
from . import custom_properties
from . import sections
from . import outfits
from . import physics
from . import morphs
from . import configuration
from . import links
from . import menu
from . import viewport_panel


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
