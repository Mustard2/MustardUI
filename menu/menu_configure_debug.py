import bpy

from .. import __package__ as base_package
from ..model_selection.active_object import (
    ModelMode,
    active_object_operator_poll,
    mustardui_active_object,
)
from . import MainPanel


class PANEL_PT_MustardUI_InitPanel_Debug(MainPanel, bpy.types.Panel):
    bl_label = "Debug"
    bl_parent_id = "PANEL_PT_MustardUI_InitPanel"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        addon_prefs = context.preferences.addons[base_package].preferences
        return (
            addon_prefs.developer
            and addon_prefs.debug
            and active_object_operator_poll(context, config=ModelMode.CONFIG)
        )

    def draw_header(self, context):
        layout = self.layout
        layout.label(text="", icon="INFO")

    def draw(self, context):

        layout = self.layout

        res, arm = mustardui_active_object(context, config=ModelMode.CONFIG)
        rig_settings = arm.MustardUI_RigSettings

        box = layout.box()
        box.enabled = False
        box.prop(rig_settings, "model_armature_object", text="Armature Object")
        box.prop(rig_settings, "model_rig_type", text="Rig Type")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_InitPanel_Debug)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_InitPanel_Debug)
