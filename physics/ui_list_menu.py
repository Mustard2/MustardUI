import bpy

from ..model_selection.active_object import mustardui_active_object
from .settings_item import mustardui_physics_item_type_dict


class MUSTARDUI_UL_PhysicsItems_UIList_Menu(bpy.types.UIList):
    """UIList for Physics Items"""

    filter_show_outfit_items: bpy.props.BoolProperty(
        name="Show Outfit Items",
        description="Show Physics Items assigned to an outfit or outfit piece",
        default=True,
    )

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if not item.object:
            layout.label(text="Object not found!", icon="ERROR")
            return

        settings = bpy.context.scene.MustardUI_Settings

        res, obj = mustardui_active_object(bpy.context, config=0)
        rig_settings = obj.MustardUI_RigSettings

        name = item.object.name
        name = (
            name
            if not rig_settings.model_MustardUI_naming_convention
            else name[len(rig_settings.model_name) + 1 :]
        )

        row = layout.row(align=True)
        row.prop(item, "enable", text="")

        row2 = row.row()
        row2.enabled = item.enable
        row2.label(text=name, icon=mustardui_physics_item_type_dict[item.type])

        row = layout.row(align=True)

        row2 = row.row(align=True)
        row2.enabled = item.enable
        if item.type in ["CAGE", "SINGLE_ITEM", "BONES_DRIVER"]:
            if item.type == "CAGE":
                row2.prop(item, "smooth_corrective", text="", icon="MOD_SMOOTH")
            row2.prop(item, "collisions", text="", icon="MOD_PHYSICS")

        row.prop(item.object, "hide_viewport", text="", emboss=False)

        if settings.advanced and item.object is not None:
            op = row.operator("mustardui.physics_rebind_single_cage", text="", icon="FILE_REFRESH")
            op.cage_name = item.object.name

    def draw_filter(self, context, layout):
        row = layout.row()
        sub = row.row(align=True)
        sub.prop(self, "filter_name", text="", icon="VIEWZOOM")
        sub.prop(self, "use_filter_invert", text="", icon="ARROW_LEFTRIGHT")

        sub = row.row(align=True)
        sub.prop(self, "use_filter_sort_alpha", text="", icon="SORTALPHA")
        sub.prop(
            self,
            "use_filter_sort_reverse",
            text="",
            icon="SORT_DESC" if self.use_filter_sort_reverse else "SORT_ASC",
        )

        sub = row.row(align=True)
        sub.prop(
            self,
            "filter_show_outfit_items",
            text="",
            icon="MOD_CLOTH",
            toggle=True,
        )

    def filter_items(self, context, data, propname):
        items = getattr(data, propname)
        helper_funcs = bpy.types.UI_UL_list

        flt_flags = [self.bitflag_filter_item] * len(items)

        if self.filter_name:
            search = self.filter_name.lower()
            for i, item in enumerate(items):
                name = item.object.name if item.object else ""
                if search not in name.lower():
                    flt_flags[i] &= ~self.bitflag_filter_item

        if self.use_filter_invert:
            for i in range(len(flt_flags)):
                flt_flags[i] ^= self.bitflag_filter_item

        if self.use_filter_sort_alpha:
            sort_data = [
                (i, item.object.name.lower() if item.object else "") for i, item in enumerate(items)
            ]
            flt_neworder = helper_funcs.sort_items_helper(
                sort_data, lambda e: e[1], self.use_filter_sort_reverse
            )
        else:
            flt_neworder = []

        if not self.filter_show_outfit_items:
            for i, item in enumerate(items):
                if item.outfit_enable:
                    flt_flags[i] &= ~self.bitflag_filter_item

        return flt_flags, flt_neworder


def register():
    bpy.utils.register_class(MUSTARDUI_UL_PhysicsItems_UIList_Menu)


def unregister():
    bpy.utils.unregister_class(MUSTARDUI_UL_PhysicsItems_UIList_Menu)
