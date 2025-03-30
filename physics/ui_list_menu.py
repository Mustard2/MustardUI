import bpy
from bpy.props import *
from ..model_selection.active_object import *
from.settings_item import mustardui_physics_item_type_dict


class MUSTARDUI_UL_PhysicsItems_UIList_Menu(bpy.types.UIList):
    """UIList for Physics Items"""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if not item.object:
            layout.label(text="Object not found!", icon="ERROR")
            return

        res, obj = mustardui_active_object(bpy.context, config=0)
        rig_settings = obj.MustardUI_RigSettings

        name = item.object.name
        name = name if not rig_settings.model_MustardUI_naming_convention else name[len(rig_settings.model_name)+1:]
        layout.label(text=name, icon=mustardui_physics_item_type_dict[item.type])
        row = layout.row(align=True)
        row.prop(item, 'enable', text="", icon="PHYSICS")
        if item.type in ["CAGE", "SINGLE_ITEM"]:
            row.prop(item, 'collisions', text="", icon="MOD_PHYSICS")
        else:
            row.label(text="", icon="BLANK1")
        row.prop(item.object, 'hide_viewport', text="")


def register():
    bpy.utils.register_class(MUSTARDUI_UL_PhysicsItems_UIList_Menu)


def unregister():
    bpy.utils.unregister_class(MUSTARDUI_UL_PhysicsItems_UIList_Menu)
