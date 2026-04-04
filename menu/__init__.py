from . import (
    menu_armature,
    menu_armature_external,
    menu_body,
    # Configure panel
    menu_configure,
    menu_configure_armature,
    # Sub-panels
    menu_configure_body,
    menu_configure_complete,
    menu_configure_debug,
    menu_configure_hair,
    menu_configure_links,
    menu_configure_morphs,
    menu_configure_others,
    menu_configure_outfit,
    menu_configure_physics,
    menu_configure_tools,
    menu_development,
    menu_hair,
    menu_links,
    menu_morphs,
    menu_outfits,
    menu_physics,
    menu_select_model,
    menu_settings,
    menu_simplify,
    menu_tools,
    menu_tools_creators,
    menu_warnings,
)


def register():
    menu_select_model.register()
    menu_development.register()
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
    menu_armature_external.register()
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
    menu_armature_external.unregister()
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
    menu_development.unregister()
    menu_select_model.unregister()
