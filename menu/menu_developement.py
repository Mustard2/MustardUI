import bpy
import platform
from . import MainPanel
from ..model_selection.active_object import *
from ..warnings.ops_fix_old_UI import check_old_UI
from .. import __package__ as base_package


class PANEL_PT_MustardUI_Developement(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Developement"
    bl_label = "Developement"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):

        addon_prefs = context.preferences.addons[base_package].preferences

        if check_old_UI():
            return False

        res, obj = mustardui_active_object(context, config=0)

        if obj is not None:
            return res and addon_prefs.developer
        return False

    def draw(self, context):

        addon_prefs = context.preferences.addons[base_package].preferences

        layout = self.layout

        layout.operator('mustardui.configuration', text="UI Configuration", icon="PREFERENCES")

        layout.separator()
        layout.operator('mustardui.property_rebuild', icon="MOD_BUILD", text="Re-build Custom Properties")
        layout.operator('mustardui.cleanmodel', text="Clean model", icon="BRUSH_DATA")
        layout.operator('mustardui.remove', text="UI Removal", icon="X")

        if platform.system() == 'Windows' and addon_prefs.debug:
            layout.separator()
            layout.operator('wm.console_toggle', text="Toggle System Console", icon="CONSOLE")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_Developement)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Developement)
