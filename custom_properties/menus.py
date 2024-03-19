from bpy.props import *
from ..model_selection.active_object import *
from .ops_props import MustardUI_Property_MenuAdd
from .ops_link import MustardUI_Property_MenuLink


class OUTLINER_MT_MustardUI_PropertySectionMenu(bpy.types.Menu):
    bl_idname = 'OUTLINER_MT_MustardUI_PropertySectionMenu'
    bl_label = 'Add to MustardUI (Section)'

    def draw(self, context):
        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings

        layout = self.layout

        for sec in rig_settings.body_custom_properties_sections:
            op = layout.operator(MustardUI_Property_MenuAdd.bl_idname, text=sec.name, icon=sec.icon)
            op.section = sec.name
            op.outfit = ""
            op.outfit_piece = ""
            op.hair = ""


# Operators to create the list of outfits when right-clicking on a property
class OUTLINER_MT_MustardUI_PropertyOutfitPieceMenu(bpy.types.Menu):
    bl_idname = 'OUTLINER_MT_MustardUI_PropertyOutfitPieceMenu'
    bl_label = 'Add to MustardUI Outfit'

    def draw(self, context):

        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings

        layout = self.layout

        if context.mustardui_propertyoutfitmenu_sel != rig_settings.extras_collection:
            op = layout.operator(MustardUI_Property_MenuAdd.bl_idname,
                                 text="Add as Global Outfit property",
                                 icon="TRIA_RIGHT")
            op.section = ""
            op.outfit = context.mustardui_propertyoutfitmenu_sel.name
            op.outfit_piece = ""
            op.hair = ""

        items = context.mustardui_propertyoutfitmenu_sel.all_objects if rig_settings.outfit_config_subcollections else context.mustardui_propertyoutfitmenu_sel.objects
        for obj in items:
            op = layout.operator(MustardUI_Property_MenuAdd.bl_idname,
                                 icon="DOT",
                                 text=obj.name[
                                      len(context.mustardui_propertyoutfitmenu_sel.name + " - "):] if rig_settings.model_MustardUI_naming_convention else obj.name)
            op.section = ""
            op.outfit = context.mustardui_propertyoutfitmenu_sel.name
            op.outfit_piece = obj.name
            op.hair = ""


# Operators to create the list of outfits when right-clicking on a property
class OUTLINER_MT_MustardUI_PropertyOutfitMenu(bpy.types.Menu):
    bl_idname = 'OUTLINER_MT_MustardUI_PropertyOutfitMenu'
    bl_label = 'Add to MustardUI Outfit'

    def draw(self, context):

        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings

        layout = self.layout

        outfit_indices = []
        for i in range(0, len(rig_settings.outfits_collections)):
            if rig_settings.outfits_collections[i].collection is not None:
                outfit_indices.append(i)

        for i in outfit_indices:
            layout.context_pointer_set("mustardui_propertyoutfitmenu_sel",
                                       rig_settings.outfits_collections[i].collection)
            layout.menu(OUTLINER_MT_MustardUI_PropertyOutfitPieceMenu.bl_idname,
                        icon="MOD_CLOTH",
                        text=rig_settings.outfits_collections[i].collection.name[
                             len(rig_settings.model_name):] if rig_settings.model_MustardUI_naming_convention else
                        rig_settings.outfits_collections[i].collection.name)
        if rig_settings.extras_collection is not None:
            items = rig_settings.extras_collection.all_objects if rig_settings.outfit_config_subcollections else rig_settings.extras_collection.objects
            if len(items) > 0:
                layout.context_pointer_set("mustardui_propertyoutfitmenu_sel", rig_settings.extras_collection)
                layout.menu(OUTLINER_MT_MustardUI_PropertyOutfitPieceMenu.bl_idname,
                            icon="PLUS",
                            text=rig_settings.extras_collection.name[
                                 len(rig_settings.model_name):] if rig_settings.model_MustardUI_naming_convention else rig_settings.extras_collection.name)


# Operators to create the list of outfits when right-clicking on a property
class OUTLINER_MT_MustardUI_PropertyHairMenu(bpy.types.Menu):
    bl_idname = 'OUTLINER_MT_MustardUI_PropertyHairMenu'
    bl_label = 'Add to MustardUI Hair'

    def draw(self, context):
        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings

        layout = self.layout

        for obj in [x for x in rig_settings.hair_collection.objects if x.type == "MESH"]:
            op = layout.operator(MustardUI_Property_MenuAdd.bl_idname,
                                 icon="STRANDS",
                                 text=obj.name[
                                      len(rig_settings.hair_collection.name):] if rig_settings.model_MustardUI_naming_convention else obj.name)
            op.section = ""
            op.outfit = ""
            op.outfit_piece = ""
            op.hair = obj.name


