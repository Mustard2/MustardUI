import bpy

from ..configuration.naming_convention import (
    strip_naming_convention,
    strip_naming_convention_collection,
)
from ..misc.icons import get_hair_icon
from ..model_selection.active_object import mustardui_active_object
from .ops_add import MustardUI_Property_MenuAdd
from .ops_link import MustardUI_Property_MenuLink


class OUTLINER_MT_MustardUI_PropertySectionMenu(bpy.types.Menu):
    bl_idname = "OUTLINER_MT_MustardUI_PropertySectionMenu"
    bl_label = "Add to MustardUI Properties"

    def draw(self, context):
        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings

        layout = self.layout

        op = layout.operator(
            MustardUI_Property_MenuAdd.bl_idname, text="Add without Section", icon="ADD"
        )
        op.section = ""
        op.outfit_is_nude = False
        op.outfit = ""
        op.outfit_piece = ""
        op.hair_global = False
        op.hair = ""

        layout.separator()

        for sec in rig_settings.body_custom_properties_sections:
            op = layout.operator(MustardUI_Property_MenuAdd.bl_idname, text=sec.name, icon=sec.icon)
            op.section = sec.name
            op.outfit_is_nude = False
            op.outfit = ""
            op.outfit_piece = ""
            op.hair_global = False
            op.hair = ""


# Operators to create the list of outfits when right-clicking on a property
class OUTLINER_MT_MustardUI_PropertyOutfitPieceMenu(bpy.types.Menu):
    bl_idname = "OUTLINER_MT_MustardUI_PropertyOutfitPieceMenu"
    bl_label = "Add to MustardUI Outfit"

    def draw(self, context):

        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings

        layout = self.layout

        if context.mustardui_propertyoutfitmenu_sel != rig_settings.extras_collection:
            op = layout.operator(
                MustardUI_Property_MenuAdd.bl_idname,
                text="Add as Global Outfit property",
                icon="TRIA_RIGHT",
            )
            op.section = ""
            op.outfit_is_nude = False
            op.outfit = context.mustardui_propertyoutfitmenu_sel.name
            op.outfit_piece = ""
            op.hair_global = False
            op.hair = ""

        items = (
            context.mustardui_propertyoutfitmenu_sel.all_objects
            if rig_settings.outfit_config_subcollections
            else context.mustardui_propertyoutfitmenu_sel.objects
        )
        for obj in items:
            op = layout.operator(
                MustardUI_Property_MenuAdd.bl_idname,
                icon="DOT",
                text=strip_naming_convention(
                    obj.name,
                    context.mustardui_propertyoutfitmenu_sel.name,
                    rig_settings.model_MustardUI_naming_convention,
                ),
            )
            op.section = ""
            op.outfit_is_nude = False
            op.outfit = context.mustardui_propertyoutfitmenu_sel.name
            op.outfit_piece = obj.name
            op.hair_global = False
            op.hair = ""


# Operators to create the list of outfits when right-clicking on a property
class OUTLINER_MT_MustardUI_PropertyOutfitMenu(bpy.types.Menu):
    bl_idname = "OUTLINER_MT_MustardUI_PropertyOutfitMenu"
    bl_label = "Add to MustardUI Outfit"

    def draw(self, context):

        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings

        layout = self.layout

        if rig_settings.outfit_nude:
            op = layout.operator(
                MustardUI_Property_MenuAdd.bl_idname,
                text="Add as Nude property",
                icon="TRIA_RIGHT",
            )
            op.section = ""
            op.outfit_is_nude = True
            op.outfit = ""
            op.outfit_piece = ""
            op.hair_global = False
            op.hair = ""

        outfit_indices = []
        for i in range(0, len(rig_settings.outfits_collections)):
            if rig_settings.outfits_collections[i].collection is not None:
                outfit_indices.append(i)

        for i in outfit_indices:
            layout.context_pointer_set(
                "mustardui_propertyoutfitmenu_sel",
                rig_settings.outfits_collections[i].collection,
            )
            layout.menu(
                OUTLINER_MT_MustardUI_PropertyOutfitPieceMenu.bl_idname,
                icon="MOD_CLOTH",
                text=strip_naming_convention_collection(
                    rig_settings.outfits_collections[i].collection.name,
                    rig_settings.model_name,
                    rig_settings.model_MustardUI_naming_convention,
                ),
            )
        if rig_settings.extras_collection is not None:
            items = (
                rig_settings.extras_collection.all_objects
                if rig_settings.extras_config_subcollections
                else rig_settings.extras_collection.objects
            )
            if len(items) > 0:
                layout.context_pointer_set(
                    "mustardui_propertyoutfitmenu_sel", rig_settings.extras_collection
                )
                layout.menu(
                    OUTLINER_MT_MustardUI_PropertyOutfitPieceMenu.bl_idname,
                    icon="PLUS",
                    text=strip_naming_convention_collection(
                        rig_settings.extras_collection.name,
                        rig_settings.model_name,
                        rig_settings.model_MustardUI_naming_convention,
                    ),
                )


