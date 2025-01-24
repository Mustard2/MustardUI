import bpy
from bpy.props import *
from ..model_selection.active_object import *


class MustardUI_Section_UIList_Switch(bpy.types.Operator):
    """Move the selected section in the list"""

    bl_idname = "mustardui.section_switch"
    bl_label = "Move Section"

    direction: bpy.props.EnumProperty(items=(('UP', 'Up', ""),
                                             ('DOWN', 'Down', ""),))

    @classmethod
    def poll(cls, context):
        res, obj = mustardui_active_object(context, config=1)
        return obj is not None

    def move_index(self, uilist, index):
        """ Move index of an item render queue while clamping it. """

        list_length = len(uilist) - 1  # (index starts at 0)
        new_index = index + (-1 if self.direction == 'UP' else 1)

        return max(0, min(new_index, list_length))

    def execute(self, context):
        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings
        uilist = rig_settings.body_custom_properties_sections
        index = context.scene.mustardui_section_uilist_index

        if len(uilist) <= index:
            return {'FINISHED'}

        neighbour = index + (-1 if self.direction == 'UP' else 1)
        uilist.move(neighbour, index)
        index = self.move_index(uilist, index)
        context.scene.mustardui_section_uilist_index = index

        # Remove the subsection status if there is no new parent section
        if index == 0:
            uilist[index].is_subsection = False

        return {'FINISHED'}


class MustardUI_Body_DeleteSection(bpy.types.Operator):
    """Delete the selected Section"""
    bl_idname = "mustardui.body_deletesection"
    bl_label = "Delete Section"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        res, obj = mustardui_active_object(context, config=1)
        return obj is not None

    def execute(self, context):
        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings
        uilist = rig_settings.body_custom_properties_sections
        index = context.scene.mustardui_section_uilist_index

        if len(uilist) <= index:
            return {'FINISHED'}

        uilist.remove(index)
        index = min(max(0, index - 1), len(uilist) - 1)
        context.scene.mustardui_section_uilist_index = index

        # Remove the subsection status if there is no new parent section
        if index == 0:
            uilist[index].is_subsection = False

        obj.update_tag()

        return {'FINISHED'}


class MustardUI_Body_AddSection(bpy.types.Operator):
    """Add a section to the list"""
    bl_idname = "mustardui.section_add"
    bl_label = "Add Section"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        res, obj = mustardui_active_object(context, config=1)
        return obj is not None

    def execute(self, context):
        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings
        uilist = rig_settings.body_custom_properties_sections

        a = uilist.add()
        a.name = "Section " + str(len(uilist))
        a.old_name = a.name
        index = len(uilist) - 1
        context.scene.mustardui_section_uilist_index = index

        obj.update_tag()

        return {'FINISHED'}


class MUSTARDUI_UL_Section_UIList(bpy.types.UIList):
    """UIList for sections"""

    def draw_item(self, context, layout, _data, item, _icon, _active_data, _active_propname, _index):

        row = layout.row(align=True)

        row.label(text="", icon=item.icon if item.icon != "NONE" else "DOT")
        if item.is_subsection:
            row.prop(item, 'name', text="", emboss=False, translate=False, icon="REMOVE")
        else:
            row.prop(item, 'name', text="", emboss=False, translate=False)

        res, obj = mustardui_active_object(context, config=1)
        custom_props = obj.MustardUI_CustomProperties
        preset_done = False
        for prop in custom_props:
            if prop.section == item.name:
                preset_done = True
                break

        row = layout.row(align=True)
        row.label(text="", icon="EXPERIMENTAL" if item.advanced else "BLANK1")
        row.label(text="", icon="PRESET" if preset_done else "BLANK1")


def register():
    bpy.utils.register_class(MustardUI_Section_UIList_Switch)
    bpy.utils.register_class(MustardUI_Body_AddSection)
    bpy.utils.register_class(MustardUI_Body_DeleteSection)
    bpy.utils.register_class(MUSTARDUI_UL_Section_UIList)
    bpy.types.Scene.mustardui_section_uilist_index = IntProperty(name="", default=0)


def unregister():
    del bpy.types.Scene.mustardui_section_uilist_index
    bpy.utils.unregister_class(MUSTARDUI_UL_Section_UIList)
    bpy.utils.unregister_class(MustardUI_Body_DeleteSection)
    bpy.utils.unregister_class(MustardUI_Body_AddSection)
    bpy.utils.unregister_class(MustardUI_Section_UIList_Switch)
