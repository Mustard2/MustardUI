import bpy
from . import MainPanel
from ..model_selection.active_object import *
from ..warnings.ops_fix_old_UI import check_old_UI
from .. import __package__ as base_package


class PANEL_PT_MustardUI_InitPanel_Links(MainPanel, bpy.types.Panel):
    bl_label = "Links"
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
        layout.label(text="", icon="WORLD")

    def draw(self, context):

        layout = self.layout
        scene = context.scene

        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings

        box = layout.box()

        box.label(text="General Settings", icon="MODIFIER")
        box.prop(rig_settings, 'links_enable')

        # Outfits list panel
        box = layout.box()
        row = box.row(align=True)
        row.label(text="Links List", icon="URL")
        row.operator("mustardui.link_import", text="", icon="COPYDOWN")
        row.operator("mustardui.link_export", text="", icon="PASTEDOWN")
        row = box.row()
        row.template_list("MUSTARDUI_UL_Links_UIList", "The_List", arm,
                          "MustardUI_Links", scene,
                          "mustardui_links_uilist_index")
        col = row.column()
        col2 = col.column(align=True)
        col2.operator("mustardui.link_add", text="", icon="ADD")
        col2.operator("mustardui.link_remove", text="", icon="REMOVE")
        col.separator()
        col2 = col.column(align=True)
        opup = col2.operator('mustardui.link_switch', icon="TRIA_UP", text="")
        opup.direction = "UP"
        opdown = col2.operator('mustardui.link_switch', icon="TRIA_DOWN", text="")
        opdown.direction = "DOWN"


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_InitPanel_Links)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_InitPanel_Links)
