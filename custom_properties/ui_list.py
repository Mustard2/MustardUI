import bpy
from bpy.props import BoolProperty, IntProperty, PointerProperty

from .. import __package__ as base_package
from ..misc.prop_utils import evaluate_path
from ..model_selection.active_object import mustardui_active_object
from .ops_set_section import MustardUI_Property_SetSection


def draw_item_by_type(
    self,
    context,
    layout,
    _data,
    item,
    _icon,
    _active_data,
    _active_propname,
    index,
    cptype=0,
):
    res, obj = mustardui_active_object(context, config=1)
    rig_settings = obj.MustardUI_RigSettings
    addon_prefs = context.preferences.addons[base_package].preferences

    if cptype not in [0, 1, 2]:
        return

    # Make sure your code supports all 3 layout types
    if self.layout_type in {"DEFAULT", "COMPACT"}:
        layout.prop(
            item,
            "name",
            text="",
            icon=item.icon if item.icon != "NONE" else "DOT",
            emboss=False,
            translate=False,
        )
        layout.scale_x = 1.0

        row = layout.row(align=True)

        if cptype == 0:
            section = rig_settings.body_custom_properties_sections.get(item.section)
            icon = "RECORD_OFF"
            if section is not None:
                icon = section.icon if section.icon not in {"", "NONE"} else "DOT"
            op = row.operator_menu_enum(
                MustardUI_Property_SetSection.bl_idname,
                "section",
                text=item.section if item.section not in {"", "NONE"} else "No Section",
                icon=icon,
            )
            op.index = index
        elif cptype == 1:
            if item.outfit is not None and item.outfit_piece is None:
                if rig_settings.model_MustardUI_naming_convention:
                    row.label(text=item.outfit.name[len(rig_settings.model_name) + 1 :])
                else:
                    row.label(text=item.outfit.name)
            elif item.outfit is not None and item.outfit_piece is not None:
                if rig_settings.model_MustardUI_naming_convention:
                    row.label(text=item.outfit_piece.name[len(rig_settings.model_name) + 1 :])
                else:
                    row.label(text=item.outfit_piece.name)
        elif cptype == 2:
            if item.hair is not None:
                if rig_settings.model_MustardUI_naming_convention:
                    row.label(text=item.hair.name[len(rig_settings.model_name) + 1 :])
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
        except Exception:
            row.label(text="", icon="ERROR")

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

    elif self.layout_type in {"GRID"}:
        layout.alignment = "CENTER"
        layout.prop(
            item,
            "name",
            text="",
            icon=item.icon if item.icon != "NONE" else "DOT",
            emboss=False,
            translate=False,
        )


def filter_items_by_type(self, context, data, propname, cptype=0):
    items = getattr(data, propname)
    helper_funcs = bpy.types.UI_UL_list
    scene = context.scene

    if self.filter_name:
        flt_flags = helper_funcs.filter_items_by_name(
            self.filter_name,
            self.bitflag_filter_item,
            items,
            "name",
            reverse=self.use_filter_sort_reverse,
        )
    else:
        flt_flags = [self.bitflag_filter_item] * len(items)

    if self.use_filter_invert:
        for i in range(len(flt_flags)):
            flt_flags[i] ^= self.bitflag_filter_item

    flt_neworder = (
        helper_funcs.sort_items_by_name(items, "name") if self.use_filter_sort_alpha else []
    )

    if cptype == 0 and self.filter_by_active_section:
        res, arm = mustardui_active_object(context, config=1)
        active_section = None
        if res:
            rig_settings = arm.MustardUI_RigSettings
            index = scene.mustardui_section_uilist_index
            if 0 <= index < len(rig_settings.body_custom_properties_sections):
                active_section = rig_settings.body_custom_properties_sections[index].name

        for i, item in enumerate(items):
            if item.section != active_section:
                flt_flags[i] &= ~self.bitflag_filter_item

    elif cptype == 1 and scene.mustardui_property_uilist_outfits_filter_outfit:
        outfit = scene.mustardui_property_uilist_outfits_filter_outfit
        piece = scene.mustardui_property_uilist_outfits_filter_piece
        for i, item in enumerate(items):
            if item.outfit != outfit or (piece and item.outfit_piece != piece):
                flt_flags[i] &= ~self.bitflag_filter_item

    elif cptype == 2 and scene.mustardui_property_uilist_hair_filter_object:
        hair_object = scene.mustardui_property_uilist_hair_filter_object
        for i, item in enumerate(items):
            if item.hair != hair_object:
                flt_flags[i] &= ~self.bitflag_filter_item

    return flt_flags, flt_neworder


def poll_filter_outfit(self, collection):
    context = bpy.context
    res, arm = mustardui_active_object(context, config=1)
    if not res:
        return False

    rig_settings = arm.MustardUI_RigSettings

    return (
        collection
        in [x.collection for x in rig_settings.outfits_collections if x.collection is not None]
        or collection == rig_settings.extras_collection
    )


