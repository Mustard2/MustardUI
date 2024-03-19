from . import ops_link
from . import ops_preset
from . import ui_list
from . import definitions


def register():
    definitions.register()
    ops_link.register()
    ops_preset.register()
    ui_list.register()


def unregister():
    ui_list.unregister()
    ops_preset.unregister()
    ops_link.unregister()
    definitions.unregister()
