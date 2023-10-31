from . import definitions
from . import ui_list


def register():
    definitions.register()
    ui_list.register()


def unregister():
    definitions.unregister()
    ui_list.unregister()
