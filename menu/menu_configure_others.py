import bpy
from . import MainPanel
from ..model_selection.active_object import *
from ..warnings.ops_fix_old_UI import check_old_UI
from .. import __package__ as base_package
from .menu_configure import row_scale


class PANEL_PT_MustardUI_InitPanel_Others(MainPanel, bpy.types.Panel):
    bl_label = "Version & Others"
    bl_parent_id = "PANEL_PT_MustardUI_InitPanel"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        if check_old_UI():
            return False

        res, arm = mustardui_active_object(context, config=1)
        addon_prefs = context.preferences.addons[base_package].preferences
        return res and addon_prefs.developer

    def draw_header(self, context):
        layout = self.layout
        layout.label(text="", icon="SETTINGS")

    def draw(self, context):

        layout = self.layout

        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings

        box = layout.box()
        box.label(text="Version", icon="INFO")
        box.prop(rig_settings, "model_version", text="")

        box = layout.box()
        box.label(text="Naming", icon="OUTLINER_DATA_FONT")
        box.prop(rig_settings, "model_MustardUI_naming_convention")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_InitPanel_Others)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_InitPanel_Others)
