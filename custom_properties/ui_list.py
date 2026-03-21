import bpy
from bpy.props import *
from ..model_selection.active_object import *
from .misc import *
from ..misc.prop_utils import *
from .. import __package__ as base_package


def draw_item_by_type(self, context, layout, _data, item, _icon, _active_data, _active_propname, _index, cptype=0):
    res, obj = mustardui_active_object(context, config=1)
    rig_settings = obj.MustardUI_RigSettings
    addon_prefs = context.preferences.addons[base_package].preferences

    if cptype not in [0, 1, 2]:
        return

    # Make sure your code supports all 3 layout types
    if self.layout_type in {'DEFAULT', 'COMPACT'}:
        layout.prop(item, 'name', text="", icon=item.icon if item.icon != "NONE" else "DOT", emboss=False,
                    translate=False)
        layout.scale_x = 1.0

        row = layout.row(align=True)

        if cptype == 1:
            if item.outfit is not None and item.outfit_piece is None:
                if rig_settings.model_MustardUI_naming_convention:
                    row.label(text=item.outfit.name[len(rig_settings.model_name) + 1:])
                else:
                    row.label(text=item.outfit.name)
            elif item.outfit is not None and item.outfit_piece is not None:
                if rig_settings.model_MustardUI_naming_convention:
                    row.label(text=item.outfit_piece.name[len(rig_settings.model_name) + 1:])
                else:
                    row.label(text=item.outfit_piece.name)
        elif cptype == 2:
            if item.hair is not None:
                if rig_settings.model_MustardUI_naming_convention:
                    row.label(text=item.hair.name[len(rig_settings.model_name) + 1:])
                else:
                    row.label(text=item.hair.name)

        try:
            error = False
            if item.is_animatable:
                obj.id_properties_ui(item.prop_name)
            if evaluate_path(item.rna, item.path) is None:
                error = True
            if error:
                row.label(text="", icon="ERROR")
        except:
            row.label(text="", icon="ERROR")

        if cptype == 0:
            if item.section == "":
                row.label(text="", icon="LIBRARY_DATA_BROKEN")

        if addon_prefs.debug:
            if item.is_animatable:
                row.label(text="", icon="ANIM")
            else:
                row.label(text="", icon="BLANK1")

        if len(item.linked_properties) > 0:
            row.label(text="", icon="LINK_BLEND")
        else:
            row.label(text="", icon="BLANK1")

        if addon_prefs.debug:
            if item.hidden:
                row.label(text="", icon="HIDE_ON")
            else:
                row.label(text="", icon="HIDE_OFF")

    elif self.layout_type in {'GRID'}:
        layout.alignment = 'CENTER'
        layout.prop(item, 'name', text="", icon=item.icon if item.icon != "NONE" else "DOT", emboss=False,
                    translate=False)


class MUSTARDUI_UL_Property_UIList(bpy.types.UIList):
    """UIList for custom properties"""

    def draw_item(self, context, layout, _data, item, _icon, _active_data, _active_propname, _index):
        draw_item_by_type(self, context, layout, _data, item, _icon, _active_data, _active_propname, _index, cptype=0)


class MUSTARDUI_UL_Property_UIListOutfits(bpy.types.UIList):
    """UIList for outfits custom properties"""

    def draw_item(self, context, layout, _data, item, _icon, _active_data, _active_propname, _index):
        draw_item_by_type(self, context, layout, _data, item, _icon, _active_data, _active_propname, _index, cptype=1)


class MUSTARDUI_UL_Property_UIListHair(bpy.types.UIList):
    """UIList for hair custom properties"""

    def draw_item(self, context, layout, _data, item, _icon, _active_data, _active_propname, _index):
        draw_item_by_type(self, context, layout, _data, item, _icon, _active_data, _active_propname, _index, cptype=2)


menus = (
    MUSTARDUI_UL_Property_UIList,
    MUSTARDUI_UL_Property_UIListOutfits,
    MUSTARDUI_UL_Property_UIListHair
)


def register():
    for m in menus:
        bpy.utils.register_class(m)

    bpy.types.Scene.mustardui_property_uilist_index = IntProperty(name="", default=0)
    bpy.types.Scene.mustardui_property_uilist_outfits_index = IntProperty(name="", default=0)
    bpy.types.Scene.mustardui_property_uilist_hair_index = IntProperty(name="", default=0)


def unregister():
    del bpy.types.Scene.mustardui_property_uilist_hair_index
    del bpy.types.Scene.mustardui_property_uilist_outfits_index
    del bpy.types.Scene.mustardui_property_uilist_index

    for m in reversed(menus):
        bpy.utils.unregister_class(m)
