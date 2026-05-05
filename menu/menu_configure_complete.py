import bpy

from .. import __package__ as base_package
from ..model_selection.active_object import mustardui_active_object
from ..warnings.can_draw_ui import can_draw_ui
from . import MainPanel


class PANEL_PT_MustardUI_InitPanel_Complete(MainPanel, bpy.types.Panel):
    bl_label = "Outfit"
    bl_parent_id = "PANEL_PT_MustardUI_InitPanel"
    bl_options = {"HIDE_HEADER"}

    @classmethod
    def poll(cls, context):
        if can_draw_ui():
            return False

        res, arm = mustardui_active_object(context, config=1)
        addon_prefs = context.preferences.addons[base_package].preferences
        return res and addon_prefs.developer

    def draw(self, context):

        layout = self.layout

        settings = bpy.context.scene.MustardUI_Settings
        res, arm = mustardui_active_object(context, config=1)

        # Configuration button
        col = layout.column(align=True)
        col.prop(settings, "advanced")
        if not arm.MustardUI_created:
            col.prop(settings, "viewport_model_selection_after_configuration")
        layout.operator("mustardui.configuration", text="End the configuration")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_InitPanel_Complete)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_InitPanel_Complete)
