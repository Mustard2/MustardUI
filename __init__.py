# MustardUI addon
# GitHub page: https://github.com/Mustard2/MustardUI

# Add-on information
bl_info = {
    "name": "MustardUI",
    "description": "Easy-to-use UI for human characters.",
    "author": "Mustard",
    "version": (0, 30, 3, 2),
    "blender": (4, 0, 0),
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
from . import diffeomorphic
from . import configuration
from . import links
from . import menu


def register():
    settings.register()
    misc.register()
    model_selection.register()
    warnings.register()
    armature.register()
    tools.register()
    tools_creators.register()
    custom_properties.register()
    sections.register()
    outfits.register()
    diffeomorphic.register()
    configuration.register()
    links.register()
    menu.register()


def unregister():
    settings.unregister()
    misc.unregister()
    model_selection.unregister()
    warnings.unregister()
    armature.unregister()
    tools.unregister()
    tools_creators.unregister()
    custom_properties.unregister()
    sections.unregister()
    outfits.unregister()
    diffeomorphic.unregister()
    configuration.unregister()
    links.unregister()
    menu.unregister()
