import bpy
from bpy.props import *
from ..model_selection.active_object import *


class MustardUI_Body_AssignToSection(bpy.types.Operator):
    """Assign properties to the selected section"""
    bl_idname = "mustardui.body_assign_to_section"
    bl_label = "Assign Properties"
    bl_options = {'UNDO'}

    def execute(self, context):

        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings
        custom_props = obj.MustardUI_CustomProperties

        uilist = rig_settings.body_custom_properties_sections
        index = context.scene.mustardui_section_uilist_index

        for prop in custom_props:
            if prop.add_section:
                prop.section = uilist[index].name
            else:
                prop.section = "" if prop.section == uilist[index].name else prop.section

        return {'FINISHED'}

    def invoke(self, context, event):

        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings
        custom_props = obj.MustardUI_CustomProperties

        uilist = rig_settings.body_custom_properties_sections
        index = context.scene.mustardui_section_uilist_index

        for prop in custom_props:
            prop.add_section = prop.section == uilist[index].name

        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):

        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings
        custom_props = obj.MustardUI_CustomProperties

        uilist = rig_settings.body_custom_properties_sections
        index = context.scene.mustardui_section_uilist_index

        layout = self.layout

        layout.label(text="Add properties to the Section \'" + uilist[index].name + "\'")

        box = layout.box()
        for prop in sorted(custom_props, key=lambda x: x.name):
            row = box.row(align=False)
            row.prop(prop, 'add_section', text="")
            row.label(text=prop.name, icon="SHAPEKEY_DATA" if prop.type in [0, 1] else "MATERIAL")


def register():
    bpy.utils.register_class(MustardUI_Body_AssignToSection)


def unregister():
    bpy.utils.unregister_class(MustardUI_Body_AssignToSection)
