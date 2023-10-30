import bpy
from bpy.props import *
from ..model_selection.active_object import *


class MustardUI_Body_SwapSection(bpy.types.Operator):
    """Change the position of the section"""
    bl_idname = "mustardui.body_swapsection"
    bl_label = "Section Position"

    mod: BoolProperty(default=False)  # False = down, True = Up
    name: StringProperty()

    def find_index_section_fromID(self, collection, item):
        i = -1
        for el in collection:
            i = i + 1
            if el.id == item:
                break
        return i

    def find_index_section(self, collection, item):
        i = -1
        for el in collection:
            i = i + 1
            if el.name == item:
                break
        return i

    def execute(self, context):

        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings
        sec_obj = rig_settings.body_custom_properties_sections
        sec_len = len(sec_obj)

        sec_index = self.find_index_section(sec_obj, self.name)
        i = sec_obj[sec_index].id

        if self.mod and i > 0:
            j = self.find_index_section_fromID(sec_obj, i - 1)
            sec_obj[sec_index].id = i - 1
            sec_obj[j].id = i
        elif not self.mod and i < sec_len - 1:
            j = self.find_index_section_fromID(sec_obj, i + 1)
            sec_obj[sec_index].id = i + 1
            sec_obj[j].id = i

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_Body_SwapSection)


def unregister():
    bpy.utils.unregister_class(MustardUI_Body_SwapSection)
