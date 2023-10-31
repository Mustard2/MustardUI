import bpy
from bpy.props import *
from ..model_selection.active_object import *


class MustardUI_Outfits_UIList_Switch(bpy.types.Operator):
    """Move the selected property in the list.\nType"""

    bl_idname = "mustardui.outfits_switch"
    bl_label = "Move Outfit"

    type: bpy.props.EnumProperty(default="BODY",
                                 items=(
                                     ("BODY", "Body", ""),
                                     ("OUTFIT", "Outfit", ""),
                                     ("HAIR", "Hair", ""))
                                 )
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
        uilist = rig_settings.outfits_collections
        index = context.scene.mustardui_outfits_uilist_index

        if len(uilist) <= index:
            return {'FINISHED'}

        neighbour = index + (-1 if self.direction == 'UP' else 1)
        uilist.move(neighbour, index)
        index = self.move_index(uilist, index)
        context.scene.mustardui_outfits_uilist_index = index

        return {'FINISHED'}


class MUSTARDUI_UL_Outfits_UIList(bpy.types.UIList):
    """UIList for outfits."""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.prop(item.collection, 'name', text="", emboss=False, translate=False)


def register():
    bpy.utils.register_class(MUSTARDUI_UL_Outfits_UIList)
    bpy.utils.register_class(MustardUI_Outfits_UIList_Switch)

    bpy.types.Scene.mustardui_outfits_uilist_index = IntProperty(name="", default=0)


def unregister():
    bpy.utils.unregister_class(MUSTARDUI_UL_Outfits_UIList)
    bpy.utils.unregister_class(MustardUI_Outfits_UIList_Switch)
