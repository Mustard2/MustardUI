import bpy

from .. import __package__ as base_package
from ..model_selection.active_object import (
    ModelMode,
    active_object_operator_poll,
    mustardui_active_object,
)
from . import MainPanel

row_scale = 1.2


class PANEL_PT_MustardUI_InitPanel(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_InitPanel"
    bl_label = "UI Configuration"

    url_MustardUI_ConfigGuide = "https://github.com/Mustard2/MustardUI/wiki/Developer-Guide"

    @classmethod
    def poll(cls, context):
        addon_prefs = context.preferences.addons[base_package].preferences
        return addon_prefs.developer and active_object_operator_poll(
            context, config=ModelMode.CONFIG
        )

    def draw(self, context):

        layout = self.layout

        res, arm = mustardui_active_object(context, config=ModelMode.CONFIG)
        rig_settings = arm.MustardUI_RigSettings

        # General Settings
        row = layout.row(align=False)
        row.label(text=arm.name, icon="OUTLINER_DATA_ARMATURE")
        row.operator("mustardui.configuration_smartcheck", icon="SHADERFX", text="")
        row.operator("wm.url_open", text="", icon="QUESTION").url = self.url_MustardUI_ConfigGuide

        box = layout.box()
        col = box.column()
        col.prop(rig_settings, "model_name", text="Name")
        col.prop(rig_settings, "model_body", text="Body")

        box.prop(rig_settings, "model_MustardUI_naming_convention")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_InitPanel)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_InitPanel)
