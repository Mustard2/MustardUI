from .menus import *


def mustardui_property_menuadd(self, context):
    res, obj = mustardui_active_object(context, config=1)

    if hasattr(context, 'button_prop') and res:

        settings = bpy.context.scene.MustardUI_Settings
        rig_settings = obj.MustardUI_RigSettings

        layout = self.layout

        layout.separator()

        op = layout.operator(MustardUI_Property_MenuAdd.bl_idname)
        op.section = ""
        op.outfit = ""
        op.outfit_piece = ""
        op.hair = ""

        sep = False
        for collection in [x for x in rig_settings.outfits_collections if x.collection is not None]:
            items = collection.collection.all_objects if rig_settings.outfit_config_subcollections else collection.collection.objects
            for object in [x for x in items]:
                if object == context.active_object:
                    op = layout.operator(MustardUI_Property_MenuAdd.bl_idname,
                                         text="Add to " + context.active_object.name, icon="MOD_CLOTH")
                    op.section = ""
                    op.outfit = collection.collection.name
                    op.outfit_piece = object.name
                    op.hair = ""
                    break
        if rig_settings.extras_collection is not None:
            items = rig_settings.extras_collection.all_objects if rig_settings.outfit_config_subcollections else rig_settings.extras_collection.objects
            if len(items) > 0:
                for object in [x for x in items]:
                    if object == context.active_object:
                        op = layout.operator(MustardUI_Property_MenuAdd.bl_idname,
                                             text="Add to " + context.active_object.name, icon="PLUS")
                        op.section = ""
                        op.outfit = rig_settings.extras_collection.name
                        op.outfit_piece = object.name
                        op.hair = ""
                        break
        if rig_settings.hair_collection is not None:
            if len(rig_settings.hair_collection.objects) > 0:
                for object in [x for x in rig_settings.hair_collection.objects if x.type == "MESH"]:
                    if object == context.active_object:
                        op = layout.operator(MustardUI_Property_MenuAdd.bl_idname,
                                             text="Add to " + context.active_object.name, icon="STRANDS")
                        op.section = ""
                        op.outfit = ""
                        op.outfit_piece = ""
                        op.hair = object.name
                        break

        layout.separator()

        if len(rig_settings.body_custom_properties_sections) > 0:
            layout.menu(OUTLINER_MT_MustardUI_PropertySectionMenu.bl_idname)
        if len([x for x in rig_settings.outfits_collections if x.collection is not None]) > 0:
            layout.menu(OUTLINER_MT_MustardUI_PropertyOutfitMenu.bl_idname, icon="MOD_CLOTH")
        if rig_settings.hair_collection is not None:
            if len(rig_settings.hair_collection.objects) > 0:
                layout.menu(OUTLINER_MT_MustardUI_PropertyHairMenu.bl_idname, icon="STRANDS")


def mustardui_property_link(self, context):
    res, obj = mustardui_active_object(context, config=1)

    if hasattr(context, 'button_prop') and res:
        layout = self.layout
        self.layout.menu(MUSTARDUI_MT_Property_LinkMenu.bl_idname, icon="LINKED")
