import bpy
from bpy.props import *
from ..model_selection.active_object import *
from ..misc.icons_list import mustardui_icon_list


# Class for single bone collection
class MustardUI_ArmatureBoneCollection(bpy.types.PropertyGroup):
    # Button in the UI List to draw the bone collection in the UI
    is_in_UI: BoolProperty(default=False,
                           name="Add to UI",
                           description="Enable to add this bone collection to the Armature panel")

    # Show the bone collection in the UI only if Advanced is enabled
    advanced: BoolProperty(default=False,
                                     name="Advanced",
                                     description="Enable Advanced layer.\nIf enabled, this layer will be shown in the "
                                                 "UI only if Advanced settings is enabled in the UI settings")

    # Default bone collections are enabled when Reset is used
    default: BoolProperty(default=False,
                           name="Default",
                           description="Default bone collections are enabled when Reset is used")

    # Icon
    icon: EnumProperty(name="Icon",
                       items=mustardui_icon_list)

    # Function to remove the layer from the UI if the outfit switcher is enabled
    # This is to avoid having a bone collection in the UI that is working on the outfit automatically
    def outfit_switcher_enable_update(self, context):
        if self.outfit_switcher_enable:
            self.is_in_UI = False
            self.default = False
        return

    # Poll function for the selection of mesh belonging to an outfit in pointer properties
    def outfit_switcher_poll_collection(self, object):
        rig_settings = self.id_data.MustardUI_RigSettings
        collections = [x.collection for x in rig_settings.outfits_collections if x.collection is not None]
        if rig_settings.extras_collection is not None:
            collections.append(rig_settings.extras_collection)
        if rig_settings.hair_collection is not None:
            collections.append(rig_settings.hair_collection)
        return object in collections

    # Poll function for the selection of mesh belonging to an outfit in pointer properties
    def outfit_switcher_poll_mesh(self, object):
        rig_settings = self.id_data.MustardUI_RigSettings
        if self.outfit_switcher_collection is not None:
            items = self.outfit_switcher_collection.all_objects if rig_settings.outfit_config_subcollections else self.outfit_switcher_collection.objects
            if object in [x for x in items]:
                return object.type == 'MESH'
        return False

    # Automatic outfits layer switcher
    outfit_switcher_enable: bpy.props.BoolProperty(default=False,
                                                   name="Outfit Switcher",
                                                   description="Enable automatic Outfit layer switcher.\nWhen the "
                                                               "selected outfit is enabled in the UI, this layer will "
                                                               "be shown/hidden automatically",
                                                   update=outfit_switcher_enable_update)

    outfit_switcher_collection: bpy.props.PointerProperty(name="Outfit/Hair",
                                                          description="When switching to this outfit, the layer will "
                                                                      "be shown/hidden. Or select the Hair collection "
                                                                      "if you want to enable this feature for all "
                                                                      "Hair pieces.\nSet also Outfit Piece/Hair if "
                                                                      "you want the layer to be shown only for a "
                                                                      "specific outfit piece/hair object",
                                                          type=bpy.types.Collection,
                                                          poll=outfit_switcher_poll_collection)

    outfit_switcher_object: bpy.props.PointerProperty(name="Outfit Piece/Hair",
                                                      description="When switching to this specific outfit piece/hair "
                                                                  "object, the layer will be shown/hidden",
                                                      type=bpy.types.Object,
                                                      poll=outfit_switcher_poll_mesh)

    # Children
    # Button to show children of the bone
    show_children: BoolProperty(default=False, name = "")


# Global Armature settings
class MustardUI_ArmatureSettings(bpy.types.PropertyGroup):
    # Outfit layers
    def mustardui_armature_visibility_outfits_update(self, context):
        poll, arm = mustardui_active_object(context, config=0)
        armature_settings = arm.MustardUI_ArmatureSettings
        rig_settings = arm.MustardUI_RigSettings
        collections = arm.collections_all
        for bcoll in collections:
            bcoll_settings = bcoll.MustardUI_ArmatureBoneCollection
            if bcoll_settings.outfit_switcher_enable:
                check_coll = (
                    bpy.data.collections[rig_settings.outfits_list] == bcoll_settings.outfit_switcher_collection
                    if rig_settings.outfits_list != "Nude" else False)
                if rig_settings.extras_collection is not None:
                    check_coll = check_coll or bcoll_settings.outfit_switcher_collection == rig_settings.extras_collection

                if bcoll_settings.outfit_switcher_object is None:
                    bcoll.is_visible = armature_settings.outfits and check_coll
                else:
                    bcoll.is_visible = (armature_settings.outfits and
                                        not bcoll_settings.outfit_switcher_object.MustardUI_outfit_visibility and
                                        (check_coll or bcoll_settings.outfit_switcher_object.MustardUI_outfit_lock))

        return

    outfits: bpy.props.BoolProperty(default=True,
                                    name="Outfits",
                                    description="Show/hide the outfit armature",
                                    update=mustardui_armature_visibility_outfits_update)

    def mustardui_armature_visibility_hair_update(self, context):
        poll, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings
        armature_settings = arm.MustardUI_ArmatureSettings
        if rig_settings.hair_collection is not None:
            for obj in [x for x in rig_settings.hair_collection.objects if
                        x.type == "ARMATURE" and rig_settings.hair_list in x.name]:
                obj.hide_viewport = not armature_settings.hair

    # Hair armature controller
    enable_automatic_hair: bpy.props.BoolProperty(default=True,
                                                  name="Armature Hair detection",
                                                  description="Enable the automatic armature hair detection.\nIf "
                                                              "enabled, the UI will automatically detect armatures in "
                                                              "the hair collection")

    hair: bpy.props.BoolProperty(default=True,
                                 name="Hair",
                                 description="Show/hide the hair armature",
                                 update=mustardui_armature_visibility_hair_update)

    # Enable Mirror from name
    mirror: bpy.props.BoolProperty(default=False,
                                   name="Mirror from Collection Name",
                                   description="Show two buttons (left and right) on the UI for selected bone "
                                               "collections.\nName the collections with the same name plus .R and .L "
                                               "to see them in the UI as two near buttons")


def register():
    bpy.utils.register_class(MustardUI_ArmatureBoneCollection)
    bpy.utils.register_class(MustardUI_ArmatureSettings)
    bpy.types.BoneCollection.MustardUI_ArmatureBoneCollection = bpy.props.PointerProperty(
        type=MustardUI_ArmatureBoneCollection)
    bpy.types.Armature.MustardUI_ArmatureSettings = bpy.props.PointerProperty(type=MustardUI_ArmatureSettings)


def unregister():
    del bpy.types.Armature.MustardUI_ArmatureSettings
    del bpy.types.BoneCollection.MustardUI_ArmatureBoneCollection
    bpy.utils.unregister_class(MustardUI_ArmatureSettings)
    bpy.utils.unregister_class(MustardUI_ArmatureBoneCollection)
