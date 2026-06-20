from . import (
    ops_add,
    ops_defvalue,
    ops_drivers,
    ops_optimize,
    settings,
    settings_morph,
    settings_presets,
    settings_section,
    ui_list_morphs,
    ui_list_morphs_menu,
    ui_list_sections,
)


def register():
    settings_morph.register()
    settings_section.register()
    settings_presets.register()
    settings.register()
    ops_add.register()
    ops_defvalue.register()
    ops_drivers.register()
    ops_optimize.register()
    ui_list_sections.register()
    ui_list_morphs.register()
    ui_list_morphs_menu.register()


def unregister():
    ui_list_morphs_menu.unregister()
    ui_list_morphs.unregister()
    ui_list_sections.unregister()
    ops_optimize.unregister()
    ops_drivers.unregister()
    ops_defvalue.unregister()
    ops_add.unregister()
    settings.unregister()
    settings_presets.unregister()
    settings_section.unregister()
    settings_morph.unregister()
