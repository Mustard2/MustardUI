import bpy
from . import MainPanel
from ..model_selection.active_object import *
import platform


class PANEL_PT_MustardUI_SettingsPanel(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_SettingsPanel"
    bl_label = "Settings"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        return res

    def draw(self, context):

        settings = bpy.context.scene.MustardUI_Settings
        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings
        addon_prefs = context.preferences.addons["MustardUI"].preferences

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

        if rig_settings.model_version != '' or (addon_prefs.debug and rig_settings.diffeomorphic_support and settings.status_diffeomorphic_version[0] > 0):
            box = layout.box()
            box.label(text="Version", icon="INFO")
            if rig_settings.model_version != '':
                box.label(text="Model:                  " + rig_settings.model_version)
            if addon_prefs.debug and rig_settings.diffeomorphic_support:
                if settings.status_diffeomorphic_version[0] > 0:
                    box.label(text="Diffeomorphic:   " + str(settings.status_diffeomorphic_version[0]) + '.' + str(
                        settings.status_diffeomorphic_version[1]) + '.' + str(settings.status_diffeomorphic_version[2]))

        if addon_prefs.debug and (addon_prefs(rig_settings.model_rig_type == "arp" and settings.status_rig_tools == 0) or (
                rig_settings.model_rig_type == "arp" and settings.status_rig_tools == 1) or (
                settings.status_diffeomorphic == 0 and rig_settings.diffeomorphic_support) or (
                settings.status_diffeomorphic == 1 and rig_settings.diffeomorphic_support) or (
                (settings.status_diffeomorphic_version[0], settings.status_diffeomorphic_version[1], settings.status_diffeomorphic_version[2]) <= (1, 6, 0))):
            box = layout.box()

            if rig_settings.model_rig_type == "arp" and settings.status_rig_tools == 1:
                box.label(icon='ERROR', text="rig_tools not enabled!")
            elif rig_settings.model_rig_type == "arp" and settings.status_rig_tools == 0:
                box.label(icon='ERROR', text="rig_tools not installed!")

            if rig_settings.diffeomorphic_support:

                if settings.status_diffeomorphic == 1:
                    box.label(icon='ERROR', text="Diffeomorphic not enabled!")
                elif settings.status_diffeomorphic == 0:
                    box.label(icon='ERROR', text="Diffeomorphic not installed!")
                else:
                    if (settings.status_diffeomorphic_version[0], settings.status_diffeomorphic_version[1],
                        settings.status_diffeomorphic_version[2]) <= (1, 6, 0) and settings.status_diffeomorphic_version[0] > -1:
                        box.label(icon='ERROR', text="Diffeomorphic 1.5 or below are not supported!")
                    elif settings.status_diffeomorphic_version[0] == -1:
                        box.label(icon='ERROR', text="Diffeomorphic version not found!")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_SettingsPanel)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_SettingsPanel)