# Operators to create the list of outfits when right-clicking on a property
class OUTLINER_MT_MustardUI_PropertyHairMenu(bpy.types.Menu):
    bl_idname = "OUTLINER_MT_MustardUI_PropertyHairMenu"
    bl_label = "Add to MustardUI Hair"

    def draw(self, context):
        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings

        layout = self.layout

        op = layout.operator(
            MustardUI_Property_MenuAdd.bl_idname,
            text="Add as Hair Global property",
            icon="TRIA_RIGHT",
        )
        op.section = ""
        op.outfit_is_nude = False
        op.outfit = ""
        op.outfit_piece = ""
        op.hair_global = True
        op.hair = ""

        types = ["MESH", "CURVES"]

        hcoll = rig_settings.hair_collection
        for obj in [x for x in hcoll.objects if x.type in types]:
            op = layout.operator(
                MustardUI_Property_MenuAdd.bl_idname,
                icon=get_hair_icon(obj),
                text=strip_naming_convention(
                    obj.name, hcoll.name, rig_settings.model_MustardUI_naming_convention
                ),
            )
            op.section = ""
            op.outfit_is_nude = False
            op.outfit = ""
            op.outfit_piece = ""
            op.hair_global = False
            op.hair = obj.name

        if rig_settings.hair_extras_collection is not None:
            hcoll = rig_settings.hair_extras_collection

            layout.separator()
            layout.label(text="Extras", icon="PLUS")

            for obj in [x for x in hcoll.objects if x.type in types]:
                op = layout.operator(
                    MustardUI_Property_MenuAdd.bl_idname,
                    icon=get_hair_icon(obj),
                    text=strip_naming_convention(
                        obj.name,
                        hcoll.name,
                        rig_settings.model_MustardUI_naming_convention,
                    ),
                )
                op.section = ""
                op.outfit_is_nude = False
                op.outfit = ""
                op.outfit_piece = ""
                op.hair_global = False
                op.hair = obj.name


# Sub-menu with the Body properties of a single Section, used by the Link menu
class MUSTARDUI_MT_Property_LinkMenu_Section(bpy.types.Menu):
    bl_idname = "MUSTARDUI_MT_Property_LinkMenu_Section"
    bl_label = "Link to Property"

    def draw(self, context):

        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings

        layout = self.layout

        section = getattr(context, "mustardui_propertylinkmenu_section", None)

        body_props = [x for x in obj.MustardUI_CustomProperties if x.is_animatable]
        if section is not None:
            props = [x for x in body_props if x.section == section.name]
        else:
            section_names = [x.name for x in rig_settings.body_custom_properties_sections]
            props = [x for x in body_props if x.section not in section_names]

        for prop in sorted(props, key=lambda x: x.name):
            op = layout.operator(
                MustardUI_Property_MenuLink.bl_idname, text=prop.name, icon=prop.icon
            )
            op.parent_rna = prop.rna
            op.parent_path = prop.path
            op.type = "BODY"


# Sub-menu with the properties of a single Outfit (or of the Extras collection), used by
# the Link menu
class MUSTARDUI_MT_Property_LinkMenu_Outfit(bpy.types.Menu):
    bl_idname = "MUSTARDUI_MT_Property_LinkMenu_Outfit"
    bl_label = "Link to Property"

    def draw(self, context):

        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings

        layout = self.layout

        outfit = getattr(context, "mustardui_propertylinkmenu_outfit", None)

        props = [
            x
            for x in obj.MustardUI_CustomPropertiesOutfit
            if x.is_animatable and x.outfit == outfit
        ]

        for prop in sorted(
            sorted(props, key=lambda x: x.name),
            key=lambda x: x.outfit_piece.name if x.outfit_piece is not None else "",
        ):
            if prop.outfit_piece is not None:
                name = (
                    strip_naming_convention(
                        prop.outfit_piece.name,
                        prop.outfit.name,
                        rig_settings.model_MustardUI_naming_convention,
                    )
                    + " - "
                    + prop.name
                )
            else:
                name = prop.name
            op = layout.operator(MustardUI_Property_MenuLink.bl_idname, text=name, icon=prop.icon)
            op.parent_rna = prop.rna
            op.parent_path = prop.path
            op.type = "OUTFIT"


