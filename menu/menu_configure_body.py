import bpy

from .. import __package__ as base_package
from ..model_selection.active_object import mustardui_active_object
from ..warnings.can_draw_ui import can_draw_ui
from . import MainPanel


class PANEL_PT_MustardUI_InitPanel_Body(MainPanel, bpy.types.Panel):
    bl_label = "Body"
    bl_parent_id = "PANEL_PT_MustardUI_InitPanel"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        if can_draw_ui():
            return False

        res, arm = mustardui_active_object(context, config=1)
        addon_prefs = context.preferences.addons[base_package].preferences
        return res and addon_prefs.developer

    def draw_header(self, context):
        layout = self.layout
        layout.label(text="", icon="OUTLINER_OB_ARMATURE")

    def draw(self, context):

        layout = self.layout

        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings

        box = layout.box()
        box.label(text="General Settings", icon="MODIFIER")
        col = box.column(align=True)
        col.prop(
            rig_settings,
            "body_enable_geometry_nodes_support",
            text="Add Geometry Nodes as Sections",
        )

        box = layout.box()
        box.label(text="Global Properties", icon="PROPERTIES")
        col = box.column(align=True)
        col.prop(rig_settings, "body_enable_subdiv")
        col.prop(rig_settings, "body_enable_smoothcorr")
        col.prop(rig_settings, "body_enable_geometry_nodes")
        col.prop(rig_settings, "body_enable_solidify")
        col.separator()
        col.prop(rig_settings, "body_enable_preserve_volume")
        col.prop(rig_settings, "body_enable_material_normal_nodes")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_InitPanel_Body)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_InitPanel_Body)
