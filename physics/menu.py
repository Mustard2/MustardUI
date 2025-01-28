import bpy
from ..model_selection.active_object import *
from .. import __package__ as base_package
from .ops_add import MustardUI_PhysicsAddItem


class OUTLINER_MT_collection(bpy.types.Menu):
    bl_label = "Custom Action Collection"

    def draw(self, context):
        pass


def mustardui_physics_add_menu(self, context):

    res, arm = mustardui_active_object(context, config=1)
    physics_settings = arm.MustardUI_PhysicsSettings
    addon_prefs = context.preferences.addons[base_package].preferences

    if res and physics_settings.enable_ui:
        if not (context.object in [x.object for x in physics_settings.items]):
            self.layout.separator()
            if addon_prefs.debug:
                self.layout.operator(MustardUI_PhysicsAddItem.bl_idname, text="Add Physics Item: " + repr(context.object.name),
                                     icon="ADD")
            else:
                self.layout.operator(MustardUI_PhysicsAddItem.bl_idname, icon="ADD")


def register():
    bpy.types.OUTLINER_MT_object.append(mustardui_physics_add_menu)


def unregister():
    bpy.types.OUTLINER_MT_object.remove(mustardui_physics_add_menu)
