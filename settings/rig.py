import bpy
from ..model_selection.active_object import *
from ..settings.outfit import *
from ..settings.daz_morph import *
from ..settings.section import *


# Main class to store model settings
class MustardUI_RigSettings(bpy.types.PropertyGroup):
    # ------------------------------------------------------------------------
    #    General model properties
    # ------------------------------------------------------------------------

    # Model name
    model_name: bpy.props.StringProperty(default="",
                                         name="Model name",
                                         description="Model name")

    # Body object
    # Poll function for the selection of mesh only in pointer properties
    def poll_mesh(self, object):
        return object.type == 'MESH'

    model_body: bpy.props.PointerProperty(name="Model Body",
                                          description="Select the mesh that will be considered the body",
                                          type=bpy.types.Object,
                                          poll=poll_mesh)

    # Armature object
    # Poll function for the selection of armatures for the armature object
    def poll_armature(self, object):
        if object.type == 'ARMATURE':
            return object.data == self.id_data
        return False

    model_armature_object: bpy.props.PointerProperty(name="Model Armature Object",
                                                     description="Mesh that will be considered the body.\nSet or "
                                                                 "change this Object if you know what you are doing",
                                                     type=bpy.types.Object,
                                                     poll=poll_armature)

    # ------------------------------------------------------------------------
    #    Body properties
    # ------------------------------------------------------------------------

    # Property for collapsing outfit properties section
    body_config_collapse: bpy.props.BoolProperty(default=True,
                                                 name="")

    # Global body mesh properties
    # Update function for Subdivision Surface modifiers
    def update_subdiv(self, context):
        for modifier in [x for x in self.model_body.modifiers if x.type == "SUBSURF"]:
            modifier.render_levels = self.body_subdiv_rend_lv
            modifier.levels = self.body_subdiv_view_lv
            modifier.show_render = self.body_subdiv_rend
            modifier.show_viewport = self.body_subdiv_view

    # Update function for Smooth Correction modifiers
    def update_smooth_corr(self, context):
        for modifier in [x for x in self.model_body.modifiers if x.type == "CORRECTIVE_SMOOTH"]:
            modifier.show_viewport = self.body_smooth_corr
            modifier.show_render = self.body_smooth_corr

    # Update function for Auto-smooth function
    def update_norm_autosmooth(self, context):

        if bpy.app.version < (4, 1, 0):
            self.model_body.data.use_auto_smooth = self.body_norm_autosmooth
            return

        for modifier in [x for x in self.model_body.modifiers if x.type == "NODES"]:
            if modifier.node_group.name != "Smooth by Angle":
                continue
            modifier.show_viewport = self.body_norm_autosmooth
            modifier.show_render = self.body_norm_autosmooth

    # Update function for Smooth Correction modifiers
    def update_solidify(self, context):
        for modifier in [x for x in self.model_body.modifiers if x.type == "SOLIDIFY"]:
            modifier.show_viewport = self.body_solidify
            modifier.show_render = self.body_solidify

    # Subdivision surface
    body_subdiv_rend: bpy.props.BoolProperty(default=True,
                                             name="Subdivision Surface (Render)",
                                             description="Enable/disable the Subdivision Surface during rendering. "
                                                         "\nThis won't affect the viewport or the viewport rendering "
                                                         "preview. \nNote that, depending on the complexity of the "
                                                         "model, enabling this can greatly affect rendering times",
                                             update=update_subdiv)
    body_subdiv_rend_lv: bpy.props.IntProperty(default=1,
                                               min=0, max=4,
                                               name="Level",
                                               description="Set the Subdivision Surface level during rendering. "
                                                           "\nNote that, depending on the complexity of the model, "
                                                           "increasing this can greatly affect rendering times",
                                               update=update_subdiv)
    body_subdiv_view: bpy.props.BoolProperty(default=False,
                                             name="Subdivision Surface (Viewport)",
                                             description="Enable/disable the Subdivision Surface in the viewport. "
                                                         "\nSince it's really computationally expensive, "
                                                         "use this only for previews and do NOT enable it during "
                                                         "posing. \nNote that it might require a lot of time to "
                                                         "activate, and Blender will freeze during this",
                                             update=update_subdiv)
    body_subdiv_view_lv: bpy.props.IntProperty(default=0,
                                               min=0, max=4,
                                               name="Level",
                                               description="Set the Subdivision Surface level in viewport. \nNote "
                                                           "that, depending on the complexity of the model, "
                                                           "increasing this can greatly affect viewport performances. "
                                                           "Moreover, each time you change this value with "
                                                           "Subdivision Surface (Viewport) enabled, Blender will "
                                                           "freeze while applying the modification",
                                               update=update_subdiv)
    body_enable_subdiv: bpy.props.BoolProperty(default=True,
                                               name="Subdivision Surface modifiers",
                                               description="")

    # Smooth correction
    body_smooth_corr: bpy.props.BoolProperty(default=True,
                                             name="Smooth Correction",
                                             description="Enable/disable the Smooth Correction modifiers. \nDisable "
                                                         "it to increase the performance in viewport, and re-enable "
                                                         "it before rendering",
                                             update=update_smooth_corr)
    body_enable_smoothcorr: bpy.props.BoolProperty(default=False,
                                                   name="Smooth Correction modifiers",
                                                   description="")

    # Normal auto smooth
    body_norm_autosmooth: bpy.props.BoolProperty(default=True,
                                                 name="Normals Auto Smooth",
                                                 description="Enable/disable the Auto-smooth for body normals. "
                                                             "\nDisable it to increase the performance in viewport, "
                                                             "and re-enable it before rendering",
                                                 update=update_norm_autosmooth)

    body_enable_norm_autosmooth: bpy.props.BoolProperty(default=True,
                                                        name="Normals Auto Smooth property",
                                                        description="")

    # Solidify
    body_solidify: bpy.props.BoolProperty(default=True,
                                          name="Solidify",
                                          description="Enable/disable the Solidify modifiers",
                                          update=update_solidify)
    body_enable_solidify: bpy.props.BoolProperty(default=False,
                                                 name="Solidify modifiers",
                                                 description="")

    # Volume Preserve
    def update_volume_preserve(self, context):

        for modifier in [x for x in self.model_body.modifiers if x.type == "ARMATURE"]:
            modifier.use_deform_preserve_volume = self.body_preserve_volume

        collections = [x.collection for x in self.outfits_collections]
        if self.extras_collection is not None:
            collections.append(self.extras_collection)

        for collection in collections:
            items = collection.all_objects if self.outfit_config_subcollections else collection.objects
            for obj in items:
                for modifier in obj.modifiers:
                    if modifier.type == "ARMATURE":
                        modifier.use_deform_preserve_volume = self.body_preserve_volume

    # Armature volume preserve
    body_preserve_volume: bpy.props.BoolProperty(default=True,
                                                 name="Volume Preserve",
                                                 description="Enable/disable the Preserve volume.\nThis will switch "
                                                             "on/off Preserve Volume for all Armature modifiers of "
                                                             "the model (body and outfits)",
                                                 update=update_volume_preserve)

    body_enable_preserve_volume: bpy.props.BoolProperty(default=False,
                                                        name="Volume Preserve property",
                                                        description="")

    # Material normals tool
    body_enable_material_normal_nodes: bpy.props.BoolProperty(default=True,
                                                              description="Enable the Eevee Optimized Normals "
                                                                          "tool.\nThis tool substitutes normal nodes "
                                                                          "with more efficient ones, which can be "
                                                                          "useful to get better performance in Render "
                                                                          "Viewport mode",
                                                              name="Eevee Optimized Normals tool")

    # Custom properties
    body_custom_properties_icons: bpy.props.BoolProperty(default=False,
                                                         name="Show Icons",
                                                         description="Enable properties icons in the menu.\nNote: "
                                                                     "this can clash with the section icons, "
                                                                     "making the menu difficult to read")
    body_custom_properties_name_order: bpy.props.BoolProperty(default=False,
                                                              name="Order by name",
                                                              description="Order the custom properties by name "
                                                                          "instead of by appareance in the list")

    # Geometry Nodes
    def update_geometry_nodes(self, context):
        for modifier in [x for x in self.model_body.modifiers if x.type == "NODES"]:
            modifier.show_viewport = self.body_geometry_nodes
            modifier.show_render = self.body_geometry_nodes

    body_geometry_nodes: bpy.props.BoolProperty(default=False,
                                                name="Geometry Nodes",
                                                description="",
                                                update=update_geometry_nodes)

    body_enable_geometry_nodes: bpy.props.BoolProperty(default=False,
                                                       name="Geometry Nodes modifiers",
                                                       description="")

    # Geometry Nodes support
    body_enable_geometry_nodes_support: bpy.props.BoolProperty(default=False,
                                                               name="Add Geometry Nodes",
                                                               description="Add Geometry Nodes to the UI as "
                                                                           "Sections.\nThe properties displayed are "
                                                                           "the attributes of the Geometry Node")

    # List of the sections for body custom properties
    body_custom_properties_sections: bpy.props.CollectionProperty(type=MustardUI_SectionItem)

    # ------------------------------------------------------------------------
    #    Outfit properties
    # ------------------------------------------------------------------------

    # Property for collapsing outfit list section
    outfit_config_collapse: bpy.props.BoolProperty(default=True,
                                                   name="")

    # Property for collapsing outfit properties section
    outfit_config_prop_collapse: bpy.props.BoolProperty(default=True)

    # Global outfit properties
    outfits_enable_global_subsurface: bpy.props.BoolProperty(default=True,
                                                             name="Subdivision Surface modifiers",
                                                             description="This tool will enable/disable modifiers "
                                                                         "only for Viewport")

    outfits_enable_global_smoothcorrection: bpy.props.BoolProperty(default=False,
                                                                   name="Smooth Correction modifiers")

    outfits_enable_global_surfacedeform: bpy.props.BoolProperty(default=False,
                                                             name="Surface Deform modifiers")

    outfits_enable_global_shrinkwrap: bpy.props.BoolProperty(default=False,
                                                             name="Shrinkwrap modifiers")

    outfits_enable_global_mask: bpy.props.BoolProperty(default=True,
                                                       name="Mask modifiers")

    outfits_enable_global_solidify: bpy.props.BoolProperty(default=False,
                                                           name="Solidify modifiers")

    outfits_enable_global_triangulate: bpy.props.BoolProperty(default=False,
                                                              name="Triangulate modifiers")

    outfits_enable_global_normalautosmooth: bpy.props.BoolProperty(default=True,
                                                                   name="Normals Auto Smooth properties")

    # OUTFITS FUNCTIONS AND DATA

    # Function to create an array of tuples for Outfit enum collections
    def outfits_list_make(self, context):
        items = []

        for el in self.outfits_collections:
            if el.collection is None:
                continue
            if hasattr(el.collection, 'name'):
                if self.model_MustardUI_naming_convention:
                    nname = el.collection.name[len(self.model_name + ' '):]
                else:
                    nname = el.collection.name
                items.append((el.collection.name, nname, el.collection.name))

        if self.outfit_nude:
            items.insert(0, ("Nude", "Nude", "Nude"))

        return items

    def update_armature_outfit_layers(self, context, armature_settings):

        poll, arm = mustardui_active_object(context, config=0)
        bcolls = [x for x in arm.collections if x.MustardUI_ArmatureBoneCollection.outfit_switcher_enable
                  and x.MustardUI_ArmatureBoneCollection.outfit_switcher_collection is not None]

        for bcoll in bcolls:
            bcoll_settings = bcoll.MustardUI_ArmatureBoneCollection
            if bcoll_settings.outfit_switcher_object is None:
                bcoll.is_visible = (armature_settings.outfits and
                                    not bcoll_settings.outfit_switcher_collection.hide_viewport)
            else:
                items = (bcoll_settings.outfit_switcher_collection.all_objects
                         if self.outfit_config_subcollections else bcoll_settings.outfit_switcher_collection.objects)
                for obj in [x for x in items]:
                    if obj == bcoll_settings.outfit_switcher_object:
                        bcoll.is_visible = (armature_settings.outfits and
                                            not bpy.data.objects[obj.name].hide_viewport and
                                            not bcoll_settings.outfit_switcher_collection.hide_viewport)

    # Function to update the visibility of the outfits/masks/armature layers when an outfit is changed
    def outfits_visibility_update(self, context):

        poll, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings

        # Update the objects and masks visibility
        outfits_list = rig_settings.outfits_list

        for collection in [x.collection for x in rig_settings.outfits_collections if x.collection is not None]:

            items = {}
            for obj in (collection.all_objects if rig_settings.outfit_config_subcollections else collection.objects):
                items[obj.name] = obj

            locked_items = [items[x] for x in items if items[x].MustardUI_outfit_lock]

            locked_collection = len(locked_items) > 0

            collection.hide_viewport = not (collection.name == outfits_list or locked_collection)
            collection.hide_render = not (collection.name == outfits_list or locked_collection)

            for _, obj in items.items():

                if locked_collection and collection.name != outfits_list:

                    obj.hide_viewport = obj.MustardUI_outfit_visibility if obj.MustardUI_outfit_lock else not obj.MustardUI_outfit_lock
                    obj.hide_render = obj.MustardUI_outfit_visibility if obj.MustardUI_outfit_lock else not obj.MustardUI_outfit_lock

                    for modifier in obj.modifiers:
                        if modifier.type == "ARMATURE":
                            modifier.show_viewport = (
                                not obj.MustardUI_outfit_visibility if obj.MustardUI_outfit_lock else obj.MustardUI_outfit_lock) if rig_settings.outfit_switch_armature_disable else True

                elif collection.name == outfits_list:

                    obj.hide_viewport = obj.MustardUI_outfit_visibility
                    obj.hide_render = obj.MustardUI_outfit_visibility

                    for modifier in obj.modifiers:
                        if modifier.type == "ARMATURE":
                            modifier.show_viewport = (
                                not obj.MustardUI_outfit_visibility) if rig_settings.outfit_switch_armature_disable else True

                else:

                    for modifier in obj.modifiers:
                        if modifier.type == "ARMATURE":
                            modifier.show_viewport = not rig_settings.outfit_switch_armature_disable

                for modifier in rig_settings.model_body.modifiers:
                    if modifier.type == "MASK" and obj.name in modifier.name:
                        modifier.show_viewport = ((
                                                          collection.name == outfits_list or obj.MustardUI_outfit_lock) and not obj.hide_viewport and rig_settings.outfits_global_mask)
                        modifier.show_render = ((
                                                        collection.name == outfits_list or obj.MustardUI_outfit_lock) and not obj.hide_viewport and rig_settings.outfits_global_mask)

        # Update armature layers visibility, checking if some are 'Outfit' layers
        rig_settings.update_armature_outfit_layers(context, arm.MustardUI_ArmatureSettings)

        # Update custom properties with "On Switch" options
        for cp in [x for x in arm.MustardUI_CustomPropertiesOutfit if
                   x.outfit_enable_on_switch or x.outfit_disable_on_switch]:

            if cp.prop_name in arm.keys():
                ui_data = arm.id_properties_ui(cp.prop_name)
                ui_data_dict = ui_data.as_dict()

                if cp.outfit_piece:

                    outfit_piece_enable = not cp.outfit_piece.hide_viewport
                    if cp.outfit.name == outfits_list and outfit_piece_enable and cp.outfit_enable_on_switch:
                        arm[cp.prop_name] = ui_data_dict['max']
                    elif cp.outfit.name != outfits_list and cp.outfit_disable_on_switch:
                        if cp.outfit_piece.MustardUI_outfit_lock and outfit_piece_enable:
                            arm[cp.prop_name] = ui_data_dict['max']
                        else:
                            arm[cp.prop_name] = ui_data_dict['default']

                else:
                    if cp.outfit.name == outfits_list and cp.outfit_enable_on_switch:
                        arm[cp.prop_name] = ui_data_dict['max']
                    elif cp.outfit.name != outfits_list and cp.outfit_disable_on_switch:
                        arm[cp.prop_name] = ui_data_dict['default']

        if rig_settings.outfits_update_tag_on_switch:
            arm.update_tag()

    # Function to update the global outfit properties
    def outfits_global_options_subsurf_update(self, context):

        collections = [x.collection for x in self.outfits_collections]
        if self.extras_collection is not None:
            collections.append(self.extras_collection)

        for collection in collections:
            items = collection.all_objects if self.outfit_config_subcollections else collection.objects
            for obj in items:
                for modifier in obj.modifiers:
                    if modifier.type == "SUBSURF" and self.outfits_enable_global_subsurface:
                        modifier.show_viewport = self.outfits_global_subsurface

    def outfits_global_options_update(self, context):

        collections = [x.collection for x in self.outfits_collections]
        if self.extras_collection is not None:
            collections.append(self.extras_collection)

        for collection in collections:
            items = collection.all_objects if self.outfit_config_subcollections else collection.objects
            for obj in items:

                if obj.type == "MESH" and self.outfits_enable_global_normalautosmooth:
                    obj.data.use_auto_smooth = self.outfits_global_normalautosmooth

                for modifier in obj.modifiers:
                    if modifier.type == "CORRECTIVE_SMOOTH" and self.outfits_enable_global_smoothcorrection:
                        modifier.show_viewport = self.outfits_global_smoothcorrection
                        modifier.show_render = self.outfits_global_smoothcorrection
                    elif modifier.type == "MASK" and self.outfits_enable_global_mask:
                        modifier.show_viewport = self.outfits_global_mask
                        modifier.show_render = self.outfits_global_mask
                    elif modifier.type == "SHRINKWRAP" and self.outfits_enable_global_shrinkwrap:
                        modifier.show_viewport = self.outfits_global_shrinkwrap
                        modifier.show_render = self.outfits_global_shrinkwrap
                    elif modifier.type == "SURFACE_DEFORM" and self.outfits_enable_global_surfacedeform:
                        modifier.show_viewport = self.outfits_global_surfacedeform
                        modifier.show_render = self.outfits_global_surfacedeform
                    elif modifier.type == "SOLIDIFY" and self.outfits_enable_global_solidify:
                        modifier.show_viewport = self.outfits_global_solidify
                        modifier.show_render = self.outfits_global_solidify
                    elif modifier.type == "TRIANGULATE" and self.outfits_enable_global_triangulate:
                        modifier.show_viewport = self.outfits_global_triangulate
                        modifier.show_render = self.outfits_global_triangulate

                for modifier in self.model_body.modifiers:
                    if modifier.type == "MASK" and obj.name in modifier.name and self.outfits_enable_global_mask:
                        modifier.show_viewport = ((
                                                          collection.name == self.outfits_list or obj.MustardUI_outfit_lock) and not obj.hide_viewport and self.outfits_global_mask)
                        modifier.show_render = ((
                                                        collection.name == self.outfits_list or obj.MustardUI_outfit_lock) and not obj.hide_viewport and self.outfits_global_mask)

    # List of the collections from which to extract the outfits
    outfits_collections: bpy.props.CollectionProperty(name="Outfits Collection List",
                                                      type=MustardUI_Outfit)

    # Outfit properties
    outfits_list: bpy.props.EnumProperty(name="Outfits List",
                                         items=outfits_list_make,
                                         update=outfits_visibility_update)

    # Nude outfit enable
    outfit_nude: bpy.props.BoolProperty(default=True,
                                        name="Nude outfit",
                                        description="Enable Nude \'outfit\' choice.\nThis will turn on/off the Nude "
                                                    "\'outfit\' in the Outfits list, which can be useful for SFW "
                                                    "models")

    # Global outfit properties
    outfits_global_subsurface: bpy.props.BoolProperty(default=True,
                                                      name="Subdivision Surface",
                                                      description="Enable/disable subdivision surface modifiers in "
                                                                  "Viewport",
                                                      update=outfits_global_options_subsurf_update)

    outfits_global_smoothcorrection: bpy.props.BoolProperty(default=False,
                                                            name="Smooth Correction",
                                                            update=outfits_global_options_update)

    outfits_global_shrinkwrap: bpy.props.BoolProperty(default=True,
                                                      name="Shrinkwrap",
                                                      update=outfits_global_options_update)

    outfits_global_surfacedeform: bpy.props.BoolProperty(default=True,
                                                         name="Surface Deform",
                                                         update=outfits_global_options_update)

    outfits_global_mask: bpy.props.BoolProperty(default=True,
                                                name="Mask",
                                                update=outfits_global_options_update)

    outfits_global_solidify: bpy.props.BoolProperty(default=True,
                                                    name="Solidify",
                                                    update=outfits_global_options_update)

    outfits_global_triangulate: bpy.props.BoolProperty(default=True,
                                                       name="Triangulate",
                                                       update=outfits_global_options_update)

    outfits_global_normalautosmooth: bpy.props.BoolProperty(default=True,
                                                            name="Normals Auto Smooth",
                                                            update=outfits_global_options_update)

    outfit_additional_options: bpy.props.BoolProperty(default=True,
                                                      name="Custom properties",
                                                      description="Enable custom properties for outfits")
    outfit_custom_properties_icons: bpy.props.BoolProperty(default=False,
                                                           name="Show Icons",
                                                           description="Enable properties icons in the outfit menu")
    outfit_custom_properties_name_order: bpy.props.BoolProperty(default=False,
                                                                name="Order by name",
                                                                description="Order the custom properties by name "
                                                                            "instead of by appareance in the list")

    outfit_global_custom_properties_collapse: bpy.props.BoolProperty(default=False,
                                                                     name="",
                                                                     description="Show additional properties for the "
                                                                                 "selected object")

    outfit_config_subcollections: bpy.props.BoolProperty(default=False,
                                                         name="Add Objects in Sub-collections",
                                                         description="Add also Objects that are in sub-collections "
                                                                     "with respect to the main Outfit collection added")

    outfits_update_tag_on_switch: bpy.props.BoolProperty(default=True,
                                                         name="Update Drivers on Switch",
                                                         description="Update the drivers when switching Outfit "
                                                                     "parts.\nDisable this option if Blender hangs or "
                                                                     "is slow when using the Outfit piece visibility "
                                                                     "buttons in the UI")

    outfit_switch_armature_disable: bpy.props.BoolProperty(default=True,
                                                           name="Disable Armature Modifiers on Switch",
                                                           description="Disable Armature modifiers of Outfits that "
                                                                       "are not visible to increase performance")

    # Extras
    def poll_collection_extras(self, object):
        if self.hair_collection is not None:
            return not object in [x.collection for x in self.outfits_collections] and object != self.hair_collection
        return not object in [x.collection for x in self.outfits_collections]

    extras_collection: bpy.props.PointerProperty(name="Extras Collection",
                                                 type=bpy.types.Collection,
                                                 poll=poll_collection_extras)
    extras_collapse_enable: bpy.props.BoolProperty(default=False,
                                                   name="Collapsable",
                                                   description="Add a collapse button for Extras.\nExtras main icon "
                                                               "will be removed")
    extras_collapse: bpy.props.BoolProperty(default=False,
                                            name="",
                                            description="Show Extras")

    # ------------------------------------------------------------------------
    #    Hair properties
    # ------------------------------------------------------------------------

    # Property for collapsing hair properties section
    hair_config_collapse: bpy.props.BoolProperty(default=True,
                                                 name="")

    # Hair collection
    def poll_collection_hair(self, object):
        if self.extras_collection is not None:
            return not object in [x.collection for x in self.outfits_collections] and object != self.extras_collection
        return not object in [x.collection for x in self.outfits_collections]

    hair_collection: bpy.props.PointerProperty(name="Hair Collection",
                                               type=bpy.types.Collection,
                                               poll=poll_collection_hair)

    # Function to create an array of tuples for hair objects in the Hair collection
    def hair_list_make(self, context):

        items = []

        if self.hair_collection is None:
            return items

        for el in self.hair_collection.objects:
            if hasattr(el, 'name') and el.type == "MESH":
                nname = el.name[len(self.model_name + ' '):] if self.model_MustardUI_naming_convention else el.name
                items.append((el.name, nname, el.name))

        return sorted(items)

    # Function to update the requested hair
    def hair_list_update(self, context):

        poll, arm = mustardui_active_object(context, config=0)

        for obj in [x for x in self.hair_collection.objects if x.type != "CURVES"]:
            obj.hide_viewport = not self.hair_list in obj.name
            obj.hide_render = not self.hair_list in obj.name
            for mod in [x for x in obj.modifiers if x.type in ["PARTICLE_SYSTEM", "ARMATURE"]]:
                if mod.type == "PARTICLE_SYSTEM":
                    mod.show_viewport = self.hair_list in obj.name
                    mod.show_render = self.hair_list in obj.name
                else:
                    mod.show_viewport = self.hair_list in obj.name if self.hair_switch_armature_disable else True

        # Update armature layers visibility, checking if some are 'Outfit' layers
        self.update_armature_outfit_layers(context, arm.MustardUI_ArmatureSettings)

        if self.hair_update_tag_on_switch:
            for obj in self.hair_collection.objects:
                obj.update_tag()

    # Hair list
    hair_list: bpy.props.EnumProperty(name="Hair List",
                                      items=hair_list_make,
                                      update=hair_list_update)

    hair_custom_properties_icons: bpy.props.BoolProperty(default=False,
                                                         name="Show Icons",
                                                         description="Enable properties icons in the menu")
    hair_custom_properties_name_order: bpy.props.BoolProperty(default=False,
                                                              name="Order by name",
                                                              description="Order the custom properties by name "
                                                                          "instead of by appareance in the list")

    hair_switch_armature_disable: bpy.props.BoolProperty(default=True,
                                                         name="Disable Armature Modifiers on Switch",
                                                         description="Disable Armature modifiers of Hair that are not "
                                                                     "visible to increase performance")

    # Hair Global Properties
    hair_enable_global_subsurface: bpy.props.BoolProperty(default=False,
                                                          name="Subdivision Surface modifiers",
                                                          description="This tool will enable/disable modifiers only "
                                                                      "for Viewport")

    hair_enable_global_smoothcorrection: bpy.props.BoolProperty(default=False,
                                                                name="Smooth Correction modifiers")

    hair_enable_global_solidify: bpy.props.BoolProperty(default=False,
                                                        name="Solidify modifiers")

    hair_enable_global_particles: bpy.props.BoolProperty(default=False,
                                                         name="Particle Hair modifiers")

    hair_enable_global_normalautosmooth: bpy.props.BoolProperty(default=False,
                                                                name="Normals Auto Smooth properties")

    # Function to update the global hair properties
    def hair_global_options_subsurf_update(self, context):

        if self.hair_collection is not None:
            for obj in self.hair_collection.objects:
                for modifier in obj.modifiers:
                    if modifier.type == "SUBSURF" and self.hair_enable_global_subsurface:
                        modifier.show_viewport = self.hair_global_subsurface

    def hair_global_options_update(self, context):

        if self.hair_collection is not None:
            for obj in self.hair_collection.objects:
                if obj.type == "MESH" and self.hair_enable_global_normalautosmooth:
                    obj.data.use_auto_smooth = self.hair_global_normalautosmooth
                for modifier in obj.modifiers:
                    if modifier.type == "CORRECTIVE_SMOOTH" and self.hair_enable_global_smoothcorrection:
                        modifier.show_viewport = self.hair_global_smoothcorrection
                        modifier.show_render = self.hair_global_smoothcorrection
                    elif modifier.type == "SOLIDIFY" and self.hair_enable_global_solidify:
                        modifier.show_viewport = self.hair_global_solidify
                        modifier.show_render = self.hair_global_solidify
                    elif modifier.type == "PARTICLE_SYSTEM" and self.hair_enable_global_particles:
                        modifier.show_viewport = self.hair_global_particles
                        modifier.show_render = self.hair_global_particles

    hair_global_subsurface: bpy.props.BoolProperty(default=True,
                                                   name="Subdivision Surface",
                                                   description="Enable/disable subdivision surface modifiers in Viewport",
                                                   update=hair_global_options_subsurf_update)

    hair_global_smoothcorrection: bpy.props.BoolProperty(default=True,
                                                         name="Smooth Correction",
                                                         update=hair_global_options_update)

    hair_global_solidify: bpy.props.BoolProperty(default=True,
                                                 name="Solidify",
                                                 update=hair_global_options_update)

    hair_global_particles: bpy.props.BoolProperty(default=True,
                                                  name="Particle Hair",
                                                  update=hair_global_options_update)

    hair_global_normalautosmooth: bpy.props.BoolProperty(default=True,
                                                         name="Normals Auto Smooth",
                                                         update=hair_global_options_update)

    hair_update_tag_on_switch: bpy.props.BoolProperty(default=True,
                                                      name="Update Drivers on Switch",
                                                      description="Update the drivers when switching Outfit "
                                                                  "parts.\nDisable this option if Blender hangs or is "
                                                                  "slow when using the Outfit piece visibility "
                                                                  "buttons in the UI")

    # Curves Hair enable
    curves_hair_enable: bpy.props.BoolProperty(default=True,
                                               name="Curves Hair",
                                               description="Show Curves Hair in the UI.\nIf enabled, Curves Hair in "
                                                           "the hair collection are automatically be added to the UI")

    # Particle system enable
    particle_systems_enable: bpy.props.BoolProperty(default=True,
                                                    name="Particle Systems",
                                                    description="Show Particle Systems in the UI.\nIf enabled, "
                                                                "particle systems on the body mesh are automatically "
                                                                "be added to the UI")

    # ------------------------------------------------------------------------
    #    External addons
    # ------------------------------------------------------------------------

    # Property for collapsing external addons section
    external_addons_collapse: bpy.props.BoolProperty(default=True,
                                                     name="")

    # Function to update global collection properties
    def diffeomorphic_enable_update(self, context):

        if self.diffeomorphic_enable:
            bpy.ops.mustardui.dazmorphs_enabledrivers()
        else:
            self.diffeomorphic_enable_settings = False
            bpy.ops.mustardui.dazmorphs_disabledrivers()

    # Diffeomorphic support
    diffeomorphic_support: bpy.props.BoolProperty(default=False,
                                                  name="Diffeomorphic",
                                                  description="Enable Diffeomorphic support.\nIf enabled, standard "
                                                              "morphs from Diffomorphic will be added to the UI")

    diffeomorphic_enable: bpy.props.BoolProperty(default=True,
                                                 name="Enable Morphs",
                                                 description="Enabling morphs might affect performance. You can "
                                                             "disable them to increase performance",
                                                 update=diffeomorphic_enable_update)

    diffeomorphic_enable_settings: bpy.props.BoolProperty(default=False,
                                                          name="Morph Settings",
                                                          description="Show the Morph Settings panel")
    diffeomorphic_enable_shapekeys: bpy.props.BoolProperty(default=True,
                                                           name="Mute Shape Keys",
                                                           description="Shape Keys will also be muted when the Morphs "
                                                                       "are disabled")
    diffeomorphic_enable_facs: bpy.props.BoolProperty(default=True,
                                                      name="Mute Face Controls",
                                                      description="Face Controls will also be muted when the Morphs "
                                                                  "are disabled")
    diffeomorphic_enable_facs_bones: bpy.props.BoolProperty(default=True,
                                                            name="Mute Face Controls Bones",
                                                            description="Bones for Face Controls will also be muted "
                                                                        "when the Morphs are disabled.\nDisabling "
                                                                        "this option, Jaw and Eyes Face controls will "
                                                                        "work correctly, at the price of performance "
                                                                        "decrease.\nNote: if Mute Face Controls is "
                                                                        "enabled, bones will always be disabled")
    diffeomorphic_enable_pJCM: bpy.props.BoolProperty(default=True,
                                                      name="Mute Corrective Morphs",
                                                      description="Corrective Morphs will also be muted when the "
                                                                  "Morphs are disabled")
    diffeomorphic_disable_exceptions: bpy.props.StringProperty(default="",
                                                               name="Exceptions",
                                                               description="Morphs that will not be disabled when "
                                                                           "morphs are disabled.\nAdd strings to add "
                                                                           "morphs (they should map the initial part "
                                                                           "of the name of the morph), separated by "
                                                                           "commas.\nNote: spaces and order are "
                                                                           "considered")

    diffeomorphic_morphs_list: bpy.props.CollectionProperty(name="Daz Morphs List",
                                                            type=MustardUI_DazMorph)

    diffeomorphic_morphs_number: bpy.props.IntProperty(default=0,
                                                       name="")

    diffeomorphic_emotions: bpy.props.BoolProperty(default=False,
                                                   name="Emotions Morphs",
                                                   description="Search for Diffeomorphic emotions")
    diffeomorphic_emotions_collapse: bpy.props.BoolProperty(default=True)
    diffeomorphic_emotions_custom: bpy.props.StringProperty(default="",
                                                            name="Custom morphs",
                                                            description="Add strings to add custom morphs (they "
                                                                        "should map the initial part of the name of "
                                                                        "the morph), separated by commas.\nNote: "
                                                                        "spaces and order are considered")

    diffeomorphic_facs_emotions: bpy.props.BoolProperty(default=False,
                                                        name="FACS Emotions Morphs",
                                                        description="Search for Diffeomorphic FACS emotions.\nThese "
                                                                    "morphs will be shown as Advanced Emotions in the"
                                                                    " UI")
    diffeomorphic_facs_emotions_collapse: bpy.props.BoolProperty(default=True)

    diffeomorphic_emotions_units: bpy.props.BoolProperty(default=False,
                                                         name="Emotions Units Morphs",
                                                         description="Search for Diffeomorphic emotions units")
    diffeomorphic_emotions_units_collapse: bpy.props.BoolProperty(default=True)

    diffeomorphic_facs_emotions_units: bpy.props.BoolProperty(default=False,
                                                              name="FACS Emotions Units Morphs",
                                                              description="Search for Diffeomorphic FACS emotions "
                                                                          "units.\nThese morphs will be shown as "
                                                                          "Advanced Emotion Units in the UI")
    diffeomorphic_facs_emotions_units_collapse: bpy.props.BoolProperty(default=True)

    diffeomorphic_body_morphs: bpy.props.BoolProperty(default=False,
                                                      name="Body Morphs Morphs",
                                                      description="Search for Diffeomorphic Body morphs")
    diffeomorphic_body_morphs_collapse: bpy.props.BoolProperty(default=True)
    diffeomorphic_body_morphs_custom: bpy.props.StringProperty(default="",
                                                               name="Custom morphs",
                                                               description="Add strings to add custom morphs (they "
                                                                           "should map the initial part of the name "
                                                                           "of the morph), separated by "
                                                                           "commas.\nNote: spaces and order are "
                                                                           "considered")

    diffeomorphic_search: bpy.props.StringProperty(name="",
                                                   description="Search for a specific morph",
                                                   default="")
    diffeomorphic_filter_null: bpy.props.BoolProperty(default=False,
                                                      name="Filter morphs",
                                                      description="Filter used morphs.\nOnly non null morphs will be "
                                                                  "shown")

    diffeomorphic_facs_bones_rot = ['lowerJaw', 'EyelidOuter', 'EyelidInner', 'EyelidUpperInner', 'EyelidUpper',
                                    'EyelidUpperOuter',
                                    'EyelidLowerOuter', 'EyelidLower', 'EyelidLowerInner']
    diffeomorphic_facs_bones_loc = ['lowerJaw', 'NasolabialLower', 'NasolabialMouthCorner', 'LipCorner',
                                    'LipLowerOuter',
                                    'LipLowerInner', 'LipLowerMiddle', 'CheekLower', 'LipNasolabialCrease',
                                    'LipUpperMiddle', 'LipUpperOuter', 'LipUpperInner', 'LipBelow', 'NasolabialMiddle']

    # ------------------------------------------------------------------------
    #    Simplify
    # ------------------------------------------------------------------------

    def update_simplify(self, context):

        settings = context.scene.MustardUI_Settings
        poll, arm = mustardui_active_object(context, config=0)
        addon_prefs = context.preferences.addons["MustardUI"].preferences
        # if arm is not None:
        #    armature_settings = arm.MustardUI_ArmatureSettings

        # Blender Simplify
        if self.simplify_blender:
            context.scene.render.use_simplify = self.simplify_enable

        # Body
        if self.body_enable_subdiv and self.simplify_enable:
            self.body_subdiv_view = not self.simplify_enable
        if self.body_enable_smoothcorr:
            self.body_smooth_corr = not self.simplify_enable
        if self.body_enable_norm_autosmooth:
            self.body_norm_autosmooth = not self.simplify_enable
        if self.body_enable_geometry_nodes:
            self.body_geometry_nodes = not self.simplify_enable
        if self.body_enable_solidify:
            self.body_solidify = not self.simplify_enable

        # Eevee Optimized Normals
        if self.simplify_normals_optimize:
            settings.material_normal_nodes = self.simplify_enable

        # Outfits
        if len(self.outfits_list) > 1 and self.simplify_outfit_global:
            if self.simplify_subdiv and self.outfits_enable_global_subsurface and self.simplify_enable:
                self.outfits_global_subsurface = not self.simplify_enable
            if self.outfits_enable_global_mask:
                self.outfits_global_mask = not self.simplify_enable
            if self.outfits_enable_global_smoothcorrection:
                self.outfits_global_smoothcorrection = not self.simplify_enable
            if self.outfits_enable_global_shrinkwrap:
                self.outfits_global_shrinkwrap = not self.simplify_enable
            if self.outfits_enable_global_solidify:
                self.outfits_global_solidify = not self.simplify_enable
            if self.outfits_enable_global_triangulate:
                self.outfits_global_triangulate = not self.simplify_enable
            if self.simplify_normals_autosmooth and self.outfits_enable_global_normalautosmooth:
                self.outfits_global_normalautosmooth = not self.simplify_enable
        if self.outfit_nude and self.simplify_outfit_switch_nude and self.simplify_enable:
            self.outfits_list = "Nude"
        if self.extras_collection is not None and self.simplify_extras and self.simplify_enable:
            items = self.extras_collection.all_objects if self.outfit_config_subcollections else self.extras_collection.objects
            for obj in items:
                if obj.MustardUI_outfit_visibility != self.simplify_enable:
                    bpy.ops.mustardui.object_visibility(obj=obj.name)

        # Hair
        if self.hair_collection is not None:
            self.hair_collection.hide_viewport = self.simplify_enable if self.simplify_hair else False
            # armature_settings.hair = not self.simplify_enable if self.simplify_hair else True

            if self.simplify_hair_global:
                if self.simplify_subdiv and self.hair_enable_global_subsurface and self.simplify_enable:
                    self.hair_global_subsurface = not self.simplify_enable
                if self.hair_enable_global_smoothcorrection:
                    self.hair_global_smoothcorrection = not self.simplify_enable
                if self.hair_enable_global_solidify:
                    self.hair_global_solidify = not self.simplify_enable
                if self.simplify_normals_autosmooth and self.hair_enable_global_normalautosmooth:
                    self.hair_global_normalautosmooth = not self.simplify_enable

        # Particle systems
        if self.simplify_particles and self.simplify_enable:

            if self.particle_systems_enable:
                for ps in [x for x in self.model_body.modifiers if x.type == "PARTICLE_SYSTEM"]:
                    ps.show_viewport = not self.simplify_enable

            if self.hair_collection is not None:

                if self.hair_enable_global_particles:
                    self.hair_global_particles = not self.simplify_enable

                for obj in [x for x in self.hair_collection.objects]:
                    for ps in [x for x in obj.modifiers if x.type == "PARTICLE_SYSTEM"]:
                        ps.show_viewport = not self.simplify_enable

        # Armature Children
        child_all = [x for x in self.model_armature_object.children if x != self.model_body]
        child = child_all

        if self.extras_collection is not None:
            items = self.extras_collection.all_objects if self.outfit_config_subcollections else self.extras_collection.objects
            for obj in [x for x in items if x in child_all]:
                child.remove(obj)
        if self.hair_collection is not None:
            for obj in [x for x in self.hair_collection.objects if x in child_all]:
                child.remove(obj)
        for col in self.outfits_collections:
            items = col.collection.all_objects if self.outfit_config_subcollections else col.collection.objects
            for obj in [x for x in items if x in child_all]:
                child.remove(obj)

        for c in child:
            c.hide_viewport = self.simplify_enable if self.simplify_armature_child else False
            for mod in [x for x in c.modifiers if
                        x.type in ["SUBSURF", "SHRINKWRAP", "CORRECTIVE_SMOOTH", "SOLIDIFY", "PARTICLE_SYSTEM",
                                   "CLOTH"]]:
                mod.show_viewport = not self.simplify_enable if self.simplify_armature_child else True

        # Diffeomorphic morphs
        if self.diffeomorphic_support and self.simplify_diffeomorphic:
            self.diffeomorphic_enable = not self.simplify_enable

        # Physics
        if self.simplify_physics and arm is not None:
            physics_settings = arm.MustardUI_PhysicsSettings
            if len(physics_settings.physics_items) > 0:
                physics_settings.physics_enable = not self.simplify_enable

        # Force No Physics
        if self.simplify_force_no_physics and self.simplify_enable:
            for obj in [x for x in bpy.data.objects if x is not None]:
                for ps in [x for x in obj.modifiers if x.type in ["SOFT_BODY", "CLOTH", "COLLISION"]]:
                    if ps.type == "COLLISION" and obj.collision is not None:
                        obj.collision.use = not self.simplify_enable
                    else:
                        ps.show_viewport = not self.simplify_enable
                    if addon_prefs.debug:
                        print("MustardUI - Disabled " + ps.type + " modifier on: " + obj.name)

        # Force No Particles
        if self.simplify_force_no_particles and self.simplify_enable:
            for obj in [x for x in bpy.data.objects if x is not None]:
                for ps in [x for x in obj.modifiers if x.type in ["PARTICLE_SYSTEM"]]:
                    ps.show_viewport = not self.simplify_enable
                    if addon_prefs.debug:
                        print("MustardUI - Disabled " + ps.type + " modifier on: " + obj.name)

        # Update drivers
        for obju in bpy.data.objects:
            obju.update_tag()

        return

    simplify_main_enable: bpy.props.BoolProperty(default=False,
                                                 name="Simplify",
                                                 description="Enable the Simplify tool, which can be used to increase "
                                                             "Viewport performance")

    simplify_enable: bpy.props.BoolProperty(default=False,
                                            name="Simplify",
                                            description="Enable Simplify options to increase Viewport performance",
                                            update=update_simplify)

    simplify_blender: bpy.props.BoolProperty(default=False,
                                             name="Blender Simplify",
                                             description="In addition to the other options, Blender Simplify is enabled when Simplify is enabled",
                                             update=update_simplify)
    simplify_normals_optimize: bpy.props.BoolProperty(default=False,
                                                      name="Affect Eevee Normals optimization",
                                                      description="Eevee Optimized Normals is activated when Simplify is enabled, and vice-versa.\nEevee shaders re-compilation might be needed",
                                                      update=update_simplify)
    simplify_subdiv: bpy.props.BoolProperty(default=True,
                                            name="Affect Subdivision (Viewport)",
                                            description="Subdivision Surface modifiers are disabled when Simplify is enabled.\nThis works only when enabling Simplify, and the status will not be reverted when Simplify is disabled again",
                                            update=update_simplify)
    simplify_normals_autosmooth: bpy.props.BoolProperty(default=True,
                                                        name="Affect Normals Auto-Smooth",
                                                        update=update_simplify)

    simplify_outfit_switch_nude: bpy.props.BoolProperty(default=False,
                                                        name="Switch to Nude",
                                                        update=update_simplify)
    simplify_outfit_global: bpy.props.BoolProperty(default=True,
                                                   name="Disable Outfit Global properties",
                                                   update=update_simplify)
    simplify_extras: bpy.props.BoolProperty(default=True,
                                            name="Hide Extras",
                                            update=update_simplify)
    simplify_hair: bpy.props.BoolProperty(default=True,
                                          name="Hide Hair (Viewport)",
                                          update=update_simplify)
    simplify_particles: bpy.props.BoolProperty(default=True,
                                               name="Disable Particles",
                                               description="Disable Particle Systems modifiers.\nThis works only when enabling Simplify, and the status will not be reverted when Simplify is disabled again",
                                               update=update_simplify)
    simplify_hair_global: bpy.props.BoolProperty(default=True,
                                                 name="Disable Hair Global properties",
                                                 update=update_simplify)
    simplify_armature_child: bpy.props.BoolProperty(default=True,
                                                    name="Hide Armature Children (Viewport)",
                                                    description="Disables all objects parented to the Armature, except the Body",
                                                    update=update_simplify)
    simplify_diffeomorphic: bpy.props.BoolProperty(default=True,
                                                   name="Disable Morphs",
                                                   update=update_simplify)
    simplify_physics: bpy.props.BoolProperty(default=False,
                                             name="Disable Physics",
                                             update=update_simplify)

    simplify_force_no_physics: bpy.props.BoolProperty(default=False,
                                                      name="Disable Physics",
                                                      description="Force the disabling of all physics modifiers on all scene Objects.\nThis works only when enabling Simplify, and the status will not be reverted when Simplify is disabled again",
                                                      update=update_simplify)
    simplify_force_no_particles: bpy.props.BoolProperty(default=False,
                                                        name="Disable Particle Systems",
                                                        description="Force the disabling of all particle system modifiers on all scene Objects.\nThis works only when enabling Simplify, and the status will not be reverted when Simplify is disabled again",
                                                        update=update_simplify)

    # ------------------------------------------------------------------------
    #    Various properties
    # ------------------------------------------------------------------------

    # Property for collapsing other properties section
    various_config_collapse: bpy.props.BoolProperty(default=True,
                                                    name="")

    # Version of the model
    model_version: bpy.props.StringProperty(name="Model version",
                                            description="Version of the model",
                                            default="")

    # Object and Collection MustardUI naming convention
    model_MustardUI_naming_convention: bpy.props.BoolProperty(default=True,
                                                              name="MustardUI Naming Convention",
                                                              description="Use the MustardUI naming convention for collections and objects.\nIf this is true, the collections and the objects listed as outfits will be stripped of unnecessary parts in the name")

    model_rig_type: bpy.props.EnumProperty(default="other",
                                           items=[("arp", "Auto-Rig Pro", "Auto-Rig Pro"),
                                                  ("rigify", "Rigify", "Rigify"), ("mhx", "MHX", "MHX"),
                                                  ("other", "Other", "Other")],
                                           name="Rig type")

    model_cleaned: bpy.props.BoolProperty(default=False)

    # Links
    # Property for collapsing links properties section
    url_config_collapse: bpy.props.BoolProperty(default=True,
                                                name="")

    # Enable link section
    links_enable: bpy.props.BoolProperty(default=True,
                                         name="Show Links")

    # Debug
    # Property for collapsing debug properties section
    debug_config_collapse: bpy.props.BoolProperty(default=True,
                                                  name="")

    # END OF MustardUI_RigSettings class


def register():
    bpy.utils.register_class(MustardUI_RigSettings)
    bpy.types.Armature.MustardUI_RigSettings = bpy.props.PointerProperty(type=MustardUI_RigSettings)

    # Redefinition for lock functionality
    bpy.types.Object.MustardUI_outfit_lock = bpy.props.BoolProperty(default=False,
                                                                    name="",
                                                                    description="Lock/unlock the outfit",
                                                                    update=MustardUI_RigSettings.outfits_visibility_update)


def unregister():
    bpy.utils.unregister_class(MustardUI_RigSettings)
