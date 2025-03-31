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

        if rig_settings.model_version != '':
            box = layout.box()
            box.label(text="Model Version: ", icon="INFO")
            box.label(text=rig_settings.model_version, icon="BLANK1")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_SettingsPanel)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_SettingsPanel)
