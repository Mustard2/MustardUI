class MainPanel:
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MustardUI"


from . import menu_select_model
from . import menu_warnings


# Configure panel
from . import menu_configure
from . import menu_developement
# Sub-panels
from . import menu_configure_body
from . import menu_configure_outfit
from . import menu_configure_hair
from . import menu_configure_armature
from . import menu_configure_physics
from . import menu_configure_tools
from . import menu_configure_morphs
from . import menu_configure_links
from . import menu_configure_others
from . import menu_configure_debug
from . import menu_configure_complete

from . import menu_tools_creators
from . import menu_body
from . import menu_morphs
from . import menu_outfits
from . import menu_hair
from . import menu_armature
from . import menu_simplify
from . import menu_physics
from . import menu_tools
from . import menu_settings
from . import menu_links


def register():
    menu_select_model.register()
    menu_developement.register()
    menu_warnings.register()
    menu_configure.register()
    menu_configure_body.register()
    menu_configure_outfit.register()
    menu_configure_hair.register()
    menu_configure_armature.register()
    menu_configure_physics.register()
    menu_configure_tools.register()
    menu_configure_morphs.register()
    menu_configure_links.register()
    menu_configure_others.register()
    menu_configure_debug.register()
    menu_configure_complete.register()
    menu_tools_creators.register()
    menu_body.register()
    menu_morphs.register()
    menu_outfits.register()
    menu_hair.register()
    menu_armature.register()
    menu_simplify.register()
    menu_physics.register()
    menu_tools.register()
    menu_settings.register()
    menu_links.register()


def unregister():
    menu_links.unregister()
    menu_settings.unregister()
    menu_tools.unregister()
    menu_physics.unregister()
    menu_simplify.unregister()
    menu_armature.unregister()
    menu_hair.unregister()
    menu_outfits.unregister()
    menu_morphs.unregister()
    menu_body.unregister()
    menu_tools_creators.unregister()
    menu_configure_complete.unregister()
    menu_configure_debug.unregister()
    menu_configure_others.unregister()
    menu_configure_links.unregister()
    menu_configure_morphs.unregister()
    menu_configure_tools.unregister()
    menu_configure_physics.unregister()
    menu_configure_armature.unregister()
    menu_configure_hair.unregister()
    menu_configure_outfit.unregister()
    menu_configure_body.unregister()
    menu_configure.unregister()
    menu_warnings.unregister()
    menu_developement.unregister()
    menu_select_model.unregister()
