import bpy
from bpy.props import *
from ..model_selection.active_object import *
from .misc import *


class MUSTARDUI_UL_Property_UIList(bpy.types.UIList):
    """UIList for custom properties."""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):

        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config=1)

        # Make sure your code supports all 3 layout types
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item, 'name', text="", icon=item.icon if item.icon != "NONE" else "DOT", emboss=False,
                        translate=False)
            layout.scale_x = 1.0

            row = layout.row(align=True)

            if settings.debug:
                if item.is_animatable:
                    row.label(text="", icon="ANIM")
                else:
                    row.label(text="", icon="BLANK1")

                try:
                    if item.is_animatable:
                        obj.id_properties_ui(item.prop_name)
                    else:
                        eval(mustardui_cp_path(item.rna, item.path))
                    row.label(text="", icon="BLANK1")
                except:
                    row.label(text="", icon="ERROR")

                if item.hidden:
                    row.label(text="", icon="HIDE_ON")
                else:
                    row.label(text="", icon="HIDE_OFF")

            if item.section == "":
                row.label(text="", icon="LIBRARY_DATA_BROKEN")
            else:
                row.label(text="", icon="BLANK1")

            if len(item.linked_properties) > 0:
                row.label(text="", icon="LINK_BLEND")
            else:
                row.label(text="", icon="BLANK1")

        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.prop(item, 'name', text="", icon=item.icon if item.icon != "NONE" else "DOT", emboss=False,
                        translate=False)


class MUSTARDUI_UL_Property_UIListOutfits(bpy.types.UIList):
    """UIList for outfits custom properties."""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):

        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings

        # Make sure your code supports all 3 layout types
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item, 'name', text="", icon=item.icon if item.icon != "NONE" else "DOT", emboss=False,
                        translate=False)
            layout.scale_x = 1.0

            row = layout.row(align=True)

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

            if settings.debug:
                if item.is_animatable:
                    row.label(text="", icon="ANIM")
                else:
                    row.label(text="", icon="BLANK1")

                try:
                    if item.is_animatable:
                        obj.id_properties_ui(item.prop_name)
                    else:
                        eval(mustardui_cp_path(item.rna, item.path))
                    row.label(text="", icon="BLANK1")
                except:
                    row.label(text="", icon="ERROR")

                if item.hidden:
                    row.label(text="", icon="HIDE_ON")
                else:
                    row.label(text="", icon="HIDE_OFF")

            if len(item.linked_properties) > 0:
                row.label(text="", icon="LINK_BLEND")
            else:
                row.label(text="", icon="BLANK1")

        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.prop(item, 'name', text="", icon=item.icon if item.icon != "NONE" else "DOT", emboss=False,
                        translate=False)


class MUSTARDUI_UL_Property_UIListHair(bpy.types.UIList):
    """UIList for outfits custom properties."""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):

        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings

        # Make sure your code supports all 3 layout types
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item, 'name', text="", icon=item.icon if item.icon != "NONE" else "DOT", emboss=False,
                        translate=False)
            layout.scale_x = 1.0

            row = layout.row(align=True)

            if item.hair is not None:
                if rig_settings.model_MustardUI_naming_convention:
                    row.label(text=item.hair.name[len(rig_settings.model_name) + 1:])
                else:
                    row.label(text=item.outfit.name)

            if settings.debug:
                if item.is_animatable:
                    row.label(text="", icon="ANIM")
                else:
                    row.label(text="", icon="BLANK1")

                try:
                    if item.is_animatable:
                        obj.id_properties_ui(item.prop_name)
                    else:
                        eval(mustardui_cp_path(item.rna, item.path))
                    row.label(text="", icon="BLANK1")
                except:
                    row.label(text="", icon="ERROR")

                if item.hidden:
                    row.label(text="", icon="HIDE_ON")
                else:
                    row.label(text="", icon="HIDE_OFF")

            if len(item.linked_properties) > 0:
                row.label(text="", icon="LINK_BLEND")
            else:
                row.label(text="", icon="BLANK1")

        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.prop(item, 'name', text="", icon=item.icon if item.icon != "NONE" else "DOT", emboss=False,
                        translate=False)


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
    for m in menus:
        bpy.utils.unregister_class(m)
