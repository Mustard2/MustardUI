import bpy
from . import MainPanel
from ..model_selection.active_object import *
from ..warnings.ops_fix_old_UI import check_old_UI
import platform
from .. import __package__ as base_package


class PANEL_PT_MustardUI_SettingsPanel(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_SettingsPanel"
    bl_label = "Settings"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        if check_old_UI():
            return False

        res, arm = mustardui_active_object(context, config=0)
        return res

    def draw(self, context):

        settings = bpy.context.scene.MustardUI_Settings
        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings
        addon_prefs = context.preferences.addons[base_package].preferences

        layout = self.layout

        # Main Settings
        box = layout.box()
        col = box.column(align=True)

        col.prop(settings, "advanced")

        if settings.viewport_model_selection:
            box.operator('mustardui.viewportmodelselection', text="Viewport Model Selection", icon="VIEW3D",
                         depress=True)
        else:
            box.operator('mustardui.viewportmodelselection', text="Viewport Model Selection", icon="VIEW3D",
                         depress=False)

        if addon_prefs.developer:
            box = layout.box()
            box.label(text="Developer Tools", icon="SETTINGS")
            box.operator('mustardui.configuration', text="UI Configuration", icon="PREFERENCES")
            box.operator('mustardui.property_rebuild', icon="MOD_BUILD", text="Re-build Custom Properties")
            box.operator('mustardui.cleanmodel', text="Clean model", icon="BRUSH_DATA")
            box.operator('mustardui.remove', text="UI Removal", icon="X")

            box.separator()
            box.operator('mustardui.debug_log', text="Create Log file", icon="FILE_TEXT")
            if platform.system() == 'Windows':
                box.operator('wm.console_toggle', text="Toggle System Console", icon="CONSOLE")

        if rig_settings.model_version != '':
            box = layout.box()
            box.label(text="Version", icon="INFO")
            box.label(text="Model:                  " + rig_settings.model_version)


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_SettingsPanel)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_SettingsPanel)
