import bpy
from bpy.props import IntProperty

from ..model_selection.active_object import mustardui_active_object
from .misc import get_cp_source, morph_filter_function


class MUSTARDUI_UL_Morphs_UIList_Menu(bpy.types.UIList):
    """UIList for Morphs"""

    def poll(cls, context):
        res, obj = mustardui_active_object(context, config=0)
        return res if obj is not None else False

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):

        settings = context.scene.MustardUI_Settings

        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings
        morphs_settings = obj.MustardUI_MorphsSettings

        body = rig_settings.model_body
        shape_keys = body.data.shape_keys if body is not None and body.data else None

        if morphs_settings.type == "GENERIC" and morphs_settings.show_type_icon:
            icon = "OBJECT_DATA" if item.custom_property else "SHAPEKEY_DATA"
            cp_source = get_cp_source(item.custom_property_source, rig_settings)
            if (
                cp_source
                and item.custom_property
                and hasattr(cp_source, f'["{bpy.utils.escape_identifier(item.path)}"]')
            ):
                layout.prop(
                    cp_source,
                    f'["{bpy.utils.escape_identifier(item.path)}"]',
                    icon=icon,
                    text=item.name,
                )
            elif item.shape_key and shape_keys is not None and item.path in shape_keys.key_blocks:
                layout.prop(
                    shape_keys.key_blocks[item.path],
                    "value",
                    icon=icon,
                    text=item.name,
                )
            else:
                layout.prop(
                    settings,
                    "daz_morphs_error",
                    text="",
                    icon="ERROR",
                    emboss=False,
                    icon_only=True,
                )
        else:
            cp_source = get_cp_source(item.custom_property_source, rig_settings)
            if (
                cp_source
                and item.custom_property
                and hasattr(cp_source, f'["{bpy.utils.escape_identifier(item.path)}"]')
            ):
                layout.prop(
                    cp_source,
                    f'["{bpy.utils.escape_identifier(item.path)}"]',
                    text=item.name,
                )
            elif item.shape_key and shape_keys is not None and item.path in shape_keys.key_blocks:
                layout.prop(
                    shape_keys.key_blocks[item.path],
                    "value",
                    text=item.name,
                )
            else:
                layout.prop(
                    settings,
                    "daz_morphs_error",
                    text="",
                    icon="ERROR",
                    emboss=False,
                    icon_only=True,
                )

    def filter_items(self, context, data, propname):
        items = getattr(data, propname)
        helper_funcs = bpy.types.UI_UL_list

        # Name filter and sorting of the list options
        flt_flags = helper_funcs.filter_items_by_name(
            self.filter_name,
            self.bitflag_filter_item,
            items,
            "name",
            reverse=self.use_filter_invert,
        ) or [self.bitflag_filter_item] * len(items)
        flt_neworder = (
            helper_funcs.sort_items_by_name(items, "name") if self.use_filter_sort_alpha else []
        )

        # Search and null filters of the Morphs panel, shared by all the lists
        poll, obj = mustardui_active_object(context, config=0)
        if obj is not None:
            morph_filter = morph_filter_function(
                obj.MustardUI_RigSettings, obj.MustardUI_MorphsSettings
            )
            for i, morph in enumerate(items):
                if flt_flags[i] and not morph_filter(morph):
                    flt_flags[i] &= ~self.bitflag_filter_item

        return flt_flags, flt_neworder


def register():
    bpy.utils.register_class(MUSTARDUI_UL_Morphs_UIList_Menu)

    bpy.types.Armature.mustardui_morphs_uilist_menu_index = IntProperty(name="", default=0)


def unregister():
    del bpy.types.Armature.mustardui_morphs_uilist_menu_index

    bpy.utils.unregister_class(MUSTARDUI_UL_Morphs_UIList_Menu)
