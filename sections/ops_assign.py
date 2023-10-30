import bpy
from bpy.props import *
from ..model_selection.active_object import *


class MustardUI_Body_PropertyAddToSection(bpy.types.Operator):
    """Assign properties to the selected section"""
    bl_idname = "mustardui.body_propertyaddtosection"
    bl_label = "Assign Properties"
    bl_options = {'UNDO'}

    section_name: bpy.props.StringProperty()

    def execute(self, context):

        res, obj = mustardui_active_object(context, config=1)
        custom_props = obj.MustardUI_CustomProperties

        for prop in custom_props:
            if prop.add_section:
                prop.section = self.section_name
            else:
                prop.section = "" if prop.section == self.section_name else prop.section

        return {'FINISHED'}

    def invoke(self, context, event):

        res, obj = mustardui_active_object(context, config=1)
        custom_props = obj.MustardUI_CustomProperties

        for prop in custom_props:
            prop.add_section = prop.section == self.section_name

        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):

        res, obj = mustardui_active_object(context, config=1)
        custom_props = obj.MustardUI_CustomProperties

        layout = self.layout

        layout.label(text="Add properties to the Section \'" + self.section_name + "\'")

        box = layout.box()
        for prop in sorted(custom_props, key=lambda x: x.name):
            row = box.row(align=False)
            row.prop(prop, 'add_section', text="")
            row.label(text=prop.name, icon="SHAPEKEY_DATA" if prop.type in [0, 1] else "MATERIAL")


def register():
    bpy.utils.register_class(MustardUI_Body_PropertyAddToSection)


def unregister():
    bpy.utils.unregister_class(MustardUI_Body_PropertyAddToSection)