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

        settings = bpy.context.scene.MustardUI_Settings

        layout = self.layout

        res, arm = mustardui_active_object(context, config=1)
        addon_prefs = context.preferences.addons[base_package].preferences
        physics_settings = arm.MustardUI_PhysicsSettings

        box = layout.box()
        box.label(text="General Settings", icon="MODIFIER")
        box.prop(physics_settings, "enable_ui")

        box = layout.box()
        box.enabled = physics_settings.enable_ui
        box.label(text="Physics Items", icon="MODIFIER")

        index = arm.mustardui_physics_items_uilist_index

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

            if index > -1:
                pi = physics_settings.items[index]

                col = box.column()
                row = col.row()
                row.prop(pi, 'type')

                col = box.column(align=True)
                col.prop(pi, 'outfit_enable')
                if pi.outfit_enable:
                    col.prop(pi, 'outfit_collection', text="Collection")
                    if pi.outfit_collection is not None:
                        col.prop(pi, 'outfit_object', text="Object")

            if settings.advanced and index > -1 and len(
                    physics_settings.items[arm.mustardui_physics_items_uilist_index].intersecting_objects) > 0:
                box = layout.box()
                box.label(text="Outfits Affected by Physics Item", icon="XRAY")

                row = box.row()
                row.template_list("MUSTARDUI_UL_PhysicsItems_Outfits_UIList", "The_List",
                                  physics_settings.items[arm.mustardui_physics_items_uilist_index],
                                  "intersecting_objects", arm,
                                  "mustardui_physics_items_outfits_uilist_index")
                col = row.column()
                col.operator('mustardui.physics_setup_intersecting_objects', icon="XRAY", text="").unique = True
                col.separator()
                col.operator("mustardui.physics_intersecting_object_remove", text="", icon="X")

        else:

            col = box.column()
            col.label(text="No Physics Item found", icon="ERROR")
            col.label(text="Right-click on Objects in Outliner to add", icon="BLANK1")

        box = layout.box()
        box.label(text="Outfits Support", icon="MOD_CLOTH")
        row = box.row(align=True)
        row.operator('mustardui.physics_setup', icon="PHYSICS")
        if settings.advanced:
            row.operator('mustardui.physics_setup_intersecting_objects', icon="XRAY", text="").unique = False
        row.operator('mustardui.physics_setup_clear', icon="X", text="")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_InitPanel_Physics)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_InitPanel_Physics)
