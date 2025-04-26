import bpy
from bpy.props import *
from ..model_selection.active_object import *


class MUSTARDUI_UL_Morphs_UIList_Menu(bpy.types.UIList):
    """UIList for Morphs"""

    def poll(cls, context):
        res, obj = mustardui_active_object(context, config=0)
        return res if obj is not None else False

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):

        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings
        morphs_settings = obj.MustardUI_MorphsSettings

        if morphs_settings.type == "GENERIC" and morphs_settings.show_type_icon:
            icon = "OBJECT_DATA" if item.custom_property else "SHAPEKEY_DATA"
            if item.custom_property:
                layout.prop(rig_settings.model_armature_object, f'["{bpy.utils.escape_identifier(item.path)}"]',
                            icon=icon, text=item.name)
            elif item.shape_key:
                layout.prop(rig_settings.model_body.data.shape_keys.key_blocks[item.path], 'value',
                            icon=icon, text=item.name)
        else:
            if item.custom_property:
                layout.prop(rig_settings.model_armature_object, f'["{bpy.utils.escape_identifier(item.path)}"]',
                            text=item.name)
            elif item.shape_key:
                layout.prop(rig_settings.model_body.data.shape_keys.key_blocks[item.path], 'value',
                            text=item.name)


def register():
    bpy.utils.register_class(MUSTARDUI_UL_Morphs_UIList_Menu)

    bpy.types.Armature.mustardui_morphs_uilist_menu_index = IntProperty(name="", default=0)


def unregister():
    del bpy.types.Armature.mustardui_morphs_uilist_menu_index

    bpy.utils.unregister_class(MUSTARDUI_UL_Morphs_UIList_Menu)
