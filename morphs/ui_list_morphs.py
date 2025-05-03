import bpy
from bpy.props import *
from ..model_selection.active_object import *


class MustardUI_Morphs_Remove(bpy.types.Operator):
    """Remove the selected Morph from the UI.\nThis do NOT delete any data, it just prevents the Morph from being shown in the UI"""
    bl_idname = "mustardui.morphs_remove"
    bl_label = "Remove Morphs"
    bl_options = {'UNDO'}

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=1)
        morphs_settings = arm.MustardUI_MorphsSettings

        uilist = morphs_settings.sections[arm.mustardui_morphs_section_uilist_index].morphs
        index = arm.mustardui_morphs_uilist_index

        if len(uilist) <= index:
            return {'FINISHED'}

        # Remove the collection from the Outfits Collections
        uilist.remove(index)

        index = min(max(0, index - 1), len(uilist) - 1)
        arm.mustardui_morphs_uilist_index = index

        arm.update_tag()

        self.report({'INFO'}, 'MustardUI - Morphs removed.')

        return {'FINISHED'}


class MustardUI_Morphs_UIList_Switch(bpy.types.Operator):
    """Move the selected property in the list"""

    bl_idname = "mustardui.morphs_items_switch"
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
        morphs_settings = obj.MustardUI_MorphsSettings
        uilist = morphs_settings.sections[obj.mustardui_morphs_section_uilist_index].morphs
        index = obj.mustardui_morphs_uilist_index

        if len(uilist) <= index:
            return {'FINISHED'}

        neighbour = index + (-1 if self.direction == 'UP' else 1)
        uilist.move(neighbour, index)
        index = self.move_index(uilist, index)
        obj.mustardui_morphs_uilist_index = index

        return {'FINISHED'}


class MUSTARDUI_UL_Morphs_UIList(bpy.types.UIList):
    """UIList for Morphs"""

    def poll(cls, context):
        res, obj = mustardui_active_object(context, config=1)
        return res if obj is not None else False

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings
        icon = "OBJECT_DATA" if item.custom_property else "SHAPEKEY_DATA"
        if ((item.custom_property and hasattr(rig_settings.model_armature_object,
                                             f'["{bpy.utils.escape_identifier(item.path)}"]'))
                or (item.shape_key and item.path in rig_settings.model_body.data.shape_keys.key_blocks.keys())):
            layout.prop(item, 'name', text="", emboss=False, translate=False, icon=icon)
        else:
            layout.prop(item, 'name', text="", emboss=False, translate=False, icon="ERROR")


def register():
    bpy.utils.register_class(MUSTARDUI_UL_Morphs_UIList)
    bpy.utils.register_class(MustardUI_Morphs_Remove)
    bpy.utils.register_class(MustardUI_Morphs_UIList_Switch)

    bpy.types.Armature.mustardui_morphs_uilist_index = IntProperty(name="", default=0)


def unregister():
    del bpy.types.Armature.mustardui_morphs_uilist_index

    bpy.utils.unregister_class(MustardUI_Morphs_UIList_Switch)
    bpy.utils.unregister_class(MustardUI_Morphs_Remove)
    bpy.utils.unregister_class(MUSTARDUI_UL_Morphs_UIList)
