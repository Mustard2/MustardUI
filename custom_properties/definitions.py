import bpy
from bpy.props import *
from ..misc.icons_list import *


class MustardUI_LinkedProperty(bpy.types.PropertyGroup):
    # Internal stored properties
    rna: StringProperty(name="RNA")
    path: StringProperty(name="Path")


class MustardUI_CustomProperty(bpy.types.PropertyGroup):
    # Type
    cp_type: EnumProperty(name="Type",
                          default="BODY",
                          items=(
                              ("BODY", "Body", "Body"),
                              ("OUTFIT", "Outfit", "Outfit"),
                              ("HAIR", "Hair", "Hair"))
                          )

    # User defined properties
    name: StringProperty(name="Custom property name")
    icon: EnumProperty(name='Icon',
                       description="Choose the icon",
                       items=mustardui_icon_list)
    advanced: BoolProperty(name='Advanced',
                           description="The property is shown only when Advanced settings are enabled")
    hidden: BoolProperty(name='Hidden',
                         description="The property is hidden from the UI.\nThis can be useful if the property is just "
                                     "a proxy for some model_selection (e.g. for On Switch actions)")

    # Internal stored properties
    rna: StringProperty(name="RNA")
    path: StringProperty(name="Path")
    prop_name: StringProperty(name="Property Name")
    is_animatable: BoolProperty(name="Animatable")
    type: StringProperty(name="Type")
    array_length: IntProperty(name="Array Length")
    subtype: StringProperty(name="Subtype")
    force_type: EnumProperty(name="Force Property Type",
                             default="None",
                             items=(
                                 ("None", "None", "None"),
                                 ("Int", "Int", "Int"),
                                 ("Bool", "Bool", "Bool"))
                             )

    # Properties stored to rebuild custom properties in case of troubles
    description: StringProperty()
    default_int: IntProperty()
    min_int: IntProperty()
    max_int: IntProperty()
    default_float: FloatProperty()
    min_float: FloatProperty()
    max_float: FloatProperty()
    default_array: StringProperty()

    # Linked properties
    linked_properties: CollectionProperty(type=MustardUI_LinkedProperty)

    # Section settings
    section: StringProperty(default="")
    add_section: BoolProperty(default=False,
                              name="Add to section",
                              description="Add the property to the selected section")

    # Outfits
    # Poll function for the selection of mesh only in pointer properties
    def poll_mesh(self, object):
        rig_settings = self.id_data.MustardUI_RigSettings
        return object.type == 'MESH' and object in [x for x in rig_settings.hair_collection.objects]

    # Poll function for the selection of mesh belonging to an outfit in pointer properties
    def outfit_switcher_poll_collection(self, object):
        rig_settings = self.id_data.MustardUI_RigSettings
        return object in [x.collection for x in rig_settings.outfits_collections if
                          x.collection is not None] or object == rig_settings.extras_collection

    # Poll function for the selection of mesh belonging to an outfit in pointer properties
    def outfit_switcher_poll_mesh(self, object):
        rig_settings = self.id_data.MustardUI_RigSettings
        if self.outfit is not None:
            items = self.outfit.all_objects if rig_settings.outfit_config_subcollections else self.outfit.objects
            if object in [x for x in items]:
                return object.type == 'MESH'

        return False

    outfit: PointerProperty(name="Outfit Collection",
                            type=bpy.types.Collection,
                            poll=outfit_switcher_poll_collection)
    outfit_piece: PointerProperty(name="Outfit Piece",
                                  type=bpy.types.Object,
                                  poll=outfit_switcher_poll_mesh)
    outfit_enable_on_switch: BoolProperty(default=False,
                                          name="Enable on Outfit Switch",
                                          description="Set the value of this property to the max value when you "
                                                      "enable the outfit/outfit piece")
    outfit_disable_on_switch: BoolProperty(default=False,
                                           name="Disable on Outfit Switch",
                                           description="Set the value of this property to the default value when you "
                                                       "disable the outfit/outfit piece")

    # Hair
    hair: PointerProperty(name="Hair Style",
                          type=bpy.types.Object,
                          poll=poll_mesh)


def register():
    bpy.utils.register_class(MustardUI_LinkedProperty)
    bpy.utils.register_class(MustardUI_CustomProperty)
    bpy.types.Armature.MustardUI_CustomProperties = CollectionProperty(type=MustardUI_CustomProperty)
    bpy.types.Armature.MustardUI_CustomPropertiesOutfit = CollectionProperty(type=MustardUI_CustomProperty)
    bpy.types.Armature.MustardUI_CustomPropertiesHair = CollectionProperty(type=MustardUI_CustomProperty)


def unregister():
    del bpy.types.Armature.MustardUI_CustomPropertiesHair
    del bpy.types.Armature.MustardUI_CustomPropertiesOutfit
    del bpy.types.Armature.MustardUI_CustomProperties
    bpy.utils.unregister_class(MustardUI_CustomProperty)
    bpy.utils.unregister_class(MustardUI_LinkedProperty)