# Operator to create the list of sections when right-clicking on the property ->
# Link to property
class MUSTARDUI_MT_Property_LinkMenu(bpy.types.Menu):
    bl_idname = "MUSTARDUI_MT_Property_LinkMenu"
    bl_label = "Link to Property"

    @classmethod
    def poll(cls, context):

        res, arm = mustardui_active_object(context, config=1)
        return res

    def draw(self, context):

        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings

        layout = self.layout

        no_prop = True

        # Body properties, one sub-menu for each Section
        body_props = [x for x in obj.MustardUI_CustomProperties if x.is_animatable]
        if len(body_props) > 0:
            layout.label(text="Properties", icon="PROPERTIES")
            no_prop = False

            sections = rig_settings.body_custom_properties_sections
            section_names = [x.name for x in sections]

            if len([x for x in body_props if x.section not in section_names]) > 0:
                layout.menu(
                    MUSTARDUI_MT_Property_LinkMenu_Section.bl_idname,
                    text="No Section",
                    icon="DOT",
                )

            for sec in sections:
                if len([x for x in body_props if x.section == sec.name]) < 1:
                    continue
                layout.context_pointer_set("mustardui_propertylinkmenu_section", sec)
                layout.menu(
                    MUSTARDUI_MT_Property_LinkMenu_Section.bl_idname,
                    text=sec.name,
                    icon=sec.icon,
                )

        # Outfit properties, one sub-menu for each Outfit
        outfit_props = [
            x
            for x in obj.MustardUI_CustomPropertiesOutfit
            if x.is_animatable
            and x.outfit != rig_settings.extras_collection
            and x.outfit is not None
        ]
        extras_props = (
            [
                x
                for x in obj.MustardUI_CustomPropertiesOutfit
                if x.is_animatable and x.outfit == rig_settings.extras_collection
            ]
            if rig_settings.extras_collection is not None
            else []
        )

        if len(outfit_props) > 0 or len(extras_props) > 0:
            if not no_prop:
                layout.separator()
            layout.label(text="Outfits", icon="MOD_CLOTH")
            no_prop = False

            outfit_collections = [
                x.collection for x in rig_settings.outfits_collections if x.collection is not None
            ]
            for prop in outfit_props:
                if prop.outfit not in outfit_collections:
                    outfit_collections.append(prop.outfit)

            for collection in outfit_collections:
                if len([x for x in outfit_props if x.outfit == collection]) < 1:
                    continue
                layout.context_pointer_set("mustardui_propertylinkmenu_outfit", collection)
                layout.menu(
                    MUSTARDUI_MT_Property_LinkMenu_Outfit.bl_idname,
                    text=strip_naming_convention_collection(
                        collection.name,
                        rig_settings.model_name,
                        rig_settings.model_MustardUI_naming_convention,
                    ),
                    icon="MOD_CLOTH",
                )

            if len(extras_props) > 0:
                layout.context_pointer_set(
                    "mustardui_propertylinkmenu_outfit", rig_settings.extras_collection
                )
                layout.menu(
                    MUSTARDUI_MT_Property_LinkMenu_Outfit.bl_idname,
                    text=strip_naming_convention_collection(
                        rig_settings.extras_collection.name,
                        rig_settings.model_name,
                        rig_settings.model_MustardUI_naming_convention,
                    ),
                    icon="PLUS",
                )

        # Hair properties
        hair_props = [x for x in obj.MustardUI_CustomPropertiesHair if x.is_animatable]
        if len(hair_props) > 0:
            if not no_prop:
                layout.separator()
            layout.label(text="Hair", icon="STRANDS")
            no_prop = False
        for prop in sorted(hair_props, key=lambda x: x.name):
            if prop.hair is not None:
                hair_name = strip_naming_convention(
                    prop.hair.name,
                    rig_settings.hair_collection.name,
                    rig_settings.model_MustardUI_naming_convention,
                )
                op = layout.operator(
                    MustardUI_Property_MenuLink.bl_idname,
                    text=hair_name + " - " + prop.name,
                    icon=prop.icon,
                )
            else:
                op = layout.operator(
                    MustardUI_Property_MenuLink.bl_idname,
                    text="Global - " + prop.name,
                    icon=prop.icon,
                )
            op.parent_rna = prop.rna
            op.parent_path = prop.path
            op.type = "HAIR"

        if no_prop:
            layout.label(text="No properties found")


menus = (
    OUTLINER_MT_MustardUI_PropertySectionMenu,
    OUTLINER_MT_MustardUI_PropertyOutfitMenu,
    OUTLINER_MT_MustardUI_PropertyOutfitPieceMenu,
    OUTLINER_MT_MustardUI_PropertyHairMenu,
    MUSTARDUI_MT_Property_LinkMenu_Section,
    MUSTARDUI_MT_Property_LinkMenu_Outfit,
    MUSTARDUI_MT_Property_LinkMenu,
)


def register():
    for m in menus:
        bpy.utils.register_class(m)

    from .menus_functions import mustardui_property_menuadd

    bpy.types.UI_MT_button_context_menu.append(mustardui_property_menuadd)
    from .menus_functions import mustardui_property_link

    bpy.types.UI_MT_button_context_menu.append(mustardui_property_link)


def unregister():
    for m in reversed(menus):
        bpy.utils.unregister_class(m)

    from .menus_functions import mustardui_property_link

    bpy.types.UI_MT_button_context_menu.remove(mustardui_property_link)
    from .menus_functions import mustardui_property_menuadd

    bpy.types.UI_MT_button_context_menu.remove(mustardui_property_menuadd)
