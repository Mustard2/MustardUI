class MainPanel:
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MustardUI"


from . import menu_select_model
from . import menu_configure
from . import menu_body
from . import menu_morphs
from . import menu_outfits
from . import menu_hair
from . import menu_armature
from . import menu_simplify
from . import menu_tools_physics
from . import menu_tools_lattice
from . import menu_tools
from . import menu_settings
from . import menu_links


def register():
    menu_select_model.register()
    menu_configure.register()
    menu_body.register()
    menu_morphs.register()
    menu_outfits.register()
    menu_hair.register()
    menu_armature.register()
    menu_simplify.register()
    menu_tools_physics.register()
    menu_tools_lattice.register()
    menu_tools.register()
    menu_settings.register()
    menu_links.register()


def unregister():
    menu_select_model.unregister()
    menu_configure.unregister()
    menu_body.unregister()
    menu_morphs.unregister()
    menu_outfits.unregister()
    menu_hair.unregister()
    menu_armature.unregister()
    menu_simplify.unregister()
    menu_tools_physics.unregister()
    menu_tools_lattice.unregister()
    menu_tools.unregister()
    menu_settings.unregister()
    menu_links.unregister()
