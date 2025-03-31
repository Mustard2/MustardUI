import bpy
from . import MainPanel
from ..model_selection.active_object import *
from ..warnings.ops_fix_old_UI import check_old_UI
from .. import __package__ as base_package


class PANEL_PT_MustardUI_InitPanel_Physics(MainPanel, bpy.types.Panel):
    bl_label = "Physics"
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
        layout.label(text="", icon="PHYSICS")

    def draw(self, context):

        layout = self.layout

        res, arm = mustardui_active_object(context, config=1)
        physics_settings = arm.MustardUI_PhysicsSettings

        box = layout.box()
        box.label(text="General Settings", icon="MODIFIER")
        box.prop(physics_settings, "enable_ui")

        box = layout.box()
        box.enabled = physics_settings.enable_ui
        box.label(text="Physics Items", icon="MODIFIER")

        if len(physics_settings.items):

            row = box.row()
            row.template_list("MUSTARDUI_UL_PhysicsItems_UIList", "The_List", physics_settings,
                              "items", arm,
                              "mustardui_physics_items_uilist_index")
            col = row.column()
            col2 = col.column(align=True)
            opup = col2.operator('mustardui.physics_items_switch', icon="TRIA_UP", text="")
            opup.direction = "UP"
            opdown = col2.operator('mustardui.physics_items_switch', icon="TRIA_DOWN", text="")
            opdown.direction = "DOWN"
            col.separator()
            col.operator("mustardui.physics_item_remove", text="", icon="X")

            index = arm.mustardui_physics_items_uilist_index
            if index > -1:
                pi = physics_settings.items[index]

                col = box.column()
                row = col.row()
                row.prop(pi, 'type')

        else:

            col = box.column()
            col.label(text="No Physics Item found", icon="ERROR")
            col.label(text="Right-click on Objects in Outliner to add", icon="BLANK1")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_InitPanel_Physics)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_InitPanel_Physics)
