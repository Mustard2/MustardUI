import bpy
from . import MainPanel
from ..model_selection.active_object import *
from ..warnings.ops_fix_old_UI import check_old_UI
from .. import __package__ as base_package


class PANEL_PT_MustardUI_SettingsPanel(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_SettingsPanel"
    bl_label = "Info & Settings"
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

        layout = self.layout

        # Main Settings
        box = layout.box()
        col = box.column(align=True)
        col.prop(settings, "advanced")

        if tuple(rig_settings.model_version_vector) > (0, 0, 0):
            box = layout.box()
            box.label(text="Model Version: ", icon="INFO")
            version = rig_settings.model_version_vector
            version = str(version[0]) + "." + str(version[1]) + "." + str(version[2])
            if rig_settings.model_version_type != "Standard":
                version = version + " " + rig_settings.model_version_type
            if rig_settings.model_version_date_enable and rig_settings.model_version_date != "":
                version = version + ' - ' + rig_settings.model_version_date
            prop = rig_settings.bl_rna.properties["model_version_type"]
            icon = prop.enum_items[rig_settings.model_version_type].icon
            box.label(text=version, icon=icon)

        # Left for old compatibility (Deprecated in MustardUI 2025.8)
        elif tuple(rig_settings.model_version_vector) == (0, 0, 0) and rig_settings.model_version != '':
            box = layout.box()
            box.label(text="Model Version: ", icon="INFO")
            version = rig_settings.model_version
            if rig_settings.model_version_date_enable and rig_settings.model_version_date != "":
                version = version + ' - ' + rig_settings.model_version_date
            box.label(text=version, icon="BLANK1")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_SettingsPanel)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_SettingsPanel)
