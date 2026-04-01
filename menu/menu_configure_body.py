import bpy
from . import MainPanel
from ..model_selection.active_object import *
from ..warnings.ops_fix_old_UI import check_old_UI
from .. import __package__ as base_package
from .menu_configure import row_scale


class PANEL_PT_MustardUI_InitPanel_Body(MainPanel, bpy.types.Panel):
    bl_label = "Body"
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
        layout.label(text="", icon="OUTLINER_OB_ARMATURE")

    def draw(self, context):

        layout = self.layout
        scene = context.scene

        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings

        box = layout.box()
        box.label(text="Global properties", icon="MODIFIER")
        col = box.column(align=True)
        col.prop(rig_settings, "body_enable_subdiv")
        col.prop(rig_settings, "body_enable_smoothcorr")
        col.prop(rig_settings, "body_enable_norm_autosmooth")
        col.prop(rig_settings, "body_enable_geometry_nodes")
        col.prop(rig_settings, "body_enable_solidify")
        col.separator()
        col.prop(rig_settings, "body_enable_preserve_volume")
        col.prop(rig_settings, "body_enable_material_normal_nodes")

        # Custom properties
        box = layout.box()
        row = box.row()
        row.label(text="Custom properties", icon="PRESET_NEW")
        row.operator('mustardui.property_smartcheck', text="", icon="SHADERFX")

        if len(arm.MustardUI_CustomProperties) > 0:
            row = box.row()
            row.template_list("MUSTARDUI_UL_Property_UIList", "The_List", arm,
                              "MustardUI_CustomProperties", scene, "mustardui_property_uilist_index")
            col = row.column()
            col.operator('mustardui.property_settings', icon="PREFERENCES", text="").type = "BODY"
            col.separator()
            col2 = col.column(align=True)
            opup = col2.operator('mustardui.property_switch', icon="TRIA_UP", text="")
            opup.direction = "UP"
            opup.type = "BODY"
            opdown = col2.operator('mustardui.property_switch', icon="TRIA_DOWN", text="")
            opdown.direction = "DOWN"
            opdown.type = "BODY"
            col.separator()
            col.operator('mustardui.property_remove', icon="X", text="").type = "BODY"

            col = box.column(align=True)
            col.prop(rig_settings, 'body_custom_properties_icons')
            col.prop(rig_settings, 'body_custom_properties_name_order')

        else:
            box = box.box()
            box.label(text="No property added yet", icon="ERROR")

        # Sections
        box = layout.box()
        box.label(text="Sections", icon="LINENUMBERS_OFF")
        box.prop(rig_settings, "body_enable_geometry_nodes_support")
        if len(arm.MustardUI_CustomProperties) > 0:
            row = box.row()
            row.template_list("MUSTARDUI_UL_Section_UIList", "The_List", rig_settings,
                              "body_custom_properties_sections", scene,
                              "mustardui_section_uilist_index")
            col = row.column()
            col2 = col.column(align=True)
            col2.operator('mustardui.body_assign_to_section', text="", icon="PRESET")
            col.separator()
            col2 = col.column(align=True)
            col2.operator('mustardui.section_add', text="", icon="ADD")
            col2.operator('mustardui.body_deletesection', text="", icon="REMOVE")
            col.separator()
            col2 = col.column(align=True)
            opup = col2.operator('mustardui.section_switch', icon="TRIA_UP", text="")
            opup.direction = "UP"
            opdown = col2.operator('mustardui.section_switch', icon="TRIA_DOWN", text="")
            opdown.direction = "DOWN"

            if scene.mustardui_section_uilist_index > -1 and len(rig_settings.body_custom_properties_sections) > 0:
                sec = rig_settings.body_custom_properties_sections[scene.mustardui_section_uilist_index]

                row = box.row()
                row.label(text="Icon")
                row.scale_x = row_scale
                row.prop(sec, "icon", text="")

                col = box.column(align=True)

                row = col.row()
                row.label(text="Description")
                row.scale_x = row_scale
                row.prop(sec, "description", text="")

                row = col.row()
                row.enabled = sec.description != ""
                row.label(text="Icon")
                row.scale_x = row_scale
                row.prop(sec, "description_icon", text="")

                col = box.column(align=True)
                row = col.row()
                row.enabled = scene.mustardui_section_uilist_index != 0
                row.prop(sec, "is_subsection")

                col = box.column(align=True)

                row = col.row()
                row.prop(sec, "advanced")

                row = col.row()
                row.prop(sec, "collapsable")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_InitPanel_Body)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_InitPanel_Body)