def poll_filter_outfit_piece(self, obj):
    filter_outfit = self.mustardui_property_uilist_outfits_filter_outfit
    if filter_outfit is None:
        return False

    return obj in list(filter_outfit.all_objects)


def poll_filter_hair_object(self, obj):
    context = bpy.context
    res, arm = mustardui_active_object(context, config=1)
    if not res:
        return False

    rig_settings = arm.MustardUI_RigSettings
    if obj.type not in {"MESH", "CURVES"}:
        return False

    hc = rig_settings.hair_collection
    hec = rig_settings.hair_extras_collection

    return (hc and obj in list(hc.objects)) or (hec and obj in list(hec.objects))


class MUSTARDUI_UL_Property_UIList(bpy.types.UIList):
    """UIList for custom properties"""

    filter_by_active_section: BoolProperty(
        name="Active Section",
        description="Show only the properties of the section selected in the Sections list",
        default=False,
    )

    def draw_item(
        self,
        context,
        layout,
        _data,
        item,
        _icon,
        _active_data,
        _active_propname,
        _index,
    ):
        draw_item_by_type(
            self,
            context,
            layout,
            _data,
            item,
            _icon,
            _active_data,
            _active_propname,
            _index,
            cptype=0,
        )

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
        sub.prop(self, "filter_by_active_section", text="", icon="LINENUMBERS_OFF")

    def filter_items(self, context, data, propname):
        return filter_items_by_type(self, context, data, propname, cptype=0)


class MUSTARDUI_UL_Property_UIListOutfits(bpy.types.UIList):
    """UIList for outfits custom properties"""

    def draw_item(
        self,
        context,
        layout,
        _data,
        item,
        _icon,
        _active_data,
        _active_propname,
        _index,
    ):
        draw_item_by_type(
            self,
            context,
            layout,
            _data,
            item,
            _icon,
            _active_data,
            _active_propname,
            _index,
            cptype=1,
        )

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

        row = layout.row(align=True)
        row.prop(
            context.scene,
            "mustardui_property_uilist_outfits_filter_outfit",
            text="",
            icon="MOD_CLOTH",
        )
        row.prop(context.scene, "mustardui_property_uilist_outfits_filter_piece", text="")

    def filter_items(self, context, data, propname):
        return filter_items_by_type(self, context, data, propname, cptype=1)


class MUSTARDUI_UL_Property_UIListHair(bpy.types.UIList):
    """UIList for hair custom properties"""

    def draw_item(
        self,
        context,
        layout,
        _data,
        item,
        _icon,
        _active_data,
        _active_propname,
        _index,
    ):
        draw_item_by_type(
            self,
            context,
            layout,
            _data,
            item,
            _icon,
            _active_data,
            _active_propname,
            _index,
            cptype=2,
        )

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

        row = layout.row(align=True)
        row.prop(
            context.scene, "mustardui_property_uilist_hair_filter_object", text="", icon="CURVES"
        )

    def filter_items(self, context, data, propname):
        return filter_items_by_type(self, context, data, propname, cptype=2)


menus = (
    MUSTARDUI_UL_Property_UIList,
    MUSTARDUI_UL_Property_UIListOutfits,
    MUSTARDUI_UL_Property_UIListHair,
)


def register():
    for m in menus:
        bpy.utils.register_class(m)

    bpy.types.Scene.mustardui_property_uilist_index = IntProperty(name="", default=0)
    bpy.types.Scene.mustardui_property_uilist_outfits_index = IntProperty(name="", default=0)
    bpy.types.Scene.mustardui_property_uilist_hair_index = IntProperty(name="", default=0)

    bpy.types.Scene.mustardui_property_uilist_outfits_filter_outfit = PointerProperty(
        name="Outfit",
        description="Show only the properties of this outfit",
        type=bpy.types.Collection,
        poll=poll_filter_outfit,
    )
    bpy.types.Scene.mustardui_property_uilist_outfits_filter_piece = PointerProperty(
        name="Piece",
        description="Show only the properties of this outfit piece.\n"
        "Leave empty to show the properties of the whole outfit",
        type=bpy.types.Object,
        poll=poll_filter_outfit_piece,
    )
    bpy.types.Scene.mustardui_property_uilist_hair_filter_object = PointerProperty(
        name="Hair",
        description="Show only the properties of this hair object",
        type=bpy.types.Object,
        poll=poll_filter_hair_object,
    )


def unregister():
    del bpy.types.Scene.mustardui_property_uilist_hair_filter_object
    del bpy.types.Scene.mustardui_property_uilist_outfits_filter_piece
    del bpy.types.Scene.mustardui_property_uilist_outfits_filter_outfit

    del bpy.types.Scene.mustardui_property_uilist_hair_index
    del bpy.types.Scene.mustardui_property_uilist_outfits_index
    del bpy.types.Scene.mustardui_property_uilist_index

    for m in reversed(menus):
        bpy.utils.unregister_class(m)