# Operator to create the list of sections when right-clicking on the property -> Link to property
class MUSTARDUI_MT_Property_LinkMenu(bpy.types.Menu):
    bl_idname = 'MUSTARDUI_MT_Property_LinkMenu'
    bl_label = 'Link to Property'

    @classmethod
    def poll(cls, context):

        res, arm = mustardui_active_object(context, config=1)
        return res

    def draw(self, context):

        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings

        layout = self.layout

        no_prop = True

        body_props = [x for x in obj.MustardUI_CustomProperties if x.is_animatable]
        if len(body_props) > 0:
            layout.label(text="Body", icon="OUTLINER_OB_ARMATURE")
        for prop in sorted(body_props, key=lambda x: x.name):
            op = layout.operator(MustardUI_Property_MenuLink.bl_idname, text=prop.name, icon=prop.icon)
            op.parent_rna = prop.rna
            op.parent_path = prop.path
            op.type = "BODY"
            no_prop = False

        outfit_props = [x for x in obj.MustardUI_CustomPropertiesOutfit if
                        x.is_animatable and x.outfit != rig_settings.extras_collection and x.outfit is not None]
        if len(outfit_props) > 0 and len(body_props) > 0:
            layout.separator()
            layout.label(text="Outfits", icon="MOD_CLOTH")
        for prop in sorted(sorted(outfit_props, key=lambda x: x.name), key=lambda x: x.outfit.name):
            outfit_name = prop.outfit.name[
                          len(rig_settings.model_name + " "):] if rig_settings.model_MustardUI_naming_convention else prop.outfit.name
            if prop.outfit_piece is not None:
                outfit_piece_name = prop.outfit_piece.name[
                                    len(prop.outfit.name + " - "):] if rig_settings.model_MustardUI_naming_convention else prop.outfit.name
                outfit_name = outfit_name + " - " + outfit_piece_name
            op = layout.operator(MustardUI_Property_MenuLink.bl_idname, text=outfit_name + " - " + prop.name,
                                 icon=prop.icon)
            op.parent_rna = prop.rna
            op.parent_path = prop.path
            op.type = "OUTFIT"
            no_prop = False

        extras_props = [x for x in obj.MustardUI_CustomPropertiesOutfit if
                        x.is_animatable and x.outfit == rig_settings.extras_collection]
        if len(extras_props) > 0 and len(body_props) > 0:
            layout.separator()
            layout.label(text="Extras", icon="PLUS")
        for prop in sorted(extras_props, key=lambda x: x.name):
            outfit_name = prop.outfit_piece.name[
                          len(rig_settings.extras_collection.name + " - "):] if rig_settings.model_MustardUI_naming_convention else prop.outfit_piece.name
            op = layout.operator(MustardUI_Property_MenuLink.bl_idname,
                                 text=outfit_name + " - " + prop.name,
                                 icon=prop.icon)
            op.parent_rna = prop.rna
            op.parent_path = prop.path
            op.type = "OUTFIT"
            no_prop = False

        hair_props = [x for x in obj.MustardUI_CustomPropertiesHair if x.is_animatable and x.hair is not None]
        if len(hair_props) > 0 and (len(outfit_props) > 0 or len(body_props) > 0):
            layout.separator()
            layout.label(text="Hair", icon="STRANDS")
        for prop in sorted(hair_props, key=lambda x: x.name):
            hair_name = prop.hair.name[
                        len(rig_settings.hair_collection.name + " "):] if rig_settings.model_MustardUI_naming_convention else prop.hair.name
            op = layout.operator(MustardUI_Property_MenuLink.bl_idname,
                                 text=hair_name + " - " + prop.name,
                                 icon=prop.icon)
            op.parent_rna = prop.rna
            op.parent_path = prop.path
            op.type = "HAIR"
            no_prop = False

        if no_prop:
            layout.label(text="No properties found")


menus = (
    OUTLINER_MT_MustardUI_PropertySectionMenu,
    OUTLINER_MT_MustardUI_PropertyOutfitMenu,
    OUTLINER_MT_MustardUI_PropertyOutfitPieceMenu,
    OUTLINER_MT_MustardUI_PropertyHairMenu,
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
