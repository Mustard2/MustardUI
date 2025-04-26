import bpy
from . import MainPanel
from ..model_selection.active_object import *
from ..warnings.ops_fix_old_UI import check_old_UI
from .. import __package__ as base_package
from .menu_configure import row_scale


class PANEL_PT_MustardUI_InitPanel_Morphs(MainPanel, bpy.types.Panel):
    bl_label = "Morphs"
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
        layout.label(text="", icon="EXPORT")

    def draw(self, context):

        layout = self.layout

        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings
        morphs_settings = arm.MustardUI_MorphsSettings

        box = layout.box()
        box.label(text="General", icon="MODIFIER")
        row = box.row()
        row.prop(morphs_settings, "enable_ui", text="Enable Morph Panel")

        row = box.row(align=True)
        row.enabled = morphs_settings.enable_ui and not morphs_settings.sections
        row.label(text="Type:")
        row.scale_x = 5
        row.prop(morphs_settings, "type", text="")

        row = box.row(align=True)
        row.operator('mustardui.morphs_check', text="Search and Add Morphs", icon="ADD")
        row.operator('mustardui.morphs_clear', text="", icon="X")

        if not morphs_settings.sections and morphs_settings.type == "GENERIC":
            box = layout.box()
            box.label(text="Sections and Morphs",
                      icon="SHAPEKEY_DATA" if morphs_settings.type != "GENERIC" else "LINENUMBERS_OFF")
            box.operator("mustardui.morphs_section_add", text="Add a Section", icon="ADD")

        if morphs_settings.sections:
            box = layout.box()
            box.enabled = morphs_settings.enable_ui
            box.label(text="Sections and Morphs", icon="SHAPEKEY_DATA" if morphs_settings.type != "GENERIC" else "LINENUMBERS_OFF")
            row = box.row()
            row.template_list("MUSTARDUI_UL_Morphs_Section_UIList", "The_List", morphs_settings,
                              "sections", arm,
                              "mustardui_morphs_section_uilist_index")
            col = row.column()
            col.enabled = morphs_settings.type == "GENERIC"
            col2 = col.column(align=True)
            col2.operator("mustardui.morphs_section_add", text="", icon="ADD")
            col2.operator("mustardui.morphs_section_remove", text="", icon="X")
            col.separator()
            col2 = col.column(align=True)
            col2.operator('mustardui.morphs_section_items_switch', icon="TRIA_UP", text="").direction = "UP"
            col2.operator('mustardui.morphs_section_items_switch', icon="TRIA_DOWN", text="").direction = "DOWN"

            if morphs_settings.type == "GENERIC":
                section = morphs_settings.sections[arm.mustardui_morphs_section_uilist_index]

                col = box.column(align=True)
                col.prop(section, 'icon')
                col.prop(section, 'shape_keys')
                col.prop(section, 'custom_properties')
                col.prop(section, 'string')

            if (arm.mustardui_morphs_section_uilist_index > -1 and
                    morphs_settings.sections[arm.mustardui_morphs_section_uilist_index].morphs):
                if morphs_settings.type == "GENERIC":
                    box = layout.box()
                    box.label(text="Morphs", icon="SHAPEKEY_DATA")

                row = box.row()
                row.template_list("MUSTARDUI_UL_Morphs_UIList", "The_List",
                                  morphs_settings.sections[arm.mustardui_morphs_section_uilist_index], "morphs",
                                  arm, "mustardui_morphs_uilist_index")
                col = row.column()
                col2 = col.column(align=True)
                col2.operator('mustardui.morphs_items_switch', icon="TRIA_UP", text="").direction = "UP"
                col2.operator('mustardui.morphs_items_switch', icon="TRIA_DOWN", text="").direction = "DOWN"
                col.separator()
                col.operator("mustardui.morphs_remove", text="", icon="X")

                if morphs_settings.type == "GENERIC":
                    box.prop(morphs_settings, 'show_type_icon')

            if morphs_settings.type != "GENERIC":
                box = layout.box()
                box.enabled = morphs_settings.enable_ui
                row = box.row(align=True)
                row.label(text="Disable Exceptions")
                row.scale_x = row_scale
                row.prop(rig_settings, "diffeomorphic_disable_exceptions", text="")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_InitPanel_Morphs)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_InitPanel_Morphs)
