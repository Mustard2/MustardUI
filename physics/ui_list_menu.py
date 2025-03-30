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

        layout.label(text=item.object.name, icon=mustardui_physics_item_type_dict[item.type])
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
