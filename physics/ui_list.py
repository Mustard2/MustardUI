import bpy
from bpy.props import IntProperty

from ..model_selection.active_object import mustardui_active_object
from .settings_item import mustardui_physics_item_type_dict


def physics_items_filter(uilist, items):
    """Filter and sort Physics Items by object name, as items have no name"""
    flt_flags = [uilist.bitflag_filter_item] * len(items)

    if uilist.filter_name:
        search = uilist.filter_name.lower()
        for i, item in enumerate(items):
            name = item.object.name if item.object else ""
            if search not in name.lower():
                flt_flags[i] &= ~uilist.bitflag_filter_item

    if uilist.use_filter_invert:
        for i in range(len(flt_flags)):
            flt_flags[i] ^= uilist.bitflag_filter_item

    if uilist.use_filter_sort_alpha:
        sort_data = [
            (i, item.object.name.lower() if item.object else "") for i, item in enumerate(items)
        ]
        flt_neworder = bpy.types.UI_UL_list.sort_items_helper(
            sort_data, lambda e: e[1], uilist.use_filter_sort_reverse
        )
    else:
        flt_neworder = []

    return flt_flags, flt_neworder


class MustardUI_PhysicsItems_UIList_Switch(bpy.types.Operator):
    """Move the selected property in the list"""

    bl_idname = "mustardui.physics_items_switch"
    bl_label = "Move Physics Item"

    direction: bpy.props.EnumProperty(
        items=(
            ("UP", "Up", ""),
            ("DOWN", "Down", ""),
        )
    )

    @classmethod
    def poll(cls, context):
        res, obj = mustardui_active_object(context, config=1)
        return obj is not None

    def move_index(self, uilist, index):
        """Move index of an item render queue while clamping it."""

        list_length = len(uilist) - 1  # (index starts at 0)
        new_index = index + (-1 if self.direction == "UP" else 1)

        return max(0, min(new_index, list_length))

    def execute(self, context):
        res, obj = mustardui_active_object(context, config=1)
        physics_settings = obj.MustardUI_PhysicsSettings
        uilist = physics_settings.items
        index = obj.mustardui_physics_items_uilist_index

        neighbour = index + (-1 if self.direction == "UP" else 1)

        if not 0 <= index < len(uilist) or not 0 <= neighbour < len(uilist):
            return {"FINISHED"}

        uilist.move(neighbour, index)
        index = self.move_index(uilist, index)
        obj.mustardui_physics_items_uilist_index = index

        return {"FINISHED"}


class MUSTARDUI_UL_PhysicsItems_UIList(bpy.types.UIList):
    """UIList for Physics Items"""

    warning: bpy.props.BoolProperty(
        name="Warning",
        description="The Physics Item seems not to have any Physics modifier active",
    )

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if item.object:
            layout.prop(item.object, "name", text="", emboss=False, translate=False)
            row = layout.row(align=True)

            # Show a Warning if no Physics modifier is found on the Physics Item
            found = True
            if item.type == "CAGE":
                found = any(
                    mod.type in ["CLOTH", "SOFT_BODY"] or (mod.type == "NODES" and mod.node_group)
                    for mod in item.object.modifiers
                )
            elif item.type == "COLLISION":
                found = any(mod.type in ["COLLISION"] for mod in item.object.modifiers)

            if not found:
                row.prop(
                    self,
                    "warning",
                    icon="ERROR",
                    text="",
                    icon_only=True,
                    emboss=False,
                )

            row.label(text="", icon=mustardui_physics_item_type_dict[item.type])
            row.label(
                text="",
                icon="MOD_CLOTH" if item.outfit_enable and item.outfit_collection else "BLANK1",
            )
        else:
            layout.label(text="Object not found!", icon="ERROR")

    def filter_items(self, context, data, propname):
        return physics_items_filter(self, getattr(data, propname))


def register():
    bpy.utils.register_class(MUSTARDUI_UL_PhysicsItems_UIList)
    bpy.utils.register_class(MustardUI_PhysicsItems_UIList_Switch)

    bpy.types.Armature.mustardui_physics_items_uilist_index = IntProperty(name="", default=0)


def unregister():
    del bpy.types.Armature.mustardui_physics_items_uilist_index

    bpy.utils.unregister_class(MustardUI_PhysicsItems_UIList_Switch)
    bpy.utils.unregister_class(MUSTARDUI_UL_PhysicsItems_UIList)
