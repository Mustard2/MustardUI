from . import settings_morph
from . import settings_section
from . import settings_presets
from . import settings
from . import ops_checkmorphs
from . import ops_defvalue
from . import ops_drivers
from . import ui_list_sections
from . import ui_list_morphs
from . import ui_list_morphs_menu
from . import ui_presets
from . import ops_presets_io


def register():
    settings_morph.register()
    settings_section.register()
    settings_presets.register()
    settings.register()
    ops_checkmorphs.register()
    ops_defvalue.register()
    ops_drivers.register()
    ui_list_sections.register()
    ui_list_morphs.register()
    ui_list_morphs_menu.register()
    ui_presets.register()
    ops_presets_io.register()


def unregister():
    ops_presets_io.unregister()
    ui_presets.unregister()
    ui_list_morphs_menu.unregister()
    ui_list_morphs.unregister()
    ui_list_sections.unregister()
    ops_drivers.unregister()
    ops_defvalue.unregister()
    ops_checkmorphs.unregister()
    settings.unregister()
    settings_presets.unregister()
    settings_section.unregister()
    settings_morph.unregister()
