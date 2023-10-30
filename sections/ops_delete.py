import bpy
from bpy.props import *
from ..model_selection.active_object import *


class MustardUI_Body_DeleteSection(bpy.types.Operator):
    """Delete the selected Section"""
    bl_idname = "mustardui.body_deletesection"
    bl_label = "Delete Section"
    bl_options = {'UNDO'}

    name: bpy.props.StringProperty(name='Name',
                                   description="Choose the name of the section")

    def find_index_section_fromID(self, collection, item):
        i = -1
        for el in collection:
            i = i + 1
            if el.id == item:
                break
        return i

    @classmethod
    def poll(cls, context):

        res, arm = mustardui_active_object(context, config=1)
        return res

    def execute(self, context):

        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings
        sec_obj = rig_settings.body_custom_properties_sections

        i = -1
        for el in sec_obj:
            i = i + 1
            if el.name == self.name:
                break

        if i >= 0:

            j = sec_obj[i].id

            for prop in obj.MustardUI_CustomProperties:
                if prop.section == sec_obj[i].name:
                    prop.section = ""

            for k in range(j + 1, len(sec_obj)):
                sec_obj[self.find_index_section_fromID(sec_obj, k)].id = k - 1

            sec_obj.remove(i)

        self.report({'INFO'}, 'MustardUI - Section \'' + self.name + '\' deleted.')

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_Body_DeleteSection)


def unregister():
    bpy.utils.unregister_class(MustardUI_Body_DeleteSection)
