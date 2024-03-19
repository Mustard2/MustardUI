import bpy
from bpy.props import *
from ..model_selection.active_object import *


class MustardUI_Links_UIList_Switch(bpy.types.Operator):
    """Move the selected property in the list"""

    bl_idname = "mustardui.link_switch"
    bl_label = "Move Link"

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
        uilist = obj.MustardUI_Links
        index = context.scene.mustardui_links_uilist_index

        if len(uilist) <= index:
            return {'FINISHED'}

        neighbour = index + (-1 if self.direction == 'UP' else 1)
        uilist.move(neighbour, index)
        index = self.move_index(uilist, index)
        context.scene.mustardui_links_uilist_index = index

        return {'FINISHED'}


class MustardUI_Link_Remove(bpy.types.Operator):
    """Remove the selected link from the list"""
    bl_idname = "mustardui.link_remove"
    bl_label = "Remove Link"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        res, obj = mustardui_active_object(context, config=1)
        return obj is not None

    def execute(self, context):
        res, obj = mustardui_active_object(context, config=1)
        uilist = obj.MustardUI_Links
        index = context.scene.mustardui_links_uilist_index

        if len(uilist) <= index:
            return {'FINISHED'}

        uilist.remove(index)
        index = min(max(0, index - 1), len(uilist) - 1)
        context.scene.mustardui_links_uilist_index = index

        obj.update_tag()

        return {'FINISHED'}


class MustardUI_Link_Add(bpy.types.Operator):
    """Add a link to the list"""
    bl_idname = "mustardui.link_add"
    bl_label = "Add Link"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        res, obj = mustardui_active_object(context, config=1)
        return obj is not None

    def execute(self, context):
        res, obj = mustardui_active_object(context, config=1)
        uilist = obj.MustardUI_Links

        a = uilist.add()
        a.name = "Link " + str(len(uilist))
        a.url = "https://blender.org/"
        index = len(uilist) - 1
        context.scene.mustardui_links_uilist_index = index

        obj.update_tag()

        return {'FINISHED'}


class MUSTARDUI_UL_Links_UIList(bpy.types.UIList):
    """UIList for links"""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row()
        row.prop(item, 'name', text="", emboss=False, translate=False)
        row.prop(item, 'url', text="", emboss=False, translate=False)


def register():
    bpy.utils.register_class(MustardUI_Links_UIList_Switch)
    bpy.utils.register_class(MustardUI_Link_Add)
    bpy.utils.register_class(MustardUI_Link_Remove)
    bpy.utils.register_class(MUSTARDUI_UL_Links_UIList)
    bpy.types.Scene.mustardui_links_uilist_index = IntProperty(name="", default=0)


def unregister():
    bpy.utils.unregister_class(MUSTARDUI_UL_Links_UIList)
    bpy.utils.unregister_class(MustardUI_Link_Remove)
    bpy.utils.unregister_class(MustardUI_Link_Add)
    bpy.utils.unregister_class(MustardUI_Links_UIList_Switch)
