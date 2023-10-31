import bpy
from bpy.props import *
from ..model_selection.active_object import *


# Addon preferences can be accessed with
#       preferences = context.preferences
#       addon_prefs = preferences.addons[__name__].preferences
class MustardUI_AddonPrefs(bpy.types.AddonPreferences):
    bl_idname = "MustardUI"

    def draw(self, context):
        layout = self.layout
        settings = bpy.context.scene.MustardUI_Settings
        layout.prop(settings, "maintenance")


def register():
    bpy.utils.register_class(MustardUI_AddonPrefs)


def unregister():
    bpy.utils.unregister_class(MustardUI_AddonPrefs)
