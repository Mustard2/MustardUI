import bpy
from . import MainPanel
from ..model_selection.active_object import *
from ..settings.rig import *
from ..tools.lattice import *
from ..tools.physics import *


class PANEL_PT_MustardUI_InitPanel(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_InitPanel"
    bl_label = "UI Configuration"

    url_MustardUI_ConfigGuide = "https://github.com/Mustard2/MustardUI/wiki/Installation-and-Configuration"

    @classmethod
    def poll(cls, context):

        res, arm = mustardui_active_object(context, config=1)
        return res

    def draw(self, context):

        layout = self.layout
        scene = context.scene

        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings
        #armature_settings = obj.MustardUI_ArmatureSettings
        tools_settings = obj.MustardUI_ToolsSettings
        lattice_settings = obj.MustardUI_LatticeSettings
        physics_settings = obj.MustardUI_PhysicsSettings

        row_scale = 1.2

        row = layout.row(align=False)
        row.label(text=obj.name, icon="OUTLINER_DATA_ARMATURE")
        row.operator('mustardui.configuration_smartcheck', icon="VIEWZOOM", text="")
        row.operator('mustardui.openlink', text="", icon="QUESTION").url = self.url_MustardUI_ConfigGuide

        box = layout.box()
        box.prop(rig_settings, "model_name", text="Name")
        box.prop(rig_settings, "model_body", text="Body")

        layout.separator()
        layout.label(text="Settings", icon="MENU_PANEL")

        # Body mesh settings
        row = layout.row(align=False)
        row.prop(rig_settings, "body_config_collapse",
                 icon="TRIA_DOWN" if not rig_settings.body_config_collapse else "TRIA_RIGHT", icon_only=True,
                 emboss=False)
        row.label(text="Body", icon="OUTLINER_OB_ARMATURE")

        if not rig_settings.body_config_collapse:
            box = layout.box()
            box.label(text="Global properties", icon="MODIFIER")
            col = box.column(align=True)
            col.prop(rig_settings, "body_enable_subdiv")
            col.prop(rig_settings, "body_enable_smoothcorr")
            col.prop(rig_settings, "body_enable_solidify")
            col.separator()
            col.prop(rig_settings, "body_enable_preserve_volume")
            col.prop(rig_settings, "body_enable_norm_autosmooth")
            col.prop(rig_settings, "body_enable_material_normal_nodes")

            # Custom properties
            box = layout.box()
            row = box.row()
            row.label(text="Custom properties", icon="PRESET_NEW")
            row.operator('mustardui.property_smartcheck', text="", icon="VIEWZOOM")

            if len(obj.MustardUI_CustomProperties) > 0:
                row = box.row()
                row.template_list("MUSTARDUI_UL_Property_UIList", "The_List", obj,
                                  "MustardUI_CustomProperties", scene, "mustardui_property_uilist_index")
                col = row.column()
                col.operator('mustardui.property_settings', icon="PREFERENCES", text="").type = "BODY"
                col.separator()
                col2 = col.column(align=True)
                opup = col2.operator('mustardui.property_switch', icon="TRIA_UP", text="")
                opup.direction = "UP"
                opup.type = "BODY"
                opdown = col2.operator('mustardui.property_switch', icon="TRIA_DOWN", text="")
                opdown.direction = "DOWN"
                opdown.type = "BODY"
                col.separator()
                col.operator('mustardui.property_remove', icon="X", text="").type = "BODY"

                col = box.column(align=True)
                col.prop(rig_settings, 'body_custom_properties_icons')
                col.prop(rig_settings, 'body_custom_properties_name_order')

            else:
                box = box.box()
                box.label(text="No property added yet", icon="ERROR")

            if len(obj.MustardUI_CustomProperties) > 0:
                box = layout.box()
                row = box.row(align=False)
                row.label(text="Sections", icon="LINENUMBERS_OFF")
                if len(rig_settings.body_custom_properties_sections) == 0:
                    box.operator('mustardui.body_addsection')
                else:
                    box = box.box()
                    row.operator('mustardui.body_addsection', text="", icon="ADD")
                    section_len = len(rig_settings.body_custom_properties_sections)
                    for i_sec in sorted([x for x in range(0, section_len)],
                                        key=lambda x: rig_settings.body_custom_properties_sections[x].id):
                        section = rig_settings.body_custom_properties_sections[i_sec]
                        row = box.row(align=False)
                        row.label(text=section.name,
                                  icon=section.icon if (section.icon != "" and section.icon != "NONE") else "DOT")
                        row.operator('mustardui.body_propertyaddtosection', text="",
                                     icon="PRESET").section_name = section.name
                        row.operator('mustardui.body_settingssection', text="", icon="PREFERENCES").name = section.name
                        row2 = row.row(align=True)
                        col = row2.column(align=True)
                        col.enabled = section.id > 0
                        swap_up = col.operator('mustardui.body_swapsection', text="", icon="TRIA_UP")
                        swap_up.name = section.name
                        swap_up.mod = True
                        col = row2.column(align=True)
                        col.enabled = section.id < section_len - 1
                        swap_down = col.operator('mustardui.body_swapsection', text="", icon="TRIA_DOWN")
                        swap_down.name = section.name
                        swap_down.mod = False
                        row.operator('mustardui.body_deletesection', text="", icon="X").name = section.name

        # Outfits properties
        row = layout.row(align=False)
        row.prop(rig_settings, "outfit_config_collapse",
                 icon="TRIA_DOWN" if not rig_settings.outfit_config_collapse else "TRIA_RIGHT", icon_only=True,
                 emboss=False)
        row.label(text="Outfits", icon="MOD_CLOTH")

        if not rig_settings.outfit_config_collapse:
            box = layout.box()
            box.label(text="General settings", icon="MODIFIER")
            col = box.column(align=True)
            col.prop(rig_settings, "outfit_nude")
            col.prop(rig_settings, "outfit_config_subcollections")
            col.prop(rig_settings, "outfit_additional_options")

            if settings.advanced:
                col.separator()
                col.prop(rig_settings, "outfit_switch_armature_disable")
                col.prop(rig_settings, "outfits_update_tag_on_switch")
            if len([x for x in rig_settings.outfits_collections if x.collection != None]) > 0:
                box = layout.box()
                # Outfit list
                row = box.row()
                row.label(text="Outfits List", icon="OUTLINER_COLLECTION")
                row.operator("Mustardui.outfits_smartcheck", text="", icon="VIEWZOOM")
                box = box.box()
                for collection in sorted([x for x in rig_settings.outfits_collections if x.collection != None],
                                         key=lambda x: x.collection.name):
                    row = box.row(align=True)
                    row.label(text=collection.collection.name)
                    row.operator("mustardui.remove_outfit", text="", icon="X").col = collection.collection.name
                    row.operator("mustardui.delete_outfit", text="", icon="TRASH").col = collection.collection.name

                # Outfit properties
                box = layout.box()
                box.label(text="Global properties", icon="MODIFIER")
                col = box.column(align=True)
                col.prop(rig_settings, "outfits_enable_global_subsurface")
                col.prop(rig_settings, "outfits_enable_global_smoothcorrection")
                col.prop(rig_settings, "outfits_enable_global_shrinkwrap")
                col.prop(rig_settings, "outfits_enable_global_mask")
                col.prop(rig_settings, "outfits_enable_global_solidify")
                col.prop(rig_settings, "outfits_enable_global_triangulate")
                col.prop(rig_settings, "outfits_enable_global_normalautosmooth")

                # Custom properties
                box = layout.box()
                row = box.row()
                row.label(text="Custom properties", icon="PRESET_NEW")

                if len(obj.MustardUI_CustomPropertiesOutfit) > 0:
                    row = box.row()
                    row.template_list("MUSTARDUI_UL_Property_UIListOutfits", "The_List", obj,
                                      "MustardUI_CustomPropertiesOutfit", scene,
                                      "mustardui_property_uilist_outfits_index")
                    col = row.column()
                    col.operator('mustardui.property_settings', icon="PREFERENCES", text="").type = "OUTFIT"
                    col.separator()
                    col2 = col.column(align=True)
                    opup = col2.operator('mustardui.property_switch', icon="TRIA_UP", text="")
                    opup.direction = "UP"
                    opup.type = "OUTFIT"
                    opdown = col2.operator('mustardui.property_switch', icon="TRIA_DOWN", text="")
                    opdown.direction = "DOWN"
                    opdown.type = "OUTFIT"
                    col.separator()
                    col.operator('mustardui.property_remove', icon="X", text="").type = "OUTFIT"

                    col = box.column(align=True)
                    col.prop(rig_settings, 'outfit_custom_properties_icons')
                    col.prop(rig_settings, 'outfit_custom_properties_name_order')

                else:
                    box = box.box()
                    box.label(text="No property added yet", icon="ERROR")

            else:
                box = layout.box()
                box.label(text="No Outfits added yet.", icon="ERROR")

            box = layout.box()

            # Extras list
            box.label(text="Extras", icon="PLUS")
            box.prop(rig_settings, "extras_collection", text="")
            box.prop(rig_settings, "extras_collapse_enable")

        # Hair
        row = layout.row(align=False)
        row.prop(rig_settings, "hair_config_collapse",
                 icon="TRIA_DOWN" if not rig_settings.hair_config_collapse else "TRIA_RIGHT", icon_only=True,
                 emboss=False)
        row.label(text="Hair", icon="STRANDS")

        if not rig_settings.hair_config_collapse:
            box = layout.box()
            box.label(text="Hair Collection", icon="OUTLINER_COLLECTION")
            box.prop(rig_settings, "hair_collection", text="")

            if rig_settings.hair_collection != None:
                if len(rig_settings.hair_collection.objects) > 0:

                    if settings.advanced:
                        box = layout.box()
                        box.label(text="General settings", icon="MODIFIER")
                        col = box.column(align=True)
                        col.prop(rig_settings, "hair_switch_armature_disable")
                        col.prop(rig_settings, "hair_update_tag_on_switch")

                    # Global properties
                    box = layout.box()
                    box.label(text="Global properties", icon="MODIFIER")
                    col = box.column(align=True)
                    col.prop(rig_settings, "hair_enable_global_subsurface")
                    col.prop(rig_settings, "hair_enable_global_smoothcorrection")
                    col.prop(rig_settings, "hair_enable_global_solidify")
                    col.prop(rig_settings, "hair_enable_global_particles")
                    col.prop(rig_settings, "hair_enable_global_normalautosmooth")

                    # Custom properties
                    box = layout.box()
                    row = box.row()
                    row.label(text="Custom properties", icon="PRESET_NEW")

                    if len(obj.MustardUI_CustomPropertiesHair) > 0:
                        row = box.row()
                        row.template_list("MUSTARDUI_UL_Property_UIListHair", "The_List", obj,
                                          "MustardUI_CustomPropertiesHair", scene,
                                          "mustardui_property_uilist_hair_index")
                        col = row.column()
                        col.operator('mustardui.property_settings', icon="PREFERENCES", text="").type = "HAIR"
                        col.separator()
                        col2 = col.column(align=True)
                        opup = col2.operator('mustardui.property_switch', icon="TRIA_UP", text="")
                        opup.direction = "UP"
                        opup.type = "HAIR"
                        opdown = col2.operator('mustardui.property_switch', icon="TRIA_DOWN", text="")
                        opdown.direction = "DOWN"
                        opdown.type = "HAIR"
                        col.separator()
                        col.operator('mustardui.property_remove', icon="X", text="").type = "HAIR"

                        col = box.column(align=True)
                        col.prop(rig_settings, 'hair_custom_properties_icons')
                        col.prop(rig_settings, 'hair_custom_properties_name_order')

                    else:
                        box = box.box()
                        box.label(text="No property added yet", icon="ERROR")
                else:
                    box = layout.box()
                    box.label(text="No Hair Objects in the collection.", icon="ERROR")

            box = layout.box()
            box.label(text="Other Hair", icon="OUTLINER_OB_CURVES")
            col = box.column()
            col.prop(rig_settings, "curves_hair_enable", text="Show Curves Hair")
            col.prop(rig_settings, "particle_systems_enable", text="Show Particle Systems")

        # Armature
        # row = layout.row(align=False)
        # row.prop(armature_settings, "config_collapse",
        #          icon="TRIA_DOWN" if not armature_settings.config_collapse else "TRIA_RIGHT", icon_only=True,
        #          emboss=False)
        # row.label(text="Armature", icon="ARMATURE_DATA")
        #
        # if not armature_settings.config_collapse:
        #     box = layout.box()
        #
        #     if len(armature_settings.layers) < 1:
        #
        #         box.operator('mustardui.armature_initialize', text="Add Armature Panel").clean = False
        #
        #     else:
        #
        #         box.label(text="General Settings", icon="MODIFIER")
        #         box.prop(armature_settings, 'enable_automatic_hair')
        #
        #         box.operator('mustardui.armature_initialize', text="Remove Armature Panel").clean = True
        #
        #         box = layout.box()
        #         box.label(text="Layers List", icon="PRESET")
        #         box.prop(armature_settings, 'config_layer', text="")
        #
        #         for i in sorted([x for x in range(0, 32) if armature_settings.config_layer[x]],
        #                         key=lambda x: armature_settings.layers[x].id):
        #             box2 = box.box()
        #             row = box2.row(align=True)
        #             row.prop(armature_settings.layers[i], "layer_config_collapse",
        #                      icon="TRIA_DOWN" if not armature_settings.layers[
        #                          i].layer_config_collapse else "TRIA_RIGHT", icon_only=True, emboss=False)
        #             if armature_settings.layers[i].name != "":
        #                 row.label(text="Layer " + str(i) + " (" + armature_settings.layers[i].name + ")")
        #             else:
        #                 row.label(text="Layer " + str(i))
        #
        #             col = row.column(align=True)
        #             if not armature_settings.layers[i].id > 0:
        #                 col.enabled = False
        #             op_up = col.operator('mustardui.armature_sort', text="", icon="TRIA_UP")
        #             op_up.up = True
        #             op_up.sort_id = armature_settings.layers[i].id
        #
        #             col = row.column(align=True)
        #             if not armature_settings.layers[i].id < armature_settings.last_id:
        #                 col.enabled = False
        #             op_down = col.operator('mustardui.armature_sort', text="", icon="TRIA_DOWN")
        #             op_down.up = False
        #             op_down.sort_id = armature_settings.layers[i].id
        #
        #             if not armature_settings.layers[i].layer_config_collapse:
        #
        #                 row = box2.row()
        #                 row.enabled = not armature_settings.layers[i].outfit_switcher_enable
        #                 row.prop(armature_settings.layers[i], 'name')
        #                 col = box2.column(align=True)
        #                 row = col.row()
        #                 row.enabled = not armature_settings.layers[i].outfit_switcher_enable
        #                 row.prop(armature_settings.layers[i], 'advanced')
        #
        #                 col.prop(armature_settings.layers[i], 'outfit_switcher_enable')
        #                 if armature_settings.layers[i].outfit_switcher_enable:
        #                     col.prop(armature_settings.layers[i], 'outfit_switcher_collection', text="Collection")
        #                     if armature_settings.layers[i].outfit_switcher_collection != None:
        #                         col.prop(armature_settings.layers[i], 'outfit_switcher_object', text="Object")
        #
        #                 # Mirror options for debug
        #                 if settings.debug:
        #                     col = box2.column(align=True)
        #                     col.enabled = False
        #                     col.prop(armature_settings.layers[i], 'mirror')
        #                     if armature_settings.layers[i].mirror:
        #                         row = col.row()
        #                         row.prop(armature_settings.layers[i], 'mirror_left')
        #                         row.prop(armature_settings.layers[i], 'mirror_layer')

        # Physics
        row = layout.row(align=False)
        row.prop(physics_settings, "config_collapse",
                 icon="TRIA_DOWN" if not physics_settings.config_collapse else "TRIA_RIGHT", icon_only=True,
                 emboss=False)
        row.label(text="Physics", icon="PHYSICS")

        if not physics_settings.config_collapse:

            box = layout.box()
            box.label(text="General Settings", icon="MODIFIER")
            box.operator('mustardui.tools_physics_clean', text="Clean Physics Panel")

            box = layout.box()
            box.label(text="Add Item", icon="ADD")

            box.prop(physics_settings, 'config_MustardUI_preset')
            box.prop(physics_settings, 'config_cage_object')
            if physics_settings.config_cage_object != None:
                box.prop_search(physics_settings, 'config_cage_object_pin_vertex_group',
                                physics_settings.config_cage_object, "vertex_groups")
                box.prop_search(physics_settings, 'config_cage_object_bending_stiff_vertex_group',
                                physics_settings.config_cage_object, "vertex_groups")
            box.operator('mustardui.tools_physics_createitem', text="Add item", icon="ADD")

            if len(physics_settings.physics_items) > 0:
                box = layout.box()
                box.label(text="Items List", icon="PRESET")

            for item in physics_settings.physics_items:

                box2 = box.box()

                try:
                    cage_object_name = item.cage_object.name
                    row = box2.row(align=False)
                    row.prop(item, "config_collapse", icon="TRIA_DOWN" if not item.config_collapse else "TRIA_RIGHT",
                             icon_only=True, emboss=False)
                    row.label(text=item.cage_object.name[
                                   len(rig_settings.model_name + ' Physics - '):] if rig_settings.model_MustardUI_naming_convention else item.cage_object.name)
                    row.operator('mustardui.tools_physics_deleteitem', text="",
                                 icon="X").cage_object_name = item.cage_object.name
                except:
                    row = box2.row(align=False)
                    row.label(text="Item not found.", icon="ERROR")
                    row.operator('mustardui.tools_physics_deleteitem', text="", icon="X").cage_object_name = ""
                    continue

                if not item.config_collapse:

                    box2.prop(item, 'MustardUI_preset')
                    row = box2.row()
                    row.enabled = False
                    row.prop(item, 'cage_object')
                    if item.cage_object != None:
                        row = box2.row()
                        row.enabled = False
                        row.prop_search(item, 'cage_object_pin_vertex_group', item.cage_object, "vertex_groups")
                        row = box2.row()
                        row.enabled = False
                        row.prop_search(item, 'cage_object_bending_stiff_vertex_group', item.cage_object,
                                        "vertex_groups")

        # Tools
        row = layout.row(align=False)
        row.prop(tools_settings, "tools_config_collapse",
                 icon="TRIA_DOWN" if not tools_settings.tools_config_collapse else "TRIA_RIGHT", icon_only=True,
                 emboss=False)
        row.label(text="Tools", icon="TOOL_SETTINGS")

        if not tools_settings.tools_config_collapse:
            box = layout.box()
            box.label(text="Enable Tools", icon="MODIFIER")
            col = box.column(align=True)
            col.prop(rig_settings, 'simplify_main_enable')
            col.prop(tools_settings, 'childof_enable')
            col.prop(tools_settings, 'autobreath_enable')
            col.prop(tools_settings, 'autoeyelid_enable')
            col.prop(tools_settings, 'lips_shrinkwrap_enable')
            col.prop(lattice_settings, 'lattice_panel_enable')

            if tools_settings.autoeyelid_enable:
                box = layout.box()
                box.label(text="Auto Eyelid Tool Settings", icon="HIDE_OFF")
                box.prop(tools_settings, 'autoeyelid_driver_type', text="Type")
                col = box.column(align=True)
                if tools_settings.autoeyelid_driver_type == "SHAPE_KEY":
                    col.prop_search(tools_settings, "autoeyelid_eyeL_shapekey", rig_settings.model_body.data.shape_keys,
                                    "key_blocks")
                    col.prop_search(tools_settings, "autoeyelid_eyeR_shapekey", rig_settings.model_body.data.shape_keys,
                                    "key_blocks")
                else:
                    col.prop(tools_settings, "autoeyelid_morph")

            if lattice_settings.lattice_panel_enable:
                box = layout.box()
                box.label(text="Lattice Tool Settings", icon="MOD_LATTICE")
                box.prop(lattice_settings, 'lattice_object')
                box.operator('mustardui.tools_latticesetup', text="Lattice Setup").mod = 0
                box.operator('mustardui.tools_latticesetup', text="Lattice Clean").mod = 1

        # External addons
        row = layout.row(align=False)
        row.prop(rig_settings, "external_addons_collapse",
                 icon="TRIA_DOWN" if not rig_settings.external_addons_collapse else "TRIA_RIGHT", icon_only=True,
                 emboss=False)
        row.label(text="External Add-ons", icon="DOCUMENTS")
        if not rig_settings.external_addons_collapse:
            box = layout.box()
            box.label(text="Enable Support", icon="MODIFIER")
            row = box.row()
            if settings.status_diffeomorphic != 2:
                row.enabled = False
            row.prop(rig_settings, "diffeomorphic_support")
            if rig_settings.diffeomorphic_support:

                box = layout.box()
                if settings.status_diffeomorphic == 1:
                    box.label(icon='ERROR', text="Debug: Diffeomorphic not enabled!")
                elif settings.status_diffeomorphic == 0:
                    box.label(icon='ERROR', text="Debug: Diffeomorphic not installed!")
                else:

                    box.label(text="Diffeomorphic Settings", icon="OUTLINER_DATA_SURFACE")

                    box2 = box.box()
                    box2.label(text="Morphs", icon="SHAPEKEY_DATA")
                    box2.prop(rig_settings, "diffeomorphic_emotions_units")
                    box2.prop(rig_settings, "diffeomorphic_emotions")
                    if rig_settings.diffeomorphic_emotions:
                        row = box2.row(align=True)
                        row.label(text="Custom morphs")
                        row.scale_x = row_scale
                        row.prop(rig_settings, "diffeomorphic_emotions_custom", text="")
                    box2.prop(rig_settings, "diffeomorphic_facs_emotions_units")
                    box2.prop(rig_settings, "diffeomorphic_facs_emotions")
                    box2.prop(rig_settings, "diffeomorphic_body_morphs")
                    if rig_settings.diffeomorphic_body_morphs:
                        row = box2.row(align=True)
                        row.label(text="Custom morphs")
                        row.scale_x = row_scale
                        row.prop(rig_settings, "diffeomorphic_body_morphs_custom", text="")

                    box2.separator()
                    row = box2.row(align=True)
                    row.label(text="Disable Exceptions")
                    row.scale_x = row_scale
                    row.prop(rig_settings, "diffeomorphic_disable_exceptions", text="")

                    box = box.box()
                    box.label(text="  Current morphs number: " + str(rig_settings.diffeomorphic_morphs_number))
                    box.operator('mustardui.dazmorphs_checkmorphs')

        # Links
        row = layout.row(align=False)
        row.prop(rig_settings, "url_config_collapse",
                 icon="TRIA_DOWN" if not rig_settings.url_config_collapse else "TRIA_RIGHT", icon_only=True,
                 emboss=False)
        row.label(text="Links", icon="WORLD")

        if not rig_settings.url_config_collapse:
            box = layout.box()

            row = box.row(align=True)
            row.label(text="Website")
            row.scale_x = row_scale
            row.prop(rig_settings, 'url_website', text="")

            row = box.row(align=True)
            row.label(text="Patreon")
            row.scale_x = row_scale
            row.prop(rig_settings, 'url_patreon', text="")

            row = box.row(align=True)
            row.label(text="Twitter")
            row.scale_x = row_scale
            row.prop(rig_settings, 'url_twitter', text="")

            row = box.row(align=True)
            row.label(text="Smutba.se")
            row.scale_x = row_scale
            row.prop(rig_settings, 'url_smutbase', text="")

            row = box.row(align=True)
            row.label(text="Documentation")
            row.scale_x = row_scale
            row.prop(rig_settings, 'url_documentation', text="")

            row = box.row(align=True)
            row.label(text="Report Bug")
            row.scale_x = row_scale
            row.prop(rig_settings, 'url_reportbug', text="")

        # Various properties
        row = layout.row(align=False)
        row.prop(rig_settings, "various_config_collapse",
                 icon="TRIA_DOWN" if not rig_settings.various_config_collapse else "TRIA_RIGHT", icon_only=True,
                 emboss=False)
        row.label(text="Version & Others", icon="SETTINGS")
        if not rig_settings.various_config_collapse:
            box = layout.box()
            box.label(text="Version", icon="INFO")
            box.prop(rig_settings, "model_version", text="")

            box = layout.box()
            box.label(text="Naming", icon="OUTLINER_DATA_FONT")
            box.prop(rig_settings, "model_MustardUI_naming_convention")

        if settings.debug:
            row = layout.row(align=False)
            row.prop(rig_settings, "debug_config_collapse",
                     icon="TRIA_DOWN" if not rig_settings.debug_config_collapse else "TRIA_RIGHT", icon_only=True,
                     emboss=False)
            row.label(text="Debug Informations", icon="INFO")

            if not rig_settings.debug_config_collapse:
                box = layout.box()
                box.enabled = False
                box.prop(rig_settings, "model_armature_object", text="Armature Object")
                box.prop(rig_settings, "model_rig_type", text="Rig Type")

        # Configuration button
        layout.separator()
        col = layout.column(align=True)
        col.prop(settings, "debug")
        col.prop(settings, "advanced")
        if not obj.MustardUI_created:
            col.prop(settings, "viewport_model_selection_after_configuration")
        layout.operator('mustardui.configuration', text="End the configuration")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_InitPanel)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_InitPanel)
