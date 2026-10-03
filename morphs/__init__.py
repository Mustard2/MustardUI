from . import (
    ops_add,
    ops_defvalue,
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
    ui_list_sections.register()
    ui_list_morphs.register()
    ui_list_morphs_menu.register()


def unregister():
    ui_list_morphs_menu.unregister()
    ui_list_morphs.unregister()
    ui_list_sections.unregister()
    ops_defvalue.unregister()
    ops_add.unregister()
    settings.unregister()
    settings_presets.unregister()
    settings_section.unregister()
    settings_morph.unregister()
