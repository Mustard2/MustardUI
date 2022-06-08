# MustardUI addon
# GitHub page: https://github.com/Mustard2/MustardUI

# Add-on informations
bl_info = {
    "name": "MustardUI",
    "description": "Create a MustardUI for a human character.",
    "author": "Mustard",
    "version": (0, 23, 0),
    "blender": (3, 2, 0),
    "warning": "",
    "doc_url": "https://github.com/Mustard2/MustardUI",
    "category": "User Interface",
}
mustardui_buildnum = "007"

import bpy
import addon_utils
import sys
import os
import re
import time
import math
import random
import platform
import itertools
from bpy.types import Header, Menu, Panel
from bpy.props import *
from bpy.app.handlers import persistent
from rna_prop_ui import rna_idprop_ui_create
from mathutils import Vector, Color, Matrix
import webbrowser

# ------------------------------------------------------------------------
#    Global icon list
# ------------------------------------------------------------------------

mustardui_icon_list = [
                ("NONE","No Icon","No Icon"),
                ("USER", "Face", "Face","USER",1),
                ("HIDE_OFF", "Eye", "Eye","HIDE_OFF",2),
                ("HAIR", "Hair", "Hair","STRANDS",3),
                ("MOD_CLOTH", "Cloth", "Cloth","MOD_CLOTH",4),
                ("MATERIAL", "Material", "Material","MATERIAL",5),
                ("ARMATURE_DATA", "Armature", "Armature","ARMATURE_DATA",6),
                ("MOD_ARMATURE", "Armature", "Armature","MOD_ARMATURE",7),
                ("EXPERIMENTAL", "Experimental", "Experimental","EXPERIMENTAL",8),
                ("PHYSICS", "Physics", "Physics","PHYSICS",9),
                ("WORLD", "World", "World","WORLD",10),
                ("PARTICLEMODE", "Comb", "Comb","PARTICLEMODE",11),
                ("OUTLINER_OB_POINTCLOUD", "Points", "Points","OUTLINER_OB_POINTCLOUD",12),
                ("MOD_DYNAMICPAINT", "Foot", "Foot","MOD_DYNAMICPAINT",13),
                ("OUTLINER_DATA_VOLUME", "Cloud", "Cloud","OUTLINER_DATA_VOLUME",14),
                ("SHAPEKEY_DATA", "Shape Key", "Shape Key","SHAPEKEY_DATA",15),
                ("FUND", "Hearth", "Hearth","FUND",16),
                ("MATSHADERBALL", "Ball", "Ball","MATSHADERBALL",17),
                ("COMMUNITY", "Community", "Community","COMMUNITY",18),
                ("LIGHT", "Light", "Light","LIGHT",19)
            ]

# ------------------------------------------------------------------------
#    Active object function
# ------------------------------------------------------------------------

# Function to decide the active object for showing properties in the UI
def mustardui_active_object(context, config = 0):
    
    settings = bpy.context.scene.MustardUI_Settings
    
    # If Viewport Model Selection is enabled, the active object will be the active object
    # only if it is an armature
    if settings.viewport_model_selection:
    
        if context.active_object == None:
            return False, None
        
        obj = context.active_object
            
        if obj.type == "ARMATURE":

            if config:
                return not obj.data.MustardUI_enable, obj.data
            else:
                return obj.data.MustardUI_enable, obj.data
        
        # The lattice case should be considered in order for the Lattice tool to work
        # In fact, it is needed for the LatticeSetting operator
        elif obj.type == "LATTICE":
            
            for armature in bpy.data.armatures:
                if obj == armature.MustardUI_LatticeSettings.lattice_object:
                    if config:
                        return False, None
                    else:
                        return armature.MustardUI_enable, armature
            
            return False, None
        
        return False, None
    
    # If Viewport Model Selection is false, use the UI with the armature selected in the model panel
    else:
        if config:
            return not settings.panel_model_selection_armature.MustardUI_enable, settings.panel_model_selection_armature
        else:
            return settings.panel_model_selection_armature.MustardUI_enable, settings.panel_model_selection_armature
        

# ------------------------------------------------------------------------
#    Classes and definitions
# ------------------------------------------------------------------------

# Class with all general settings variables
class MustardUI_Settings(bpy.types.PropertyGroup):
    
    # Model selection
    viewport_model_selection: bpy.props.BoolProperty(default = True,
                        name = "Viewport model selection",
                        description = "Enable viewport model selection.\nIf disabled, a model selection panel will appear instead, where a model can be selected")
    viewport_model_selection_after_configuration: bpy.props.BoolProperty(default = False,
                        name = "Viewport model selection",
                        description = "Enable viewport model selection after the end of the configuration.\nIt is advised to leave this off if only one character with MustardUI is available on the scene")
    
    panel_model_selection_armature: bpy.props.PointerProperty(type = bpy.types.Armature)
    
    # Main Settings definitions
    # Version of the MustardUI
    version: bpy.props.StringProperty(default = "0.0.1",
                        name = "MustardUI version",
                        description = "Version of MustardUI add-on")
    
    # Settings changed by the creator
    # Advanced settings
    advanced: bpy.props.BoolProperty(default = False,
                        name = "Advanced Options",
                        description = "Unlock Advanced Options.\nMore advanced options will be shown in the UI")
    # Debug mode
    debug: bpy.props.BoolProperty(default = False,
                        name = "Debug Mode",
                        description = "Unlock Debug Mode.\nMore messaged will be generated in the console.\nEnable it only if you encounter problems, as it might degrade general Blender performance")
    
    # Maintenance tools
    maintenance: bpy.props.BoolProperty(default = False,
                        name="Maintenance Tools",
                        description="Enable Maintenance Tools.\nVarious maintenance tools will be added to the UI and in the Settings panel")
    
    # RIG TOOLS STATUS
    
    # This function checks that the rig_tools addon is installed and enabled.
    def addon_check(addon_names):
        
        addon_utils.modules_refresh()
        
        addon_num = len(addon_names)
        
        addon_status = []
        addon_names_found = []
        
        for i in range(addon_num):
            for addon in addon_utils.addons_fake_modules:
                if addon_names[i] in addon:
                    addon_names_found.append(addon)
                    default, state = addon_utils.check(addon)
                    addon_status.append(2 if default else 1)
        
        if 2 in addon_status:
            for i in range(len(addon_names_found)):
                if addon_status[i] == 2:
                    print("MustardUI - " + addon_names_found[i] + " add-on enabled and running.")
                    return 2
        elif 1 in addon_status and not 2 in addon_status:
            for addon_name in addon_names_found:
                print("MustardUI - " + addon_name + " add-on installed but not enabled.")
            return 1
        else:
            for addon_name in addon_names:
                print("MustardUI - %s add-on not installed." % addon_name)
        
        return 0
    
    # Rig-tools addon status definition
    status_rig_tools: bpy.props.IntProperty(default = addon_check(["auto_rig_pro-master", "rig_tools"]),
                        name = "rig_tools addon status")
    
    # Rig-tools addon status definition
    status_diffeomorphic: bpy.props.IntProperty(default = addon_check(["import_daz"]),
                        name = "diffeomorphic addon status")
    
    # Rig-tools addon status definition
    status_mhx: bpy.props.IntProperty(default = addon_check(["mhx_rts"]),
                        name = "mhx_rts addon status")
    
    def addon_version_check(addon_name):
        try:
            # Find the correct addon name
            addon_utils.modules_refresh()
            
            for addon in addon_utils.addons_fake_modules:
                if addon_name in addon:
                    default, state = addon_utils.check(addon)
                    if state:
                        break
            
            mod = sys.modules[addon]
            version = mod.bl_info.get('version', (-1, -1, -1))
            print("MustardUI - " + addon + " version is " + str(version[0]) + "." + str(version[1]) + "." + str(version[2]) + ".")
            return version
        except:
            print("MustardUI - Can not find " + addon_name + " version.")
            return (-1, -1, -1)
    
    status_diffeomorphic_version: bpy.props.IntVectorProperty(default = addon_version_check("import_daz"))
    
    # Property for custom properties errors
    custom_properties_error: bpy.props.BoolProperty(name = "",
                        description = "Can not find the property.\nCheck the property or use the Re-build Custom Properties operator in Settings")
    custom_properties_error_nonanimatable: bpy.props.BoolProperty(name = "",
                        description = "Can not find the property.\nRemove the property in the Configuration panel and add it again")
    
    # Property for morphs errors
    daz_morphs_error: bpy.props.BoolProperty(name = "",
                        description = "Can not find the Daz Morph.\nRe-run the Check Morphs operator in the Configuration menu to solve this")
    
    # Material normals mute
    def update_material_normal(self, context):
        
        bpy.ops.mustardui.material_normalmap_nodes(custom = not self.material_normal_nodes)
        
        return
    
    material_normal_nodes: bpy.props.BoolProperty(default = True,
                        name = "Material Normals",
                        description = "Enable the Material Normals tool.\nThis tool substitute normal nodes with more efficient ones, which can be useful to get better performance in shadow preview viewport mode",
                        update = update_material_normal)

# Register and create the setting class in the Scene object
bpy.utils.register_class(MustardUI_Settings)
bpy.types.Scene.MustardUI_Settings = bpy.props.PointerProperty(type = MustardUI_Settings)

# Properties to specify if the Armature has a MustardUI currently in use
bpy.types.Armature.MustardUI_enable = bpy.props.BoolProperty(default = False,
                    name = "")

# Properties to specify if the Armature has a MustardUI created
bpy.types.Armature.MustardUI_created = bpy.props.BoolProperty(default = False,
                    name = "")


# Outfit informations
# Class to store outfit informations
class MustardUI_Outfit(bpy.types.PropertyGroup):
    # Collection storing the outfit pieces
    collection: bpy.props.PointerProperty(name = "Outfit Collection",
                        type = bpy.types.Collection)

bpy.utils.register_class(MustardUI_Outfit)


# Properties and functions specific to objects
bpy.types.Object.MustardUI_additional_options_show = bpy.props.BoolProperty(default = False,
                    name = "",
                    description = "Show additional properties for the selected object")
bpy.types.Object.MustardUI_additional_options_show_lock = bpy.props.BoolProperty(default = False,
                    name = "",
                    description = "Show additional properties for the selected object")
bpy.types.Object.MustardUI_outfit_visibility = bpy.props.BoolProperty(default = False,
                    name = "",
                    description = "")
bpy.types.Object.MustardUI_outfit_lock = bpy.props.BoolProperty(default = False,
                    name = "",
                    description = "Lock/unlock the outfit")

# Daz Morphs informations
# Class to store morphs informations
class MustardUI_DazMorph(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name = "Name")
    path: bpy.props.StringProperty(name = "Path")
    # 0: Emotion Units, 1: Emotions, 2: FACS Emotion Units, 3: FACS Emotions, 4: Body Morphs
    type: bpy.props.IntProperty(name = "Type")

bpy.utils.register_class(MustardUI_DazMorph)

# ------------------------------------------------------------------------
#    Sections
# ------------------------------------------------------------------------

# Section for body properties
class MustardUI_SectionItem(bpy.types.PropertyGroup):
    
    # Name of the section
    name: bpy.props.StringProperty(name = "Section name")
    
    # Section ID
    id: bpy.props.IntProperty(name = "Section ID")
    
    # Section icon
    icon : bpy.props.StringProperty(name="Section Icon",
                        default="")
    
    # Advanced settings
    advanced: bpy.props.BoolProperty(default = False,
                        name = "Advanced",
                        description = "The section will be shown only when Advances Settings is enabled")
    
    # Collapsable
    collapsable: bpy.props.BoolProperty(default = False,
                        name = "Collapsable",
                        description = "Add a collapse icon to the section.\nNote that this might give bad UI results if combined with an icon")
    collapsed: bpy.props.BoolProperty(name = "",
                        default = False)

bpy.utils.register_class(MustardUI_SectionItem)

# Main class to store model settings
class MustardUI_RigSettings(bpy.types.PropertyGroup):
    
    # ------------------------------------------------------------------------
    #    General model properties
    # ------------------------------------------------------------------------
    
    # Model name
    model_name: bpy.props.StringProperty(default = "",
                        name = "Model name",
                        description = "Model name")
    
    # Body object
    # Poll function for the selection of mesh only in pointer properties
    def poll_mesh(self, object):
        return object.type == 'MESH'
    
    model_body: bpy.props.PointerProperty(name = "Model Body",
                        description = "Select the mesh that will be considered the body",
                        type = bpy.types.Object,
                        poll = poll_mesh)
    
    # Armature object
    # Poll function for the selection of armatures for the armature object
    def poll_armature(self, object):
        
        if object.type == 'ARMATURE':
            return object.data == self.id_data
        else:
            return False
    
    model_armature_object: bpy.props.PointerProperty(name = "Model Armature Object",
                        description = "Mesh that will be considered the body.\nSet or change this Object if you know what you are doing",
                        type = bpy.types.Object,
                        poll = poll_armature)
    
    # ------------------------------------------------------------------------
    #    Body properties
    # ------------------------------------------------------------------------
    
    # Property for collapsing outfit properties section
    body_config_collapse: bpy.props.BoolProperty(default = True,
                        name = "")
    
    # Global body mesh properties
    # Update function for Subdivision Surface modifiers
    def update_subdiv(self, context):
    
        for modifier in self.model_body.modifiers:
            if modifier.type == "SUBSURF":
                modifier.render_levels = self.body_subdiv_rend_lv
                modifier.levels = self.body_subdiv_view_lv
                modifier.show_render = self.body_subdiv_rend
                modifier.show_viewport = self.body_subdiv_view
        return
    
    # Update function for Smooth Correction modifiers
    def update_smooth_corr(self, context):
        
        for modifier in self.model_body.modifiers:
            if modifier.type == "CORRECTIVE_SMOOTH":
                modifier.show_viewport = self.body_smooth_corr
                modifier.show_render = self.body_smooth_corr
        
        return
    
    # Update function for Auto-smooth function
    def update_norm_autosmooth(self, context):
        
        self.model_body.data.use_auto_smooth = self.body_norm_autosmooth
        
        return
    
    # Subdivision surface
    body_subdiv_rend: bpy.props.BoolProperty(default = True,
                        name = "Subdivision Surface (Render)",
                        description = "Enable/disable the subdivision surface during rendering. \nThis won't affect the viewport or the viewport rendering preview. \nNote that, depending on the complexity of the model, enabling this can greatly affect rendering times",
                        update = update_subdiv)
    body_subdiv_rend_lv: bpy.props.IntProperty(default = 1,
                        min = 0,max = 4,
                        name = "Level",
                        description = "Set the subdivision surface level during rendering. \nNote that, depending on the complexity of the model, increasing this can greatly affect rendering times",
                        update = update_subdiv)
    body_subdiv_view: bpy.props.BoolProperty(default = False,
                        name = "Subdivision Surface (Viewport)",
                        description = "Enable/disable the subdivision surface in the viewport. \nSince it's really computationally expensive, use this only for previews and do NOT enable it during posing. \nNote that it might require a lot of time to activate, and Blender will freeze during this",
                        update = update_subdiv)
    body_subdiv_view_lv: bpy.props.IntProperty(default = 0,
                        min = 0,max = 4,
                        name = "Level",
                        description = "Set the subdivision surface level in viewport. \nNote that, depending on the complexity of the model, increasing this can greatly affect viewport performances. Moreover, each time you change this value with Subdivision Surface (Viewport) enabled, Blender will freeze while applying the modification",
                        update = update_subdiv)
    body_enable_subdiv: bpy.props.BoolProperty(default = True,
                        name = "Subdivision Surface modifiers",
                        description = "")
    
    # Smooth correction
    body_smooth_corr: bpy.props.BoolProperty(default = True,
                        name = "Smooth Correction",
                        description = "Enable/disable the smooth correction. \nDisable it to increase the performance in viewport, and re-enable it before rendering",
                        update = update_smooth_corr)
    body_enable_smoothcorr: bpy.props.BoolProperty(default = True,
                        name = "Smooth Correction modifiers",
                        description = "")
    
    # Normal auto smooth
    body_norm_autosmooth: bpy.props.BoolProperty(default = True,
                        name = "Normals Auto Smooth",
                        description = "Enable/disable the auto-smooth for body normals. \nDisable it to increase the performance in viewport, and re-enable it before rendering",
                        update = update_norm_autosmooth)
    
    body_enable_norm_autosmooth: bpy.props.BoolProperty(default = True,
                        name = "Normals Auto Smooth property",
                        description = "")
    
    def update_volume_preserve(self, context):
        
        for modifier in self.model_body.modifiers:
            if modifier.type == "ARMATURE":
                modifier.use_deform_preserve_volume = self.body_preserve_volume
        
        collections = [x.collection for x in self.outfits_collections]
        if self.extras_collection != None:
            collections.append(self.extras_collection)
        
        for collection in collections:
            for obj in collection.objects:
                for modifier in obj.modifiers:
                    if modifier.type == "ARMATURE":
                        modifier.use_deform_preserve_volume = self.body_preserve_volume
            
        return
    
    # Armature volume preserve
    body_preserve_volume: bpy.props.BoolProperty(default = True,
                        name = "Volume Preserve",
                        description = "Enable/disable the Preserve volume.\nThis will switch on/off Preserve Volume for all Armature modifiers of the model (body and outfits)",
                        update = update_volume_preserve)
    
    body_enable_preserve_volume: bpy.props.BoolProperty(default = False,
                        name = "Volume Preserve property",
                        description = "")
    
    # Material normals tool
    body_enable_material_normal_nodes: bpy.props.BoolProperty(default = True,
                        description = "Enable the Material Normals tool.\nThis tool substitute normal nodes with more efficient ones, which can be useful to get better performance in shadow preview viewport mode",
                        name = "Material Normals tool")
    
    # Custom properties
    body_custom_properties_icons: bpy.props.BoolProperty(default = False,
                        name = "Show Icons",
                        description = "Enable properties icons in the menu.\nNote: this can clash with the section icons, making the menu difficult to read")
    body_custom_properties_name_order: bpy.props.BoolProperty(default = False,
                        name = "Order by name",
                        description = "Order the custom properties by name instead of by appareance in the list")
    
    # List of the sections for body custom properties
    body_custom_properties_sections: bpy.props.CollectionProperty(type = MustardUI_SectionItem)
    
    # ------------------------------------------------------------------------
    #    Outfit properties
    # ------------------------------------------------------------------------
    
    # Property for collapsing outfit list section
    outfit_config_collapse: bpy.props.BoolProperty(default = True,
                        name = "")
    
    # Property for collapsing outfit properties section
    outfit_config_prop_collapse: bpy.props.BoolProperty(default = True)
    
    # Global outfit properties
    outfits_enable_global_subsurface: bpy.props.BoolProperty(default = True,
                        name = "Subdivision Surface modifiers",
                        description = "This tool will enable/disable modifiers only for Viewport")
    
    outfits_enable_global_smoothcorrection: bpy.props.BoolProperty(default = True,
                        name = "Smooth Correction modifiers")
    
    outfits_enable_global_shrinkwrap: bpy.props.BoolProperty(default = True,
                        name = "Shrinkwrap modifiers")
    
    outfits_enable_global_mask: bpy.props.BoolProperty(default = True,
                        name = "Mask modifiers")
    
    outfits_enable_global_solidify: bpy.props.BoolProperty(default = False,
                        name = "Solidify modifiers")
    
    outfits_enable_global_triangulate: bpy.props.BoolProperty(default = False,
                        name = "Triangulate modifiers")
    
    outfits_enable_global_normalautosmooth: bpy.props.BoolProperty(default = True,
                        name = "Normals Auto Smooth properties")
    
    # OUTFITS FUNCTIONS AND DATA
        
    # Function to create an array of tuples for Outfit enum collections
    def outfits_list_make(self, context):
        
        items = []
        
        for el in self.outfits_collections:
            
            if el.collection == None:
                continue
            
            if hasattr(el.collection, 'name'):
                if self.model_MustardUI_naming_convention:
                    nname = el.collection.name[len(self.model_name + ' '):]
                else:
                    nname = el.collection.name
                items.append( (el.collection.name,nname,el.collection.name) )
        
        items = sorted(items)
        
        if self.outfit_nude:
            items.insert( 0, ("Nude", "Nude", "Nude") )
        
        return items

    # Function to update the visibility of the outfits/masks/armature layers when an outfit is changed
    def outfits_visibility_update(self, context):
        
        poll, obj = mustardui_active_object(context, config = 0)
        armature_settings = obj.MustardUI_ArmatureSettings
        
        outfits_list = self.outfits_list
        
        collections = [x.collection for x in self.outfits_collections if x.collection != None]
        
        # Update the objects and masks visibility
        for collection in collections:
            
            locked_collection = len([x for x in collection.objects if x.MustardUI_outfit_lock])>0
            
            collection.hide_viewport = not (collection.name == outfits_list or locked_collection)
            collection.hide_render = not (collection.name == outfits_list or locked_collection)
            
            for obj in collection.objects:
                    
                if locked_collection and collection.name != outfits_list:
                    
                    obj.hide_viewport = obj.MustardUI_outfit_visibility if obj.MustardUI_outfit_lock else not obj.MustardUI_outfit_lock
                    obj.hide_render = obj.MustardUI_outfit_visibility if obj.MustardUI_outfit_lock else not obj.MustardUI_outfit_lock
                
                elif collection.name == outfits_list:
                    
                    obj.hide_viewport = obj.MustardUI_outfit_visibility
                    obj.hide_render = obj.MustardUI_outfit_visibility
            
                for modifier in self.model_body.modifiers:
                    if modifier.type == "MASK" and obj.name in modifier.name:
                        modifier.show_viewport = ( (collection.name == outfits_list or obj.MustardUI_outfit_lock) and not obj.hide_viewport and self.outfits_global_mask)
                        modifier.show_render = ( (collection.name == outfits_list or obj.MustardUI_outfit_lock) and not obj.hide_viewport and self.outfits_global_mask)

        if len(armature_settings.layers)>0:
            outfit_armature_layers = [x for x in range(0,32) if armature_settings.layers[x].outfit_switcher_enable and armature_settings.layers[x].outfit_switcher_collection != None]
        
            # Update armature layers visibility, checking if some are 'Outfit' layers
            for i in outfit_armature_layers:
                if armature_settings.layers[i].outfit_switcher_object == None:
                    armature_settings.layers[i].show = not armature_settings.layers[i].outfit_switcher_collection.hide_viewport
                else:
                    for object in [x for x in armature_settings.layers[i].outfit_switcher_collection.objects]:
                        if object == armature_settings.layers[i].outfit_switcher_object:
                            armature_settings.layers[i].show = not bpy.data.objects[object.name].hide_viewport and not armature_settings.layers[i].outfit_switcher_collection.hide_viewport

    # Function to update the global outfit properties
    def outfits_global_options_update(self, context):
        
        collections = [x.collection for x in self.outfits_collections]
        if self.extras_collection != None:
            collections.append(self.extras_collection)
        
        for collection in collections:
            for obj in collection.objects:
                
                if obj.type == "MESH":
                    obj.data.use_auto_smooth = self.outfits_global_normalautosmooth
                
                for modifier in obj.modifiers:
                    if modifier.type == "SUBSURF":
                        modifier.show_viewport = self.outfits_global_subsurface
                    elif modifier.type == "CORRECTIVE_SMOOTH":
                        modifier.show_viewport = self.outfits_global_smoothcorrection
                        modifier.show_render = self.outfits_global_smoothcorrection
                    elif modifier.type == "MASK":
                        modifier.show_viewport = self.outfits_global_mask
                        modifier.show_render = self.outfits_global_mask
                    elif modifier.type == "SHRINKWRAP":
                        modifier.show_viewport = self.outfits_global_shrinkwrap
                        modifier.show_render = self.outfits_global_shrinkwrap
                    elif modifier.type == "SOLIDIFY":
                        modifier.show_viewport = self.outfits_global_solidify
                        modifier.show_render = self.outfits_global_solidify
                    elif modifier.type == "TRIANGULATE":
                        modifier.show_viewport = self.outfits_global_triangulate
                        modifier.show_render = self.outfits_global_triangulate
        
                for modifier in self.model_body.modifiers:
                    if modifier.type == "MASK" and obj.name in modifier.name:
                        modifier.show_viewport = ( (collection.name == self.outfits_list or obj.MustardUI_outfit_lock) and not obj.hide_viewport and self.outfits_global_mask)
                        modifier.show_render = ( (collection.name == self.outfits_list or obj.MustardUI_outfit_lock) and not obj.hide_viewport and self.outfits_global_mask)
            
        return

    # List of the collections from which to extract the outfits
    outfits_collections: bpy.props.CollectionProperty(name = "Outfits Collection List",
                        type=MustardUI_Outfit)
    
    # Outfit properties
    outfits_list: bpy.props.EnumProperty(name = "Outfits List",
                        items = outfits_list_make,
                        update = outfits_visibility_update)
    
    # Nude outfit enable
    outfit_nude: bpy.props.BoolProperty(default = True,
                        name = "Nude outfit",
                        description = "Enable Nude \'outfit\' choice.\nThis will turn on/off the Nude \'outfit\' in the Outfits list, which can be useful for SFW models")
    
    # Global outfit properties
    outfits_global_subsurface: bpy.props.BoolProperty(default = True,
                        name = "Subdivision Surface",
                        description = "Enable/disable subdivision surface modifiers in Viewport",
                        update = outfits_global_options_update)
    
    outfits_global_smoothcorrection: bpy.props.BoolProperty(default = True,
                        name = "Smooth Correction",
                        update = outfits_global_options_update)
    
    outfits_global_shrinkwrap: bpy.props.BoolProperty(default = True,
                        name = "Shrinkwrap",
                        update = outfits_global_options_update)
                        
    outfits_global_mask: bpy.props.BoolProperty(default = True,
                        name = "Mask",
                        update = outfits_global_options_update)
    
    outfits_global_solidify: bpy.props.BoolProperty(default = True,
                        name = "Solidify",
                        update = outfits_global_options_update)
    
    outfits_global_triangulate: bpy.props.BoolProperty(default = True,
                        name = "Triangulate",
                        update = outfits_global_options_update)
                        
    outfits_global_normalautosmooth: bpy.props.BoolProperty(default = True,
                        name = "Normals Auto Smooth",
                        update = outfits_global_options_update)
    
    outfit_additional_options: bpy.props.BoolProperty(default = True,
                        name = "Custom properties",
                        description = "Enable custom properties for outfits")
    outfit_custom_properties_icons: bpy.props.BoolProperty(default = False,
                        name = "Show Icons",
                        description = "Enable properties icons in the outfit menu")
    outfit_custom_properties_name_order: bpy.props.BoolProperty(default = False,
                        name = "Order by name",
                        description = "Order the custom properties by name instead of by appareance in the list")
    
    outfit_global_custom_properties_collapse: bpy.props.BoolProperty(default = False,
                        name = "",
                        description = "Show additional properties for the selected object")
    
    # Extras
    extras_collection: bpy.props.PointerProperty(name = "Extras Collection",
                        type = bpy.types.Collection)
    extras_collapse_enable: bpy.props.BoolProperty(default = False,
                        name = "Collapsable",
                        description = "Add a collapse button for Extras.\nExtras main icon will be removed")
    extras_collapse: bpy.props.BoolProperty(default = False,
                        name = "",
                        description = "Show Extras")

    # ------------------------------------------------------------------------
    #    Hair properties
    # ------------------------------------------------------------------------
    
    # Property for collapsing hair properties section
    hair_config_collapse: bpy.props.BoolProperty(default = True,
                        name = "")
    
    # Hair collection
    hair_collection : bpy.props.PointerProperty(name="Hair Collection",
                        type=bpy.types.Collection)
    
    # Function to create an array of tuples for hair objects in the Hair collection
    def hair_list_make(self, context):
        
        items = []
        
        for el in self.hair_collection.objects:
            if hasattr(el, 'name') and el.type == "MESH":
                items.append( (el.name,el.name,el.name) )
            
        return sorted(items)
    
    # Function to update global collection properties
    def hair_list_update(self, context):
        
        for object in self.hair_collection.objects:
            object.hide_viewport = not self.hair_list in object.name
            object.hide_render = not self.hair_list in object.name
        
        return
    
    # Hair list
    hair_list: bpy.props.EnumProperty(name = "Hair List",
                        items = hair_list_make,
                        update = hair_list_update)
    
    hair_custom_properties_icons: bpy.props.BoolProperty(default = False,
                        name = "Show Icons",
                        description = "Enable properties icons in the menu")
    hair_custom_properties_name_order: bpy.props.BoolProperty(default = False,
                        name = "Order by name",
                        description = "Order the custom properties by name instead of by appareance in the list")
    
    # Particle system enable
    particle_systems_enable: bpy.props.BoolProperty(default = True,
                        name = "Particle Systems",
                        description = "Show Particle Systems in the UI.\nIf enabled, particle systems on the body mesh will automatically be added to the UI")
    
    # ------------------------------------------------------------------------
    #    External addons
    # ------------------------------------------------------------------------
    
    # Property for collapsing external addons section
    external_addons_collapse: bpy.props.BoolProperty(default = True,
                        name = "")
    
    # Function to update global collection properties
    def diffeomorphic_enable_update(self, context):
        
        if self.diffeomorphic_enable:
            bpy.ops.mustardui.dazmorphs_enabledrivers()
        else:
            bpy.ops.mustardui.dazmorphs_disabledrivers()
        
        return
    
    # Diffeomorphic support
    diffeomorphic_support: bpy.props.BoolProperty(default = False,
                        name = "Diffeomorphic",
                        description = "Enable Diffeomorphic support.\nIf enabled, standard morphs from Diffomorphic will be added to the UI")
    
    diffeomorphic_enable: bpy.props.BoolProperty(default = True,
                        name = "Enable Morphs",
                        description = "Select the model armature to enable this button.\nEnabling morphs might affect performance. You can disable them to increase performance",
                        update = diffeomorphic_enable_update)
    
    diffeomorphic_model_version: bpy.props.EnumProperty(default = "1.5",
                        items = [("1.6", "1.6", "1.6"), ("1.5", "1.5", "1.5")],
                        name = "Diffeomorphic Version")
    
    diffeomorphic_morphs_list: bpy.props.CollectionProperty(name = "Daz Morphs List",
                        type=MustardUI_DazMorph)
    
    diffeomorphic_morphs_number: bpy.props.IntProperty(default = 0,
                        name = "")
    
    diffeomorphic_emotions: bpy.props.BoolProperty(default = False,
                        name = "Emotions Morphs",
                        description = "Search for Diffeomorphic emotions")
    diffeomorphic_emotions_collapse: bpy.props.BoolProperty(default = True)
    diffeomorphic_emotions_custom: bpy.props.StringProperty(default = "",
                        name = "Custom morphs",
                        description = "Add strings to add custom morphs (they should map the initial part of the name of the morph), separated by commas.\nNote: spaces and order are considered")
    
    diffeomorphic_facs_emotions: bpy.props.BoolProperty(default = False,
                        name = "FACS Emotions Morphs",
                        description = "Search for Diffeomorphic FACS emotions")
    diffeomorphic_facs_emotions_collapse: bpy.props.BoolProperty(default = True)
    
    diffeomorphic_emotions_units: bpy.props.BoolProperty(default = False,
                        name = "Emotions Units Morphs",
                        description = "Search for Diffeomorphic emotions units")
    diffeomorphic_emotions_units_collapse: bpy.props.BoolProperty(default = True)
    
    diffeomorphic_facs_emotions_units: bpy.props.BoolProperty(default = False,
                        name = "FACS Emotions Units Morphs",
                        description = "Search for Diffeomorphic FACS emotions units")
    diffeomorphic_facs_emotions_units_collapse: bpy.props.BoolProperty(default = True)
    
    diffeomorphic_body_morphs: bpy.props.BoolProperty(default = False,
                        name = "Body Morphs Morphs",
                        description = "Search for Diffeomorphic Body morphs")
    diffeomorphic_body_morphs_collapse: bpy.props.BoolProperty(default = True)
    diffeomorphic_body_morphs_custom: bpy.props.StringProperty(default = "",
                        name = "Custom morphs",
                        description = "Add strings to add custom morphs (they should map the initial part of the name of the morph), separated by commas.\nNote: spaces and order are considered")
    
    diffeomorphic_search: bpy.props.StringProperty(name = "",
                        description = "Search for a specific morph",
                        default = "")
    diffeomorphic_filter_null: bpy.props.BoolProperty(default = False,
                        name = "Filter morphs",
                        description = "Filter used morphs.\nOnly non null morphs will be shown")
    
    # Script for 1.5 morph support
    
    # Function to force Register in text file added
    def update_file_register(self, context):
        if self.diffeomorphic_1_5_script != None:
            if "def evalMorphsLoc(pb, idx):" in rig_settings.diffeomorphic_1_5_script.as_string():
                self.diffeomorphic_1_5_script.use_module = True
        return
    
    diffeomorphic_1_5_script: PointerProperty(type=bpy.types.Text,
                        name = "Diffeomorphic 1.5 Morph support script",
                        description = "From Diffeomorphic 1.6.1, 1.5 Morphs are not supported. You can provide this support script to enable them",
                        update = update_file_register)
    
    # ------------------------------------------------------------------------
    #    Various properties
    # ------------------------------------------------------------------------
    
    # Property for collapsing other properties section
    various_config_collapse: bpy.props.BoolProperty(default = True,
                        name = "")
    
    # Version of the model
    model_version: bpy.props.StringProperty(name = "Model version",
                        description = "Version of the model",
                        default = "")
    
    # Object and Collection MustardUI naming convention
    model_MustardUI_naming_convention: bpy.props.BoolProperty(default = True,
                        name = "MustardUI Naming Convention",
                        description = "Use the MustardUI naming convention for collections and objects.\nIf this is true, the collections and the objects listed as outfits will be stripped of unnecessary parts in the name")

    model_rig_type: bpy.props.EnumProperty(default = "other",
                        items = [("arp", "Auto-Rig Pro", "Auto-Rig Pro"), ("rigify", "Rigify", "Rigify"), ("mhx", "MHX", "MHX"), ("other", "Other", "Other")],
                        name = "Rig type")
    
    model_cleaned: bpy.props.BoolProperty(default = False)
    
    # Links
    # Property for collapsing links properties section
    url_config_collapse: bpy.props.BoolProperty(default = True,
                        name = "")
    
    # Standard links to MustardUI documentation and tutorial
    url_MustardUI: bpy.props.StringProperty(default = "https://github.com/Mustard2/MustardUI")
    
    url_MustardUI_reportbug: bpy.props.StringProperty(default = "https://github.com/Mustard2/MustardUI/issues")
    
    url_MustardUItutorial: bpy.props.StringProperty(default = "https://github.com/Mustard2/MustardUI/wiki/Tutorial")
    
    # Links that can be changed by the creator in the configuration tool
    url_website: bpy.props.StringProperty(default = "",
                        name = "Website")
    
    url_patreon: bpy.props.StringProperty(default = "",
                        name = "Patreon")
    
    url_twitter: bpy.props.StringProperty(default = "",
                        name = "Twitter")
    
    url_smutbase: bpy.props.StringProperty(default = "",
                        name = "Smutba.se")
    
    url_documentation: bpy.props.StringProperty(default = "",
                        name = "Documentation")
    
    url_reportbug: bpy.props.StringProperty(default = "",
                        name = "Report bug")
    
    # Debug
    # Property for collapsing debug properties section
    debug_config_collapse: bpy.props.BoolProperty(default = True,
                        name = "")
    
    ####### END OF MustardUI_RigSettings class ########

bpy.utils.register_class(MustardUI_RigSettings)
bpy.types.Armature.MustardUI_RigSettings = bpy.props.PointerProperty(type = MustardUI_RigSettings)

# Redefinition for lock functionality
bpy.types.Object.MustardUI_outfit_lock = bpy.props.BoolProperty(default = False,
                    name = "",
                    description = "Lock/unlock the outfit",
                    update = MustardUI_RigSettings.outfits_visibility_update)

# ------------------------------------------------------------------------
#    Armature layer Properties and operators
# ------------------------------------------------------------------------

# This operator initialize the armature panel
# It creates 32 instances of the MustardUI_ArmatureLayer to be filled with settings
class MustardUI_Armature_Initialize(bpy.types.Operator):
    """Initialize/remove the Armature configuration"""
    bl_idname = "mustardui.armature_initialize"
    bl_label = "Initialize/remove the Armature configuration"
    
    clean: bpy.props.BoolProperty(default = False)

    @classmethod
    def poll(cls, context):
        
        res, arm = mustardui_active_object(context, config = 1)
        armature_settings = arm.MustardUI_ArmatureSettings
        return res

    def execute(self, context):
        
        res, arm = mustardui_active_object(context, config = 1)
        armature_settings = arm.MustardUI_ArmatureSettings
        
        if not self.clean:
            
            for i in range(0,32):
                armature_settings.layers.add()
            
            self.report({'INFO'}, 'MustardUI - Armature initialization complete.')
        
        else:
            
            for i in reversed(range(0,32)):
                armature_settings.layers.remove(i)
                armature_settings.config_layer[i] = False
            
            armature_settings.config_layer_store = armature_settings.config_layer
            armature_settings.last_id = -1
            
            self.report({'INFO'}, 'MustardUI - Armature removal complete.')
        
        return {'FINISHED'}

# This operator will check for additional options for the outfits
class MustardUI_Armature_Sort(bpy.types.Operator):
    """Change order of the Armature layer"""
    bl_idname = "mustardui.armature_sort"
    bl_label = ""
    
    sort_id: bpy.props.IntProperty(default = False)
    up: bpy.props.BoolProperty(default = False)

    def execute(self, context):
        
        poll, arm = mustardui_active_object(context, config = 1)
        armature_settings = arm.MustardUI_ArmatureSettings
        layers = armature_settings.layers
        
        for i in range(0,32):
            
            if armature_settings.layers[i].id == self.sort_id:
                layer_id = i
            elif armature_settings.layers[i].id == self.sort_id - 1:
                layer_id_up = i
            elif armature_settings.layers[i].id == self.sort_id + 1:
                layer_id_down = i
        
        if self.up:
            armature_settings.layers[layer_id_up].id = armature_settings.layers[layer_id].id
            armature_settings.layers[layer_id].id = armature_settings.layers[layer_id].id - 1
        else:
            armature_settings.layers[layer_id_down].id = armature_settings.layers[layer_id].id
            armature_settings.layers[layer_id].id = armature_settings.layers[layer_id].id + 1       
        
        return {'FINISHED'}

def mustardui_armature_visibility_update(self, context):
    
    poll, arm = mustardui_active_object(context, config = 0)
    rig_settings = arm.MustardUI_RigSettings
    armature_settings = arm.MustardUI_ArmatureSettings
    
    if rig_settings.hair_collection != None:
        for object in [x for x in rig_settings.hair_collection.objects if x.type == "ARMATURE"]:
            if rig_settings.hair_list in object.name:
                object.hide_viewport = not armature_settings.hair
    
    for i in [x for x in range(0,32) if armature_settings.config_layer[x]]:
        arm.layers[i] = armature_settings.layers[i].show
    
    return

def outfit_switcher_enable_update(self, context):
    
    if self.outfit_switcher_enable:
        self.name = "Outfit reserved " + str(self.id)
    else:
        self.name = ""
    
    return

class MustardUI_ArmatureLayer(bpy.types.PropertyGroup):
    
    # Configuration setting (collapse of layer settings)
    layer_config_collapse: bpy.props.BoolProperty(default = False, name = "")
    
    id: bpy.props.IntProperty(default = -1)
    
    name: bpy.props.StringProperty(default = "",
                        name = "Name",
                        description = "The name of the layer that will be shown in the UI")
    
    advanced: bpy.props.BoolProperty(default = False,
                        name = "Advanced",
                        description = "Enable Advanced layer.\nIf enabled, this layer will be shown in the UI only if Advanced settings is enabled in the UI settings")
    
    show: bpy.props.BoolProperty(default = True,
                        name = "Show/Hide layer",
                        description = "Show/Hide the selected layer",
                        update = mustardui_armature_visibility_update)
    
    mirror: bpy.props.BoolProperty(default = False,
                        name = "Mirror",
                        description = "Enable Mirror.\nThis will add a line of two buttons in the Armature panel, one for the left and one for the right layer")
    
    mirror_left: bpy.props.BoolProperty(default = True,
                        name = "Left",
                        description = "The Left layer.\nThe mirrored layer will be called Right, the inverse if this is unchecked")
    
    mirror_layer: bpy.props.IntProperty(default = -1,
                        name = "Mirror Layer",
                        description = "The armature layer which mirror this")
    
    # Poll function for the selection of mesh belonging to an outfit in pointer properties
    def outfit_switcher_poll_collection(self, object):
        
        rig_settings = self.id_data.MustardUI_RigSettings
        
        return object in [x.collection for x in rig_settings.outfits_collections if x.collection != None] or object == rig_settings.extras_collection
    
    # Poll function for the selection of mesh belonging to an outfit in pointer properties
    def outfit_switcher_poll_mesh(self, object):
        
        if self.outfit_switcher_collection != None:
            if object in [x for x in self.outfit_switcher_collection.objects]:
                return object.type == 'MESH'
        
        return False
    
    # Automatic outfits layer switcher
    outfit_switcher_enable: bpy.props.BoolProperty(default = False,
                        name = "Outfit Switcher",
                        description = "Enable automatic Outfit layer switcher.\nWhen the selected outfit is enabled in the UI, this layer will be shown/hidden automatically",
                        update = outfit_switcher_enable_update)
    
    outfit_switcher_collection: bpy.props.PointerProperty(name = "Outfit",
                        description = "Outfits Switcher outfit.\nWhen Outfit Switcher is enabled, when switching to this outfit this layer will be shown/hidden.\nSet also Outfit Piece if you want the layer to be shown only for a specific outfit piece",
                        type = bpy.types.Collection,
                        poll = outfit_switcher_poll_collection)
    
    outfit_switcher_object: bpy.props.PointerProperty(name = "Outfit Piece",
                        description = "Outfits Switcher outfit piece.\nWhen Outfit Switcher is enabled, when switching to this outfit piece this layer will be shown/hidden",
                        type = bpy.types.Object,
                        poll = outfit_switcher_poll_mesh)
    
bpy.utils.register_class(MustardUI_ArmatureLayer)

class MustardUI_ArmatureSettings(bpy.types.PropertyGroup):

    # Property for collapsing rig properties section
    config_collapse: bpy.props.BoolProperty(default = True,
                        name = "")
    
    def layers_update(self, context):
        
        if len(self.layers)<31:
            return
        
        for i in range(0,32):
            if self.config_layer[i] != self.config_layer_store[i]:
                
                if self.config_layer[i]:
                    self.last_id = self.last_id + 1
                    self.layers[i].id = self.last_id
                
                else:
                    for j in range(0,32):
                        if self.layers[j].id > self.layers[i].id:
                            self.layers[j].id = self.layers[j].id - 1
                        
                    self.last_id = self.last_id - 1
                    self.layers[i].id = -1
                        
        
        self.config_layer_store = self.config_layer
        
        return

    config_layer: bpy.props.BoolVectorProperty(subtype = "LAYER",
                        name = "Layer",
                        size = 32,
                        update = layers_update)
    
    # Used for creating ordered ids
    last_id: bpy.props.IntProperty(default = -1)
    
    config_layer_store: bpy.props.BoolVectorProperty(subtype="LAYER",
                        size=32)
    
    layers: bpy.props.CollectionProperty(name = "Armature Layers",
                        type = MustardUI_ArmatureLayer)
    
    # Hair armature controller
    enable_automatic_hair: bpy.props.BoolProperty(default = True,
                        name = "Armature Hair detection",
                        description = "Enable the automatic armature hair detection.\nIf enabled, the UI will automatically detect armatures in the hair collection")
    
    hair: bpy.props.BoolProperty(default = True,
                        name = "Hair",
                        description = "Show/hide the hair armature",
                        update = mustardui_armature_visibility_update)
    
    # IK/FK Support
    ik_fk_collapse: bpy.props.BoolProperty(default = True,
                        name = "")
    
    enable_ik_fk: bpy.props.BoolProperty(default = False,
                        name = "IK/FK support",
                        description = "Enable the IK/FK switch tools if available for the current rig")
    enable_ik_fk_snap: bpy.props.BoolProperty(default = False,
                        name = "IK/FK snap tools",
                        description = "Enable the IK/FK snap tools if available for the current rig")
    
    

bpy.utils.register_class(MustardUI_ArmatureSettings)
bpy.types.Armature.MustardUI_ArmatureSettings = bpy.props.PointerProperty(type = MustardUI_ArmatureSettings)

# ------------------------------------------------------------------------
#    Tools definitions
# ------------------------------------------------------------------------

# Function to show message boxes for tools
def ShowMessageBox(message = "", title = "Message Box", icon = 'INFO'):

    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)

# Class to store tools settings
class MustardUI_ToolsSettings(bpy.types.PropertyGroup):
    
    # Property for collapsing tools properties section
    tools_config_collapse: bpy.props.BoolProperty(default = True,
                        name = "")

    # Child Of
    childof_enable: bpy.props.BoolProperty(default = True,
                        name = "Child Of",
                        description = "Enable the Child Of tool.\nThis tool will allow a quick creation of Child Of modifiers between two selected bones")
    
    childof_influence: bpy.props.FloatProperty(default = 1.0,
                        min = 0.0, max = 1.0,
                        name = "Influence",
                        description = "Set the influence the parent Bone will have on the Child one")
    
    # Name of the modifiers created by the tool
    childof_constr_name: bpy.props.StringProperty(default = 'MustardUI_ChildOf')
    
    # Auto Breath
    autobreath_enable: bpy.props.BoolProperty(default = False,
                        name = "Auto Breath",
                        description = "Enable the Auto Breath tool.\nThis tool will allow a quick creation of a breathing animation")
    
    autobreath_frequency: bpy.props.FloatProperty(default = 16.0,
                        min = 1.0, max = 200.0,
                        name = "Frequency",
                        description = "Breathing frequency in breath/minute")
    
    autobreath_amplitude: bpy.props.FloatProperty(default = 1.0,
                        min = 0.0, max = 1.0,
                        name = "Amplitude",
                        description = "Amplitude of the breathing animation")
    
    autobreath_random: bpy.props.FloatProperty(default = 0.01,
                        min = 0.0, max = 1.0,
                        name = "Random factor",
                        description = "Randomization of breathing")
    
    autobreath_sampling: bpy.props.IntProperty(default = 1,
                        min = 1, max = 24,
                        name = "Sampling",
                        description = "Number of frames beetween two animations key")
    
    # Auto Blink
    autoeyelid_enable: bpy.props.BoolProperty(default = False,
                        name = "Auto Blink",
                        description = "Enable the Auto Blink tool.\nThis tool will allow a quick creation of eyelid blinking animation")
    
    autoeyelid_driver_type: bpy.props.EnumProperty(default = "SHAPE_KEY",
                        items = [("SHAPE_KEY", "Shape Key", "Shape Key", "SHAPEKEY_DATA", 0), ("MORPH", "Morph", "Morph", "OUTLINER_OB_ARMATURE", 1)],
                        name = "Driver type")
    
    autoeyelid_blink_length: bpy.props.FloatProperty(default = 1.,
                        min = 0.1, max = 20.0,
                        name = "Blink Length Factor",
                        description = "Increasing this value, you will proportionally increase the length of the blink from the common values of 0.1-0.25 ms")
    
    autoeyelid_blink_rate_per_minute: bpy.props.IntProperty(default = 26,
                        min = 1, max = 104,
                        name = "Blink Chance",
                        description = "Number of blinks per minute.\nNote that some randomization is included in the tool, therefore the final realization number might be different")
    
    autoeyelid_eyeL_shapekey: bpy.props.StringProperty(name = "Key",
                        description = "Name of the first shape key to animate (required)")
    autoeyelid_eyeR_shapekey: bpy.props.StringProperty(name = "Optional",
                        description = "Name of the second shape key to animate (optional)")
    autoeyelid_morph: bpy.props.StringProperty(name = "Morph",
                        description = "The name of the morph should be the name of the custom property in the Armature object, and not the name of the morph shown in the UI")
    
    # ------------------------------------------------------------------------
    #    Tools - Lips Shrinkwrap
    # ------------------------------------------------------------------------

    def lips_shrinkwrap_bones_corner_list(context, rig_type, armature):
        
        if rig_type == "arp":
            return ['c_lips_smile.r','c_lips_smile.l']
        elif rig_type == "mhx":
            if "LipCorner.l" in [x.name for x in armature.bones]:
                return ['LipCorner.l','LipCorner.r']
            else:
                return ['LipCorner.L','LipCorner.R']
        else:
            return []
    
    def lips_shrinkwrap_bones_list(context, rig_type, armature):
        
        if rig_type == "arp":
            return ['c_lips_smile.r','c_lips_top.r','c_lips_top_01.r','c_lips_top.x','c_lips_top.l','c_lips_top_01.l','c_lips_smile.l','c_lips_bot.r','c_lips_bot_01.r','c_lips_bot.x','c_lips_bot.l','c_lips_bot_01.l']
        elif rig_type == "mhx":
            if "LipCorner.l" in [x.name for x in armature.bones]:
                return ['LipCorner.l', 'LipLowerOuter.l', 'LipLowerInner.l', 'LipLowerMiddle', 'LipLowerInner.r', 'LipLowerOuter.r', 'LipCorner.r', 'LipUpperMiddle', 'LipUpperOuter.l', 'LipUpperInner.l', 'LipUpperInner.r', 'LipUpperOuter.r']
            else:
                return ['LipCorner.L', 'LipLowerOuter.L', 'LipLowerInner.L', 'LipLowerMiddle', 'LipLowerInner.R', 'LipLowerOuter.R', 'LipCorner.R', 'LipUpperMiddle', 'LipUpperOuter.L', 'LipUpperInner.L', 'LipUpperInner.R', 'LipUpperOuter.R']
        else:
            return []
    
    def lips_shrinkwrap_update(self, context):
        
        poll, arm = mustardui_active_object(context, config = 0)
        rig_type = arm.MustardUI_RigSettings.model_rig_type
        
        if self.lips_shrinkwrap_armature_object != None:
            armature = self.lips_shrinkwrap_armature_object
        else:
            ShowMessageBox("Fatal error", "MustardUI Information", icon = "ERROR")
        
        bones_lips = self.lips_shrinkwrap_bones_list(rig_type, arm)
        
        ob = bpy.context.active_object
        
        if self.lips_shrinkwrap and self.lips_shrinkwrap_obj:
            
            for bone in bones_lips:
                
                constr_check = False
                
                if not (0 < len([m for m in armature.pose.bones[bone].constraints if m.type == "SHRINKWRAP"])):
                    constr = armature.pose.bones[bone].constraints.new('SHRINKWRAP')
                    constr.name = self.lips_shrink_constr_name
                    constr_check = True
                
                elif not constr_check:
                    for c in armature.pose.bones[bone].constraints:
                        if c.name == self.lips_shrink_constr_name:
                            constr_check = True
                            break
                
                if not constr_check:
                    constr = armature.pose.bones[bone].constraints.new('SHRINKWRAP')
                    constr.name = self.lips_shrink_constr_name
                
                constr = armature.pose.bones[bone].constraints[self.lips_shrink_constr_name]
                constr.target = self.lips_shrinkwrap_obj
                
                constr.wrap_mode = "OUTSIDE"
                constr.distance = self.lips_shrinkwrap_dist
                
                if bone in self.lips_shrinkwrap_bones_corner_list(rig_type, arm):
                    constr.distance = constr.distance * self.lips_shrinkwrap_dist_corr
            
            if self.lips_shrinkwrap_friction and ob == armature:
            
                for bone in bones_lips:
                
                    constr_check = False
                
                    if not (0 < len([m for m in armature.pose.bones[bone].constraints if m.type == "CHILD_OF"])):
                        constr = armature.pose.bones[bone].constraints.new('CHILD_OF')
                        constr.name = self.lips_shrink_constr_name+'_fric'
                        constr_check = True
                
                    elif not constr_check:
                        for c in armature.pose.bones[bone].constraints:
                            if c.name == self.lips_shrink_constr_name+'_fric':
                                constr_check = True
                                break
                
                    if not constr_check:
                        constr = armature.pose.bones[bone].constraints.new('CHILD_OF')
                        constr.name = self.lips_shrink_constr_name+'_fric'
                
                    constr = armature.pose.bones[bone].constraints[self.lips_shrink_constr_name+'_fric']
                    if self.lips_shrinkwrap_obj_fric:
                        constr.target = self.lips_shrinkwrap_obj_fric
                        constr.subtarget = self.lips_shrinkwrap_obj_fric_sec
                    else:
                        constr.target = self.lips_shrinkwrap_obj
                    constr.use_scale_x = False
                    constr.use_scale_y = False
                    constr.use_scale_z = False
                
                    context_py = bpy.context.copy()
                    context_py["constraint"] = constr
                
                    org_layers = ob.data.layers[:]
                    for i in range(len(org_layers)):
                        ob.data.layers[i] = True
                
                    ob.data.bones.active = armature.pose.bones[bone].bone
                    #bpy.ops.constraint.childof_set_inverse(context_py, constraint=self.lips_shrink_constr_name+'_fric', owner='BONE')
                
                    for i in range(len(org_layers)):
                        ob.data.layers[i] = org_layers[i]
                
                    constr.influence = self.lips_shrinkwrap_friction_infl
        
            elif self.lips_shrinkwrap and self.lips_shrinkwrap_friction and ob != armature:
            
                ShowMessageBox("You must select any model armature bone, in Pose mode, to apply the friction.", "MustardUI Information", icon = "ERROR")
        
            else:
            
                for bone in bones_lips:
                    for c in armature.pose.bones[bone].constraints:
                        if c.name == self.lips_shrink_constr_name+'_fric':
                            to_remove = armature.pose.bones[bone].constraints[self.lips_shrink_constr_name+'_fric']
                            armature.pose.bones[bone].constraints.remove(to_remove)
        
        elif self.lips_shrinkwrap and not self.lips_shrinkwrap_obj:
            
            self.lips_shrinkwrap = False
            ShowMessageBox("Select an Object. No modifier has been added", "MustardUI Information")
        
        else:
            
            for bone in bones_lips:
                for c in armature.pose.bones[bone].constraints:
                    if self.lips_shrink_constr_name in c.name:
                        to_remove = armature.pose.bones[bone].constraints[c.name]
                        armature.pose.bones[bone].constraints.remove(to_remove)
        
        return

    def lips_shrinkwrap_distance_update(self, context):
        
        poll, arm = mustardui_active_object(context, config = 0)
        rig_type = arm.MustardUI_RigSettings.model_rig_type
        
        if self.lips_shrinkwrap_armature_object != None and arm != None:
            armature = self.lips_shrinkwrap_armature_object
        else:
            ShowMessageBox("Fatal error", "MustardUI Information", icon = "ERROR")
            
        bones_lips = self.lips_shrinkwrap_bones_list(rig_type, arm)
        
        if self.lips_shrinkwrap:
        
            for bone in bones_lips:
                
                constr = armature.pose.bones[bone].constraints[self.lips_shrink_constr_name]
                constr.distance = self.lips_shrinkwrap_dist
                
                if bone in self.lips_shrinkwrap_bones_corner_list(rig_type, arm):
                    constr.distance = constr.distance * self.lips_shrinkwrap_dist_corr
        
        return

    def lips_shrinkwrap_friction_infl_update(self, context):
        
        poll, arm = mustardui_active_object(context, config = 0)
        rig_type = arm.MustardUI_RigSettings.model_rig_type
        
        if self.lips_shrinkwrap_armature_object != None and arm != None:
            armature = self.lips_shrinkwrap_armature_object
        else:
            ShowMessageBox("Fatal error", "MustardUI Information", icon = "ERROR")
        
        bones_lips = self.lips_shrinkwrap_bones_list(rig_type, arm)
        
        if self.lips_shrinkwrap_friction and self.lips_shrinkwrap:
        
            for bone in bones_lips:
                
                constr = armature.pose.bones[bone].constraints[self.lips_shrink_constr_name+'_fric']
                constr.influence = self.lips_shrinkwrap_friction_infl
        
        return

    def lips_shrinkwrap_obj_sec_poll(self, object):
        
        if self.lips_shrinkwrap_obj.type == 'MESH':
        
            return object.type == 'VERTEXGROUP'
        
        else:
            
            return object.type == 'EMPTY'
        
        return

    # Config enable
    lips_shrinkwrap_enable: bpy.props.BoolProperty(default = False,
                                             name="Lips Shrinkwrap",
                                             description="Enable Lips shrinkwrap tool.\nThis can be added only on ARP and MHX rigs")
    
    # Poll function for the selection of mesh only in pointer properties
    def poll_armature(self, object):
        return object.type == 'ARMATURE'
    
    lips_shrink_constr_name: bpy.props.StringProperty(default = "MustardUI_lips_shrink_constr")
    
    lips_shrinkwrap_armature_object: bpy.props.PointerProperty(type = bpy.types.Object,
                        name = "Armature Object",
                        description = "Set the armature object.\nThis should be the Armature Object of the main model",
                        poll = poll_armature)
    
    lips_shrinkwrap: bpy.props.BoolProperty(default = False,
                        name="Enable",
                        description="Enable lips shrinkwrap",
                        update = lips_shrinkwrap_update)

    lips_shrinkwrap_friction: bpy.props.BoolProperty(default = False,
                        name="Enable Friction",
                        description="Enable friction to lips shrinkwrap.",
                        update = lips_shrinkwrap_update)

    lips_shrinkwrap_dist: bpy.props.FloatProperty(default = 0.01,
                        min = 0.0,
                        name = "Distance",
                        description = "Set the distance of the lips bones to the Object",
                        update = lips_shrinkwrap_distance_update)

    lips_shrinkwrap_dist_corr: bpy.props.FloatProperty(default = 1.0,
                        min = 0.0, max = 2.0,
                        name = "Outer bones correction",
                        description = "Set the correction of the outer mouth bones to adjust the result.\nThis value is the fraction of the distance that will be applied to the outer bones shrinkwrap modifiers",
                        update = lips_shrinkwrap_distance_update)

    lips_shrinkwrap_friction_infl: bpy.props.FloatProperty(default = 0.1,
                        min = 0.0, max = 1.0,
                        name = "Coefficient",
                        description = "Set the friction coefficient of the lips shrinkwrap.\nIf the coefficient is 1, the bone will follow the Object completely",
                        update = lips_shrinkwrap_friction_infl_update)
    
    lips_shrinkwrap_obj: bpy.props.PointerProperty(type = bpy.types.Object,
                        name = "Object",
                        description = "Select the object where to apply the lips shrinkwrap",
                        update = lips_shrinkwrap_update)

    lips_shrinkwrap_obj_fric: bpy.props.PointerProperty(type = bpy.types.Object,
                        name = "Object",
                        description = "Select the object to use as a reference for the friction effect.\nIf no object is selected, the same object inserted in the main properties will be used",
                        update = lips_shrinkwrap_update)

    lips_shrinkwrap_obj_fric_sec: bpy.props.StringProperty(name = "Sub-target")

bpy.utils.register_class(MustardUI_ToolsSettings)
bpy.types.Armature.MustardUI_ToolsSettings = bpy.props.PointerProperty(type = MustardUI_ToolsSettings)

# ------------------------------------------------------------------------
#    Custom Properties
# ------------------------------------------------------------------------

class MustardUI_LinkedProperty(bpy.types.PropertyGroup):
    
    # Internal stored properties
    rna : bpy.props.StringProperty(name = "RNA")
    path : bpy.props.StringProperty(name = "Path")

class MustardUI_CustomProperty(bpy.types.PropertyGroup):
    
    # Type
    cp_type: bpy.props.EnumProperty(name = "Type",
                        default = "BODY",
                        items = (("BODY", "Body", "Body"), ("OUTFIT", "Outfit", "Outfit"), ("HAIR", "Hair", "Hair")))
    
    # User defined properties
    name : bpy.props.StringProperty(name = "Custom property name")
    icon : bpy.props.EnumProperty(name='Icon',
                        description="Choose the icon",
                        items = mustardui_icon_list)
    
    # Internal stored properties
    rna : bpy.props.StringProperty(name = "RNA")
    path : bpy.props.StringProperty(name = "Path")
    prop_name : bpy.props.StringProperty(name = "Property Name")
    is_animatable: bpy.props.BoolProperty(name = "Animatable")
    type : bpy.props.StringProperty(name = "Type")
    array_length : bpy.props.IntProperty(name = "Array Length")
    subtype : bpy.props.StringProperty(name = "Subtype")
    force_type: bpy.props.EnumProperty(name = "Force Property Type",
                        default="None",
                        items=(("None", "None", "None"), ("Int", "Int", "Int"), ("Bool", "Bool", "Bool")))
    
    # Bool value show
    def update_bool_value(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config = 0)
        
        if obj != None:
            
            obj[self.prop_name] = self.bool_value
        
        return 
    
    is_bool: bpy.props.BoolProperty(name = "Bool value")
    bool_value: bpy.props.BoolProperty(name = "",
                        update = update_bool_value,
                        description = "")
    
    # Properties stored to rebuild custom properties in case of troubles
    description: bpy.props.StringProperty()
    default_int: bpy.props.IntProperty()
    min_int: bpy.props.IntProperty()
    max_int: bpy.props.IntProperty()
    default_float: bpy.props.FloatProperty()
    min_float: bpy.props.FloatProperty()
    max_float: bpy.props.FloatProperty()
    default_array: bpy.props.StringProperty()
    
    # Linked properties
    linked_properties: bpy.props.CollectionProperty(type = MustardUI_LinkedProperty)
    
    # Section settings
    section: bpy.props.StringProperty(default = "")
    add_section: bpy.props.BoolProperty(default = False,
                        name = "Add to section",
                        description = "Add the property to the selected section")
    
    # Outfits
    # Poll function for the selection of mesh only in pointer properties
    def poll_mesh(self, object):
        
        rig_settings = self.id_data.MustardUI_RigSettings
        
        return object.type == 'MESH' and object in [x for x in rig_settings.hair_collection.objects]
    
    # Poll function for the selection of mesh belonging to an outfit in pointer properties
    def outfit_switcher_poll_collection(self, object):
        
        rig_settings = self.id_data.MustardUI_RigSettings
        
        return object in [x.collection for x in rig_settings.outfits_collections if x.collection != None] or object == rig_settings.extras_collection
    
    # Poll function for the selection of mesh belonging to an outfit in pointer properties
    def outfit_switcher_poll_mesh(self, object):
        
        if self.outfit != None:
            if object in [x for x in self.outfit.objects]:
                return object.type == 'MESH'
        
        return False
    
    outfit: bpy.props.PointerProperty(name = "Outfit Collection",
                        type = bpy.types.Collection,
                        poll = outfit_switcher_poll_collection)
    outfit_piece: bpy.props.PointerProperty(name = "Outfit Piece",
                        type = bpy.types.Object,
                        poll = outfit_switcher_poll_mesh)
    
    # Hair
    hair: bpy.props.PointerProperty(name = "Hair Style",
                        type = bpy.types.Object,
                        poll = poll_mesh)
    
bpy.utils.register_class(MustardUI_LinkedProperty)
bpy.utils.register_class(MustardUI_CustomProperty)
bpy.types.Armature.MustardUI_CustomProperties = bpy.props.CollectionProperty(type = MustardUI_CustomProperty)
bpy.types.Armature.MustardUI_CustomPropertiesOutfit = bpy.props.CollectionProperty(type = MustardUI_CustomProperty)
bpy.types.Armature.MustardUI_CustomPropertiesHair = bpy.props.CollectionProperty(type = MustardUI_CustomProperty)

# Function to check keys of custom properties (only for debug)
def dump(obj, text):
    print('-'*40, text, '-'*40)
    for attr in dir(obj):
        if hasattr( obj, attr ):
            print( "obj.%s = %s" % (attr, getattr(obj, attr)))

# Function to check over all custom properties
def mustardui_check_cp(obj, rna, path):
    
    for cp in obj.MustardUI_CustomProperties:
        if cp.rna == rna and cp.path == path:
            return False
    
    for cp in obj.MustardUI_CustomPropertiesOutfit:
        if cp.rna == rna and cp.path == path:
            return False
    
    for cp in obj.MustardUI_CustomPropertiesHair:
        if cp.rna == rna and cp.path == path:
            return False

    return True

# Function to choose correct custom properties list
def mustardui_choose_cp(obj, type, scene):
    
    if type == "BODY":
        return obj.MustardUI_CustomProperties, scene.mustardui_property_uilist_index
    elif type == "OUTFIT":
        return obj.MustardUI_CustomPropertiesOutfit, scene.mustardui_property_uilist_outfits_index
    else:
        return obj.MustardUI_CustomPropertiesHair, scene.mustardui_property_uilist_hair_index

def mustardui_update_index_cp(type, scene, index):
    
    if type == "BODY":
        scene.mustardui_property_uilist_index = index
    elif type == "OUTFIT":
        scene.mustardui_property_uilist_outfits_index = index
    else:
        scene.mustardui_property_uilist_hair_index = index

# Function to add driver
def mustardui_add_driver(obj, rna, path, prop, prop_name):
        
        driver_object = eval(rna)
        driver_object.driver_remove(path)
        driver = driver_object.driver_add(path)
        
        # No array property
        if prop.array_length == 0:
            driver = driver.driver
            driver.type = "AVERAGE"
            var = driver.variables.new()
            var.name                 = 'mustardui_var'
            var.targets[0].id_type   = "ARMATURE"
            var.targets[0].id        = obj
            var.targets[0].data_path = '["' + prop_name + '"]'
        
        # Array property
        else:
            for i in range(0,prop.array_length):
                driver[i] = driver[i].driver
                driver[i].type = "AVERAGE"
                
                var = driver[i].variables.new()
                var.name                 = 'mustardui_var'
                var.targets[0].id_type   = "ARMATURE"
                var.targets[0].id        = obj
                var.targets[0].data_path = '["' + prop_name + '"]' + '['+ str(i) + ']'
        
        return

def mustardui_clean_prop(obj, uilist, index, settings):
        
        # Delete custom property and drivers
        try:
            ui_data = obj.id_properties_ui(uilist[index].prop_name)
            ui_data.clear()
        except:
            if settings.debug:
                print('MustardUI - Could not clear UI properties. Skipping for this custom property')
        
        # Delete custom property
        try:
            del obj[uilist[index].prop_name]
        except:
            if settings.debug:
                print('MustardUI - Properties not found. Skipping custom properties deletion')
        
        # Remove linked properties drivers
        for lp in uilist[index].linked_properties:
            try:
                driver_object = eval(lp.rna)
                driver_object.driver_remove(lp.path)
            except:
                print("MustardUI - Could not delete driver with path: " + lp.rna)
        
        # Remove driver
        try:
            driver_object = eval(uilist[index].rna)
            driver_object.driver_remove(uilist[index].path)
        except:
            print("MustardUI - Could not delete driver with path: " + uilist[index].rna)
        
        return

def mustardui_cp_path(rna, path):
    
    return rna + "." + path if not all(["[" in path, "]" in path]) else rna + path

# Operator to add the right click button on properties
class MustardUI_Property_MenuAdd(bpy.types.Operator):
    """Add the property to the menu"""
    bl_idname = "mustardui.property_menuadd"
    bl_label = "Add to MustardUI (Un-sorted)"
    bl_options = {'UNDO'}
    
    section: bpy.props.StringProperty(default = "")
    outfit: bpy.props.StringProperty(default = "")
    outfit_piece: bpy.props.StringProperty(default = "")
    hair: bpy.props.StringProperty(default = "")

    @classmethod
    def poll(cls, context):
        
        res, arm = mustardui_active_object(context, config = 1)
        return res

    def execute(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config = 1)
        if self.outfit != "":
            custom_props = obj.MustardUI_CustomPropertiesOutfit
        elif self.hair != "":
            custom_props = obj.MustardUI_CustomPropertiesHair
        else:
            custom_props = obj.MustardUI_CustomProperties
        
        if not hasattr(context, 'button_prop'):
            self.report({'ERROR'}, 'MustardUI - Can not create custom property from this property.')
            return {'FINISHED'}
        
        prop = context.button_prop
        
        # dump(prop, 'button_prop')
        
        # Copy the path of the selected property
        try:
            bpy.ops.ui.copy_data_path_button(full_path=True)
        except:
            self.report({'ERROR'}, 'MustardUI - Invalid selection.')
            return {'FINISHED'}
        
        # Adjust the property path to be exported
        rna, path = context.window_manager.clipboard.rsplit('.', 1)
        if '][' in path:
            path, rem = path.rsplit('[', 1)
            rna = rna + '.' + path
            path = '[' + rem
        elif '[' in path:
            path, rem = path.rsplit('[', 1)
        
        # Check if the property was already added
        if not mustardui_check_cp(obj, rna, path):
            self.report({'ERROR'}, 'MustardUI - This property was already added.')
            return {'FINISHED'}
        
        # Try to find a better name than default_value for material nodes
        if "node_tree.nodes" in rna:
            rna_node = rna.rsplit(".", 1)
            
            # Check for .type existance
            try:
                if eval(rna_node[0] + ".type") in ["VALUE", "RGB"]:
                    prop_name_ui = eval(rna_node[0] + ".name")
                else:
                    prop_name_ui = eval(rna + ".name")
            except:
                prop_name_ui = prop.name
            
        # Try to find a better name than default_value for shape keys
        elif "shape_keys" in rna and "key_block" in rna:
            prop_name_ui = eval(rna + ".name")
        else:
            prop_name_ui = prop.name
        
        # Add custom property to the object
        prop_name = prop_name_ui
        if prop.is_animatable:
            
            add_string_num = 1
            while prop_name in obj.keys():
                add_string_num += 1
                prop_name = prop_name_ui + ' ' + str(add_string_num)
            
            if prop.type == "ENUM":
                pass
            
            # Change custom properties settings
            elif prop.type == "BOOLEAN" and prop.array_length < 1:
                rna_idprop_ui_create(obj, prop_name, default=eval(rna + '.' + path),
                                    description=prop.description,
                                    overridable=True)
                    
            elif hasattr(prop, 'hard_min') and hasattr(prop, 'hard_max') and hasattr(prop, 'default') and hasattr(prop, 'description') and hasattr(prop, 'subtype'):
                description = prop.description if (not "node_tree.nodes" in rna and not "shape_keys" in rna) else ""
                rna_idprop_ui_create(obj, prop_name, default=prop.default if prop.array_length == 0 else eval(mustardui_cp_path(rna, path)),
                                    min=prop.hard_min if prop.subtype != "COLOR" else 0.,
                                    max=prop.hard_max if prop.subtype != "COLOR" else 1.,
                                    description=description,
                                    overridable=True,
                                    subtype=prop.subtype if prop.subtype != "FACTOR" else None)
            elif hasattr(prop, 'description'):
                rna_idprop_ui_create(obj, prop_name, default=eval(mustardui_cp_path(rna, path)),
                                    description=prop.description)
        
        # Add driver
        force_non_animatable = False
        try:
            if prop.is_animatable and (not prop.type in ["BOOLEAN", "ENUM"] or (prop.type == "BOOLEAN" and prop.array_length < 1)):
                mustardui_add_driver(obj, rna, path, prop, prop_name)
            else:
                force_non_animatable = True
        except:
            force_non_animatable = True
        
        # Add property to the collection of properties
        if not (rna,path) in [(x.rna,x.path) for x in custom_props]:
            
            cp = custom_props.add()
            cp.rna = rna
            cp.path = path
            cp.name = prop_name_ui
            cp.prop_name = prop_name
            cp.type = prop.type
            if hasattr(prop, 'array_length'):
                cp.array_length = prop.array_length
            cp.subtype = prop.subtype
            
            # Try to find icon
            if "materials" in rna:
                cp.icon = "MATERIAL"
            elif "key_blocks" in rna:
                cp.icon = "SHAPEKEY_DATA"
            
            cp.is_bool = prop.type == "BOOLEAN"
            if prop.type == "BOOLEAN" and prop.array_length<1:
                cp.bool_value = eval(rna + '.' + path)
            cp.is_animatable = prop.is_animatable if not force_non_animatable else False
            
            cp.section = self.section
            
            # Assign type
            if self.outfit != "":
                cp.cp_type = "OUTFIT"
            elif self.hair != "":
                cp.cp_type = "HAIR"
            else:
                cp.cp_type = "BODY"
            
            # Outfit and hair properties
            if self.outfit != "":
                cp.outfit = bpy.data.collections[self.outfit]
                if self.outfit_piece != "":
                    cp.outfit_piece = bpy.data.objects[self.outfit_piece]
            elif self.hair != "":
                cp.hair = bpy.data.objects[self.hair]
            
            if cp.is_animatable:
                
                ui_data_dict = obj.id_properties_ui(prop_name).as_dict()
                
                if hasattr(prop, 'description'):
                    cp.description = ui_data_dict['description']
                if hasattr(prop, 'default'):
                    if prop.array_length == 0:
                        if prop.type == "FLOAT":
                            cp.default_float = prop.default
                        elif prop.type == "INT" or prop.type == "BOOLEAN":
                            cp.default_int = prop.default
                    else:
                        cp.default_array = str(ui_data_dict['default'])
                        
                if hasattr(prop, 'hard_min') and prop.type != "BOOLEAN":
                    if prop.type == "FLOAT":
                        cp.min_float = prop.hard_min
                    elif prop.type == "INT":
                        cp.min_int = prop.hard_min
                if hasattr(prop, 'hard_max') and prop.type != "BOOLEAN":
                    if prop.type == "FLOAT":
                        cp.max_float = prop.hard_max
                    elif prop.type == "INT":
                        cp.max_int = prop.hard_max
        else:
            self.report({'ERROR'}, 'MustardUI - An error occurred while adding the property to the custom properties list.')
            return {'FINISHED'}
        
        # Update the drivers
        obj.update_tag()
        
        self.report({'INFO'}, 'MustardUI - Property added.')
    
        return {'FINISHED'}

# Operator to add the right click button on properties
class MustardUI_Property_MenuLink(bpy.types.Operator):
    """Link the property to an existing one.\nType"""
    bl_idname = "mustardui.property_menulink"
    bl_label = "Link property to another MustardUI property"
    bl_options = {'UNDO'}
    
    parent_rna: bpy.props.StringProperty()
    parent_path: bpy.props.StringProperty()
    type: bpy.props.EnumProperty(default = "BODY",
                        items = (("BODY", "Body", ""), ("OUTFIT", "Outfit", ""), ("HAIR", "Hair", "")))
    
    @classmethod
    def poll(cls, context):
        
        res, arm = mustardui_active_object(context, config = 1)
        return res

    def execute(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config = 1)
        custom_props, nu = mustardui_choose_cp(obj, self.type, context.scene)
        
        prop = context.button_prop
        
        if not hasattr(context, 'button_prop') or not hasattr(prop, 'array_length'):
            self.report({'ERROR'}, 'MustardUI - Can not link this property to anything.')
            return {'FINISHED'}
        
        if not prop.is_animatable:
            self.report({'ERROR'}, 'MustardUI - Can not link a \'non animatable\' property.')
            return {'FINISHED'}
        
        found = False
        for parent_prop in custom_props:
            if parent_prop.rna == self.parent_rna and parent_prop.path == self.parent_path:
                found = True
                break
        if not found:
            self.report({'ERROR'}, 'MustardUI - An error occurred while searching for parent property.')
            return {'FINISHED'}
        
        try:
            parent_prop_length = len( eval( mustardui_cp_path(parent_prop.rna, parent_prop.path) ) )
        except:
            parent_prop_length = 0
        
        if prop.array_length != parent_prop_length:
            self.report({'ERROR'}, 'MustardUI - Can not link properties with different array length.')
            return {'FINISHED'}
        
        if parent_prop.type != prop.type:
            self.report({'ERROR'}, 'MustardUI - Can not link properties with different type.')
            return {'FINISHED'}
        
        # dump(prop, 'button_prop')
        
        # Copy the path of the selected property
        try:
            bpy.ops.ui.copy_data_path_button(full_path=True)
        except:
            self.report({'ERROR'}, 'MustardUI - Invalid selection.')
            return {'FINISHED'}
        
        # Adjust the property path to be exported
        rna, path = context.window_manager.clipboard.rsplit('.', 1)
        if '][' in path:
            path, rem = path.rsplit('[', 1)
            rna = rna + '.' + path
            path = '[' + rem
        elif '[' in path:
            path, rem = path.rsplit('[', 1)
        
        if parent_prop.rna == rna and parent_prop.path == path:
            self.report({'ERROR'}, 'MustardUI - Can not link a property with itself.')
            return {'FINISHED'}
        
        if not mustardui_check_cp(obj, rna, path):
            self.report({'ERROR'}, 'MustardUI - Can not link a property already added.')
            return {'FINISHED'}
        
        switched_warning = False
        for check_prop in custom_props:
            for i in range(0,len(check_prop.linked_properties)):
                if check_prop.linked_properties[i].rna == rna and check_prop.linked_properties[i].path == path:
                    switched_warning = True
                    check_prop.linked_properties.remove(i)
        
        # Add driver
        if prop.is_animatable:
            mustardui_add_driver(obj, rna, path, prop, parent_prop.prop_name)
        
        # Add linked property to list
        if not (rna, path) in [(x.rna, x.path) for x in parent_prop.linked_properties]:
            lp = parent_prop.linked_properties.add()
            lp.rna = rna
            lp.path = path
        else:
            self.report({'ERROR'}, 'MustardUI - An error occurred while linking the property.')
            return {'FINISHED'}
        
        obj.update_tag()
        
        if switched_warning:
            self.report({'WARNING'}, 'MustardUI - Switched linked property.')
        else:
            self.report({'INFO'}, 'MustardUI - Property linked.')
    
        return {'FINISHED'}

class WM_MT_button_context(Menu):
    bl_label = "Custom Action"

    def draw(self, context):
        pass

# Operator to create the list of sections when right clicking on a property
class OUTLINER_MT_MustardUI_PropertySectionMenu(bpy.types.Menu):
    bl_idname = 'OUTLINER_MT_MustardUI_PropertySectionMenu'
    bl_label = 'Add to MustardUI (Section)'

    def draw(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config = 1)
        rig_settings = obj.MustardUI_RigSettings
        
        layout = self.layout
        
        for sec in rig_settings.body_custom_properties_sections:
            op = layout.operator(MustardUI_Property_MenuAdd.bl_idname, text=sec.name, icon=sec.icon)
            op.section = sec.name
            op.outfit = ""
            op.outfit_piece = ""
            op.hair = ""

# Operators to create the list of outfits when right clicking on a property
class OUTLINER_MT_MustardUI_PropertyOutfitPieceMenu(bpy.types.Menu):
    bl_idname = 'OUTLINER_MT_MustardUI_PropertyOutfitPieceMenu'
    bl_label = 'Add to MustardUI Outfit'

    def draw(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config = 1)
        rig_settings = obj.MustardUI_RigSettings
        
        layout = self.layout
        
        if context.mustardui_propertyoutfitmenu_sel != rig_settings.extras_collection:
            op = layout.operator(MustardUI_Property_MenuAdd.bl_idname, text="Add as Global Outfit property", icon = "TRIA_RIGHT")
            op.section = ""
            op.outfit = context.mustardui_propertyoutfitmenu_sel.name
            op.outfit_piece = ""
            op.hair = ""
        
        for obj in context.mustardui_propertyoutfitmenu_sel.objects:
            op = layout.operator(MustardUI_Property_MenuAdd.bl_idname, icon = "DOT", text=obj.name[len(context.mustardui_propertyoutfitmenu_sel.name+ " - "):] if rig_settings.model_MustardUI_naming_convention else obj.name)
            op.section = ""
            op.outfit = context.mustardui_propertyoutfitmenu_sel.name
            op.outfit_piece = obj.name
            op.hair = ""

# Operators to create the list of outfits when right clicking on a property
class OUTLINER_MT_MustardUI_PropertyOutfitMenu(bpy.types.Menu):
    bl_idname = 'OUTLINER_MT_MustardUI_PropertyOutfitMenu'
    bl_label = 'Add to MustardUI Outfit'

    def draw(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config = 1)
        rig_settings = obj.MustardUI_RigSettings
        
        layout = self.layout
        
        outfit_indices = []
        for i in range(0, len(rig_settings.outfits_collections)):
            if rig_settings.outfits_collections[i].collection != None:
                outfit_indices.append(i)
        
        for i in outfit_indices:
            layout.context_pointer_set("mustardui_propertyoutfitmenu_sel", rig_settings.outfits_collections[i].collection)
            layout.menu(OUTLINER_MT_MustardUI_PropertyOutfitPieceMenu.bl_idname, icon = "MOD_CLOTH", text=rig_settings.outfits_collections[i].collection.name[len(rig_settings.model_name):] if rig_settings.model_MustardUI_naming_convention else rig_settings.outfits_collections[i].collection.name)
        if rig_settings.extras_collection != None:
            if len(rig_settings.extras_collection.objects) > 0:
                layout.context_pointer_set("mustardui_propertyoutfitmenu_sel", rig_settings.extras_collection)
                layout.menu(OUTLINER_MT_MustardUI_PropertyOutfitPieceMenu.bl_idname, icon = "PLUS", text=rig_settings.extras_collection.name[len(rig_settings.model_name):] if rig_settings.model_MustardUI_naming_convention else rig_settings.extras_collection.name)

# Operators to create the list of outfits when right clicking on a property
class OUTLINER_MT_MustardUI_PropertyHairMenu(bpy.types.Menu):
    bl_idname = 'OUTLINER_MT_MustardUI_PropertyHairMenu'
    bl_label = 'Add to MustardUI Hair'

    def draw(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config = 1)
        rig_settings = obj.MustardUI_RigSettings
        
        layout = self.layout
        
        for obj in [x for x in rig_settings.hair_collection.objects if x.type == "MESH"]:
            op = layout.operator(MustardUI_Property_MenuAdd.bl_idname, icon = "STRANDS", text=obj.name[len(rig_settings.hair_collection.name):] if rig_settings.model_MustardUI_naming_convention else obj.name)
            op.section = ""
            op.outfit = ""
            op.outfit_piece = ""
            op.hair = obj.name
   
def mustardui_property_menuadd(self, context):
    
    res, obj = mustardui_active_object(context, config = 1)
    
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
        for collection in [x for x in rig_settings.outfits_collections if x.collection != None]:
            for object in collection.collection.objects:
                if object == context.active_object:
                    op = layout.operator(MustardUI_Property_MenuAdd.bl_idname, text = "Add to " + context.active_object.name, icon="MOD_CLOTH")
                    op.section = ""
                    op.outfit = collection.collection.name
                    op.outfit_piece = object.name
                    op.hair = ""
                    break
        if rig_settings.extras_collection != None:
            if len(rig_settings.extras_collection.objects) > 0:
                for object in rig_settings.extras_collection.objects:
                    if object == context.active_object:
                        op = layout.operator(MustardUI_Property_MenuAdd.bl_idname, text = "Add to " + context.active_object.name, icon="PLUS")
                        op.section = ""
                        op.outfit = rig_settings.extras_collection.name
                        op.outfit_piece = object.name
                        op.hair = ""
                        break
        if rig_settings.hair_collection != None:
            if len(rig_settings.hair_collection.objects) > 0:
                for object in [x for x in rig_settings.hair_collection.objects if x.type == "MESH"]:
                    if object == context.active_object:
                        op = layout.operator(MustardUI_Property_MenuAdd.bl_idname, text = "Add to " + context.active_object.name, icon="STRANDS")
                        op.section = ""
                        op.outfit = ""
                        op.outfit_piece = ""
                        op.hair = object.name
                        break
        
        layout.separator()
        
        if len(rig_settings.body_custom_properties_sections)>0:
            layout.menu(OUTLINER_MT_MustardUI_PropertySectionMenu.bl_idname)
        if len([x for x in rig_settings.outfits_collections if x.collection != None])>0:
            layout.menu(OUTLINER_MT_MustardUI_PropertyOutfitMenu.bl_idname, icon="MOD_CLOTH")
        if rig_settings.hair_collection != None:
            if len(rig_settings.hair_collection.objects) > 0:
                layout.menu(OUTLINER_MT_MustardUI_PropertyHairMenu.bl_idname, icon="STRANDS")

def mustardui_property_link(self, context):
    
    res, obj = mustardui_active_object(context, config = 1)
    
    if hasattr(context, 'button_prop') and res:
        layout = self.layout
        self.layout.menu(MUSTARDUI_MT_Property_LinkMenu.bl_idname, icon="LINKED")

# Operator to create the list of sections when right clicking on the property -> Link to property
class MUSTARDUI_MT_Property_LinkMenu(bpy.types.Menu):
    bl_idname = 'MUSTARDUI_MT_Property_LinkMenu'
    bl_label = 'Link to Property'

    @classmethod
    def poll(cls, context):
        
        res, arm = mustardui_active_object(context, config = 1)
        return res

    def draw(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config = 1)
        rig_settings = obj.MustardUI_RigSettings
        
        layout = self.layout
        
        no_prop = True
        
        body_props = [x for x in obj.MustardUI_CustomProperties if x.is_animatable]
        if len(body_props)>0:
            layout.label(text = "Body", icon = "OUTLINER_OB_ARMATURE")
        for prop in sorted(body_props, key = lambda x:x.name):
            op = layout.operator(MustardUI_Property_MenuLink.bl_idname, text=prop.name, icon=prop.icon)
            op.parent_rna = prop.rna
            op.parent_path = prop.path
            op.type = "BODY"
            no_prop = False
        
        outfit_props = [x for x in obj.MustardUI_CustomPropertiesOutfit if x.is_animatable and x.outfit != rig_settings.extras_collection and x.outfit != None]
        if len(outfit_props) > 0 and len(body_props) > 0:
            layout.separator()
            layout.label(text = "Outfits", icon = "MOD_CLOTH")
        for prop in sorted(sorted(outfit_props, key = lambda x:x.name), key=lambda x:x.outfit.name):
            outfit_name = prop.outfit.name[len(rig_settings.model_name + " "):] if rig_settings.model_MustardUI_naming_convention else prop.outfit.name
            if prop.outfit_piece != None:
                outfit_piece_name = prop.outfit_piece.name[len(prop.outfit.name + " - "):] if rig_settings.model_MustardUI_naming_convention else prop.outfit.name
                outfit_name = outfit_name + " - " + outfit_piece_name
            op = layout.operator(MustardUI_Property_MenuLink.bl_idname, text=outfit_name + " - " + prop.name, icon=prop.icon)
            op.parent_rna = prop.rna
            op.parent_path = prop.path
            op.type = "OUTFIT"
            no_prop = False
        
        extras_props = [x for x in obj.MustardUI_CustomPropertiesOutfit if x.is_animatable and x.outfit == rig_settings.extras_collection]
        if len(extras_props) > 0 and len(body_props) > 0:
            layout.separator()
            layout.label(text = "Extras", icon = "PLUS")
        for prop in sorted(extras_props, key = lambda x:x.name):
            outfit_name = prop.outfit_piece.name[len(rig_settings.extras_collection.name + " - "):] if rig_settings.model_MustardUI_naming_convention else prop.outfit_piece.name
            op = layout.operator(MustardUI_Property_MenuLink.bl_idname, text=outfit_name + " - " + prop.name, icon=prop.icon)
            op.parent_rna = prop.rna
            op.parent_path = prop.path
            op.type = "OUTFIT"
            no_prop = False
        
        hair_props = [x for x in obj.MustardUI_CustomPropertiesHair if x.is_animatable and x.hair != None]
        if len(hair_props) > 0 and (len(outfit_props) > 0 or len(body_props) > 0):
            layout.separator()
            layout.label(text = "Hair", icon = "STRANDS")
        for prop in sorted(hair_props, key = lambda x:x.name):
            hair_name = prop.hair.name[len(rig_settings.hair_collection.name + " "):] if rig_settings.model_MustardUI_naming_convention else prop.hair.name
            op = layout.operator(MustardUI_Property_MenuLink.bl_idname, text=hair_name + " - " + prop.name, icon=prop.icon)
            op.parent_rna = prop.rna
            op.parent_path = prop.path
            op.type = "HAIR"
            no_prop = False
        
        if no_prop:
            layout.label(text="No properties found")

class MUSTARDUI_UL_Property_UIList(bpy.types.UIList):
    """UIList for custom properties."""

    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_propname, index):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config = 1)
        
        # Make sure your code supports all 3 layout types
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item, 'name', text ="", icon = item.icon if item.icon != "NONE" else "DOT", emboss=False, translate=False)
            layout.scale_x = 1.0
            
            row = layout.row(align = True)
            
            if settings.debug:
                if item.is_animatable:
                    row.label(text="", icon="ANIM")
                else:
                    row.label(text="", icon="BLANK1")
                
                try:
                    if item.is_animatable:
                        obj.id_properties_ui(item.prop_name)
                    else:
                        eval(mustardui_cp_path(item.rna,item.path))
                    row.label(text="", icon="BLANK1")
                except:
                    row.label(text="", icon="ERROR")
            
            if item.section == "":
                row.label(text="", icon = "LIBRARY_DATA_BROKEN")
            else:
                row.label(text="", icon="BLANK1")
            
            if len(item.linked_properties) > 0:
                row.label(text="", icon="LINK_BLEND")
            else:
                row.label(text="", icon="BLANK1")
                
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.prop(item, 'name', text ="", icon = item.icon if item.icon != "NONE" else "DOT", emboss=False, translate=False)

class MUSTARDUI_UL_Property_UIListOutfits(bpy.types.UIList):
    """UIList for outfits custom properties."""

    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_propname, index):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config = 1)
        rig_settings = obj.MustardUI_RigSettings
        
        # Make sure your code supports all 3 layout types
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item, 'name', text ="", icon = item.icon if item.icon != "NONE" else "DOT", emboss=False, translate=False)
            layout.scale_x = 1.0
            
            row = layout.row(align = True)
            
            if item.outfit != None and item.outfit_piece == None:
                if rig_settings.model_MustardUI_naming_convention:
                    row.label(text=item.outfit.name[len(rig_settings.model_name) + 1:])
                else:
                    row.label(text=item.outfit.name)
            elif item.outfit != None and item.outfit_piece != None:
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
                        eval(mustardui_cp_path(item.rna,item.path))
                    row.label(text="", icon="BLANK1")
                except:
                    row.label(text="", icon="ERROR")
            
            if len(item.linked_properties) > 0:
                row.label(text="", icon="LINK_BLEND")
            else:
                row.label(text="", icon="BLANK1")
                
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.prop(item, 'name', text ="", icon = item.icon if item.icon != "NONE" else "DOT", emboss=False, translate=False)

class MUSTARDUI_UL_Property_UIListHair(bpy.types.UIList):
    """UIList for outfits custom properties."""

    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_propname, index):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config = 1)
        rig_settings = obj.MustardUI_RigSettings
        
        # Make sure your code supports all 3 layout types
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item, 'name', text ="", icon = item.icon if item.icon != "NONE" else "DOT", emboss=False, translate=False)
            layout.scale_x = 1.0
            
            row = layout.row(align = True)
            
            if item.hair != None:
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
                        eval(mustardui_cp_path(item.rna,item.path))
                    row.label(text="", icon="BLANK1")
                except:
                    row.label(text="", icon="ERROR")
            
            if len(item.linked_properties) > 0:
                row.label(text="", icon="LINK_BLEND")
            else:
                row.label(text="", icon="BLANK1")
                
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.prop(item, 'name', text ="", icon = item.icon if item.icon != "NONE" else "DOT", emboss=False, translate=False)

class MustardUI_Property_Remove(bpy.types.Operator):
    """Remove the selected property from the list.\nType"""
    bl_idname = "mustardui.property_remove"
    bl_label = "Remove property"
    
    type: bpy.props.EnumProperty(default = "BODY",
                        items = (("BODY", "Body", ""), ("OUTFIT", "Outfit", ""), ("HAIR", "Hair", "")))
    
    @classmethod
    def poll(cls, context):
        
        res, obj = mustardui_active_object(context, config = 1)
        return obj != None
    
    def execute(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config = 1)
        uilist, index = mustardui_choose_cp(obj, self.type, context.scene)
        
        if len(uilist) <= index:
            return{'FINISHED'}
        
        # Remove custom property and driver
        mustardui_clean_prop(obj, uilist, index, settings)
        
        uilist.remove(index)
        index = min(max(0, index - 1), len(uilist) - 1)
        mustardui_update_index_cp(self.type, context.scene, index)
        
        obj.update_tag()
        
        return{'FINISHED'}

class MustardUI_Property_Switch(bpy.types.Operator):
    """Move the selected property in the list.\nType"""

    bl_idname = "mustardui.property_switch"
    bl_label = "Move property"
    
    type: bpy.props.EnumProperty(default = "BODY",
                        items = (("BODY", "Body", ""), ("OUTFIT", "Outfit", ""), ("HAIR", "Hair", "")))
    direction: bpy.props.EnumProperty(items=(('UP', 'Up', ""),
                                              ('DOWN', 'Down', ""),))

    @classmethod
    def poll(cls, context):
        
        res, obj = mustardui_active_object(context, config = 1)
        return obj != None

    def move_index(self, uilist, index):
        """ Move index of an item render queue while clamping it. """

        list_length = len(uilist) - 1  # (index starts at 0)
        new_index = index + (-1 if self.direction == 'UP' else 1)

        return max(0, min(new_index, list_length))

    def execute(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config = 1)
        uilist, index = mustardui_choose_cp(obj, self.type, context.scene)
        
        if len(uilist) <= index:
            return{'FINISHED'}

        neighbour = index + (-1 if self.direction == 'UP' else 1)
        uilist.move(neighbour, index)
        index = self.move_index(uilist, index)
        mustardui_update_index_cp(self.type, context.scene, index)

        return{'FINISHED'}

class MustardUI_Property_Settings(bpy.types.Operator):
    """Modify the property settings.\nType"""
    bl_idname = "mustardui.property_settings"
    bl_label = "Property settings"
    bl_icon = "PREFERENCES"
    bl_options = {'UNDO'}
    
    name : bpy.props.StringProperty(name='Name',
                        description="Name of the property")
    icon : bpy.props.EnumProperty(name='Icon',
                        description="Icon of the property",
                        items = mustardui_icon_list)
    description : bpy.props.StringProperty(name='Description',
                        description="Choose the name of the section")
    force_type: bpy.props.EnumProperty(name = "Force Property Type",
                        default="None",
                        description="Force the type of the property to be boolean or integer. If None, the original type is preserved",
                        items=(("None", "None", "None"), ("Int", "Int", "Int"), ("Bool", "Bool", "Bool")))
    type: bpy.props.EnumProperty(default = "BODY",
                        items = (("BODY", "Body", ""), ("OUTFIT", "Outfit", ""), ("HAIR", "Hair", "")))
    
    max_int : bpy.props.IntProperty(name = "Maximum value")
    min_int : bpy.props.IntProperty(name = "Minimum value")
    max_float : bpy.props.FloatProperty(name = "Maximum value")
    min_float : bpy.props.FloatProperty(name = "Minimum value")
    default_int : bpy.props.IntProperty(name = "Default value")
    default_bool : bpy.props.BoolProperty(name = "Default value")
    default_float : bpy.props.FloatProperty(name = "Default value")
    default_array: bpy.props.StringProperty(name = "Default array value")
    
    default_color: bpy.props.FloatVectorProperty(name = "Default color value",
                        size = 4,
                        subtype = "COLOR",
                        min = 0., max = 1.,
                        default = [0.,0.,0.,1.],
                        description = "")
    
    @classmethod
    def poll(cls, context):
        
        res, obj = mustardui_active_object(context, config = 1)
        return obj != None
    
    def execute(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config = 1)
        custom_props, index = mustardui_choose_cp(obj, self.type, context.scene)
        custom_prop = custom_props[index]
        
        if self.name == "":
            self.report({'ERROR'}, 'MustardUI - Can not rename a property with an empty name.')
            return {'FINISHED'}
        
        prop_type = custom_prop.type
        if prop_type == "FLOAT" and (isinstance(self.max_float, int) or isinstance(self.min_float, int) or isinstance(self.default_float, int)):
            self.report({'ERROR'}, 'MustardUI - Can not change type of the custom property.')
            return {'FINISHED'}
        
        if custom_prop.array_length > 0 and custom_prop.subtype != "COLOR" and len(eval(self.default_array)) != custom_prop.array_length:
            self.report({'ERROR'}, 'MustardUI - Can not change default with different vector dimension.')
            return {'FINISHED'}
        
        custom_prop.name = self.name
        custom_prop.icon = self.icon
        
        if custom_prop.is_animatable:
            
            prop_name = custom_prop.prop_name
            prop_array = custom_prop.array_length > 0
            prop_subtype = custom_prop.subtype
            
            ui_data = obj.id_properties_ui(prop_name)
            ui_data_dict = ui_data.as_dict()
            
            custom_prop.is_bool = self.force_type == "Bool" or custom_prop.type == "BOOLEAN"
            
            if prop_type == "FLOAT":
                custom_prop.force_type = self.force_type
            
            if custom_prop.is_bool:
                ui_data.update(min=0,max=1)
                obj[prop_name] = min(1,max(0,int(obj[prop_name])))
            elif not custom_prop.is_bool and prop_type == "FLOAT" and self.force_type == "None":
                
                ui_data.clear()
                
                rna_idprop_ui_create(obj, prop_name,
                                    default=self.default_float if custom_prop.array_length == 0 else eval(self.default_array) if prop_subtype != "COLOR" else self.default_color,
                                    min=self.min_float if prop_subtype != "COLOR" else 0.,
                                    max=self.max_float if prop_subtype != "COLOR" else 1.,
                                    description=self.description,
                                    overridable=True,
                                    subtype=custom_prop.subtype if prop_subtype != "FACTOR" else None)
                
                custom_prop.description = self.description
                custom_prop.min_float = self.min_float
                custom_prop.max_float = self.max_float
                if custom_prop.array_length == 0:
                    custom_prop.default_float = self.default_float
                    obj[prop_name] = float(obj[prop_name])
                else:
                    custom_prop.default_array = self.default_array if prop_subtype != "COLOR" else str(ui_data.as_dict()['default'])
                custom_prop.is_bool = False
            elif not custom_prop.is_bool and (prop_type == "INT" or self.force_type == "Int"):
                
                ui_data.clear()
                
                rna_idprop_ui_create(obj, prop_name,
                                    default=self.default_int if custom_prop.array_length == 0 else eval(self.default_array),
                                    min=self.min_int,
                                    max=self.max_int,
                                    description=self.description,
                                    overridable=True,
                                    subtype=custom_prop.subtype if prop_subtype != "FACTOR" else None)
                
                custom_prop.description = self.description
                custom_prop.min_int = self.min_int
                custom_prop.max_int = self.max_int
                if custom_prop.array_length == 0:
                    custom_prop.default_int = self.default_int
                    obj[prop_name] = int(obj[prop_name])
                else:
                    custom_prop.default_array = self.default_array
                custom_prop.is_bool = False
            else:
                ui_data.update(description = custom_prop.description)
                custom_prop.description = self.description
                
        obj.update_tag()
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config = 1)
        custom_props, index = mustardui_choose_cp(obj, self.type, context.scene)
        
        if len(custom_props) <= index:
            return {'FINISHED'}
        
        custom_prop = custom_props[index]
        prop_name = custom_prop.prop_name
        prop_array = custom_prop.array_length > 0
        
        self.name = custom_prop.name
        self.icon = custom_prop.icon
        self.description = custom_prop.description
        self.default_array = "[]"
        
        if custom_prop.is_animatable:
            
            prop_type = custom_prop.type
            self.force_type = custom_prop.force_type
            
            try:
                ui_data = obj.id_properties_ui(custom_prop.prop_name)
                ui_data_dict = ui_data.as_dict()
            except:
                self.report({'ERROR'}, 'MustardUI - An error occurred while retrieving UI data. Try to rebuild properties to solve this')
                return {'FINISHED'}
            
            if not custom_prop.is_bool and (prop_type == "INT" or self.force_type == "Int"):
                self.max_int = ui_data_dict['max']
                self.min_int = ui_data_dict['min']
                if custom_prop.array_length == 0:
                    self.default_int = ui_data_dict['default']
                else:
                    self.default_array = str(ui_data_dict['default'])
            elif not custom_prop.is_bool and prop_type == "FLOAT" and self.force_type == "None":
                self.max_float = ui_data_dict['max']
                self.min_float = ui_data_dict['min']
                if self.min_float == self.max_float:
                    self.max_float += 1
                if custom_prop.array_length > 0:
                    if custom_prop.subtype != "COLOR":
                        self.default_array = str(ui_data_dict['default'])
                    else:
                        self.default_color = ui_data_dict['default']
                else:
                    self.default_float = ui_data_dict['default']
        
        return context.window_manager.invoke_props_dialog(self, width = 550 if settings.debug else 450)
            
    def draw(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config = 1)
        custom_props, index = mustardui_choose_cp(obj, self.type, context.scene)
        custom_prop = custom_props[index]
        prop_cp_type = custom_prop.cp_type
        prop_name = custom_prop.prop_name
        prop_array = custom_prop.array_length > 0
        
        scale = 3.0
        
        layout = self.layout
        
        box = layout.box()
        
        row=box.row()
        row.label(text="Name:")
        row.scale_x=scale
        row.prop(self, "name", text="")
        
        row=box.row()
        row.label(text="Icon:")
        row.scale_x=scale
        row.prop(self, "icon", text="")
        
        if prop_cp_type == "OUTFIT":
            row=box.row()
            row.label(text="Outfit:")
            row.scale_x=scale
            row.prop(custom_prop, "outfit", text="")
            
            row=box.row()
            row.label(text="Outfit piece:")
            row.scale_x=scale
            row.prop(custom_prop, "outfit_piece", text="")
        
        if prop_cp_type == "HAIR":
            row=box.row()
            row.label(text="Hair:")
            row.scale_x=scale
            row.prop(custom_prop, "hair", text="")
        
        if custom_prop.is_animatable:
            
            prop_type = custom_prop.type
            
            if not custom_prop.is_bool:
                
                box = layout.box()
            
                row=box.row()
                row.label(text="Description:")
                row.scale_x=scale
                row.prop(self, "description", text="")
                
                if prop_type == "FLOAT" and custom_prop.subtype != "COLOR":
                    
                    if custom_prop.array_length == 0:
                        row=box.row()
                        row.label(text="Force type:")
                        row.scale_x=scale
                        row.prop(self, "force_type", text="")
                    
                        if self.force_type == "None":
                    
                            row=box.row()
                            row.label(text="Default:")
                            row.scale_x=scale
                            row.prop(self, "default_float", text="")
                    else:    
                        row=box.row()
                        row.label(text="Default:")
                        row.scale_x=scale
                        row.prop(self, "default_array", text="")
                    
                    if self.force_type == "None":
                        
                        row=box.row()
                        row.label(text="Min / Max")
                        row.scale_x=scale
                        row2=row.row(align=True)
                        row2.prop(self, "min_float", text="")
                        row2.prop(self, "max_float", text="")
                
                if custom_prop.subtype == "COLOR":
                    row=box.row()
                    row.label(text="Default:")
                    row.scale_x=scale
                    row.prop(self, "default_color", text="")
                
                if prop_type == "INT" or self.force_type == "Int":
                    
                    row=box.row()
                    row.label(text="Default:")
                    row.scale_x=scale
                    row.prop(self, "default_int", text="")
                    
                    row=box.row()
                    row.label(text="Min / Max")
                    row.scale_x=scale
                    row2=row.row(align=True)
                    row2.prop(self, "min_int", text="")
                    row2.prop(self, "max_int", text="")
        
            elif custom_prop.is_bool and prop_type == "FLOAT":
                box = layout.box()
                row=box.row()
                row.label(text="Force type:")
                row.scale_x=scale
                row.prop(self, "force_type", text="")
                
                if custom_prop.force_type != self.force_type and custom_prop.force_type == "Bool":
                    box.label(text="Re-open this Settings panel to change settings", icon="ERROR")
            
            if len(custom_prop.linked_properties)>0:
                
                layout.label(text="Linked Properties", icon="LINK_BLEND")
                box = layout.box()
                
                for lp in custom_prop.linked_properties:
                    
                    row = box.row()
                    row.label(text=mustardui_cp_path(lp.rna, lp.path), icon = "RNA")
                    op = row.operator('mustardui.property_removelinked', text="", icon ="X")
                    op.rna = lp.rna
                    op.path = lp.path
                    op.type = self.type
        
        if settings.debug:
            
            box = layout.box()
            
            row=box.row()
            row.label(text="Property name: "+ custom_prop.prop_name, icon="PROPERTIES")
            
            row=box.row()
            row.label(text=custom_prop.rna, icon="RNA")
            

class MustardUI_Property_RemoveLinked(bpy.types.Operator):
    """Remove the linked property from the list.\nType"""
    bl_idname = "mustardui.property_removelinked"
    bl_label = "Remove linked property"
    
    rna: bpy.props.StringProperty()
    path: bpy.props.StringProperty()
    
    type: bpy.props.EnumProperty(default = "BODY",
                        items = (("BODY", "Body", ""), ("OUTFIT", "Outfit", ""), ("HAIR", "Hair", "")))

    def clean_prop(self, obj, uilist, index):
        
        # Remove linked property driver
        try:
            driver_object = eval(self.rna)
            driver_object.driver_remove(self.path)
            return True
        except:
            return False
    
    @classmethod
    def poll(cls, context):
        
        res, obj = mustardui_active_object(context, config = 1)
        return obj != None
    
    def execute(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config = 1)
        uilist, index = mustardui_choose_cp(obj, self.type, context.scene)
        
        # Remove custom property and driver
        driver_removed = self.clean_prop(obj, uilist, index)
        
        # Find the linked property index to remove it from the list
        i = -1
        for lp in uilist[index].linked_properties:
            i +=1
            if lp.rna == self.rna and lp.path == self.path:
                break
        
        if i != -1:
            uilist[index].linked_properties.remove(i)
        
        obj.update_tag()
        
        if not driver_removed:
            self.report({'WARNING'}, 'MustardUI - The linked property was removed from the UI, but the associated driver was not found: you might need to remove it manually.')
        
        return{'FINISHED'}          

class MustardUI_Property_Rebuild(bpy.types.Operator):
    """Rebuild all drivers and custom properties. This can be used if the properties aren't working or if the properties max/min/default/descriptions are broken"""
    bl_idname = "mustardui.property_rebuild"
    bl_label = "Rebuild"
    
    def add_driver(self, obj, rna, path, prop_name):
        
        driver_object = eval(rna)
        driver_object.driver_remove(path)
        driver = driver_object.driver_add(path)
        
        try:
            array_length = len(eval(mustardui_cp_path(rna,path)))
        except:
            array_length = 0
        
        # No array property
        if array_length == 0:
            driver = driver.driver
            driver.type = "AVERAGE"
            var = driver.variables.new()
            var.name                 = 'mustardui_var'
            var.targets[0].id_type   = "ARMATURE"
            var.targets[0].id        = obj
            var.targets[0].data_path = '["' + prop_name + '"]'
        
        # Array property
        else:
            for i in range(0,array_length):
                driver[i] = driver[i].driver
                driver[i].type = "AVERAGE"
                
                var = driver[i].variables.new()
                var.name                 = 'mustardui_var'
                var.targets[0].id_type   = "ARMATURE"
                var.targets[0].id        = obj
                var.targets[0].data_path = '["' + prop_name + '"]' + '['+ str(i) + ']'
        
        return
    
    @classmethod
    def poll(cls, context):
        
        res, arm = mustardui_active_object(context, config = 0)
        return res
    
    def execute(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config = 0)
        
        # Rebuild all custom properties
        custom_props = [(x,0) for x in obj.MustardUI_CustomProperties]
        for x in obj.MustardUI_CustomPropertiesOutfit:
            custom_props.append((x,1))
        for x in obj.MustardUI_CustomPropertiesHair:
            custom_props.append((x,2))
        
        errors = 0
        
        to_remove = []
        
        for custom_prop, prop_type in [x for x in custom_props if x[0].is_animatable]:
            
            prop_name = custom_prop.prop_name
            
            if prop_name in obj.keys():
                del obj[prop_name]
            
            if custom_prop.is_bool or custom_prop.force_type == "Bool":
                rna_idprop_ui_create(obj, prop_name, default=int(eval(mustardui_cp_path(custom_prop.rna,custom_prop.path))),
                                    min=0,
                                    max=1,
                                    description=custom_prop.description,
                                    overridable=True)
            
            elif not custom_prop.is_bool and custom_prop.type == "FLOAT" and custom_prop.force_type == "None":
                rna_idprop_ui_create(obj, prop_name,
                                    default=custom_prop.default_float if custom_prop.array_length == 0 else eval(custom_prop.default_array),
                                    min=custom_prop.min_float if custom_prop.subtype != "COLOR" else 0.,
                                    max=custom_prop.max_float if custom_prop.subtype != "COLOR" else 1.,
                                    description=custom_prop.description,
                                    overridable=True,
                                    subtype=custom_prop.subtype if custom_prop.subtype != "FACTOR" else None)
                            
            elif not custom_prop.is_bool and (custom_prop.type == "INT" or custom_prop.force_type == "Int"):
                rna_idprop_ui_create(obj, prop_name,
                                    default=int(custom_prop.default_int) if custom_prop.array_length == 0 else eval(custom_prop.default_array),
                                    min=custom_prop.min_int,
                                    max=custom_prop.max_int,
                                    description=custom_prop.description,
                                    overridable=True,
                                    subtype=custom_prop.subtype if custom_prop.subtype != "FACTOR" else None)
            
            else:
                rna_idprop_ui_create(obj, prop_name,
                                    default=eval(mustardui_cp_path(custom_prop.rna,custom_prop.path)),
                                    description=custom_prop.description,
                                    overridable=True)
            
            # Rebuilding custom properties and their linked properties drivers
            try:
                self.add_driver(obj, custom_prop.rna, custom_prop.path, custom_prop.prop_name)
                for linked_custom_prop in custom_prop.linked_properties:
                    self.add_driver(obj, linked_custom_prop.rna, linked_custom_prop.path, custom_prop.prop_name)
            except:
                errors += 1
                
                if "[" in custom_prop.path and "]" in custom_prop.path:
                    print('MustardUI - Something went wrong when trying to restore ' + custom_prop.name + ' at \'' + custom_prop.rna + custom_prop.path + '\'. This custom property will be removed.')
                else:
                    print('MustardUI - Something went wrong when trying to restore ' + custom_prop.name + ' at \'' + custom_prop.rna + '.' + custom_prop.path + '\'. This custom property will be removed.')
                
                if prop_type == 0:
                    uilist = obj.MustardUI_CustomProperties
                elif prop_type == 1:
                    uilist = obj.MustardUI_CustomPropertiesOutfit
                else:
                    uilist = obj.MustardUI_CustomPropertiesHair
                
                for i in range(0, len(uilist)):
                    if uilist[i].rna == custom_prop.rna and uilist[i].path == custom_prop.path:
                        break
                
                mustardui_clean_prop(obj, uilist, i, settings)
                to_remove.append((i,prop_type))
        
        for i, prop_type in reversed(to_remove):
            
            if prop_type == 0:
                uilist = obj.MustardUI_CustomProperties
            elif prop_type == 1:
                uilist = obj.MustardUI_CustomPropertiesOutfit
            else:
                uilist = obj.MustardUI_CustomPropertiesHair
            
            uilist.remove(i)        
        
        obj.update_tag()
        
        if errors > 0:
            if errors > 1:
                self.report({'WARNING'}, 'MustardUI - ' + str(errors) + ' custom properties were corrupted and deleted. Check the console for more infos.')
            else:
                self.report({'WARNING'}, 'MustardUI - A custom property was corrupted and deleted. Check the console for more infos.')
        else:
            self.report({'INFO'}, 'MustardUI - All the drivers and custom properties rebuilt.')
        
        return {'FINISHED'}

# Operator to add the right click button on properties
class MustardUI_Property_SmartCheck(bpy.types.Operator):
    """Check if some properties respect the MustardUI Int/Float/Bool convention, and automatically add them as additional properties"""
    bl_idname = "mustardui.property_smartcheck"
    bl_label = "Smart Check"
    bl_options = {'UNDO'}
    
    def add_driver(self, obj, rna, path, prop_name):
        
        driver_object = eval(rna)
        driver_object.driver_remove(path)
        driver = driver_object.driver_add(path)
        
        try:
            array_length = len(eval(mustardui_cp_path(rna,path)))
        except:
            array_length = 0
        
        # No array property
        if array_length == 0:
            driver = driver.driver
            driver.type = "AVERAGE"
            var = driver.variables.new()
            var.name                 = 'mustardui_var'
            var.targets[0].id_type   = "ARMATURE"
            var.targets[0].id        = obj
            var.targets[0].data_path = '["' + prop_name + '"]'
        
        # Array property
        else:
            for i in range(0,array_length):
                driver[i] = driver[i].driver
                driver[i].type = "AVERAGE"
                
                var = driver[i].variables.new()
                var.name                 = 'mustardui_var'
                var.targets[0].id_type   = "ARMATURE"
                var.targets[0].id        = obj
                var.targets[0].data_path = '["' + prop_name + '"]' + '['+ str(i) + ']'
        
        return
    
    def link_property(self, obj, rna, path, parent_prop, custom_props):
        
        for check_prop in custom_props:
            for i in range(0,len(check_prop.linked_properties)):
                if check_prop.linked_properties[i].rna == rna and check_prop.linked_properties[i].path == path:
                    check_prop.linked_properties.remove(i)
        
        # Add driver
        try:
            self.add_driver(obj, rna, path, parent_prop.prop_name)
        except:
            print("MustardUI - Could not link property to " + parent_prop.prop_name)
        
        # Add linked property to list
        if not rna in [x.rna for x in parent_prop.linked_properties] or not path in [x.path for x in parent_prop.linked_properties]:
            lp = parent_prop.linked_properties.add()
            lp.rna = rna
            lp.path = path
        
        return
    
    def add_custom_property(self, obj, rna, path, name, type, custom_props, sections_to_recover):
        
        # Check if the property was already added. If yes, link it to the one already added
        for cp in custom_props:
            if cp.rna == rna and cp.path == path:
                if cp.prop_name in obj.keys():
                    return
            if cp.name == name:
                self.link_property(obj, rna, path, cp, custom_props)
                return
        
        # Add custom property to the object
        prop_name = name
            
        add_string_num = 1
        while prop_name in obj.keys():
            add_string_num += 1
            prop_name = name + ' ' + str(add_string_num)
        
        obj[prop_name] = eval(rna + "." + path)
        
        # Change custom properties settings
        rna_idprop_ui_create(obj, prop_name,
                            default=int(eval(rna + "." + path)) if type in ["INT", "BOOLEAN"] else eval(rna + "." + path),
                            min=0 if type in ["INT", "BOOLEAN"] else 0.,
                            max=1 if type in ["INT", "BOOLEAN"] else 1.,
                            overridable=True,
                            subtype="COLOR" if type == "COLOR" else None)
        
        # Add driver
        try:
            self.add_driver(obj, rna, path, prop_name)
        except:
            print("MustardUI - Could not add a driver for " + prop_name)
            del obj[prop_name]
            return
        
        # Add property to the collection of properties
        if not (rna,path) in [(x.rna,x.path) for x in custom_props]:
            
            ui_data = obj.id_properties_ui(prop_name)
            ui_data_dict = ui_data.as_dict()
            
            cp = custom_props.add()
            cp.rna = rna
            cp.path = path
            cp.prop_name = prop_name
            cp.type = "FLOAT" if type == "COLOR" else type
            cp.subtype = "COLOR" if type == "COLOR" else "NONE"
            cp.array_length = 4 if type == "COLOR" else 0
            cp.name = name
            
            cp.is_bool = type == "BOOLEAN"
            if cp.is_bool:
                cp.bool_value = int(eval(mustardui_cp_path(rna,path)))
            
            cp.is_animatable = True
            for cptr in sections_to_recover:
                if cptr[0] == rna and cptr[1] == path:
                    cp.section = cptr[2]
                    break
            
            if 'description' in ui_data_dict.keys():
                cp.description = ui_data_dict['description']
            if 'default' in ui_data_dict.keys() and type != "BOOLEAN":
                if type == "FLOAT":
                    cp.default_float = ui_data_dict['default']
                elif type == "INT":
                    cp.default_int = ui_data_dict['default']
                else:
                    cp.default_array = str(ui_data_dict['default'])
            if 'min' in ui_data_dict.keys() and type != "BOOLEAN":
                if type == "FLOAT":
                    cp.min_float = ui_data_dict['min']
                elif type == "INT":
                    cp.min_int = ui_data_dict['min']
            if 'max' in ui_data_dict.keys() and type != "BOOLEAN":
                if type == "FLOAT":
                    cp.max_float = ui_data_dict['max']
                elif type == "INT":
                    cp.max_int = ui_data_dict['max']
        
        obj.property_overridable_library_set('["'+ prop_name +'"]', True)
        
        return
    
    @classmethod
    def poll(cls, context):
        
        res, arm = mustardui_active_object(context, config = 1)
        return res

    def execute(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config = 1)
        rig_settings = obj.MustardUI_RigSettings
        custom_props = obj.MustardUI_CustomProperties
        
        k = 0
        
        index_to_remove = []
        sections_to_recover = []
        for i in range(0, len(custom_props)):
            if "MustardUI Float - " in custom_props[i].rna or "MustardUI Int - " in custom_props[i].rna or "MustardUI Bool - " in custom_props[i].rna or "MustardUI - " in custom_props[i].rna:
                if custom_props[i].section != "":
                    sections_to_recover.append([custom_props[i].rna, custom_props[i].path, custom_props[i].section])
                index_to_remove.append(i)
        
        for i in reversed(index_to_remove):
            mustardui_clean_prop(obj, custom_props, i, settings)
            custom_props.remove(i)

        for mat in rig_settings.model_body.data.materials:
            for j in range(len(mat.node_tree.nodes)):
                if "MustardUI Float" in mat.node_tree.nodes[j].name and mat.node_tree.nodes[j].type=="VALUE":
                    self.add_custom_property(obj, 'bpy.data.materials[\''+mat.name+'\'].node_tree.nodes[\''+mat.node_tree.nodes[j].name+'\'].outputs[0]', 'default_value', mat.node_tree.nodes[j].name[len("MustardUI Float - "):], "FLOAT", custom_props, sections_to_recover)
                    k = k + 1
                elif "MustardUI Bool" in mat.node_tree.nodes[j].name and mat.node_tree.nodes[j].type=="VALUE":
                    self.add_custom_property(obj, 'bpy.data.materials[\''+mat.name+'\'].node_tree.nodes[\''+mat.node_tree.nodes[j].name+'\'].outputs[0]', 'default_value', mat.node_tree.nodes[j].name[len("MustardUI Bool - "):], "BOOLEAN", custom_props, sections_to_recover)
                    k = k + 1
                elif "MustardUI Int" in mat.node_tree.nodes[j].name and mat.node_tree.nodes[j].type=="VALUE":
                    self.add_custom_property(obj, 'bpy.data.materials[\''+mat.name+'\'].node_tree.nodes[\''+mat.node_tree.nodes[j].name+'\'].outputs[0]', 'default_value', mat.node_tree.nodes[j].name[len("MustardUI Int - "):], "INT", custom_props, sections_to_recover)
                    k = k + 1
                elif "MustardUI" in mat.node_tree.nodes[j].name and mat.node_tree.nodes[j].type=="RGB":
                    self.add_custom_property(obj, 'bpy.data.materials[\''+mat.name+'\'].node_tree.nodes[\''+mat.node_tree.nodes[j].name+'\'].outputs[0]', 'default_value', mat.node_tree.nodes[j].name[len("MustardUI - "):], "COLOR", custom_props, sections_to_recover)
                    k = k + 1
        
        if rig_settings.model_body.data.shape_keys != None:
            for shape_key in rig_settings.model_body.data.shape_keys.key_blocks:
                if "MustardUI Float" in shape_key.name:
                    self.add_custom_property(obj, 'bpy.data.objects[\''+rig_settings.model_body.name+'\'].data.shape_keys.key_blocks[\''+shape_key.name+'\']', 'value', shape_key.name[len("MustardUI Float - "):], "FLOAT", custom_props, sections_to_recover)
                    k = k + 1
                elif "MustardUI Bool" in shape_key.name:
                    self.add_custom_property(obj, 'bpy.data.objects[\''+rig_settings.model_body.name+'\'].data.shape_keys.key_blocks[\''+shape_key.name+'\']', 'value', shape_key.name[len("MustardUI Bool - "):], "BOOL", custom_props, sections_to_recover)
                    k = k + 1
        
        # Update the drivers
        obj.update_tag()
        
        self.report({'INFO'}, 'MustardUI - Smart Check found ' + str(k) + ' properties.')
    
        return {'FINISHED'}


# ------------------------------------------------------------------------
#    Sections for body additional options
# ------------------------------------------------------------------------

# Operator to add a new section
class MustardUI_Body_AddSection(bpy.types.Operator):
    """Add a new Section"""
    bl_idname = "mustardui.body_addsection"
    bl_label = "Add Section"
    bl_icon = "PREFERENCES"
    bl_options = {'UNDO'}
    
    name : bpy.props.StringProperty(name='Name',
                        description="Choose the name of the Section",
                        default = "Section")
    icon : bpy.props.EnumProperty(name='Icon',
                        description="Choose the icon.\nNote that the icon name MUST respect Blender convention. All the icons can be found in the Icon Viewer default Blender addon",
                        items = mustardui_icon_list)
    advanced: bpy.props.BoolProperty(default = False,
                        name = "Advanced",
                        description = "The section will be shown only when Advances Settings is enabled")
    collapsable: bpy.props.BoolProperty(default = False,
                        name = "Collapsable",
                        description = "Add a collapse icon to the section.\nNote that this might give bad UI results if combined with an icon")

    @classmethod
    def poll(cls, context):
        
        res, arm = mustardui_active_object(context, config = 1)
        return res
    
    def execute(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config = 1)
        rig_settings = obj.MustardUI_RigSettings
        
        sec_obj = rig_settings.body_custom_properties_sections
        sec_len = len(rig_settings.body_custom_properties_sections)
        
        if self.name == "":
            
            self.report({'ERROR'}, 'MustardUI - Cannot create sections with this name.')
            return {'FINISHED'}
           
        j = -1
        for el in sec_obj:
            j = j+1
            if el.name == self.name:
                self.report({'WARNING'}, 'MustardUI - Cannot create sections with same name.')
                return {'FINISHED'}
        
        add_item = sec_obj.add()
        add_item.name = self.name
        add_item.icon = self.icon
        add_item.advanced = self.advanced
        add_item.collapsable = self.collapsable
        add_item.id = sec_len
        
        self.report({'INFO'}, 'MustardUI - Section \'' + self.name +'\' created.')
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        
        return context.window_manager.invoke_props_dialog(self)
            
    def draw(self, context):
        
        layout = self.layout
        
        scale = 3.0
        
        row=layout.row()
        row.label(text="Name:")
        row.scale_x=scale
        row.prop(self, "name", text="")
        
        row=layout.row()
        row.label(text="Icon:")
        row.scale_x=scale
        row.prop(self, "icon", text="")
        
        row=layout.row()
        row.prop(self, "advanced", text="")
        row.label(text="Advanced")
        
        row=layout.row()
        row.prop(self, "collapsable", text="")
        row.label(text="Collapsable")

# Delete Section
class MustardUI_Body_DeleteSection(bpy.types.Operator):
    """Delete the selected Section"""
    bl_idname = "mustardui.body_deletesection"
    bl_label = "Delete Section"
    bl_options = {'UNDO'}
    
    name : bpy.props.StringProperty(name='Name',
        description="Choose the name of the section")
    
    def find_index_section_fromID(self, collection, item):
        i=-1
        for el in collection:
            i=i+1
            if el.id == item:
                break
        return i

    @classmethod
    def poll(cls, context):
        
        res, arm = mustardui_active_object(context, config = 1)
        return res
    
    def execute(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config = 1)
        rig_settings = obj.MustardUI_RigSettings
        sec_obj = rig_settings.body_custom_properties_sections
        
        i=-1
        for el in sec_obj:
            i=i+1
            if el.name == self.name:
                break
        
        if i>=0:
            
            j = sec_obj[i].id
            
            for prop in obj.MustardUI_CustomProperties:
                if prop.section == sec_obj[i].name:
                    prop.section = ""
            
            for k in range(j+1,len(sec_obj)):
                sec_obj[self.find_index_section_fromID(sec_obj, k)].id = k-1
            
            sec_obj.remove(i)
        
        self.report({'INFO'}, 'MustardUI - Section \'' + self.name +'\' deleted.')
        
        return {'FINISHED'}

# Section Property settings
class MustardUI_Body_SettingsSection(bpy.types.Operator):
    """Modify the section settings."""
    bl_idname = "mustardui.body_settingssection"
    bl_label = "Section settings"
    bl_icon = "PREFERENCES"
    bl_options = {'UNDO'}
    
    name : bpy.props.StringProperty(name='Name',
                        description="Choose the name of the section")
    icon : bpy.props.EnumProperty(name='Icon',
                        description="Choose the icon.\nNote that the icon name MUST respect Blender convention. All the icons can be found in the Icon Viewer default Blender addon.",
                        items = mustardui_icon_list)
    advanced: bpy.props.BoolProperty(default = False,
                        name = "Advanced",
                        description = "The section will be shown only when Advances Settings is enabled")
    collapsable: bpy.props.BoolProperty(default = False,
                        name = "Collapsable",
                        description = "Add a collapse icon to the section.\nNote that this might give bad UI results if combined with an icon")
        
    name_edit : bpy.props.StringProperty(name='Name',
                        description="Choose the name of the section")
    ID : bpy.props.IntProperty()

    def find_index_section(self, collection, item):
        i=-1
        for el in collection:
            i=i+1
            if el.name == item:
                break
        return i
    
    @classmethod
    def poll(cls, context):
        
        res, arm = mustardui_active_object(context, config = 1)
        return res
    
    def execute(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config = 1)
        rig_settings = obj.MustardUI_RigSettings
        sec_obj = rig_settings.body_custom_properties_sections
        
        if self.name_edit == "":
            self.report({'WARNING'}, 'MustardUI - Can not rename a Section with an empty name.')
            return {'FINISHED'}
        
        i = self.find_index_section(sec_obj,self.name)
        
        for prop in obj.MustardUI_CustomProperties:
            if prop.section == sec_obj[i].name:
                prop.section = self.name_edit
            
        if i>=0:
           
            sec_obj[i].name = self.name_edit
            sec_obj[i].icon = self.icon
            sec_obj[i].advanced = self.advanced
            sec_obj[i].collapsable = self.collapsable
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config = 1)
        rig_settings = obj.MustardUI_RigSettings
        sec_obj = rig_settings.body_custom_properties_sections
        
        self.name_edit = self.name
        self.ID = self.find_index_section(sec_obj,self.name)
        self.icon = sec_obj[self.ID].icon
        self.advanced = sec_obj[self.ID].advanced
        self.collapsable = sec_obj[self.ID].collapsable
        
        return context.window_manager.invoke_props_dialog(self)
            
    def draw(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config = 1)
        rig_settings = obj.MustardUI_RigSettings
        sec_obj = rig_settings.body_custom_properties_sections
        
        scale = 3.0
        
        layout = self.layout
        
        row=layout.row()
        row.label(text="Name:")
        row.scale_x=scale
        row.prop(self, "name_edit", text="")
        
        row=layout.row()
        row.label(text="Icon:")
        row.scale_x=scale
        row.prop(self, "icon", text="")
        
        row=layout.row()
        row.prop(self, "advanced", text="")
        row.label(text="Advanced")
        
        row=layout.row()
        row.prop(self, "collapsable", text="")
        row.label(text="Collapsable")

# Operator to change Section position
class MustardUI_Body_SwapSection(bpy.types.Operator):
    """Change the position of the section"""
    bl_idname = "mustardui.body_swapsection"
    bl_label = "Change the section position"
    
    mod : bpy.props.BoolProperty(default = False) # False = down, True = Up
    name : bpy.props.StringProperty()
    
    def find_index_section_fromID(self, collection, item):
        i=-1
        for el in collection:
            i=i+1
            if el.id == item:
                break
        return i
    
    def find_index_section(self, collection, item):
        i=-1
        for el in collection:
            i=i+1
            if el.name == item:
                break
        return i
    
    def execute(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config = 1)
        rig_settings = obj.MustardUI_RigSettings
        sec_obj = rig_settings.body_custom_properties_sections
        sec_len = len(sec_obj)
        
        sec_index = self.find_index_section(sec_obj,self.name)
        i = sec_obj[sec_index].id
            
        if self.mod and i > 0:
            j = self.find_index_section_fromID(sec_obj, i-1)
            sec_obj[sec_index].id = i-1
            sec_obj[j].id = i
        elif not self.mod and i < sec_len-1:
            j = self.find_index_section_fromID(sec_obj, i+1)
            sec_obj[sec_index].id = i+1
            sec_obj[j].id = i
        
        return {'FINISHED'}

# Operator to change Section position
class MustardUI_Body_PropertyAddToSection(bpy.types.Operator):
    """Assign properties to the selected section"""
    bl_idname = "mustardui.body_propertyaddtosection"
    bl_label = "Assign properties"
    
    section_name : bpy.props.StringProperty()
    
    def execute(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config = 1)
        rig_settings = obj.MustardUI_RigSettings
        custom_props = obj.MustardUI_CustomProperties
        
        for prop in custom_props:
            if prop.add_section:
                prop.section = self.section_name
            else:
                prop.section = "" if prop.section == self.section_name else prop.section
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config = 1)
        rig_settings = obj.MustardUI_RigSettings
        custom_props = obj.MustardUI_CustomProperties
        
        for prop in custom_props:
            prop.add_section = prop.section == self.section_name
        
        return context.window_manager.invoke_props_dialog(self)
            
    def draw(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config = 1)
        rig_settings = obj.MustardUI_RigSettings
        custom_props = obj.MustardUI_CustomProperties
        
        layout = self.layout
        
        layout.label(text = "Add properties to the Section \'" + self.section_name + "\'")
        
        box = layout.box()
        for prop in sorted(custom_props, key = lambda x:x.name):
            row = box.row(align = False)
            row.prop(prop,'add_section', text = "")
            row.label(text = prop.name, icon = "SHAPEKEY_DATA" if prop.type in [0,1] else "MATERIAL")

# ------------------------------------------------------------------------
#    Add Collection Operator
# ------------------------------------------------------------------------

# Operator to add the collection to the selected section
class MustardUI_AddOutfit(bpy.types.Operator):
    """Add the collection as an outfit.\nThis can be done only in Configuration mode"""
    bl_idname = "mustardui.add_collection"
    bl_label = "Add Outfit"

    @classmethod
    def poll(cls, context):
        
        res, arm = mustardui_active_object(context, config = 1)
        return res

    def execute(self, context):
        
        res, arm = mustardui_active_object(context, config = 1)
        rig_settings = arm.MustardUI_RigSettings
        
        add_coll = bpy.context.collection

        i=True
        for el in rig_settings.outfits_collections:
            if el.collection == add_coll:
                i=False
                break
        if i:
            add_item = rig_settings.outfits_collections.add()
            add_item.collection = add_coll
            self.report({'INFO'}, 'MustardUI - Outfit added.')
        else:
            self.report({'WARNING'}, 'MustardUI - Outfit was already added.')

        return {'FINISHED'}

class OUTLINER_MT_collection(Menu):
    bl_label = "Custom Action Collection"

    def draw(self, context):
        pass
    
def mustardui_collection_menu(self, context):
    
    res, arm = mustardui_active_object(context, config = 1)
    
    if res:
        self.layout.separator()
        self.layout.operator(MustardUI_AddOutfit.bl_idname)

class MustardUI_RemoveOutfit(bpy.types.Operator):
    """Remove the selected outfit from the Menu.\nThe collection will NOT be deleted"""
    bl_idname = "mustardui.delete_outfit"
    bl_label = "Remove the selected collection from the menu"
    bl_options = {'UNDO'}
    
    col : bpy.props.StringProperty()

    def execute(self, context):
        
        res, arm = mustardui_active_object(context, config = 1)
        rig_settings = arm.MustardUI_RigSettings
        
        i = 0
        for el in rig_settings.outfits_collections:
            if el.collection.name == self.col:
                rig_settings.outfits_collections.remove(i)
                break
            i = i + 1
        
        self.report({'INFO'}, 'MustardUI - Outfit removed.')
        
        return {'FINISHED'}

# ------------------------------------------------------------------------
#    Diffeomorphic Support
# ------------------------------------------------------------------------

# Function to add a option to the object, if not already there
def mustardui_add_dazmorph(collection, item):
    
    for el in collection:
        if el.name == item[0] and el.path == item[1] and el.type == item[2]:
            return
    
    add_item = collection.add()
    add_item.name = item[0]
    add_item.path = item[1]
    add_item.type = item[2]
    
    return

# This operator will check for additional options for the outfits
class MustardUI_DazMorphs_CheckMorphs(bpy.types.Operator):
    """Search for morphs to display in the UI External Morphs panel"""
    bl_idname = "mustardui.dazmorphs_checkmorphs"
    bl_label = "Check Morphs"

    @classmethod
    def poll(cls, context):
        
        res, arm = mustardui_active_object(context, config = 1)
        return res

    def execute(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, arm = mustardui_active_object(context, config = 1)
        rig_settings = arm.MustardUI_RigSettings
        
        # Try to assign the rig object
        if not arm.MustardUI_created:
            if context.active_object != None and context.active_object.type == "ARMATURE":
                rig_settings.model_armature_object = context.active_object
            else:
                self.report({'ERROR'}, 'MustardUI - You need to complete the first configuration before being able to add Morphs to the UI.')
                return {'FINISHED'}
        
        # Clean the morphs
        rig_settings.diffeomorphic_morphs_list.clear()
        
        # TYPE: 0: Emotion Units, 1: Emotions, 2: FACS Emotion Units, 3: FACS Emotions, 4: Body Morphs
        
        # Default lists
        facs_emotions_default_list = ['facs_ctrl_Afraid', 'facs_ctrl_Angry', 'facs_ctrl_Flirting', 'facs_ctrl_Frown', 'facs_ctrl_Shock', 'facs_ctrl_SmileFullFace', 'facs_ctrl_SmileOpenFullFace', 'facs_ctrl_Surprised']
        
        # Emotions Units
        if rig_settings.diffeomorphic_emotions_units:
            emotions_units = [x for x in rig_settings.model_armature_object.keys() if ('eCTRL' in x or 'ECTRL' in x) and not "HD" in x and not "eCTRLSmile" in x and not 'eCTRLv' in x and sum(1 for c in x if c.isupper()) >= 6]
                
            for emotion in emotions_units:
                name = emotion[len('eCTRL')] + ''.join([c if not c.isupper() else ' ' + c for c in emotion[len('eCTRL')+1:]])
                mustardui_add_dazmorph(rig_settings.diffeomorphic_morphs_list, [name, emotion, 0])
        
        # Emotions
        if rig_settings.diffeomorphic_emotions:
            
            emotions = [x for x in rig_settings.model_armature_object.keys() if 'eCTRL' in x and not "HD" in x and not 'eCTRLv' in x and (sum(1 for c in x if c.isupper()) < 6 or "eCTRLSmile" in x)]
            
            # Custom Diffeomorphic emotions
            emotions_custom = []
            for string in [x for x in rig_settings.diffeomorphic_emotions_custom.split(',') if x != '']:
                for x in [x for x in rig_settings.model_armature_object.keys() if not "Adjust Custom" in x]:
                    if string in x:
                        emotions_custom.append(x)
            
            for emotion in emotions:
                name = emotion[len('eCTRL')] + ''.join([c if not c.isupper() else ' ' + c for c in emotion[len('eCTRL')+1:]])
                mustardui_add_dazmorph(rig_settings.diffeomorphic_morphs_list, [name, emotion, 1])
            for emotion in emotions_custom:
                mustardui_add_dazmorph(rig_settings.diffeomorphic_morphs_list, [emotion, emotion, 1])
        
         # FACS Emotions Units
        if rig_settings.diffeomorphic_facs_emotions_units:
            
            facs_emotions_units = []
            facs_emotions_units.append([x for x in rig_settings.model_armature_object.keys() if 'facs_ctrl_' in x and not x in facs_emotions_default_list])
            facs_emotions_units.append([x for x in rig_settings.model_armature_object.keys() if 'facs_bs_' in x and sum(1 for c in x if c.isupper()) >= 2])
            facs_emotions_units.append([x for x in rig_settings.model_armature_object.keys() if 'facs_jnt_' in x and sum(1 for c in x if c.isupper()) >= 2])
            facs_emotions_units = itertools.chain.from_iterable(facs_emotions_units)
            
            for emotion in facs_emotions_units:
                name = emotion[emotion.rfind('_', 0, 12) + 1] + ''.join([c if not c.isupper() else ' ' + c for c in emotion[emotion.rfind('_', 0, 12)+2:]])
                name = name.rstrip('_div2')
                mustardui_add_dazmorph(rig_settings.diffeomorphic_morphs_list, [name, emotion, 2])
        
        # FACS Emotions
        if rig_settings.diffeomorphic_facs_emotions:
            
            facs_emotions = [x for x in rig_settings.model_armature_object.keys() if x in facs_emotions_default_list]
            for emotion in facs_emotions:
                name = emotion[len('facs_ctrl_')] + ''.join([c if not c.isupper() else ' ' + c for c in emotion[len('facs_ctrl_')+1:]])
                mustardui_add_dazmorph(rig_settings.diffeomorphic_morphs_list, [name, emotion, 3])
        
        # Body Morphs
        if rig_settings.diffeomorphic_body_morphs:
            
            body_morphs_FBM = [x for x in rig_settings.model_armature_object.keys() if 'FBM' in x and sum(1 for c in x if c.isdigit()) < 1 and sum(1 for c in x if c.isupper()) < 6]
            body_morphs_CTRLB = [x for x in rig_settings.model_armature_object.keys() if 'CTRLBreasts' in x and not 'pCTRLBreasts' in x and sum(1 for c in x if c.isupper()) < 10]
            body_morphs_PBM = [x for x in rig_settings.model_armature_object.keys() if 'PBMBreasts' in x and sum(1 for c in x if c.isupper()) < 10]
            
            # Custom Diffeomorphic emotions
            body_morphs_custom = []
            for string in [x for x in rig_settings.diffeomorphic_body_morphs_custom.split(',') if x != '']:
                for x in [x for x in rig_settings.model_armature_object.keys() if not "Adjust Custom" in x]:
                    if string in x:# and sum(1 for c in x if c.isupper()) < 6:
                        body_morphs_custom.append(x)
            
            for morph in body_morphs_FBM:
                name = morph[len('FBM')] + ''.join([c if not c.isupper() else ' ' + c for c in morph[len('FBM')+1:]])
                mustardui_add_dazmorph(rig_settings.diffeomorphic_morphs_list, [name, morph, 4])
            for morph in body_morphs_CTRLB:
                name = morph[len('CTRL')] + ''.join([c if not c.isupper() else ' ' + c for c in morph[len('CTRL')+1:]])
                mustardui_add_dazmorph(rig_settings.diffeomorphic_morphs_list, [name, morph, 4])
            for morph in body_morphs_PBM:
                name = morph[len('PBM')] + ''.join([c if not c.isupper() else ' ' + c for c in morph[len('PBM')+1:]])
                mustardui_add_dazmorph(rig_settings.diffeomorphic_morphs_list, [name, morph, 4])
            for morph in body_morphs_custom:
                mustardui_add_dazmorph(rig_settings.diffeomorphic_morphs_list, [morph, morph, 4])
        
        properties_number = 0                       
        if settings.debug:
            print("\nMustardUI - Diffeomorphic Daz Morphs found\n")
            # Print the options
        for el in rig_settings.diffeomorphic_morphs_list:
            if settings.debug:
                print(el.name+" with path "+el.path+', type: '+str(el.type))
            properties_number = properties_number + 1
        
        rig_settings.diffeomorphic_morphs_number = properties_number
        
        
        self.report({'INFO'}, 'MustardUI - Diffeomorphic Daz Morphs check completed.')

        return {'FINISHED'}

# This operator will check for additional options for the outfits
class MustardUI_DazMorphs_DefaultValues(bpy.types.Operator):
    """Set the value of all morphs to the default value"""
    bl_idname = "mustardui.dazmorphs_defaultvalues"
    bl_label = "Restore default values"
    
    @classmethod
    def poll(cls, context):
        
        res, arm = mustardui_active_object(context, config = 0)
        return res

    def execute(self, context):
        
        res, arm = mustardui_active_object(context, config = 0)
        rig_settings = arm.MustardUI_RigSettings
        
        for morph in rig_settings.diffeomorphic_morphs_list:
            rig_settings.model_armature_object[morph.path] = 0.
        
        arm.update_tag()
        rig_settings.model_armature_object.update_tag()
        
        self.report({'INFO'}, 'MustardUI - Morphs values restored to default.')
        
        return {'FINISHED'}

class MustardUI_DazMorphs_ClearPose(bpy.types.Operator):
    """Revert the position of all the bones to the Rest position"""
    bl_idname = "mustardui.dazmorphs_clearpose"
    bl_label = "Clear pose"
    bl_options = {'REGISTER', 'UNDO'}
    
    def setWorldMatrix(self, ob, wmat):
        Zero = Vector((0,0,0))
        One = Vector((1,1,1))
        if ob.parent:
            if ob.parent_type in ['OBJECT', 'VERTEX', 'VERTEX_3']:
                ob.matrix_parent_inverse = ob.parent.matrix_world.inverted()
            elif ob.parent_type == 'BONE':
                pb = ob.parent.pose.bones[ob.parent_bone]
                ob.matrix_parent_inverse = pb.matrix.inverted()
        ob.matrix_world = wmat
        if Vector(ob.location).length < 1e-6:
            ob.location = Zero
        if Vector(ob.rotation_euler).length < 1e-6:
            ob.rotation_euler = Zero
        if (Vector(ob.scale) - One).length < 1e-6:
            ob.scale = One
    
    @classmethod
    def poll(cls, context):
        
        res, arm = mustardui_active_object(context, config = 0)
        return res
 
    def execute(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, arm = mustardui_active_object(context, config = 1)
        rig_settings = arm.MustardUI_RigSettings
        
        warnings = 0
        
        try:
            unit = Matrix()
            self.setWorldMatrix(rig_settings.model_armature_object, unit)
            for pb in rig_settings.model_armature_object.pose.bones:
                pb.matrix_basis = unit
        except:
            warnings = warnings + 1
        
        if warnings < 1:
            self.report({'INFO'}, 'MustardUI - Pose cleared successfully')
        else:
            self.report({'ERROR'}, 'MustardUI - An error occurred while clearing the pose')
        
        return{'FINISHED'}

# Function to mute daz drivers
def muteDazFcurves(rig, mute, useLocation = True, useRotation = True, useScale = True):
        
    def isDazFcurve(path):
        for string in ["(fin)", "(rst)", ":Loc:", ":Rot:", ":Sca:", ":Hdo:", ":Tlo"]:
            if string in path:
                return True
        return False

    if rig and rig.data.animation_data:
        for fcu in rig.data.animation_data.drivers:
            if isDazFcurve(fcu.data_path):
                fcu.mute = mute

    if rig and rig.animation_data:
        for fcu in rig.animation_data.drivers:
            words = fcu.data_path.split('"')
            if words[0] == "pose.bones[":
                channel = words[-1].rsplit(".",1)[-1]
                if ((channel in ["rotation_euler", "rotation_quaternion"] and useRotation) or
                    (channel == "location" and useLocation) or
                    (channel == "scale" and useScale) or
                    channel in ["HdOffset", "TlOffset"]):
                    fcu.mute = mute

    for ob in rig.children:
        if ob.type == 'MESH':
            skeys = ob.data.shape_keys
            if skeys and skeys.animation_data:
                for fcu in skeys.animation_data.drivers:
                    words = fcu.data_path.split('"')
                    if words[0] == "key_blocks[":
                        fcu.mute = mute
                        sname = words[1]
                        if sname in skeys.key_blocks.keys():
                            skey = skeys.key_blocks[sname]
                            skey.mute = mute

class MustardUI_DazMorphs_DisableDrivers(bpy.types.Operator):
    """Disable drivers to improve performance (the correctives will not be disabled). This can be used only if the armature is selected"""
    bl_idname = "mustardui.dazmorphs_disabledrivers"
    bl_label = "Button"
    bl_options = {'REGISTER', 'UNDO'}
    
    # Function to prevent the DisableDriver operator to switch off custom properties drivers
    def check_driver(self, arm, datapath):
        
        for cp in arm.MustardUI_CustomProperties:
            if datapath in cp.rna + "." + cp.path:
                return False
        for cp in arm.MustardUI_CustomPropertiesOutfit:
            if datapath in cp.rna + "." + cp.path:
                return False
        for cp in arm.MustardUI_CustomPropertiesHair:
            if datapath in cp.rna + "." + cp.path:
                return False
        
        return True
 
    def execute(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, arm = mustardui_active_object(context, config = 0)
        rig_settings = arm.MustardUI_RigSettings
        
        objects = [rig_settings.model_body]
        
        aobj = context.active_object
        
        context.view_layer.objects.active = rig_settings.model_armature_object
        
        warnings = 0
        
        try:
            if rig_settings.diffeomorphic_model_version == "1.6":
                muteDazFcurves(rig_settings.model_armature_object, True, True, True, True)
                if hasattr(rig_settings.model_armature_object,'DazDriversDisabled'):
                    rig_settings.model_armature_object.DazDriversDisabled = True
            else:
                bpy.ops.daz.disable_drivers()
        except:
            warnings = warnings + 1
            if settings.debug:
                print('MustardUI - Error occurred while muting Daz drivers.')
        
        for collection in [x for x in rig_settings.outfits_collections if x.collection != None]:
            for obj in collection.collection.objects:
                if obj.type == "MESH":
                    objects.append(obj)
        
        for obj in objects:
            if obj.data.shape_keys != None:
                if obj.data.shape_keys.animation_data != None:
                    for driver in obj.data.shape_keys.animation_data.drivers:
                        if not "pJCM" in driver.data_path and not "MustardUINotDisable" in driver.data_path:
                            driver.mute = self.check_driver(arm, driver.data_path)
                        if "MustardUINotDisable" in driver.data_path:
                            driver.mute = False
        
        for driver in rig_settings.model_armature_object.animation_data.drivers:
            if "evalMorphs" in driver.driver.expression:
                    driver.mute = self.check_driver(arm, driver.data_path)
        
        rig_settings.diffeomorphic_emotions_units_collapse = True
        rig_settings.diffeomorphic_emotions_collapse = True
        rig_settings.diffeomorphic_facs_emotions_units_collapse = True
        rig_settings.diffeomorphic_facs_emotions_collapse = True
        rig_settings.diffeomorphic_body_morphs_collapse = True
        
        context.view_layer.objects.active = aobj
        
        if warnings < 1:
            self.report({'INFO'}, 'MustardUI - Morphs drivers disabled.')
        else:
            self.report({'WARNING'}, 'MustardUI - An error occurred while disabling morphs.')
        
        return{'FINISHED'}

class MustardUI_DazMorphs_EnableDrivers(bpy.types.Operator):
    """Enable all drivers. This can be used only if the armature is selected"""
    bl_idname = "mustardui.dazmorphs_enabledrivers"
    bl_label = "Button"
    bl_options = {'REGISTER', 'UNDO'}
 
    def execute(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, arm = mustardui_active_object(context, config = 0)
        rig_settings = arm.MustardUI_RigSettings
        
        objects = [rig_settings.model_body]
        
        aobj = context.active_object
        
        context.view_layer.objects.active = rig_settings.model_armature_object
        
        warnings = 0
        
        try:
            if rig_settings.diffeomorphic_model_version == "1.6":
                muteDazFcurves(rig_settings.model_armature_object, False, True, True, True)
                if hasattr(rig_settings.model_armature_object,'DazDriversDisabled'):
                    rig_settings.model_armature_object.DazDriversDisabled = False
            else:
                bpy.ops.daz.enable_drivers()
        except:
            warnings = warnings + 1
            if settings.debug:
                print('MustardUI - Error occurred while un-muting Daz drivers.')
        
        for collection in [x for x in rig_settings.outfits_collections if x.collection != None]:
            for obj in collection.collection.objects:
                if obj.type == "MESH":
                    objects.append(obj)
        
        for obj in objects:
            if obj.data.shape_keys != None:
                if obj.data.shape_keys.animation_data != None:
                    for driver in obj.data.shape_keys.animation_data.drivers:
                        if not "pJCM" in driver.data_path and not "MustardUINotDisable" in driver.data_path:
                            driver.mute = False
                            
        
        for driver in rig_settings.model_armature_object.animation_data.drivers:
            
            if "evalMorphs" in driver.driver.expression or driver.driver.expression == "0.0" or driver.driver.expression == "-0.0":
                    driver.mute = False
        
        context.view_layer.objects.active = aobj
        
        if warnings < 1:
            self.report({'INFO'}, 'MustardUI - Morphs drivers enabled.')
        else:
            self.report({'WARNING'}, 'MustardUI - An error occurred while enabling morphs.')  
    
        return{'FINISHED'}

# ------------------------------------------------------------------------
#    Viewport Model Selection Operator
# ------------------------------------------------------------------------

class MustardUI_ViewportModelSelection(bpy.types.Operator):
    """Turn on/off Viewport Model Selection"""
    bl_idname = "mustardui.viewportmodelselection"
    bl_label = "Turn on/off Viewport Model Selection"
    bl_options = {'REGISTER'}

    def execute(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        
        poll, settings.panel_model_selection_armature = mustardui_active_object(context, 0)
        settings.viewport_model_selection = not settings.viewport_model_selection
        
        return {'FINISHED'}

class MustardUI_SwitchModel(bpy.types.Operator):
    """Switch to the selected model"""
    bl_idname = "mustardui.switchmodel"
    bl_label = "Switch model"
    bl_options = {'REGISTER'}
    
    model_to_switch : bpy.props.StringProperty()
    
    @classmethod
    def poll(cls, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        
        return not settings.viewport_model_selection

    def execute(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        
        # Check if you are trying to switch to the same model already in use
        if bpy.data.armatures[self.model_to_switch] == settings.panel_model_selection_armature:
            self.report({'WARNING'}, 'MustardUI - Already using ' + bpy.data.armatures[self.model_to_switch].MustardUI_RigSettings.model_name + ' model.')
            return {'FINISHED'}
        
        # Change the model if it is not None
        if bpy.data.armatures[self.model_to_switch] != None:
            settings.panel_model_selection_armature = bpy.data.armatures[self.model_to_switch]
            self.report({'INFO'}, 'MustardUI - Switched to ' + bpy.data.armatures[self.model_to_switch].MustardUI_RigSettings.model_name + '.')
        else:
            self.report({'ERROR'}, 'MustardUI - Error occurred while switching the model.')
        
        return {'FINISHED'}

# ------------------------------------------------------------------------
#    Configuration and Deletion Operators
# ------------------------------------------------------------------------

class MustardUI_Configuration(bpy.types.Operator):
    """Configure MustardUI"""
    bl_idname = "mustardui.configuration"
    bl_label = "Configure MustardUI"
    bl_options = {'REGISTER'}
    
    @classmethod
    def poll(cls, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        
        if settings.viewport_model_selection:
            return context.active_object.type != "LATTICE"
        else:
            return True

    def execute(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        
        res, obj = mustardui_active_object(context, config = 1)
        rig_settings = obj.MustardUI_RigSettings
        lattice_settings = obj.MustardUI_LatticeSettings
        armature_settings = obj.MustardUI_ArmatureSettings
        tools_settings = obj.MustardUI_ToolsSettings
        
        warnings = 0
        
        if not obj.MustardUI_enable:
            
            if settings.debug:
                print("\n\nMustardUI - Configuration Logs")
        
            # Various checks
            if rig_settings.model_body == None:
                self.report({'ERROR'}, 'MustardUI - A body mesh should be selected.')
                return {'FINISHED'}
            
            if rig_settings.model_name == "":
                self.report({'ERROR'}, 'MustardUI - A name should be selected.')
                return {'FINISHED'}
            
            # Allocate the armature object
            if not obj.MustardUI_created:
                if context.active_object != None and context.active_object.type == "ARMATURE":
                    rig_settings.model_armature_object = context.active_object
                    if tools_settings.lips_shrinkwrap_enable:
                        tools_settings.lips_shrinkwrap_armature_object = rig_settings.model_armature_object
                else:
                    self.report({'ERROR'}, 'MustardUI - Be sure to select the armature Object in the viewport before continuing.')
                    return {'FINISHED'}
            
            # Check Body mesh scale
            if rig_settings.model_body.scale[0] != 1. or rig_settings.model_body.scale[1] != 1. or rig_settings.model_body.scale[2] != 1.:
                warnings = warnings + 1
                if settings.debug:
                    print('MustardUI - Configuration Warning - The selected body mesh seems not to have the scale applied.\n This might generate issues with the tools.')
            
            # Check and eventually clean deleted outfit collections
            index_to_delete = []
            for x in range(len(rig_settings.outfits_collections)):
                if not hasattr(rig_settings.outfits_collections[x].collection, 'name'):
                    index_to_delete.append(x)
                    if settings.debug:
                        print('MustardUI - A ghost outfit collection has been removed.')
            for x in index_to_delete:
                rig_settings.outfits_collections.remove(x)
            
            if tools_settings.autoeyelid_enable:
                
                if (tools_settings.autoeyelid_eyeL_shapekey == "" and tools_settings.autoeyelid_eyeR_shapekey == "") and tools_settings.autoeyelid_driver_type == "SHAPE_KEY":
                    self.report({'ERROR'}, 'MustardUI - At least one shape key should be selected if Auto Blink tool is enabled.')
                    return {'FINISHED'}
                
                elif tools_settings.autoeyelid_morph == "" and tools_settings.autoeyelid_driver_type == "MORPH":
                    self.report({'ERROR'}, 'MustardUI - At least one custom property should be selected if Auto Blink tool is enabled.')
                    return {'FINISHED'}
                
                elif tools_settings.autoeyelid_morph != "" and tools_settings.autoeyelid_driver_type == "MORPH":
                    try:
                        rig_settings.model_armature_object[tools_settings.autoeyelid_morph] = float(rig_settings.model_armature_object[tools_settings.autoeyelid_morph])
                    except:
                        self.report({'ERROR'}, 'MustardUI - The custom property selected for Auto Blink can not be found.')
                        return {'FINISHED'}
            
            # Check lattice object definition
            if lattice_settings.lattice_object == None and lattice_settings.lattice_panel_enable:
                self.report({'ERROR'}, 'MustardUI - A lattice object should be selected if Lattice tool is enabled.')
                return {'FINISHED'}
            
            # Check name of armature layers
            for i in [x for x in range(0,32) if armature_settings.config_layer[x]]:
                if armature_settings.layers[i].name == "":
                    warnings = warnings + 1
                    if settings.debug:
                        print('MustardUI - Configuration Warning - Layer ' + str(i) + ' do not have a name defined')
                if armature_settings.layers[i].outfit_switcher_enable and armature_settings.layers[i].outfit_switcher_collection == None:
                    warnings = warnings + 1
                    if settings.debug:
                        print('MustardUI - Configuration Warning - Layer ' + str(i) + ' has Outfit Switcher enabled, but no collection has been defined')
            
            # Check the mirror option of the layer
            for i in [x for x in range(0,32) if armature_settings.config_layer[x]]:
                
                armature_settings.layers[i].mirror = False
                armature_settings.layers[i].mirror_layer = -1
                
                mirror_string = ""
                if ".R" in armature_settings.layers[i].name:
                    mirror_string = ".R"
                elif ".L" in armature_settings.layers[i].name:
                    mirror_string = ".L"
                
                if mirror_string == "":
                    continue
                
                armature_settings.layers[i].mirror = mirror_string == ".R" or mirror_string == ".L"
                armature_settings.layers[i].mirror_left = mirror_string == ".L"
                
                if armature_settings.layers[i].name.find(mirror_string) > 1:
                    rng = list(range(0,32))
                    rng.remove(i)
                    mirror_layer = [x for x in rng if armature_settings.config_layer[x] and (".R" in armature_settings.layers[x].name or ".L" in armature_settings.layers[x].name) and armature_settings.layers[i].name[:armature_settings.layers[i].name.find(mirror_string)] in armature_settings.layers[x].name and armature_settings.layers[i].name[armature_settings.layers[i].name.find(mirror_string) + len(mirror_string):] in armature_settings.layers[x].name]
                    if len(mirror_layer) > 0:
                        armature_settings.layers[i].mirror_layer = mirror_layer[0]
                    else:
                        armature_settings.layers[i].mirror_layer = -1
                        warnings = warnings + 1
                        if settings.debug:
                            print('MustardUI - Configuration Warning - Can not find a mirror layer. Mirror has been disabled.')
                        armature_settings.layers[i].mirror = False
                else:
                    warnings = warnings + 1
                    if settings.debug:
                        print('MustardUI - Configuration Warning - Layer ' + str(i) + ' seems not to have the correct mirror naming convention. Mirror has been disabled.')
                    armature_settings.layers[i].mirror = False
            
            # Check the type of the rig
            rig_recognized = 0
            if hasattr(obj,'[\"arp_updated\"]'):
                rig_settings.model_rig_type = "arp"
                rig_recognized += 1
            elif hasattr(obj,'[\"rig_id\"]'):
                rig_settings.model_rig_type = "rigify"
                rig_recognized += 1
            elif hasattr(rig_settings.model_armature_object,'[\"MhxRig\"]'):
                rig_settings.model_rig_type = "mhx"
                rig_recognized += 1
            else:
                rig_settings.model_rig_type = "other"
            
            if rig_recognized < 2:
                print('MustardUI - The rig has been recognized as ' + rig_settings.model_rig_type)
            else:
                warnings = warnings + 1
                if settings.debug:
                    print('MustardUI - Configuration Warning - The rig has multiple rig types. This might create problems in the UI')
            
            # Check MHX requirements for IK/FK support
            if armature_settings.enable_ik_fk and (settings.status_diffeomorphic_version[0],settings.status_diffeomorphic_version[1],settings.status_diffeomorphic_version[2]) >= (1,6,0):
                armature_settings.enable_ik_fk = False
                armature_settings.enable_ik_fk_snap = False
                warnings = warnings + 1
                if settings.debug:
                    print('MustardUI - Configuration Warning - IK/FK support requested for MHX rig, but from Diffeomorphic 1.6.0 it has been moved to MHX independent panel')
            
            if armature_settings.enable_ik_fk and rig_settings.model_rig_type == "mhx" and settings.status_diffeomorphic < 2:
                warnings = warnings + 1
                if settings.debug:
                    print('MustardUI - Configuration Warning - IK/FK support requested for MHX rig, but Diffeomorphic is not installed')
            
            if armature_settings.enable_ik_fk and rig_settings.model_rig_type != "mhx":
                armature_settings.enable_ik_fk = False
                armature_settings.enable_ik_fk_snap = False
                warnings = warnings + 1
                if settings.debug:
                    print('MustardUI - Configuration Warning - IK/FK support requested for non-MHX rig. The IK/FK option will be switched off')
            
            # Check Diffeomorphic 1.5 morph support script
            if rig_settings.diffeomorphic_support:
                if rig_settings.diffeomorphic_1_5_script != None:
                    if not "def evalMorphsLoc(pb, idx):" in rig_settings.diffeomorphic_1_5_script.as_string():
                        rig_settings.diffeomorphic_1_5_script = None
                        warnings = warnings + 1
                        if settings.debug:
                            print('MustardUI - Configuration Warning - The Diffeomorphic 1.5 Morphs support script selected is invalid')
            
            # Check shrinkwrap modifier requirements
            if tools_settings.lips_shrinkwrap_enable and not rig_settings.model_rig_type in ['arp', 'mhx']:
                tools_settings.lips_shrinkwrap_armature_object = None
                tools_settings.lips_shrinkwrap_enable = False
                warnings = warnings + 1
                if settings.debug:
                    print('MustardUI - Configuration Warning - Lips shrinkwrap requested for a rig which is not ARP or MHX. The tool has been disabled')                  
            
            if warnings > 0:
                if settings.debug:
                    print("\n\n")
                self.report({'WARNING'}, 'MustardUI - Some warning were generated during the configuration. Enable Debug mode and check the console for more informations')
            else:
                if settings.debug:
                    print("MustardUI - Configuration Warning - No warning or errors during the configuration\n\n")
                self.report({'INFO'}, 'MustardUI - Configuration complete.')
        
        obj.MustardUI_enable = not obj.MustardUI_enable

        if ((settings.viewport_model_selection_after_configuration and not settings.viewport_model_selection) or (not settings.viewport_model_selection_after_configuration and settings.viewport_model_selection)) and not obj.MustardUI_created:
            bpy.ops.mustardui.viewportmodelselection()
        
        obj.MustardUI_created = True
        
        return {'FINISHED'}

class MustardUI_Configuration_SmartCheck(bpy.types.Operator):
    """Search for MustardUI configuration options based on the name of the model and its body"""
    bl_idname = "mustardui.configuration_smartcheck"
    bl_label = "MustardUI setting smart search tool."
    bl_options = {'REGISTER'}
    
    @classmethod
    def poll(cls, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        
        res, arm = mustardui_active_object(context, config = 1)
        
        if arm != None:
            rig_settings = arm.MustardUI_RigSettings
            return rig_settings.model_MustardUI_naming_convention and rig_settings.model_body != None and rig_settings.model_name != ""
        else:
            return False

    def execute(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        
        res, obj = mustardui_active_object(context, config = 1)
        rig_settings = obj.MustardUI_RigSettings
        lattice_settings = obj.MustardUI_LatticeSettings
        armature_settings = obj.MustardUI_ArmatureSettings
        tools_settings = obj.MustardUI_ToolsSettings
        
        # Try to assign the rig object
        if not obj.MustardUI_created:
            if context.active_object != None and context.active_object.type == "ARMATURE":
                rig_settings.model_armature_object = context.active_object
        
        # Initialize Smart Check header
        if settings.debug:
            print('\nMustardUI - Smart Check - Start\n')
            
        if settings.debug:
            print('MustardUI - Smart Check - Searching for body additional options\n')
        # Check for body additional properties
        bpy.ops.mustardui.property_smartcheck()
        
        # Search for oufit collections
        if settings.debug:
            print('\nMustardUI - Smart Check - Searching for outfits\n')
        
        outfits_collections = [x for x in bpy.data.collections if (rig_settings.model_name in x.name) and (not 'Hair' in x.name) and (not 'Extras' in x.name) and (not 'Physics' in x.name) and (not rig_settings.model_name == x.name) and (not '_' in x.name)]

        for collection in outfits_collections:
            
            add_collection = True
            for el in rig_settings.outfits_collections:
                if el.collection == collection:
                    add_collection = False
                    break
            
            if settings.debug:
                print('MustardUI - Smart Check - ' + collection.name + ' added: ' + str(add_collection))
            
            if add_collection:
                add_item = rig_settings.outfits_collections.add()
                add_item.collection = collection
        
        # Search for hair
        if settings.debug:
            print('\nMustardUI - Smart Check - Searching for hair.')
        hair_collections = [x for x in bpy.data.collections if (rig_settings.model_name in x.name) and ('Hair' in x.name)]
        if rig_settings.hair_collection == None:
            if len(hair_collections) == 1:
                rig_settings.hair_collection = hair_collections[0]
                print('\nMustardUI - Smart Check - ' + hair_collections[0].name + ' set as Hair collection')
            elif len(hair_collections) == 0:
                print('\nMustardUI - Smart Check - Can not find any Hair collection compatible with MustardUI naming convention.')
            else:
                print('\nMustardUI - Smart Check - More than 1 collection has been found. No collection has been set as the Hair one to avoid un-wanted behaviour.')
        else:
            print('\nMustardUI - Smart Check - Hair collection already defined. Skipping this part.')
        
        # Search for extras
        if settings.debug:
            print('\nMustardUI - Smart Check - Searching for extras.')
        
        if rig_settings.extras_collection == None:
            extras_collections = [x for x in bpy.data.collections if (rig_settings.model_name in x.name) and ('Extras' in x.name)]
            if len(extras_collections) == 1:
                rig_settings.extras_collection = extras_collections[0]
                print('\nMustardUI - Smart Check - ' + extras_collections[0].name + ' set as Extras collection')
            elif len(extras_collections) == 0:
                print('\nMustardUI - Smart Check - Can not find any Extras collection compatible with MustardUI naming convention.')
            else:
                print('\nMustardUI - Smart Check - More than 1 collection has been found. No collection has been set as the Extras one to avoid un-wanted behaviour.')
        else:
            print('\nMustardUI - Smart Check - Extras collection already defined. Skipping this part.')
        
        # Standard armature setup
        
        preset_Mustard_models = []
        
        if hasattr(obj,'[\"arp_updated\"]'):
            if settings.debug:
                print('\nMustardUI - Smart Check - Found an ARP rig, version: \'' + obj["arp_updated"] + '\' .')
            print('\nMustardUI - Smart Check - Setting layers as for Mustard models.')
            
            preset_Mustard_models = [(0, "Main", False),
                                    (1, "Advanced", False),
                                    (7, "Extra", False),
                                    (10, "Child Of - Ready", False),
                                    (31, "Rigging - Ready", True)]     
        
        elif hasattr(obj,'[\"rig_id\"]'):
            if settings.debug:
                print('\nMustardUI - Smart Check - Found a Rigify rig.')
            print('\nMustardUI - Smart Check - Setting layers for Rigify.')
            
            preset_Mustard_models = [(1, "Face", False),
                                    (2, "Face (details)", False),
                                    (3, "Torso", False),
                                    (4, "Torso (Tweak)", False),
                                    (5, "Fingers", False),
                                    (6, "Fingers (Tweak)", False),
                                    (7, "Arm.L (IK)", False),
                                    (10, "Arm.R (IK)", False),
                                    (8, "Arm.L (FK)", False),
                                    (11, "Arm.R (FK)", False),
                                    (9, "Arm.L (Tweak)", False),
                                    (12, "Arm.R (Tweak)", False),
                                    (13, "Leg.L (IK)", False),
                                    (16, "Leg.R (IK)", False),
                                    (14, "Leg.L (FK)", False),
                                    (17, "Leg.R (FK)", False),
                                    (15, "Leg.L (Tweak)", False),
                                    (18, "Leg.R (Tweak)", False),
                                    (28, "Root", False)]
        
        elif rig_settings.model_armature_object != None:
            if hasattr(rig_settings.model_armature_object,'[\"MhxRig\"]'):
                if settings.debug:
                    print('\nMustardUI - Smart Check - Found a MHX rig.')
                print('\nMustardUI - Smart Check - Setting layers for MHX.')
                
                preset_Mustard_models = [(10, "Face", False),
                                        (8, "Face (details)", False),
                                        (1, "Spine", False),
                                        (2, "Arm.L (IK)", False),
                                        (18, "Arm.R (IK)", False),
                                        (3, "Arm.L (FK)", False),
                                        (19, "Arm.R (FK)", False),
                                        (4, "Leg.L (IK)", False),
                                        (20, "Leg.R (IK)", False),
                                        (5, "Leg.L (FK)", False),
                                        (21, "Leg.R (FK)", False),
                                        (12, "Extra.L", False),
                                        (28, "Extra.R", False),
                                        (6, "Hand.L", False),
                                        (22, "Hand.R", False),
                                        (7, "Fingers.L", False),
                                        (23, "Fingers.R", False),
                                        (13, "Toes.L", False),
                                        (29, "Toes.R", False),
                                        (9, "Tweak", False),
                                        (0, "Root", False)]
            
        if len(preset_Mustard_models) >0:
            
            if len(armature_settings.layers)<1:
                    bpy.ops.mustardui.armature_initialize(clean = False)
                
            for layer in preset_Mustard_models:
                if not armature_settings.config_layer[ layer[0] ]:
                    armature_settings.config_layer[ layer[0] ] = True   
                    armature_settings.layers[ layer[0] ].name = layer[1]
                    armature_settings.layers[ layer[0] ].advanced = layer[2]
                    armature_settings.layers[ layer[0] ].layer_config_collapse = True
                    if settings.debug:
                        print('\nMustardUI - Smart Check - Armature layer ' + str(layer[0]) + ' set.')
                else:
                    if settings.debug:
                        print('\nMustardUI - Smart Check - Armature layer ' + str(layer[0]) + ' already defined.')     
        
        # Lips Shrinkwrap
        if tools_settings.lips_shrinkwrap_armature_object == None:
            tools_settings.lips_shrinkwrap_armature_object = rig_settings.model_body.find_armature()
        
        # End of debug messages
        if settings.debug:
            print('\nMustardUI - Smart Check - End')
        
        self.report({'INFO'}, 'MustardUI - Smart Check complete.')
        
        return {'FINISHED'}

class MustardUI_RemoveUI(bpy.types.Operator):
    """Remove MustardUI"""
    bl_idname = "mustardui.remove"
    bl_label = "RemoveUI MustardUI.\nThe settings will be preserved on the armature if you want to re-enable it, but it will not be shown in the model list anymore"
    bl_options = {'REGISTER'}
    
    @classmethod
    def poll(cls, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        
        if settings.viewport_model_selection:
            return context.active_object.type != "LATTICE"
        else:
            return True

    def execute(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        
        res, obj = mustardui_active_object(context, config = 1)
        rig_settings = obj.MustardUI_RigSettings
        tools_settings = obj.MustardUI_ToolsSettings
        lattice_settings = obj.MustardUI_LatticeSettings
        armature_settings = obj.MustardUI_ArmatureSettings
        
        obj.MustardUI_enable = not obj.MustardUI_enable
        obj.MustardUI_created = False
        
        settings.viewport_model_selection = True
        
        self.report({'INFO'}, 'MustardUI - MustardUI deletion complete. Switched to Viewport Model Selection')
        
        return {'FINISHED'}

class MustardUI_RegisterUIFile(bpy.types.Operator):
    """Register the UI.\nThe script file will be linked to the armature and will be transfered if the model is appended in another .blend file"""
    bl_idname = "mustardui.registeruifile"
    bl_label = "Register the UI"
    
    register: bpy.props.BoolProperty(default = True)
    
    @classmethod
    def poll(cls, context):
        
        res, obj = mustardui_active_object(context, config = 0)
        
        return res
    
    def execute(self, context):
        
        res, obj = mustardui_active_object(context, config = 0)
        
        #filename = re.search('mustard_ui.py', os.path.basename(__file__)).group(1)
        
        if self.register:
            try:
                obj.MustardUI_script_file = bpy.data.texts['mustard_ui.py']
            except:
                self.report({'ERROR'}, "MustardUI: Can not register UI in " + obj.name + ". Change the script name to \'mustard_ui.py\'.")
                return {'FINISHED'}
            bpy.data.texts['mustard_ui.py'].use_module = True
            self.report({'INFO'}, "MustardUI: UI correctly registered in " + obj.name)
        else:
            obj.MustardUI_script_file.use_module = False
            obj.MustardUI_script_file = None
            self.report({'INFO'}, "MustardUI: UI correctly un-registered in " + obj.name)
        
        return {'FINISHED'}

# ------------------------------------------------------------------------
#    Outfit visibility operator
# ------------------------------------------------------------------------

# Operator to shiwtch visibility of an object
class MustardUI_OutfitVisibility(bpy.types.Operator):
    """Chenge the visibility of the selected object"""
    bl_idname = "mustardui.object_visibility"
    bl_label = "Hide/Unhide Object visibility"
    bl_options = {'UNDO'}
    
    obj : bpy.props.StringProperty()

    def execute(self, context):
        
        bpy.data.objects[self.obj].hide_viewport = not bpy.data.objects[self.obj].hide_viewport
        bpy.data.objects[self.obj].hide_render = bpy.data.objects[self.obj].hide_viewport
        bpy.data.objects[self.obj].MustardUI_outfit_visibility = bpy.data.objects[self.obj].hide_viewport
        
        poll, obj = mustardui_active_object(context, config = 0)
        rig_settings = obj.MustardUI_RigSettings
        armature_settings = obj.MustardUI_ArmatureSettings
        
        if rig_settings.extras_collection != None:
            rig_settings.extras_collection.hide_viewport = len([x for x in rig_settings.extras_collection.objects if not x.hide_render]) == 0
            rig_settings.extras_collection.hide_render = rig_settings.extras_collection.hide_viewport
        
        if rig_settings.model_body:
            for modifier in rig_settings.model_body.modifiers:
                if modifier.type == "MASK" and self.obj in modifier.name and rig_settings.outfits_global_mask:
                    modifier.show_viewport = not bpy.data.objects[self.obj].hide_viewport
                    modifier.show_render = not bpy.data.objects[self.obj].hide_viewport
        else:
            self.report({'WARNING'}, 'MustardUI - Outfit Body has not been specified.')
        
        if len(armature_settings.layers) > 0:
            outfit_armature_layers = [x for x in range(0,32) if armature_settings.layers[x].outfit_switcher_enable and armature_settings.layers[x].outfit_switcher_collection != None]

            for i in outfit_armature_layers:
                for object in [x for x in armature_settings.layers[i].outfit_switcher_collection.objects]:
                    if object == armature_settings.layers[i].outfit_switcher_object:
                        armature_settings.layers[i].show = not bpy.data.objects[object.name].hide_viewport and not armature_settings.layers[i].outfit_switcher_collection.hide_viewport
        
        return {'FINISHED'}

# ------------------------------------------------------------------------
#    Outfit Optimization Button
# ------------------------------------------------------------------------

class MustardUI_GlobalOutfitPropSwitch(bpy.types.Operator):
    """Enable/disable all modifiers/functions that might impact on viewport performance"""
    bl_idname = "mustardui.switchglobal_outfits"
    bl_label = ""
    
    enable: IntProperty(default=False)
    
    def execute(self, context):
        
        poll, obj = mustardui_active_object(context, config = 0)
        rig_settings = obj.MustardUI_RigSettings
        
        rig_settings.outfits_global_subsurface = self.enable
        rig_settings.outfits_global_smoothcorrection = self.enable
        rig_settings.outfits_global_shrinkwrap = self.enable
        rig_settings.outfits_global_mask = self.enable
        rig_settings.outfits_global_solidify = self.enable
        rig_settings.outfits_global_triangulate = self.enable
        rig_settings.outfits_global_normalautosmooth = self.enable
        
        return {'FINISHED'}

# ------------------------------------------------------------------------
#    Tools - ChildOf Parent
# ------------------------------------------------------------------------

class MustardUI_Tools_ChildOf(bpy.types.Operator):
    """Apply Child Of modifier"""
    bl_idname = "mustardui.tools_childof"
    bl_label = "Apply Child Of modifier"
    bl_options = {'REGISTER'}
    
    clean: IntProperty(name='CLEAN',
        description="Clean action",
        default=0
    )

    def execute(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        
        poll, arm = mustardui_active_object(context, config = 0)
        tools_settings = arm.MustardUI_ToolsSettings
        
        if self.clean==0:
        
            ob = bpy.context.active_object
        
            if len(bpy.context.selected_pose_bones)==2:
                
                if bpy.context.selected_pose_bones[0].id_data == bpy.context.selected_pose_bones[1].id_data:
                    parent_bone = bpy.context.selected_pose_bones[0]
                    child_bone = bpy.context.selected_pose_bones[1]
                else:
                    parent_bone = bpy.context.selected_pose_bones[1]
                    child_bone = bpy.context.selected_pose_bones[0]
                
                if ob == child_bone.id_data:
        
                    constr = child_bone.constraints.new('CHILD_OF')
                    constr.name = tools_settings.childof_constr_name
        
                    constr.target = parent_bone.id_data
                    constr.subtarget = parent_bone.name
            
                    context_py = bpy.context.copy()
                    context_py["constraint"] = constr
            
                    org_layers = ob.data.layers[:]
                    for i in range(len(org_layers)):
                        ob.data.layers[i] = True
            
                    ob.data.bones.active = child_bone.id_data.pose.bones[child_bone.name].bone
            
                    for i in range(len(org_layers)):
                        ob.data.layers[i] = org_layers[i]
        
                    constr.influence = tools_settings.childof_influence
                    
                    self.report({'INFO'}, 'MustardUI - The two selected Bones has been parented.')
        
                else:
                    self.report({'ERROR'}, 'MustardUI - You should select two Bones. No modifier has been added.')
                
            else:
                self.report({'ERROR'}, 'MustardUI - You should select two Bones. No modifier has been added.')
        
        else:
            
            mod_cont = 0
            for obj in bpy.data.objects:
                if obj.type=="ARMATURE":
                    for bone in obj.pose.bones:
                        for constr in bone.constraints:
                            if tools_settings.childof_constr_name in constr.name:
                                bone.constraints.remove(constr)
                                if settings.debug:
                                    print('MustardUI - Constraint of '+bone.name+' in '+obj.name+' successfully removed.')
                                mod_cont = mod_cont + 1
            
            if mod_cont>0:
                self.report({'INFO'}, 'MustardUI - '+str(mod_cont)+" modifiers successfully removed.")
            else:
                self.report({'WARNING'}, 'MustardUI - No modifier was found. None was removed.')
        
        return {'FINISHED'}

# ------------------------------------------------------------------------
#    Tools - Auto-Breath
# ------------------------------------------------------------------------

class MustardUI_Tools_AutoBreath(bpy.types.Operator):
    """Automatically create keyframes for breathing animation"""
    bl_idname = "mustardui.tools_autobreath"
    bl_label = "Auto Breath"
    bl_options = {'REGISTER'}

    def execute(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        
        poll, arm = mustardui_active_object(context, config = 0)
        tools_settings = arm.MustardUI_ToolsSettings
        
        if len(bpy.context.selected_pose_bones) != 1:
            self.report({'ERROR'}, 'MustardUI - You should select one bone only. No key has been added.')
            return {'FINISHED'}
        
        # Check scene settings
        frame_start = context.scene.frame_start
        frame_end = context.scene.frame_end 
        fps = context.scene.render.fps / context.scene.render.fps_base
        context.scene.frame_current = frame_start
        
        # Selected bone
        breath_bone = bpy.context.selected_pose_bones[0]
        
        # Check which transformations are available, and save the rest pose
        lock_loc = [1, 1, 1]
        rest_loc = [0., 0., 0.]
        lock_sca = [1, 1, 1]
        rest_sca = [0., 0., 0.]
        for i in range(3):
            lock_loc[i] = not breath_bone.lock_location[i]
            rest_loc[i] = breath_bone.location[i]
            lock_sca[i] = not breath_bone.lock_scale[i]
            rest_sca[i] = breath_bone.scale[i]
        
        # Check if the bones are complying with definitions of rest pose (value = 1.)
        warning = False
        for i in range(3):
            if lock_loc[i]:
                if breath_bone.location[i] != 1.:
                    warning = True
                    break
            if lock_sca[i]:
                if breath_bone.scale[i] != 1.:
                    warning = True
                    break
        
        # Compute quantities
        freq = 2. * 3.14 * tools_settings.autobreath_frequency/(fps*60)
        amplitude = tools_settings.autobreath_amplitude/2.
        sampling = tools_settings.autobreath_sampling
        rand = tools_settings.autobreath_random
        
        # Create frames
        for frame in range(frame_start, frame_end, sampling):
            
            freq_eff = freq * (1. + random.uniform(-rand,rand) )
            
            factor = (1. - math.cos( freq_eff  * (frame - frame_start) ) ) * amplitude
            
            for i in range(3):
                breath_bone.location[i] = rest_loc[i] * (1. + lock_loc[i] * factor)
                breath_bone.scale[i] = rest_sca[i] * (1 + lock_sca[i] * factor)
            
            if any(lock_loc):
                breath_bone.keyframe_insert(data_path="location", frame=frame)
            if any(lock_sca):
                breath_bone.keyframe_insert(data_path="scale", frame=frame)
        
        if warning:
            self.report({'WARNING'}, 'MustardUI - Initial unlocked transformations should be = 1. Results might be uncorrect')
        else:
            self.report({'INFO'}, 'MustardUI - Auto Breath applied with '+str(breath_bone.name)+".")
        
        return {'FINISHED'}

# ------------------------------------------------------------------------
#    Tools - Auto Blink
# ------------------------------------------------------------------------

class MustardUI_Tools_AutoEyelid(bpy.types.Operator):
    """Automatically create keyframes for eyelid animation"""
    bl_idname = "mustardui.tools_autoeyelid"
    bl_label = "Auto Blink"
    bl_options = {'REGISTER'}
    
    def blinkFrame(self, frame, value, blink_driver, obj, type):
        
        if type == "SHAPE_KEY":
            if blink_driver in obj.data.shape_keys.key_blocks.keys():
                obj.data.shape_keys.key_blocks[blink_driver].value = value
                obj.data.update_tag()
                obj.data.shape_keys.key_blocks[blink_driver].keyframe_insert(data_path='value', index=-1, frame=frame)
                return False
            else:
                return True
        else:
            if blink_driver in obj.keys():
                obj[blink_driver] = value
                obj.update_tag()
                obj.keyframe_insert(data_path='["' + blink_driver + '"]', index=-1, frame=frame)
                return False
            else:
                return True

    def execute(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        
        poll, arm = mustardui_active_object(context, config = 0)
        rig_settings = arm.MustardUI_RigSettings
        tools_settings = arm.MustardUI_ToolsSettings
        
        # Check scene settings
        frame_start = context.scene.frame_start
        frame_end = context.scene.frame_end 
        fps = context.scene.render.fps / context.scene.render.fps_base
        context.scene.frame_current = frame_start

        blink_length_frames = [math.floor(fps * .1), math.ceil(fps * .25 * tools_settings.autoeyelid_blink_length)]  # default: 100 - 250 ms
        blink_chance_per_half_second = 2. * tools_settings.autoeyelid_blink_rate_per_minute / (60 * 2)  # calculated every half second, default: 26
        
        blink_drivers = []
        if tools_settings.autoeyelid_driver_type == "SHAPE_KEY":
            for blink_driver in [tools_settings.autoeyelid_eyeL_shapekey, tools_settings.autoeyelid_eyeR_shapekey]:
                if blink_driver != "":
                    blink_drivers.append(blink_driver)
        else:
            blink_drivers.append(tools_settings.autoeyelid_morph)
        
        error = 0
        
        for frame in range(frame_start, frame_end):
            if frame % fps / 2 == 0:
                r = random.random()
                if r < blink_chance_per_half_second:
                    rl = random.randint(blink_length_frames[0], blink_length_frames[1])
                    blinkStart = frame
                    blinkMid = frame+math.floor(rl/2)
                    blinkEnd = frame+rl
                    if settings.debug:
                        print("MustardUI Auto Blink: Frame: ", frame, " - Blinking start: ", blinkStart, " - Blink Mid: ", blinkMid, " - Blink End:", blinkEnd)
                    for blink_driver in blink_drivers:
                        target_object = rig_settings.model_body if tools_settings.autoeyelid_driver_type == "SHAPE_KEY" else rig_settings.model_armature_object
                        error = error + self.blinkFrame(blinkStart, 0., blink_driver, target_object, tools_settings.autoeyelid_driver_type)
                        error = error + self.blinkFrame(blinkMid,   1., blink_driver, target_object, tools_settings.autoeyelid_driver_type)
                        error = error + self.blinkFrame(blinkEnd,   0., blink_driver, target_object, tools_settings.autoeyelid_driver_type)
        
        if error < 1:
            self.report({'INFO'}, 'MustardUI - Auto Blink applied.')
        else:
            self.report({'ERROR'}, 'MustardUI - Auto Blink shape keys/morph seems to be missing. Results might be corrupted.')
            
        return {'FINISHED'}

# ------------------------------------------------------------------------
#    Tools - Lattice
# ------------------------------------------------------------------------

class MustardUI_Tools_LatticeSetup(bpy.types.Operator):
    """Setup/Clean Lattice modifiers for all model Objects.\nThis function will create (or delete) Lattice modifiers linked with the Lattice object chosen and put it at the top of the modifiers list.\nWhen cleaning, only MustardUI Lattice modifiers are deleted"""
    bl_idname = "mustardui.tools_latticesetup"
    bl_label = "Setup Lattice modification for all model Objects"
    bl_options = {'REGISTER'}
    
    mod: IntProperty(name='MOD',
        description="MOD",
        default=0
    )
    
    @classmethod
    def poll(cls, context):
        
        res, arm = mustardui_active_object(context, config = 1)
        
        # Check if the lattice object is defined
        if arm != None:
            lattice_settings = arm.MustardUI_LatticeSettings
        
            return lattice_settings.lattice_object != None
        
        else:
            return False

    def execute(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, arm = mustardui_active_object(context, config = 1)
        rig_settings = arm.MustardUI_RigSettings
        lattice_settings = arm.MustardUI_LatticeSettings
        
        arm_obj = context.active_object
        
        mod_name = lattice_settings.lattice_modifiers_name + "Body Lattice"
        
        if self.mod==0:
            
            latt = lattice_settings.lattice_object
            
            # Body add
            new_mod = True
            obj = rig_settings.model_body
            for modifier in obj.modifiers:
                if modifier.type == "LATTICE" and modifier.name == mod_name:
                    new_mod=False
            if new_mod and obj.type=="MESH":        
                mod = obj.modifiers.new(name=mod_name, type='LATTICE')
                obj.modifiers[mod_name].object = latt
                bpy.context.view_layer.objects.active = obj
                while obj.modifiers.find(mod_name) != 0:
                    bpy.ops.object.modifier_move_up(modifier=mod_name)
                bpy.context.view_layer.objects.active = arm_obj
            
            # Outfits add
            for collection in [x for x in rig_settings.outfits_collections if x.collection != None]:
                for obj in collection.collection.objects:
                    new_mod = True
                    for modifier in obj.modifiers:
                        if modifier.type == "LATTICE" and modifier.name == mod_name:
                            new_mod=False
                    if new_mod and obj.type=="MESH":        
                        mod = obj.modifiers.new(name=mod_name, type='LATTICE')
                        obj.modifiers[mod_name].object = latt
                        bpy.context.view_layer.objects.active = obj
                        while obj.modifiers.find(mod_name) != 0:
                            bpy.ops.object.modifier_move_up(modifier=mod_name)
                        bpy.context.view_layer.objects.active = arm_obj
            
            self.report({'INFO'}, "MustardUI: Lattice Setup complete")
        
        else:
            
            # Remove body modifier
            obj = rig_settings.model_body
            if obj.type=="MESH" and obj.modifiers.get(mod_name) != None:
                obj.modifiers.remove(obj.modifiers.get(mod_name))
            
            # Remove objects modifiers
            for collection in [x for x in rig_settings.outfits_collections if x.collection != None]:
                for obj in collection.collection.objects:
                    if obj.type=="MESH" and obj.modifiers.get(mod_name) != None:
                        obj.modifiers.remove(obj.modifiers.get(mod_name))
            
            self.report({'INFO'}, "MustardUI: Lattice Uninstallation complete")
        
        return {'FINISHED'}

class MustardUI_Tools_LatticeModify(bpy.types.Operator):
    """Create a custom Lattice shape key"""
    bl_idname = "mustardui.tools_lattice"
    bl_label = "Create a custom Lattice modification"
    bl_options = {'REGISTER'}
    
    mod: IntProperty(name='MOD',
        description="MOD",
        default=0
    )

    def execute(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config = 1)
        rig_settings = obj.MustardUI_RigSettings
        lattice_settings = obj.MustardUI_LatticeSettings
        
        latt = lattice_settings.lattice_object
        
        # Store armature object to use it as active object at the end
        for object in bpy.data.objects:
            if object.data == obj:
                arm_obj = object
        
        shape_key_custom_name = lattice_settings.lattice_modifiers_name +"Custom"
        
        lattice_settings.lattice_mod_status = False
        
        if self.mod==0:
            
            lattice_settings.lattice_mod_status = True
            
            new_key= True
            
            bpy.context.view_layer.objects.active = latt
            
            for key in latt.data.shape_keys.key_blocks:
                key.value = 0.
                if key.name==shape_key_custom_name:
                    new_key=False
                    break
            
            if new_key:
                shapeKey = latt.shape_key_add(from_mix=False)
                shapeKey.name = shape_key_custom_name
            
            lattice_settings.lattice_key_value = 1.
            latt.data.shape_keys.key_blocks[shape_key_custom_name].value = 1.
            index = latt.data.shape_keys.key_blocks.find(shape_key_custom_name)
            latt.active_shape_key_index = index
            latt.hide_viewport = False
            try:
                bpy.ops.object.mode_set(mode='EDIT')
            except:
                bpy.context.view_layer.objects.active = arm_obj
                self.report({'ERROR'}, "MustardUI: Be sure that "+lattice_settings.lattice_object.name+" is not temporarily disabled in viewport (eye icon)!")
                lattice_settings.lattice_mod_status = False
        
        elif self.mod==1:
            
            bpy.context.view_layer.objects.active = latt
            bpy.ops.object.mode_set(mode='OBJECT')
            latt.hide_viewport = True
            bpy.context.view_layer.objects.active = arm_obj
            lattice_settings.lattice_mod_status = False
        
        else:
            
            bpy.context.view_layer.objects.active = latt
            if bpy.context.view_layer.objects.active == latt:
                index = latt.data.shape_keys.key_blocks.find(shape_key_custom_name)
                latt.active_shape_key_index = index
                
                bpy.ops.object.shape_key_remove()
            
                shapeKey = latt.shape_key_add(from_mix=False)
                shapeKey.name = shape_key_custom_name
            
                self.report({'INFO'}, "MustardUI: Custom shape key reset")
            else:
                self.report({'ERROR'}, "MustardUI: Can not select Lattice Object")
            
            bpy.context.view_layer.objects.active = arm_obj 
        
        return {'FINISHED'}

class MustardUI_LatticeSettings(bpy.types.PropertyGroup):
    
    # Poll function for the selection of mesh only in pointer properties
    def poll_lattice(self, object):
        return object.type == 'LATTICE'
    
    lattice_panel_enable: bpy.props.BoolProperty(default = False,
                                            name = "Lattice",
                                            description = "Enable the Lattice tool.\nThis tool will allow a quick creation of shapes that affect all outfits")
    lattice_modifiers_name: bpy.props.StringProperty(default = "MustardUI - ")

    def lattice_enable_update(self, context):
        
        for object in bpy.data.objects:
            for modifier in object.modifiers:
                if modifier.type == "LATTICE" and self.lattice_modifiers_name in modifier.name:
                    modifier.show_render = self.lattice_enable
                    modifier.show_viewport = self.lattice_enable
        return

    # Function to create an array of tuples for lattice keys
    def lattice_keys_list(self, context):
    
        settings = bpy.context.scene.MustardUI_Settings
        
        latt = self.lattice_object
    
        items = [("Base","Base","Base shape.\nThe body without modifications.")]
        
        for key in latt.data.shape_keys.key_blocks:
            if hasattr(key, 'name'):
                if self.lattice_modifiers_name in key.name:
                    nname=key.name[len(self.lattice_modifiers_name):]
                    items.append( (key.name, nname, key.name) )
        
        return items
    
    def lattice_shapekey_update(self, context):
        
        latt = self.lattice_object
        
        for key in latt.data.shape_keys.key_blocks:
            if "MustardUI" in key.name:
                key.value=0.
        
        if self.lattice_keys != "Base":
            self.lattice_key_value = 1.
        
        return

    def lattice_prop_update(self, context):
        
        latt = self.lattice_object
        
        latt.data.interpolation_type_u = self.lattice_interpolation
        latt.data.interpolation_type_v = self.lattice_interpolation
        latt.data.interpolation_type_w = self.lattice_interpolation
        
        if self.lattice_keys != "Base":
            latt.data.shape_keys.key_blocks[self.lattice_keys].value = self.lattice_key_value
        
        return


    lattice_object: bpy.props.PointerProperty(name = "Lattice Object",
                        description = "The Lattice that will be used for body modifications",
                        type = bpy.types.Object,
                        poll = poll_lattice)
    
    lattice_enable: bpy.props.BoolProperty(default = False,
                        name = "Lattice body modification",
                        description = "Enable lattice body modifications.\nDisable if not used to increase viewport performance",
                        update = lattice_enable_update)
    
    lattice_mod_status: bpy.props.BoolProperty(default = False)
    
    lattice_keys: bpy.props.EnumProperty(name = "",
                        description = "Key selected",
                        items = lattice_keys_list,
                        update = lattice_shapekey_update)
    
    lattice_key_value: bpy.props.FloatProperty(default = 0.,
                        min = 0., max = 1.,
                        name = "Deformation Intensity",
                        description = "Intensity of lattice deformation",
                        update = lattice_prop_update)
    
    lattice_interpolation: bpy.props.EnumProperty(name = "",
                        description = "",
                        items = [("KEY_BSPLINE","BSpline","BSpline"),("KEY_LINEAR","Linear","Linear"),("KEY_CARDINAL","Cardinal","Cardinal"),("KEY_CATMULL_ROM","Catmull-Rom","Catmull-Rom")],
                        update = lattice_prop_update)

bpy.utils.register_class(MustardUI_LatticeSettings)
bpy.types.Armature.MustardUI_LatticeSettings = bpy.props.PointerProperty(type = MustardUI_LatticeSettings)

# ------------------------------------------------------------------------
#    Tools - Physics
# ------------------------------------------------------------------------

class MustardUI_Tools_Physics_CreateItem(bpy.types.Operator):
    """Create a physics panel using the selected cage object in the UI"""
    bl_idname = "mustardui.tools_physics_createitem"
    bl_label = "Add the Item to the Physics Items list.\nThis will also create the necessary modifiers and clothes settings"
    bl_options = {'REGISTER'}
    
    @classmethod
    def poll(cls, context):
        
        res, arm = mustardui_active_object(context, config = 1)
        
        # Check if the lattice object is defined
        if arm != None:
            physics_settings = arm.MustardUI_PhysicsSettings
            cage_objects = []
            for el in physics_settings.physics_items:
                cage_objects.append(el.cage_object)
        
            return physics_settings.config_cage_object != None and physics_settings.config_cage_object_pin_vertex_group != "" and not physics_settings.config_cage_object in cage_objects
        
        else:
            return False
    
    def execute(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        
        res, arm = mustardui_active_object(context, config = 1)
        
        arm_obj = context.active_object
        
        rig_settings = arm.MustardUI_RigSettings
        physics_settings = arm.MustardUI_PhysicsSettings
        
        # Show an error if the model body has not been set
        if rig_settings.model_body == None:
            self.report({'ERROR'}, "MustardUI: Can not add the Physics item without a defined Body object")
            return {'FINISHED'}
        
        # Set the modifier name
        mod_name = physics_settings.physics_modifiers_name + physics_settings.config_cage_object.name + " Cage"
        
        # Adding the item to the physics items list
        add_item = physics_settings.physics_items.add()
        add_item.cage_object = physics_settings.config_cage_object
        add_item.cage_object_pin_vertex_group = physics_settings.config_cage_object_pin_vertex_group
        add_item.cage_object_bending_stiff_vertex_group = physics_settings.config_cage_object_bending_stiff_vertex_group
        add_item.MustardUI_preset = physics_settings.config_MustardUI_preset
        
        # Adding modifier to the body
        # Body add
        new_mod = True
        obj = rig_settings.model_body
        for modifier in [x for x in obj.modifiers if x.type == "MESH_DEFORM"]:
            if modifier.object == bpy.data.objects[physics_settings.config_cage_object.name]:
                new_mod = False
        if new_mod and obj.type=="MESH":        
            mod = obj.modifiers.new(name = mod_name, type='MESH_DEFORM')
            mod.object = physics_settings.config_cage_object
            mod.use_dynamic_bind = True
            
            # Move modifier
            arm_mod_id = 0
            for i in range(len(obj.modifiers)):
                if obj.modifiers[i].type == "ARMATURE":
                    arm_mod_id = i
            while obj.modifiers.find(mod_name) > arm_mod_id + 1:
                with context.temp_override(object=obj):
                    bpy.ops.object.modifier_move_up(modifier = mod.name)
            
            with context.temp_override(object=obj):
                bpy.ops.object.meshdeform_bind(modifier=mod.name)
            
            mod.show_viewport = physics_settings.physics_enable
            mod.show_render = physics_settings.physics_enable
        
        # Outfits add
        for collection in [x for x in rig_settings.outfits_collections if x.collection != None]:
            for obj in collection.collection.objects:
                new_mod = True
                for modifier in [x for x in obj.modifiers if x.type == "MESH_DEFORM"]:
                    if modifier.object == bpy.data.objects[physics_settings.config_cage_object.name]:
                        new_mod=False
                if new_mod and obj.type=="MESH":        
                    mod = obj.modifiers.new(name=mod_name, type='MESH_DEFORM')
                    mod.object = physics_settings.config_cage_object
                    mod.use_dynamic_bind = True
                    
                    # Move modifier
                    arm_mod_id = 0
                    for i in range(len(obj.modifiers)):
                        if obj.modifiers[i].type == "ARMATURE":
                            arm_mod_id = i
                    while obj.modifiers.find(mod_name) > arm_mod_id + 1:
                        with context.temp_override(object=obj):
                            bpy.ops.object.modifier_move_up(modifier = mod.name)
                    
                    with context.temp_override(object=obj):
                        bpy.ops.object.meshdeform_bind(modifier=mod.name)
                    
                    mod.show_viewport = physics_settings.physics_enable
                    mod.show_render = physics_settings.physics_enable
        
        # Add cloth modifier to cage and set the settings
        mod_name = physics_settings.physics_modifiers_name + "Cage"
        
        obj = physics_settings.config_cage_object
        for modifier in obj.modifiers:
            if modifier.type == "CLOTH":
                obj.modifiers.remove(obj.modifiers.get(modifier.name))
        
        mod = obj.modifiers.new(name = mod_name, type='CLOTH')
        
        # Quality Steps
        mod.settings.quality = 7
        mod.settings.time_scale = .95
        # Bending model
        mod.settings.bending_model = "ANGULAR"
        # Pin group
        mod.settings.vertex_group_mass = physics_settings.config_cage_object_pin_vertex_group
        
        # Physics settings
        mod.settings.tension_stiffness = 1.
        mod.settings.compression_stiffness = 0.1
        mod.settings.shear_stiffness = 0.02
        mod.settings.bending_stiffness = 0.02
        
        mod.settings.tension_damping = 1.
        mod.settings.compression_damping = 0.1
        mod.settings.shear_damping = 0.02
        mod.settings.bending_damping = 0.02
        
        # Vertex groups
        mod.settings.vertex_group_structural_stiffness = physics_settings.config_cage_object_pin_vertex_group
        mod.settings.vertex_group_shear_stiffness = physics_settings.config_cage_object_pin_vertex_group
        if physics_settings.config_cage_object_bending_stiff_vertex_group != "":
            mod.settings.vertex_group_bending = physics_settings.config_cage_object_bending_stiff_vertex_group
        mod.settings.bending_stiffness_max = 1.
        
        # Internal springs
        mod.settings.use_internal_springs = True
        mod.settings.internal_spring_max_diversion = 45 / 180 * 3.14 # conversion to radians
        mod.settings.internal_spring_normal_check = True
        mod.settings.internal_tension_stiffness = .1
        mod.settings.internal_compression_stiffness = .1
        mod.settings.internal_tension_stiffness_max = .3
        mod.settings.internal_compression_stiffness_max = .3
        
        # Pressure
        mod.settings.use_pressure = True
        mod.settings.uniform_pressure_force = .06
        mod.settings.pressure_factor = 1.
        
        # Gravity factor
        mod.settings.effector_weights.gravity = 0.
        
        # Collisions
        mod.collision_settings.collision_quality = 5
        mod.collision_settings.use_collision = False
        
        while obj.modifiers.find(mod.name) > 0:
            with context.temp_override(object=obj):
                bpy.ops.object.modifier_move_up(modifier = mod.name)
        
        mod.show_viewport = physics_settings.physics_enable
        mod.show_render = physics_settings.physics_enable
        
        physics_settings.config_cage_object = None
        physics_settings.config_cage_object_pin_vertex_group = ""
        physics_settings.config_cage_object_bending_stiff_vertex_group = ""
        
        self.report({'INFO'}, "MustardUI: Physics Item added")
        
        return {'FINISHED'}

class MustardUI_Tools_Physics_DeleteItem(bpy.types.Operator):
    """Delete a physics panel using the selected cage object in the UI"""
    bl_idname = "mustardui.tools_physics_deleteitem"
    bl_label = "Delete a physics panel"
    bl_options = {'REGISTER'}
    
    cage_object_name: StringProperty()
    
    def execute(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        
        res, arm = mustardui_active_object(context, config = 1)
        
        arm_obj = context.active_object
        
        rig_settings = arm.MustardUI_RigSettings
        physics_settings = arm.MustardUI_PhysicsSettings
        
        if self.cage_object_name == "":
            
            item_ID = 0
            for item in physics_settings.physics_items:
                if item.cage_object == None:
                    physics_settings.physics_items.remove(item_ID)
                item_ID = item_ID + 1
            
            self.report({'WARNING'}, "MustardUI: Physics Item list cleaned from un-referenced cages. The modifiers could not be cleaned.")
            
            return {'FINISHED'}
                
        
        # Remove modifiers from the body
        obj = rig_settings.model_body
        for modifier in [x for x in obj.modifiers if x.type == "MESH_DEFORM"]:
            if modifier.object == bpy.data.objects[self.cage_object_name]:
                obj.modifiers.remove(obj.modifiers.get(modifier.name))
        
        # Remove objects modifiers
        for collection in [x for x in rig_settings.outfits_collections if x.collection != None]:
            for obj in collection.collection.objects:
                for modifier in [x for x in obj.modifiers if x.type == "MESH_DEFORM"]:
                    if modifier.object == bpy.data.objects[self.cage_object_name]:
                        obj.modifiers.remove(obj.modifiers.get(modifier.name))
        
        # Remove cloth modifier from the cage
        obj = bpy.data.objects[self.cage_object_name]
        if obj != None:
            for modifier in obj.modifiers:
                if modifier.type == "CLOTH":
                    obj.modifiers.remove(obj.modifiers.get(modifier.name))
        
        remove_ID = 0
        for el in physics_settings.physics_items:
            if el.cage_object.name == self.cage_object_name:
                break
            remove_ID = remove_ID + 1
        
        physics_settings.physics_items.remove(remove_ID)
        
        self.report({'INFO'}, "MustardUI: Physics Item deleted")
        
        return {'FINISHED'}

class MustardUI_Tools_Physics_Clean(bpy.types.Operator):
    """Remove all the physics items"""
    bl_idname = "mustardui.tools_physics_clean"
    bl_label = "Clear the physics items from the list"
    bl_options = {'REGISTER'}
    
    @classmethod
    def poll(cls, context):
        
        res, arm = mustardui_active_object(context, config = 1)
        
        # Check if the lattice object is defined
        if arm != None:
            physics_settings = arm.MustardUI_PhysicsSettings
        
            return len(physics_settings.physics_items) > 0
        
        else:
            return False
    
    def execute(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        
        res, arm = mustardui_active_object(context, config = 1)
        
        arm_obj = context.active_object
        
        rig_settings = arm.MustardUI_RigSettings
        physics_settings = arm.MustardUI_PhysicsSettings
        
        for cage in [x.cage_object for x in physics_settings.physics_items]:
            
            # Remove modifiers from the body
            obj = rig_settings.model_body
            for modifier in [x for x in obj.modifiers if x.type == "MESH_DEFORM"]:
                if modifier.object == cage:
                    obj.modifiers.remove(obj.modifiers.get(modifier.name))
            
            # Remove objects modifiers
            for collection in [x for x in rig_settings.outfits_collections if x.collection != None]:
                for obj in collection.collection.objects:
                    for modifier in [x for x in obj.modifiers if x.type == "MESH_DEFORM"]:
                        if modifier.object == cage:
                            obj.modifiers.remove(obj.modifiers.get(modifier.name))
            
            # Remove cloth modifier from the cage
            obj = cage
            if obj != None:
                for modifier in obj.modifiers:
                    if modifier.type == "CLOTH":
                        obj.modifiers.remove(obj.modifiers.get(modifier.name))
        
        physics_settings.physics_items.clear()
        
        self.report({'INFO'}, "MustardUI: Physics Items removed")
        
        return {'FINISHED'}

class MustardUI_Tools_Physics_ReBind(bpy.types.Operator):
    """Re-bind mesh deform cages to the Body mesh.\nUse this tool if the mesh is deformed after the cage has been modified"""
    bl_idname = "mustardui.tools_physics_rebind"
    bl_label = "Re-bind Cages"
    bl_options = {'REGISTER'}
    
    @classmethod
    def poll(cls, context):
        
        res, arm = mustardui_active_object(context, config = 0)
        
        return arm != None
    
    def execute(self, context):
        
        res, arm = mustardui_active_object(context, config = 0)
            
        rig_settings = arm.MustardUI_RigSettings
        physics_settings = arm.MustardUI_PhysicsSettings
        
        for cage in [x for x in physics_settings.physics_items]:
            
            for collection in [x for x in rig_settings.outfits_collections if x.collection != None]:
                for obj in collection.collection.objects:
                    for modifier in obj.modifiers:
                        if modifier.type == 'MESH_DEFORM':
                            if cage.cage_object == modifier.object:
                                with context.temp_override(object=obj):
                                    bpy.ops.object.meshdeform_bind(modifier=modifier.name)
                               if not modifier.is_bound:
                                    with context.temp_override(object=obj):
                                        bpy.ops.object.meshdeform_bind(modifier=modifier.name)
            
            obj = rig_settings.model_body
            for modifier in rig_settings.model_body.modifiers:
                if modifier.type == 'MESH_DEFORM':
                    if cage.cage_object == modifier.object:
                        with context.temp_override(object=obj):
                            bpy.ops.object.meshdeform_bind(modifier=modifier.name)
                        if not modifier.is_bound:
                            with context.temp_override(object=obj):
                                bpy.ops.object.meshdeform_bind(modifier=modifier.name)
        
        return {'FINISHED'}

class MustardUI_Tools_Physics_SimulateObject(bpy.types.Operator):
    """Bake the physics for the selected object only"""
    bl_idname = "mustardui.tools_physics_simulateobject"
    bl_label = "Bake the physics for the selected object only"
    bl_options = {'REGISTER'}
    
    cage_object_name: StringProperty()
    
    def execute(self, context):
        
        res, arm = mustardui_active_object(context, config = 0)
        
        if arm == None:
            self.report({'ERROR'}, "MustardUI: Uncorrect selected object")
            return {'FINISHED'}
        
        physics_settings = arm.MustardUI_PhysicsSettings
        
        try:
            cage = bpy.data.objects[self.cage_object_name]
            for modifier in cage.modifiers:
                if modifier.type == "CLOTH":
                    cage_cache = modifier.point_cache
                    
            override = {'active_object': cage, 'point_cache': cage_cache}
            if not cage_cache.is_baked:
                bpy.ops.ptcache.bake(override, bake=True)
            else:
                bpy.ops.ptcache.free_bake(override)
            
            self.report({'INFO'}, "MustardUI: Bake procedure complete")
        except:
            self.report({'ERROR'}, "MustardUI: An error occurred while baking physics")
        
        return {'FINISHED'}

# Function for global and single physics item visbility
def mustardui_physics_enable_update(self, context):
        
    res, arm = mustardui_active_object(context, config = 1)
    
    if arm == None:
        return
        
    rig_settings = arm.MustardUI_RigSettings
    physics_settings = arm.MustardUI_PhysicsSettings
    
    for cage in [x for x in physics_settings.physics_items]:
        
        for modifier in cage.cage_object.modifiers:
            if modifier.type == 'CLOTH':
                modifier.show_viewport = physics_settings.physics_enable and cage.physics_enable
                modifier.show_render = physics_settings.physics_enable and cage.physics_enable
    
        for collection in [x for x in rig_settings.outfits_collections if x.collection != None]:
            for obj in collection.collection.objects:
                for modifier in obj.modifiers:
                    if modifier.type == 'MESH_DEFORM':
                        if cage.cage_object == modifier.object:
                            modifier.show_viewport = physics_settings.physics_enable and cage.physics_enable
                            modifier.show_render = physics_settings.physics_enable and cage.physics_enable

        for modifier in rig_settings.model_body.modifiers:
            if modifier.type == 'MESH_DEFORM':
                if cage.cage_object == modifier.object:
                    modifier.show_viewport = physics_settings.physics_enable and cage.physics_enable
                    modifier.show_render = physics_settings.physics_enable and cage.physics_enable
       
    return

# Physics item informations
# Class to store physics item informations
class MustardUI_PhysicsItem(bpy.types.PropertyGroup):
    
    # Property for collapsing rig properties section
    config_collapse: bpy.props.BoolProperty(default = True,
                        name = "")
    
    # Body object
    # Poll function for the selection of mesh only in pointer properties
    def poll_mesh(self, object):
        
        res, obj = mustardui_active_object(context, config = 1)
        physics_settings = obj.MustardUI_PhysicsSettings
        
        cage_objects = []
        for el in physics_settings:
            cage_objects.append(el.cage_object)
        
        return object.type == 'MESH' and not object in cage_objects
    
    cage_object: bpy.props.PointerProperty(type = bpy.types.Object,
                        poll = poll_mesh,
                        name = "Cage",
                        description = "Select the object to use as a cage")

    cage_object_pin_vertex_group: bpy.props.StringProperty(name = "Pin Vertex Group")
    cage_object_bending_stiff_vertex_group: bpy.props.StringProperty(name = "Bending Stiffness Vertex Group")
    
    MustardUI_preset: bpy.props.BoolProperty(default = True,
                        name = "Compact Definitions",
                        description = "Enable compact definitions of physical settings.\nEnable this to substitute tension, compression, shear and bending with more 'human readable' settings")
    
    physics_enable: bpy.props.BoolProperty(default = True,
                        name = "Enable Physics",
                        description = "Enable Physics simulation for this item",
                        update = mustardui_physics_enable_update)
   
    # Physics settings
    
    def physics_settings_update(self, context):
        
        res, arm = mustardui_active_object(context, config = 0)
        
        if arm == None:
            return
        
        physics_settings = arm.MustardUI_PhysicsSettings
        
        mod = None
        for modifier in self.cage_object.modifiers:
            if modifier.type == "CLOTH":
                mod = modifier
        if mod == None:
            print("MustardUI - Error in finding the \'CLOTH\' modifier.")
            return
        
        # Inertia effect
        mod.settings.mass = 0.3 * self.inertia**.5
        
        # Stiffness effect
        mod.settings.uniform_pressure_force = .06 * self.stiffness**1.6
        mod.settings.compression_damping = 0.1  * self.stiffness**.2
        mod.settings.compression_stiffness = .1  * self.stiffness**.2
        mod.settings.bending_stiffness_max = 1. * self.stiffness**1.
        
        # Bounciness effect
        mod.settings.internal_compression_stiffness = 0.1 /self.bounciness
        mod.settings.internal_compression_stiffness_max = mod.settings.internal_compression_stiffness * 3.
        
        return
    
    bounciness: bpy.props.FloatProperty(default = 1.,
                        min = 0.01,
                        name = "Bounciness",
                        update = physics_settings_update)
    stiffness: bpy.props.FloatProperty(default = 1.,
                        min = 0.01,
                        name = "Stiffness",
                        update = physics_settings_update)
    inertia: bpy.props.FloatProperty(default = 1.,
                        min = 0.01,
                        name = "Inertia",
                        update = physics_settings_update)

bpy.utils.register_class(MustardUI_PhysicsItem)

class MustardUI_PhysicsSettings(bpy.types.PropertyGroup):
    
    # Property for collapsing rig properties section
    config_collapse: bpy.props.BoolProperty(default = True,
                        name = "")
    
    # Modifiers name convention
    physics_modifiers_name: bpy.props.StringProperty(default = "MustardUI ")
    
    physics_enable: bpy.props.BoolProperty(default = False,
                        name="Enable Physics",
                        description="Enable/disable physics simulation.\nThis can greatly affect the performance in viewport, therefore enable it only for renderings or checks.\nNote that the baked physics will be deleted if you disable physics",
                        update = mustardui_physics_enable_update)
    
    # Body object
    # Poll function for the selection of mesh only in pointer properties
    def poll_mesh(self, object):
        
        cage_objects = []
        for el in self.physics_items:
            cage_objects.append(el.cage_object)
        
        return object.type == 'MESH' and not object in cage_objects
    
    config_cage_object: bpy.props.PointerProperty(type = bpy.types.Object,
                        poll = poll_mesh,
                        name = "Cage",
                        description = "Select the object to use as a cage")
    
    config_cage_object_pin_vertex_group: bpy.props.StringProperty(name = "Pin Vertex Group")
    config_cage_object_bending_stiff_vertex_group: bpy.props.StringProperty(name = "Bending Stiffness Vertex Group")
    
    config_MustardUI_preset: bpy.props.BoolProperty(default = True,
                        name = "Compact Definitions",
                        description = "Enable compact definitions of physical settings.\nEnable this to substitute tension, compression, shear and bending with more 'human readable' settings")
    
    # Function to create an array of tuples for Outfit enum collections
    def physics_items_list_make(self, context):
        
        res, arm = mustardui_active_object(context, config = 1)
        
        if arm == None:
            return
        
        rig_settings = arm.MustardUI_RigSettings
        naming_conv = rig_settings.model_MustardUI_naming_convention
        
        items = []
        
        for cage in self.physics_items:
            if cage.cage_object != None:
                if naming_conv:
                    nname = cage.cage_object.name[len(rig_settings.model_name + ' Physics - '):]
                else:
                    nname = cage.cage_object.name
                items.append( (cage.cage_object.name, nname, cage.cage_object.name) )
        
        items = sorted(items)
        
        return items
    
    def simulation_update(self, context):
        
        mod_name = self.physics_modifiers_name + "Cage"
        
        for cage in [x.cage_object for x in self.physics_items if x.cage_object != None]:
            mod = None
            for modifier in cage.modifiers:
                if modifier.type == "CLOTH":
                    mod = modifier
                
                if mod == None:
                    print("MustardUI - Error in finding the \'CLOTH\' modifier: " + mod_name)
                    return
                
                mod.settings.quality = self.simulation_quality
                mod.collision_settings.collision_quality = self.simulation_quality_collision
                
                mod.point_cache.frame_start = self.simulation_start
                mod.point_cache.frame_end = self.simulation_end
        
        for object in bpy.data.objects:
            
            for modifier in object.modifiers:
                
                if modifier.type == "CLOTH":
                    mod = modifier
                    
                    mod.settings.quality = self.simulation_quality
                    mod.collision_settings.collision_quality = self.simulation_quality_collision
                    
                    mod.point_cache.frame_start = self.simulation_start
                    mod.point_cache.frame_end = self.simulation_end
                
        return
    
    physics_items: bpy.props.CollectionProperty(type = MustardUI_PhysicsItem)
    
    physics_items_list: bpy.props.EnumProperty(name = "Physics Items",
                        items = physics_items_list_make)
    
    # Simulation properties
    simulation_start: bpy.props.IntProperty(default = 1,
                        name = "Simulation Start",
                        description = "Frame on which the simulation starts",
                        update = simulation_update)
    
    simulation_end: bpy.props.IntProperty(default = 250,
                        name = "Simulation End",
                        description = "Frame on which the simulation stops",
                        update = simulation_update)
        
    simulation_quality: bpy.props.IntProperty(default = 5,
                        name = "Quality",
                        description = "Quality of the simulation in steps per frame (higher is better quality but slower)",
                        update = simulation_update)
    
    simulation_quality_collision: bpy.props.IntProperty(default = 2,
                        name = "Collision Quality",
                        update = simulation_update)
    
bpy.utils.register_class(MustardUI_PhysicsSettings)
bpy.types.Armature.MustardUI_PhysicsSettings = bpy.props.PointerProperty(type = MustardUI_PhysicsSettings)

# ------------------------------------------------------------------------
#    Normal Maps Optimizer (thanks to theoldben)
# ------------------------------------------------------------------------
# Original implementation: https://github.com/theoldben/BlenderNormalGroups

class MustardUI_Material_NormalMap_Nodes(bpy.types.Operator):
    bl_description = "Switch normal map nodes to a faster custom node"
    bl_idname = 'mustardui.material_normalmap_nodes'
    bl_label = "Normal Map nodes to Custom"
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        return (bpy.data.materials or bpy.data.node_groups)

    def execute(self, context):
        def mirror(new, old):
            """Copy attributes of the old node to the new node"""
            new.parent = old.parent
            new.label = old.label
            new.mute = old.mute
            new.hide = old.hide
            new.select = old.select
            new.location = old.location

            # inputs
            for (name, point) in old.inputs.items():
                input = new.inputs.get(name)
                if input:
                    input.default_value = point.default_value
                    for link in point.links:
                        new.id_data.links.new(link.from_socket, input)

            # outputs
            for (name, point) in old.outputs.items():
                output = new.outputs.get(name)
                if output:
                    output.default_value = point.default_value
                    for link in point.links:
                        new.id_data.links.new(output, link.to_socket)

        def get_custom():
            name = 'Normal Map Optimized'
            group = bpy.data.node_groups.get(name)

            if not group and self.custom:
                group = default_custom_nodes()

            return group

        def set_custom(nodes):
            group = get_custom()
            if not group:
                return

            for node in nodes:
                new = None
                if self.custom:
                    if isinstance(node, bpy.types.ShaderNodeNormalMap):
                        new = nodes.new(type='ShaderNodeGroup')
                        new.node_tree = group
                else:
                    if isinstance(node, bpy.types.ShaderNodeGroup):
                        if node.node_tree == group:
                            new = nodes.new(type='ShaderNodeNormalMap')

                if new:
                    name = node.name
                    mirror(new, node)
                    nodes.remove(node)
                    new.name = name

        for mat in bpy.data.materials:
            set_custom(getattr(mat.node_tree, 'nodes', []))
        for group in bpy.data.node_groups:
            set_custom(group.nodes)

        if (not self.custom) and get_custom():
            bpy.data.node_groups.remove(get_custom())

        return {'FINISHED'}

    custom: bpy.props.BoolProperty(
        name="To Custom",
        description="Set all normals to custom group, or revert back to normal",
        default=True,
    )

def default_custom_nodes():
    use_new_nodes = (bpy.app.version >= (2, 81))

    group = bpy.data.node_groups.new('Normal Map Optimized', 'ShaderNodeTree')

    nodes = group.nodes
    links = group.links

    # Input
    input = group.inputs.new('NodeSocketFloat', 'Strength')
    input.default_value = 1.0
    input.min_value = 0.0
    input.max_value = 1.0
    input = group.inputs.new('NodeSocketColor', 'Color')
    input.default_value = ((0.5, 0.5, 1.0, 1.0))

    # Output
    group.outputs.new('NodeSocketVector', 'Normal')

    # Add Nodes
    frame = nodes.new('NodeFrame')
    frame.name = 'Matrix * Normal Map'
    frame.label = 'Matrix * Normal Map'
    frame.location = Vector((540.0, -80.0))
    frame.hide = False
    frame.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node = nodes.new('ShaderNodeVectorMath')
    node.name = 'Vector Math'
    node.label = ''
    node.parent = frame
    node.hide = True
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.location = Vector((-60.0, 20.0))
    node.operation = 'DOT_PRODUCT'
    node.inputs[0].default_value = (0.5, 0.5, 0.5)  # Vector
    node.inputs[1].default_value = (0.5, 0.5, 0.5)  # Vector
    if use_new_nodes:
        node.inputs[2].default_value = (1.0, 1.0, 1.0)  # Scale
    node = nodes.new('ShaderNodeVectorMath')
    node.name = 'Vector Math.001'
    node.label = ''
    node.parent = frame
    node.hide = True
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.location = Vector((-60.0, -20.0))
    node.operation = 'DOT_PRODUCT'
    node.inputs[0].default_value = (0.5, 0.5, 0.5)  # Vector
    node.inputs[1].default_value = (0.5, 0.5, 0.5)  # Vector
    if use_new_nodes:
        node.inputs[2].default_value = (1.0, 1.0, 1.0)  # Scale
    node = nodes.new('ShaderNodeVectorMath')
    node.name = 'Vector Math.002'
    node.label = ''
    node.parent = frame
    node.hide = True
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.location = Vector((-60.0, -60.0))
    node.inputs[0].default_value = (0.5, 0.5, 0.5)  # Vector
    node.inputs[1].default_value = (0.5, 0.5, 0.5)  # Vector
    if use_new_nodes:
        node.inputs[2].default_value = (1.0, 1.0, 1.0)  # Scale
    node.operation = 'DOT_PRODUCT'
    node = nodes.new('ShaderNodeCombineXYZ')
    node.name = 'Combine XYZ'
    node.label = ''
    node.parent = frame
    node.hide = True
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.location = Vector((100.0, -20.0))
    node.inputs[0].default_value = 0.0  # X
    node.inputs[1].default_value = 0.0  # Y
    node.inputs[2].default_value = 0.0  # Z

    frame = nodes.new('NodeFrame')
    frame.name = 'Generate TBN from Bump Node'
    frame.label = 'Generate TBN from Bump Node'
    frame.location = Vector((-192.01412963867188, -77.50459289550781))
    frame.hide = False
    frame.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node = nodes.new('ShaderNodeUVMap')
    node.name = 'UV Map'
    node.label = ''
    node.parent = frame
    node.hide = True
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.location = Vector((-247.98587036132812, -2.4954071044921875))
    node = nodes.new('ShaderNodeSeparateXYZ')
    node.name = 'UV Gradients'
    node.label = 'UV Gradients'
    node.parent = frame
    node.hide = True
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.location = Vector((-87.98587036132812, -2.4954071044921875))
    node.inputs[0].default_value = (0.0, 0.0, 0.0)  # Vector
    # node.outputs.remove((node.outputs['Z']))
    node = nodes.new('ShaderNodeNewGeometry')
    node.name = 'Normal'
    node.label = 'Normal'
    node.parent = frame
    node.hide = True
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.location = Vector((72.01412963867188, -62.49540710449219))
    # for out in node.outputs:
    #     if out.name not in ['Normal']:
    #         node.outputs.remove(out)
    node = nodes.new('ShaderNodeBump')
    node.name = 'Bi-Tangent'
    node.label = 'Bi-Tangent'
    node.parent = frame
    node.hide = True
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.location = Vector((72.01412963867188, -22.495407104492188))
    node.invert = True
    node.inputs[0].default_value = 1.0  # Strength
    node.inputs[1].default_value = 1000.0  # Distance
    node.inputs[2].default_value = 1.0  # Height
    if use_new_nodes:
        node.inputs[3].default_value = 1.0  # Height_dx
        node.inputs[4].default_value = 1.0  # Height_dy
        node.inputs[5].default_value = (0.0, 0.0, 0.0)  # Normal
    else:
        node.inputs[3].default_value = (0.0, 0.0, 0.0)  # Normal
    # for inp in node.inputs:
    #     if inp.name not in ['Height']:
    #         node.inputs.remove(inp)
    node = nodes.new('ShaderNodeBump')
    node.name = 'Tangent'
    node.label = 'Tangent'
    node.parent = frame
    node.hide = True
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.location = Vector((72.01412963867188, 17.504592895507812))
    node.invert = True
    # for inp in node.inputs:
    #     if inp.name not in ['Height']:
    #         node.inputs.remove(inp)

    frame = nodes.new('NodeFrame')
    frame.name = 'Node'
    frame.label = 'Normal Map Processing'
    frame.location = Vector((180.0, -260.0))
    frame.hide = False
    frame.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node = nodes.new('NodeGroupInput')
    node.name = 'Group Input'
    node.label = ''
    node.parent = frame
    node.hide = True
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.location = Vector((-400.0, 20.0))
    node = nodes.new('ShaderNodeMixRGB')
    node.name = 'Influence'
    node.label = ''
    node.parent = frame
    node.hide = True
    node.location = Vector((-240.0, 20.0))
    node.inputs[1].default_value = (0.5, 0.5, 1.0, 1.0)  # Color1
    node = nodes.new('ShaderNodeVectorMath')
    node.name = 'Vector Math.003'
    node.label = ''
    node.parent = frame
    node.hide = True
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.location = Vector((-80.0, 20.0))
    node.operation = 'SUBTRACT'
    node.inputs[0].default_value = (0.5, 0.5, 0.5)  # Vector
    node.inputs[1].default_value = (0.5, 0.5, 0.5)  # Vector
    if use_new_nodes:
        node.inputs[2].default_value = (1.0, 1.0, 1.0)  # Scale
    # node.inputs.remove(node.inputs[1])
    node = nodes.new('ShaderNodeVectorMath')
    node.name = 'Vector Math.004'
    node.label = ''
    node.parent = frame
    node.hide = True
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.location = Vector((80.0, 20.0))
    node.inputs[0].default_value = (0.5, 0.5, 0.5)  # Vector
    node.inputs[1].default_value = (0.5, 0.5, 0.5)  # Vector
    if use_new_nodes:
        node.inputs[2].default_value = (1.0, 1.0, 1.0)  # Scale

    frame = nodes.new('NodeFrame')
    frame.name = 'Transpose Matrix'
    frame.label = 'Transpose Matrix'
    frame.location = Vector((180.0, -80.0))
    frame.hide = False
    frame.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node = nodes.new('ShaderNodeCombineXYZ')
    node.name = 'Combine XYZ.001'
    node.label = ''
    node.parent = frame
    node.hide = True
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.location = Vector((80.0, 20.0))
    node.inputs[0].default_value = 0.0  # X
    node.inputs[1].default_value = 0.0  # Y
    node.inputs[2].default_value = 0.0  # Z
    node = nodes.new('ShaderNodeCombineXYZ')
    node.name = 'Combine XYZ.002'
    node.label = ''
    node.parent = frame
    node.hide = True
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.location = Vector((80.0, -20.0))
    node.inputs[0].default_value = 0.0  # X
    node.inputs[1].default_value = 0.0  # Y
    node.inputs[2].default_value = 0.0  # Z
    node = nodes.new('ShaderNodeCombineXYZ')
    node.name = 'Combine XYZ.003'
    node.label = ''
    node.parent = frame
    node.hide = True
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.location = Vector((80.0, -60.0))
    node.inputs[0].default_value = 0.0  # X
    node.inputs[1].default_value = 0.0  # Y
    node.inputs[2].default_value = 0.0  # Z
    node = nodes.new('ShaderNodeSeparateXYZ')
    node.name = 'Separate XYZ.001'
    node.label = ''
    node.parent = frame
    node.hide = True
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.location = Vector((-80.0, 20.0))
    node.inputs[0].default_value = (0.0, 0.0, 0.0)  # Vector
    node = nodes.new('ShaderNodeSeparateXYZ')
    node.name = 'Separate XYZ.002'
    node.label = ''
    node.parent = frame
    node.hide = True
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.location = Vector((-80.0, -20.0))
    node.inputs[0].default_value = (0.0, 0.0, 0.0)  # Vector
    node = nodes.new('ShaderNodeSeparateXYZ')
    node.name = 'Separate XYZ.003'
    node.label = ''
    node.parent = frame
    node.hide = True
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.location = Vector((-80.0, -60.0))
    node.inputs[0].default_value = (0.0, 0.0, 0.0)  # Vector

    node = nodes.new('NodeGroupOutput')
    node.name = 'Group Output'
    node.label = ''
    node.location = Vector((840.0, -80.0))
    node.hide = False
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.inputs[0].default_value = (0.0, 0.0, 0.0)  # Normal

    # Connect the nodes
    links.new(nodes['Group Input'].outputs['Strength'], nodes['Influence'].inputs[0])
    links.new(nodes['Group Input'].outputs['Color'], nodes['Influence'].inputs[2])
    links.new(nodes['Influence'].outputs['Color'], nodes['Vector Math.003'].inputs[0])
    links.new(nodes['UV Gradients'].outputs['X'], nodes['Tangent'].inputs['Height'])
    links.new(nodes['UV Gradients'].outputs['Y'], nodes['Bi-Tangent'].inputs['Height'])
    links.new(nodes['UV Map'].outputs['UV'], nodes['UV Gradients'].inputs['Vector'])
    links.new(nodes['Tangent'].outputs['Normal'], nodes['Separate XYZ.001'].inputs[0])
    links.new(nodes['Bi-Tangent'].outputs['Normal'], nodes['Separate XYZ.002'].inputs[0])
    links.new(nodes['Normal'].outputs['Normal'], nodes['Separate XYZ.003'].inputs[0])
    links.new(nodes['Vector Math.004'].outputs['Vector'], nodes['Vector Math'].inputs[1])
    links.new(nodes['Combine XYZ.001'].outputs['Vector'], nodes['Vector Math'].inputs[0])
    links.new(nodes['Vector Math.004'].outputs['Vector'], nodes['Vector Math.001'].inputs[1])
    links.new(nodes['Combine XYZ.002'].outputs['Vector'], nodes['Vector Math.001'].inputs[0])
    links.new(nodes['Vector Math.004'].outputs['Vector'], nodes['Vector Math.002'].inputs[1])
    links.new(nodes['Combine XYZ.003'].outputs['Vector'], nodes['Vector Math.002'].inputs[0])
    links.new(nodes['Vector Math.003'].outputs['Vector'], nodes['Vector Math.004'].inputs[0])
    links.new(nodes['Vector Math.003'].outputs['Vector'], nodes['Vector Math.004'].inputs[1])
    links.new(nodes['Vector Math'].outputs['Value'], nodes['Combine XYZ'].inputs['X'])
    links.new(nodes['Vector Math.001'].outputs['Value'], nodes['Combine XYZ'].inputs['Y'])
    links.new(nodes['Vector Math.002'].outputs['Value'], nodes['Combine XYZ'].inputs['Z'])
    links.new(nodes['Separate XYZ.001'].outputs['X'], nodes['Combine XYZ.001'].inputs['X'])
    links.new(nodes['Separate XYZ.002'].outputs['X'], nodes['Combine XYZ.001'].inputs['Y'])
    links.new(nodes['Separate XYZ.003'].outputs['X'], nodes['Combine XYZ.001'].inputs['Z'])
    links.new(nodes['Separate XYZ.001'].outputs['Y'], nodes['Combine XYZ.002'].inputs['X'])
    links.new(nodes['Separate XYZ.002'].outputs['Y'], nodes['Combine XYZ.002'].inputs['Y'])
    links.new(nodes['Separate XYZ.003'].outputs['Y'], nodes['Combine XYZ.002'].inputs['Z'])
    links.new(nodes['Separate XYZ.001'].outputs['Z'], nodes['Combine XYZ.003'].inputs['X'])
    links.new(nodes['Separate XYZ.002'].outputs['Z'], nodes['Combine XYZ.003'].inputs['Y'])
    links.new(nodes['Separate XYZ.003'].outputs['Z'], nodes['Combine XYZ.003'].inputs['Z'])
    links.new(nodes['Combine XYZ'].outputs['Vector'], nodes['Group Output'].inputs['Normal'])

    return group

# ------------------------------------------------------------------------
#    Clean Model
# ------------------------------------------------------------------------

class MustardUI_CleanModel(bpy.types.Operator):
    """Clean the model to get better performance, at the cost of deleting some features/shape keys/morphs/outfits"""
    bl_idname = "mustardui.cleanmodel"
    bl_label = "Clean Model"
    bl_options = {'UNDO'}
    
    remove_unselected_outfits: bpy.props.BoolProperty(default=False,
                    name = "Delete Unselected Outfits",
                    description = "Remove all the outfits that are not selected in the UI (Outfits list)")
    
    remove_nulldrivers: bpy.props.BoolProperty(default=False,
                    name = "Remove Null Drivers",
                    description = "Remove drivers whose equations are \'0.0\' or \'-0.0\'")
    
    remove_morphs: bpy.props.BoolProperty(default=False,
                    name = "Remove Morphs",
                    description = "Remove all morphs (except JCMs and FACS if not enabled below)")
    remove_morphs_shapekeys: bpy.props.BoolProperty(default=False,
                    name = "Remove Shape Keys",
                    description = "Remove selected morphs shape keys")
    remove_morphs_jcms: bpy.props.BoolProperty(default=False,
                    name = "Remove JCMs",
                    description = "Remove JCMs")
    remove_morphs_facs: bpy.props.BoolProperty(default=False,
                    name = "Remove FACS",
                    description = "Remove FACS")
    
    def isDazFcurve(self, path):
        for string in [":Loc:", ":Rot:", ":Sca:", ":Hdo:", ":Tlo"]:
            if string in path:
                return True
        return False
    
    def remove_props_from_group(self, obj, group, props_removed):
        
        if hasattr(obj, group):
            props = eval("obj." + group)
            idx = []
            for n, prop in enumerate(props):
                prop_name = prop.name
                if not "pJCM" in prop.name or self.remove_morphs_jcms:
                    idx.append(n)
                    props_removed.append(prop.name)
            
            for i in reversed(idx):
                props.remove(i)
        
        return props_removed
    
    def remove_props_from_cat_group(self, obj, group, props_removed):
        
        if hasattr(obj, group):           
            categories = eval("obj." + group) 
            for cat in categories:
                props = cat['morphs']
                idx = []
                for n, prop in enumerate(props):
                    if "name" in prop:
                        prop_name = prop['name']
                        if not "pJCM" in prop_name or self.remove_morphs_jcms:
                            idx.append(n)
                            props_removed.append(prop_name)
                    else:
                        idx.append(n)
                    
                for i in reversed(idx):
                    del props[i]
        
        return props_removed
    
    @classmethod
    def poll(cls, context):
        
        res, arm = mustardui_active_object(context, config = 0)
        
        return res
 
    def execute(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, arm = mustardui_active_object(context, config = 0)
        rig_settings = arm.MustardUI_RigSettings
        
        options = self.remove_nulldrivers or self.remove_morphs or self.remove_unselected_outfits
        
        if not options:
            return {'FINISHED'}
        
        if settings.debug:
            print("MustardUI Clean model statistics")
        
        null_drivers_removed = 0
        morphs_props_removed = 0
        morphs_drivers_removed = 0
        morphs_shapekeys_removed = 0
        outfits_deleted = 0
        outfits_cp_deleted = 0
        
        # Remove null drivers
        if self.remove_nulldrivers:
            
            for obj in [x for x in bpy.data.objects if x.type == "MESH"]:
                if obj.animation_data != None:
                    drivers = obj.animation_data.drivers
                    for driver in drivers:
                        if driver.driver.expression == "0.0" or driver.driver.expression == "-0.0":
                            drivers.remove(driver)
                            null_drivers_removed = null_drivers_removed + 1
                if obj.data.shape_keys != None:
                    if obj.data.shape_keys.animation_data != None:
                        drivers = obj.data.shape_keys.animation_data.drivers
                        for driver in drivers:
                            if driver.driver.expression == "0.0" or driver.driver.expression == "-0.0":
                                drivers.remove(driver)
                                morphs_drivers_removed = morphs_drivers_removed + 1
            
            if settings.debug:
                print("  Null drivers removed: " + str(null_drivers_removed))
        
        # Check diffeomorphic custom morphs existance and delete all of them (except JCMs)
        if self.remove_morphs:
            
            props_removed = []
            
            # Add props to the removed list from the armature
            if self.remove_morphs_jcms:
                props_removed = self.remove_props_from_group(rig_settings.model_armature_object,
                                                            "DazStandardjcms", props_removed)
                props_removed.append("pJCM")
            if self.remove_morphs_facs or rig_settings.diffeomorphic_model_version == "1.5":
                props_removed = self.remove_props_from_group(rig_settings.model_armature_object,
                                                            "DazFacs", props_removed)
                props_removed.append("facs")
            props_removed = self.remove_props_from_group(rig_settings.model_armature_object,
                                                        "DazUnits", props_removed)
            props_removed = self.remove_props_from_group(rig_settings.model_armature_object,
                                                        "DazExpressions", props_removed)
            props_removed = self.remove_props_from_group(rig_settings.model_armature_object,
                                                        "DazBody", props_removed)
            props_removed = self.remove_props_from_group(rig_settings.model_armature_object,
                                                        "DazCustom", props_removed)
            props_removed = self.remove_props_from_group(rig_settings.model_armature_object,
                                                        "DazCustom", props_removed)
            props_removed = self.remove_props_from_cat_group(rig_settings.model_armature_object,
                                                        "DazMorphCats", props_removed)
            
            # Add props to the removed list from the body
            if self.remove_morphs_jcms:
                props_removed = self.remove_props_from_group(rig_settings.model_body,
                                                            "DazStandardjcms", props_removed)
            if self.remove_morphs_facs or rig_settings.diffeomorphic_model_version == "1.5":
                props_removed = self.remove_props_from_group(rig_settings.model_body,
                                                            "DazFacs", props_removed)
            props_removed = self.remove_props_from_group(rig_settings.model_body,
                                                        "DazUnits", props_removed)
            props_removed = self.remove_props_from_group(rig_settings.model_body,
                                                        "DazExpressions", props_removed)
            props_removed = self.remove_props_from_group(rig_settings.model_body,
                                                        "DazBody", props_removed)
            props_removed = self.remove_props_from_group(rig_settings.model_body,
                                                        "DazCustom", props_removed)
            props_removed = self.remove_props_from_cat_group(rig_settings.model_body,
                                                        "DazMorphCats", props_removed)
            
            # Manually append to remove standard expressions and units
            props_removed.append("eJCM")
            props_removed.append("eCTRL")
            
            # Remove unused drivers and shape keys
            aobj = context.active_object
            context.view_layer.objects.active = rig_settings.model_armature_object
            
            # Find objects where to remove drivers and shape keys
            objects = [rig_settings.model_body]
            
            for collection in [x for x in [y for y in rig_settings.outfits_collections if y.collection != None] if x.collection != None]:
                for obj in collection.collection.objects:
                    if obj.type == "MESH":
                        objects.append(obj)
            for obj in rig_settings.extras_collection.objects:
                if obj.type == "MESH":
                    objects.append(obj)
            for obj in bpy.data.objects:
                if obj.find_armature() == rig_settings.model_armature_object and obj.type == "MESH":
                    objects.append(obj)
            
            # Remove shape keys and their drivers
            for obj in objects:
                if obj.data.shape_keys != None:
                    if obj.data.shape_keys.animation_data != None:
                        drivers = obj.data.shape_keys.animation_data.drivers
                        for driver in drivers:
                            words = driver.data_path.split('"')
                            for cp in props_removed:
                                if words[0] == "key_blocks[" and cp in words[1]:
                                    drivers.remove(driver)
                                    morphs_drivers_removed = morphs_drivers_removed + 1
                                    break
                    if self.remove_morphs_shapekeys:
                        for sk in obj.data.shape_keys.key_blocks:
                            for cp in props_removed:
                                if cp in sk.name:
                                    obj.shape_key_remove(sk)
                                    morphs_shapekeys_removed = morphs_shapekeys_removed + 1
                                    break
                
                obj.update_tag()
            
            # Remove drivers from objects
            objects.append(arm)
            for obj in objects:
                if obj.animation_data != None:
                    if obj.animation_data.drivers != None:
                        drivers = obj.animation_data.drivers
                        for driver in drivers:
                            ddelete = "evalMorphs" in driver.driver.expression or driver.driver.expression == "0.0" or driver.driver.expression == "-0.0"
                            for cp in props_removed:
                                ddelete = ddelete or (cp in driver.data_path or self.isDazFcurve(driver.data_path))
                                for v in driver.driver.variables:
                                    ddelete = ddelete or cp in v.targets[0].data_path
                            if ddelete:
                                drivers.remove(driver)
                                morphs_drivers_removed = morphs_drivers_removed + 1
                        obj.update_tag()
            
            # Remove drivers from bones
            for bone in [x for x in rig_settings.model_armature_object.pose.bones if "(drv)" in x.name]:
                bone.driver_remove('location')
                bone.driver_remove('rotation_euler')
                bone.driver_remove('scale')
            
            context.view_layer.objects.active = aobj
            
            # Remove custom properties from armature
            # TODO: avoid removing jaw bone stuffs for facs (thing above is not sufficient)
            for cp in props_removed:
                for kp in [x for x in rig_settings.model_armature_object.keys()]:
                    if cp in kp and (not "pJCM" in kp or self.remove_morphs_jcms) or self.isDazFcurve(kp):      
                        del rig_settings.model_armature_object[kp]
                        morphs_props_removed = morphs_props_removed + 1
                for kp in [x for x in arm.keys()]:
                    if cp in kp and (not "pJCM" in kp or self.remove_morphs_jcms) or self.isDazFcurve(kp):
                        del arm[kp]
                        morphs_props_removed = morphs_props_removed + 1
            
            # Remove diffeomorphic support from the UI to avoid errors in the UI, or restore it if FACS are asked
            if not self.remove_morphs_facs and not rig_settings.diffeomorphic_model_version == "1.5":
                rig_settings.diffeomorphic_morphs_list.clear()
                rig_settings.diffeomorphic_body_morphs = False
                rig_settings.diffeomorphic_emotions = False
                rig_settings.diffeomorphic_emotions_units = False
                bpy.ops.mustardui.configuration()
                bpy.ops.mustardui.dazmorphs_checkmorphs()
                bpy.ops.mustardui.configuration()
            else:
                rig_settings.diffeomorphic_morphs_list.clear()
                rig_settings.diffeomorphic_support = False
            
            if settings.debug:
                print("  Morph properties removed: " + str(morphs_props_removed))
                print("  Morph drivers removed: " + str(morphs_drivers_removed))
                print("  Morph shape keys removed: " + str(morphs_shapekeys_removed))
        
        # Remove unselected outfits
        if self.remove_unselected_outfits:
            
            current_outfit = rig_settings.outfits_list
            
            for col in [x.collection for x in [y for y in rig_settings.outfits_collections if y.collection != None] if x.collection.name != current_outfit]:
                
                # Remove custom properties
                for cpn, cp in enumerate(arm.MustardUI_CustomPropertiesOutfit):
                    if cp.outfit == col:
                        mustardui_clean_prop(arm, arm.MustardUI_CustomPropertiesOutfit, cpn, settings)
                        outfits_cp_deleted = outfits_cp_deleted + 1
                
                for obj in col.objects:
                    data = obj.data
                    obj_type = obj.type
                    bpy.data.objects.remove(obj)
                    if obj_type == "MESH":
                        bpy.data.meshes.remove(data)
                    elif obj_type == "ARMATURE":
                        bpy.data.armatures.remove(data)
                
                bpy.ops.mustardui.delete_outfit(col =  col.name)
                bpy.data.collections.remove(col)
                outfits_deleted = outfits_deleted + 1
            
            rig_settings.outfits_list = current_outfit
            
            if settings.debug:
                print("  Outfits deleted: " + str(outfits_deleted))
                print("  Outfit custom properties deleted: " + str(outfits_cp_deleted))
        
        # Final messages
        operations = null_drivers_removed + morphs_props_removed + morphs_drivers_removed + morphs_shapekeys_removed + outfits_deleted + outfits_cp_deleted
        
        if operations > 0:
            self.report({'INFO'}, "MustardUI - Model cleaned.")
            rig_settings.model_cleaned = True
        else:
            self.report({'WARNING'}, "MustardUI - No operation was needed with current cleaning settings.")
        
        return{'FINISHED'}
    
    def invoke(self, context, event):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config = 0)
        rig_settings = obj.MustardUI_RigSettings
        
        return context.window_manager.invoke_props_dialog(self, width = 500)
            
    def draw(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config = 0)
        rig_settings = obj.MustardUI_RigSettings
        sec_obj = rig_settings.body_custom_properties_sections
        
        layout = self.layout
        
        box = layout.box()
        box.label(text="Notes:")
        box.label(text="Read the descriptions of all buttons (keep the mouse on the buttons).", icon="DOT")
        box.label(text="Do not use while producing, but before starting a project with the model.", icon="DOT")
        box.label(text="This is a highly destructive operation! Use it at your own risk!", icon="ERROR")
        
        box = layout.box()
        box.label(text="General", icon="MODIFIER")
        box.prop(self, "remove_unselected_outfits")
        if self.remove_unselected_outfits:
            box.label(text="Outfits objects will be deleted!", icon="ERROR")
            box.label(text="Save and restart Blender (repeat two times) to remove unused data", icon="BLANK1")
        box.prop(self, "remove_nulldrivers")
        
        if rig_settings.diffeomorphic_support:
            
            if not hasattr(rig_settings.model_armature_object, "DazMorphCats"):
                box = layout.box()
                box.label(text="Diffeomorphic is needed to clean morphs!", icon="ERROR")
        
            box = layout.box()
            box.label(text="Diffeomorphic Morphs", icon="DOCUMENTS")
            box.enabled = hasattr(rig_settings.model_armature_object, "DazMorphCats")
            box.prop(self, "remove_morphs")
            if self.remove_morphs:
                box.label(text="Morphs will be deleted!", icon="ERROR")
                box.label(text="Some bones of the Face rig might not work even if Remove Face Rig Morphs is disabled!", icon="BLANK1")
            if rig_settings.diffeomorphic_model_version == "1.6":
                row = box.row()
                row.enabled = self.remove_morphs
                row.prop(self, "remove_morphs_facs", text = "Remove Face Rig Morphs")
            row = box.row()
            row.enabled = self.remove_morphs
            row.prop(self, "remove_morphs_jcms", text = "Remove Corrective Morphs")
            row = box.row()
            row.enabled = self.remove_morphs
            row.prop(self, "remove_morphs_shapekeys")

# ------------------------------------------------------------------------
#    Debug 
# ------------------------------------------------------------------------

class MustardUI_Debug_Log(bpy.types.Operator):
    """Create a file with informations to debug errors.\nThis tool will only write on a .txt file and will NOT change any model or Blender setting"""
    bl_idname = "mustardui.debug_log"
    bl_label = "Create a file with informations to debug errors"
    bl_options = {'REGISTER'}
    
    def new_line(self):
        return "\n"
    
    def tab(self):
        return "\t"
    
    def bar(self):
        return "---------------------------------------------" + self.new_line()
    
    def header(self, name):
        return self.bar() + name + self.new_line() + self.new_line()
    
    def addon_status(self, status, addon_name):
        if status == 2:
            return addon_name + " status:"  + self.tab() + "Correctly installed and enabled" + self.new_line()
        elif status == 1:
            return addon_name + " status:"  + self.tab() + "Installed but not enabled" + self.new_line()
        else:
            return addon_name + " status:"  + self.tab() + "Not correctly installed or wrong add-on folder name" + self.new_line()
            
    
    @classmethod
    def poll(cls, context):
        
        res, arm = mustardui_active_object(context, config = 1)
        
        return arm != None

    def execute(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, arm = mustardui_active_object(context, config = 1)
        rig_settings = arm.MustardUI_RigSettings
        physics_settings = arm.MustardUI_PhysicsSettings
        
        log = ""
        
        # Create logs
        
        # System
        log += self.header("System")
        
        log += "Blender version:" + self.tab() + bpy.app.version_string
        log += self.new_line()
        
        if bpy.context.preferences.addons['cycles']:
            
            device_type = bpy.context.preferences.addons['cycles'].preferences.compute_device_type
            
            log += "Device type:" + self.tab() + self.tab() + device_type
            log += self.new_line()
            
            log += "Devices"
            log += self.new_line()
            for device in [x for x in bpy.context.preferences.addons['cycles'].preferences.devices if (x.type == device_type or x.type == "CPU")]:
                log += self.tab() + '- '
                if device.use:
                    log += "[active] "
                log += device.name
                log += self.new_line()
        
        log += self.new_line()
        
        # Model
        log += self.header("Model")
        
        log += "Model name:" + self.tab() + self.tab() + rig_settings.model_name
        log += self.new_line()
        if rig_settings.model_version!='':
            log += "Model version:" + self.tab() + self.tab() + rig_settings.model_version
            log += self.new_line()
        log += "MustardUI version:" + self.tab() + str(bl_info["version"][0]) + '.' + str(bl_info["version"][1]) + '.' + str(bl_info["version"][2])
        log += self.new_line()
        log += "Model rig type:" + self.tab() + self.tab() + rig_settings.model_rig_type
        log += "Model cleaned:" + self.tab() + self.tab() + str(rig_settings.model_cleaned)
        
        log += self.new_line()
        log += self.new_line()
        
        # Diffeomorphic
        if rig_settings.diffeomorphic_support:
            log += self.header("Diffeomorphic")
            
            log += self.addon_status(settings.status_diffeomorphic, "Diffeomorphic")
            
            if settings.status_diffeomorphic > 1:
                log += "Diffeomorphic version:"  + self.tab() + str(settings.status_diffeomorphic_version[0]) + '.' + str(settings.status_diffeomorphic_version[1]) + '.' + str(settings.status_diffeomorphic_version[2])
                log += self.new_line()
            
            log += self.addon_status(settings.status_mhx, "MHX Addon")
            
            log += self.new_line()
            log += self.new_line()
        
        # Viewport performance
        log += self.header("Viewport performance")
        
        log += "Custom normals:" + self.tab() + self.tab() + ("Disabled" if settings.material_normal_nodes else "Enabled")
        log += self.new_line()
        
        if rig_settings.diffeomorphic_support and settings.status_diffeomorphic > 1:
            log += "External Morphs:" + self.tab() + ("Enabled" if rig_settings.diffeomorphic_enable else "Disabled")
            log += self.new_line()
        if len(physics_settings.physics_items)>0:
            log += "Physics:" + self.tab() + self.tab() + ("Enabled" if physics_settings.physics_enable else "Disabled")
            log += self.new_line()
        
        if rig_settings.hair_collection != None:
            log += "Hair status:" + self.tab() + self.tab() + ("Hidden" if rig_settings.hair_collection.hide_viewport else "Shown")
            log += self.new_line()
        if rig_settings.extras_collection != None:
            log += "Extras status:" + self.tab() + self.tab() + ("Hidden" if rig_settings.extras_collection.hide_viewport else "Shown")
            log += self.new_line()
        
        log += self.new_line()
        
        # Write to file
        try:
            abs_path = bpy.context.blend_data.filepath[:bpy.context.blend_data.filepath.rfind('\\')] + '\\'
            log_file = open(abs_path+'mustardui_log.txt','w')
            log_file.write(log)
            log_file.close()
            
            self.report({'INFO'}, "MustardUI - An log file 'mustardui_log.txt' has been created in the model folder.")
        except:
            self.report({'WARNING'}, "MustardUI - Cannot create a log file. Try to run Blender with admin privilegies.")
        
        return {'FINISHED'}

# ------------------------------------------------------------------------
#    Link (thanks to Mets3D)
# ------------------------------------------------------------------------

class MustardUI_LinkButton(bpy.types.Operator):
    """Open links in a web browser"""
    bl_idname = "mustardui.openlink"
    bl_label = "Open Link in web browser"
    bl_options = {'REGISTER'}
    
    url: StringProperty(name='URL',
        description="URL",
        default="http://blender.org/"
    )

    def execute(self, context):
        webbrowser.open_new(self.url) # opens in default browser
        return {'FINISHED'}

# ------------------------------------------------------------------------
#    Panel
# ------------------------------------------------------------------------

# MustardUI Menu
class MainPanel:
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MustardUI"

# Choose model panel
class PANEL_PT_MustardUI_SelectModel(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_SelectModel"
    bl_label = "Model Selection"
    
    @classmethod
    def poll(cls, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, arm = mustardui_active_object(context, config = 0)
        return res and len([x for x in bpy.data.armatures if x.MustardUI_created])>1 and not settings.viewport_model_selection

    def draw(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        
        layout = self.layout
        
        for armature in [x for x in bpy.data.armatures if x.MustardUI_created]:
            layout.operator('mustardui.switchmodel', text=armature.MustardUI_RigSettings.model_name, depress = armature == settings.panel_model_selection_armature).model_to_switch = armature.name

# Initial configuration panel (for creators)
class PANEL_PT_MustardUI_InitPanel(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_InitPanel"
    bl_label = "UI Configuration"
    
    @classmethod
    def poll(cls, context):
        
        res, arm = mustardui_active_object(context, config = 1)
        return res
    
    def draw(self, context):
        
        layout = self.layout
        scene = context.scene
        
        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config = 1)
        rig_settings = obj.MustardUI_RigSettings
        armature_settings = obj.MustardUI_ArmatureSettings
        tools_settings = obj.MustardUI_ToolsSettings
        lattice_settings = obj.MustardUI_LatticeSettings
        physics_settings = obj.MustardUI_PhysicsSettings
        
        row_scale = 1.2
        
        row = layout.row(align=False)
        row.label(text=obj.name, icon = "OUTLINER_DATA_ARMATURE")
        row.operator('mustardui.configuration_smartcheck', icon = "VIEWZOOM", text = "")
        
        box = layout.box()
        box.prop(rig_settings,"model_name", text = "Name")
        box.prop(rig_settings,"model_body", text = "Body")
        
        layout.separator()
        layout.label(text="Settings",icon="MENU_PANEL")
        
        # Body mesh settings
        row = layout.row(align=False)
        row.prop(rig_settings, "body_config_collapse", icon="TRIA_DOWN" if not rig_settings.body_config_collapse else "TRIA_RIGHT", icon_only=True, emboss=False)
        row.label(text="Body",icon="OUTLINER_OB_ARMATURE")
        
        if not rig_settings.body_config_collapse:
            box = layout.box()
            box.label(text="Global properties", icon="MODIFIER")
            col = box.column(align=True)
            col.prop(rig_settings,"body_enable_subdiv")
            col.prop(rig_settings,"body_enable_smoothcorr")
            col.prop(rig_settings,"body_enable_norm_autosmooth")
            col.prop(rig_settings,"body_enable_material_normal_nodes")
            col.prop(rig_settings,"body_enable_preserve_volume")
            
            # Custom properties
            box = layout.box()
            row = box.row()
            row.label(text="Custom properties", icon="PRESET_NEW")
            row.operator('mustardui.property_smartcheck', text = "", icon = "VIEWZOOM")
            
            if len(obj.MustardUI_CustomProperties) > 0:
                row = box.row()
                row.template_list("MUSTARDUI_UL_Property_UIList", "The_List", obj,
                                  "MustardUI_CustomProperties", scene, "mustardui_property_uilist_index")
                col = row.column()
                col.operator('mustardui.property_settings', icon = "PREFERENCES", text = "").type = "BODY"
                col.separator()
                col2 = col.column(align = True)
                opup   = col2.operator('mustardui.property_switch', icon = "TRIA_UP", text = "")
                opup.direction = "UP"
                opup.type = "BODY"
                opdown = col2.operator('mustardui.property_switch', icon = "TRIA_DOWN", text = "")
                opdown.direction = "DOWN"
                opdown.type = "BODY"
                col.separator()
                col.operator('mustardui.property_remove', icon = "X", text = "").type = "BODY"
                
                col = box.column(align=True)
                col.prop(rig_settings, 'body_custom_properties_icons')
                col.prop(rig_settings, 'body_custom_properties_name_order')
                
            else:
                box = box.box()
                box.label(text = "No property added yet", icon = "ERROR")
            
            if len(obj.MustardUI_CustomProperties) > 0:
                box = layout.box()
                row = box.row(align = False)
                row.label(text = "Sections", icon = "LINENUMBERS_OFF")
                if len(rig_settings.body_custom_properties_sections) == 0:
                    box.operator('mustardui.body_addsection')
                else:
                    box = box.box()
                    row.operator('mustardui.body_addsection', text="", icon ="ADD")
                    section_len = len(rig_settings.body_custom_properties_sections)
                    for i_sec in sorted([x for x in range(0,section_len)], key = lambda x:rig_settings.body_custom_properties_sections[x].id):
                        section = rig_settings.body_custom_properties_sections[i_sec]
                        row = box.row(align = False)
                        row.label(text = section.name, icon = section.icon if (section.icon != "" and section.icon != "NONE") else "DOT")
                        row.operator('mustardui.body_propertyaddtosection', text = "", icon = "PRESET").section_name = section.name
                        row.operator('mustardui.body_settingssection', text = "", icon = "PREFERENCES").name = section.name
                        row2 = row.row(align = True)
                        col = row2.column(align = True)
                        col.enabled = section.id > 0
                        swap_up = col.operator('mustardui.body_swapsection', text = "", icon = "TRIA_UP")
                        swap_up.name = section.name
                        swap_up.mod = True
                        col = row2.column(align = True)
                        col.enabled = section.id < section_len - 1
                        swap_down = col.operator('mustardui.body_swapsection', text = "", icon = "TRIA_DOWN")
                        swap_down.name = section.name
                        swap_down.mod = False
                        row.operator('mustardui.body_deletesection', text = "", icon = "X").name = section.name
        
        # Outfits properties
        row = layout.row(align=False)
        row.prop(rig_settings, "outfit_config_collapse", icon="TRIA_DOWN" if not rig_settings.outfit_config_collapse else "TRIA_RIGHT", icon_only=True, emboss=False)
        row.label(text="Outfits",icon="MOD_CLOTH")
        
        if not rig_settings.outfit_config_collapse:
            box = layout.box()
            box.label(text="General settings", icon="MODIFIER")
            col = box.column(align=True)
            col.prop(rig_settings,"outfit_nude")
            col.prop(rig_settings,"outfit_additional_options")
            if len([x for x in rig_settings.outfits_collections if x.collection != None])>0:
                box = layout.box()
                # Outfit list
                box.label(text="Outfits List", icon="OUTLINER_COLLECTION")
                box = box.box()
                for collection in [x for x in rig_settings.outfits_collections if x.collection != None]:
                    row = box.row()
                    row.label(text=collection.collection.name)
                    del_col = row.operator("mustardui.delete_outfit",text="",icon="X").col = collection.collection.name
                
                # Custom properties
                box = layout.box()
                row = box.row()
                row.label(text="Custom properties", icon="PRESET_NEW")
                
                if len(obj.MustardUI_CustomPropertiesOutfit) > 0:
                    row = box.row()
                    row.template_list("MUSTARDUI_UL_Property_UIListOutfits", "The_List", obj,
                                      "MustardUI_CustomPropertiesOutfit", scene, "mustardui_property_uilist_outfits_index")
                    col = row.column()
                    col.operator('mustardui.property_settings', icon = "PREFERENCES", text = "").type = "OUTFIT"
                    col.separator()
                    col2 = col.column(align = True)
                    opup   = col2.operator('mustardui.property_switch', icon = "TRIA_UP", text = "")
                    opup.direction = "UP"
                    opup.type = "OUTFIT"
                    opdown = col2.operator('mustardui.property_switch', icon = "TRIA_DOWN", text = "")
                    opdown.direction = "DOWN"
                    opdown.type = "OUTFIT"
                    col.separator()
                    col.operator('mustardui.property_remove', icon = "X", text = "").type = "OUTFIT"
                    
                    col = box.column(align=True)
                    col.prop(rig_settings, 'outfit_custom_properties_icons')
                    col.prop(rig_settings, 'outfit_custom_properties_name_order')
                    
                else:
                    box = box.box()
                    box.label(text = "No property added yet", icon = "ERROR")
                
                # Outfit properties
                box = layout.box()
                box.label(text="Global properties", icon="MODIFIER")
                col = box.column(align=True)
                col.prop(rig_settings,"outfits_enable_global_subsurface")
                col.prop(rig_settings,"outfits_enable_global_smoothcorrection")
                col.prop(rig_settings,"outfits_enable_global_shrinkwrap")
                col.prop(rig_settings,"outfits_enable_global_mask")
                col.prop(rig_settings,"outfits_enable_global_solidify")
                col.prop(rig_settings,"outfits_enable_global_triangulate")
                col.prop(rig_settings,"outfits_enable_global_normalautosmooth")
            
            else:
                box = layout.box()
                box.label(text="No Outfits added yet.", icon="ERROR")
            
            box = layout.box()
            
            # Extras list
            box.label(text="Extras", icon="PLUS")
            box.prop(rig_settings,"extras_collection", text="")
            box.prop(rig_settings,"extras_collapse_enable")
        
        # Hair
        row = layout.row(align=False)
        row.prop(rig_settings, "hair_config_collapse", icon="TRIA_DOWN" if not rig_settings.hair_config_collapse else "TRIA_RIGHT", icon_only=True, emboss=False)
        row.label(text="Hair",icon="STRANDS")
        
        if not rig_settings.hair_config_collapse:
            box = layout.box()
            box.label(text="Hair Collection", icon="OUTLINER_COLLECTION")
            box.prop(rig_settings,"hair_collection", text="")
            
            if rig_settings.hair_collection != None:
                if len(rig_settings.hair_collection.objects) > 0:
                    # Custom properties
                    box = layout.box()
                    row = box.row()
                    row.label(text="Custom properties", icon="PRESET_NEW")
                    
                    if len(obj.MustardUI_CustomPropertiesHair) > 0:
                        row = box.row()
                        row.template_list("MUSTARDUI_UL_Property_UIListHair", "The_List", obj,
                                          "MustardUI_CustomPropertiesHair", scene, "mustardui_property_uilist_hair_index")
                        col = row.column()
                        col.operator('mustardui.property_settings', icon = "PREFERENCES", text = "").type = "HAIR"
                        col.separator()
                        col2 = col.column(align = True)
                        opup   = col2.operator('mustardui.property_switch', icon = "TRIA_UP", text = "")
                        opup.direction = "UP"
                        opup.type = "HAIR"
                        opdown = col2.operator('mustardui.property_switch', icon = "TRIA_DOWN", text = "")
                        opdown.direction = "DOWN"
                        opdown.type = "HAIR"
                        col.separator()
                        col.operator('mustardui.property_remove', icon = "X", text = "").type = "HAIR"
                        
                        col = box.column(align=True)
                        col.prop(rig_settings, 'hair_custom_properties_icons')
                        col.prop(rig_settings, 'hair_custom_properties_name_order')
                        
                    else:
                        box = box.box()
                        box.label(text = "No property added yet", icon = "ERROR")
            
            box = layout.box()
            box.label(text="Particle Systems", icon="PARTICLES")
            box.prop(rig_settings,"particle_systems_enable", text="Enable")
        
        # Armature
        row = layout.row(align=False)
        row.prop(armature_settings, "config_collapse", icon="TRIA_DOWN" if not armature_settings.config_collapse else "TRIA_RIGHT", icon_only=True, emboss=False)
        row.label(text="Armature",icon="ARMATURE_DATA")
        
        if not armature_settings.config_collapse:
            box = layout.box()
            
            if len(armature_settings.layers)<1:
                
                box.operator('mustardui.armature_initialize', text = "Add Armature Panel").clean = False
            
            else:
                
                box.label(text="General Settings",icon="MODIFIER")
                box.prop(armature_settings, 'enable_automatic_hair')
                col = box.column()
                row = col.row()
                row.prop(armature_settings, 'enable_ik_fk')
                row = col.row()
                row.enabled = armature_settings.enable_ik_fk
                row.prop(armature_settings, 'enable_ik_fk_snap')
                
                box = layout.box()
                box.label(text="Layers List",icon="PRESET")
                box.prop(armature_settings, 'config_layer', text="")
                
                for i in sorted([x for x in range(0,32) if armature_settings.config_layer[x]], key = lambda x:armature_settings.layers[x].id):
                    box2 = box.box()
                    row = box2.row(align=True)
                    row.prop(armature_settings.layers[i], "layer_config_collapse", icon="TRIA_DOWN" if not armature_settings.layers[i].layer_config_collapse else "TRIA_RIGHT", icon_only=True, emboss=False)
                    if armature_settings.layers[i].name != "":
                        row.label(text="Layer " + str(i) + " (" + armature_settings.layers[i].name + ")")
                    else:
                        row.label(text="Layer " + str(i))
                    
                    # Showing the order ID of the armature layer on the UI for eventual debug purposes
                    if settings.debug:
                        col = row.column(align=True)
                        col.scale_x = 0.4
                        col.label(text="ID: " + str(armature_settings.layers[i].id))
                        
                    col = row.column(align=True)
                    if not armature_settings.layers[i].id > 0:
                        col.enabled = False
                    op_up = col.operator('mustardui.armature_sort', text = "", icon = "TRIA_UP")
                    op_up.up = True
                    op_up.sort_id = armature_settings.layers[i].id
                    
                    col = row.column(align=True)
                    if not armature_settings.layers[i].id < armature_settings.last_id:
                        col.enabled = False
                    op_down = col.operator('mustardui.armature_sort', text = "", icon = "TRIA_DOWN")
                    op_down.up = False
                    op_down.sort_id = armature_settings.layers[i].id
                    
                    if not armature_settings.layers[i].layer_config_collapse:
                        
                        row = box2.row()
                        row.enabled = not armature_settings.layers[i].outfit_switcher_enable
                        row.prop(armature_settings.layers[i],'name')
                        if not armature_settings.layers[i].outfit_switcher_enable:
                            box2.prop(armature_settings.layers[i],'advanced')
                        
                        box2.prop(armature_settings.layers[i],'outfit_switcher_enable')
                        if armature_settings.layers[i].outfit_switcher_enable:
                            box2.prop(armature_settings.layers[i],'outfit_switcher_collection')
                            if armature_settings.layers[i].outfit_switcher_collection != None:
                                box2.prop(armature_settings.layers[i],'outfit_switcher_object')
                        
                        # Mirror options for debug
                        if settings.debug:
                            col = box2.column()
                            col.enabled = False
                            col.prop(armature_settings.layers[i],'mirror')
                            if armature_settings.layers[i].mirror:
                               row = col.row()
                               row.prop(armature_settings.layers[i],'mirror_left')
                               row.prop(armature_settings.layers[i],'mirror_layer')
                
                box = layout.box()
                box.operator('mustardui.armature_initialize', text = "Remove Armature Panel").clean = True
        
        # Physics
        row = layout.row(align=False)
        row.prop(physics_settings, "config_collapse", icon="TRIA_DOWN" if not physics_settings.config_collapse else "TRIA_RIGHT", icon_only=True, emboss=False)
        row.label(text="Physics",icon="PHYSICS")
        
        if not physics_settings.config_collapse:
            
            box = layout.box()
            box.label(text="General Settings",icon="MODIFIER")
            box.operator('mustardui.tools_physics_clean', text = "Clean Physics Panel")
            
            box = layout.box()
            box.label(text="Add Item",icon="ADD")
            
            box.prop(physics_settings,'config_MustardUI_preset')
            box.prop(physics_settings,'config_cage_object')
            if physics_settings.config_cage_object != None:
                box.prop_search(physics_settings,'config_cage_object_pin_vertex_group', physics_settings.config_cage_object,"vertex_groups")
                box.prop_search(physics_settings,'config_cage_object_bending_stiff_vertex_group', physics_settings.config_cage_object,"vertex_groups")
            box.operator('mustardui.tools_physics_createitem', text = "Add item", icon = "ADD")
            
            if len(physics_settings.physics_items) > 0:
                box = layout.box()
                box.label(text="Items List",icon="PRESET")
            
            for item in physics_settings.physics_items:
                
                box2 = box.box()
                
                try:
                    cage_object_name = item.cage_object.name
                    row = box2.row(align=False)
                    row.prop(item, "config_collapse", icon="TRIA_DOWN" if not item.config_collapse else "TRIA_RIGHT", icon_only=True, emboss=False)
                    row.label(text = item.cage_object.name[len(rig_settings.model_name + ' Physics - '):] if rig_settings.model_MustardUI_naming_convention else item.cage_object.name)
                    row.operator('mustardui.tools_physics_deleteitem', text = "", icon = "X").cage_object_name = item.cage_object.name
                except:
                    row = box2.row(align=False)
                    row.label(text = "Item not found.", icon = "ERROR")
                    row.operator('mustardui.tools_physics_deleteitem', text = "", icon = "X").cage_object_name = ""
                    continue
                
                if not item.config_collapse:
                
                    box2.prop(item,'MustardUI_preset')
                    row = box2.row()
                    row.enabled = False
                    row.prop(item,'cage_object')
                    if item.cage_object != None:
                        row = box2.row()
                        row.enabled = False
                        row.prop_search(item,'cage_object_pin_vertex_group', item.cage_object, "vertex_groups")
                        row = box2.row()
                        row.enabled = False
                        row.prop_search(item,'cage_object_bending_stiff_vertex_group', item.cage_object, "vertex_groups")
        
        # Tools
        row = layout.row(align=False)
        row.prop(tools_settings, "tools_config_collapse", icon="TRIA_DOWN" if not tools_settings.tools_config_collapse else "TRIA_RIGHT", icon_only=True, emboss=False)
        row.label(text="Tools",icon="TOOL_SETTINGS")
        
        if not tools_settings.tools_config_collapse:
            box = layout.box()
            box.label(text="Enable Tools", icon="MODIFIER")
            col = box.column(align=True)
            col.prop(tools_settings,'childof_enable')
            col.prop(tools_settings,'autobreath_enable')
            col.prop(tools_settings,'autoeyelid_enable')
            col.prop(tools_settings,'lips_shrinkwrap_enable')
            col.prop(lattice_settings,'lattice_panel_enable')
            
            if tools_settings.autoeyelid_enable:
                box = layout.box()
                box.label(text="Auto Eyelid Tool Settings", icon="HIDE_OFF")
                box.prop(tools_settings,'autoeyelid_driver_type', text="Type")
                col = box.column(align=True)
                if tools_settings.autoeyelid_driver_type == "SHAPE_KEY":
                    col.prop_search(tools_settings, "autoeyelid_eyeL_shapekey", rig_settings.model_body.data.shape_keys, "key_blocks")
                    col.prop_search(tools_settings, "autoeyelid_eyeR_shapekey", rig_settings.model_body.data.shape_keys, "key_blocks")
                else:
                    col.prop(tools_settings, "autoeyelid_morph")
            
            if lattice_settings.lattice_panel_enable:
                box = layout.box()
                box.label(text="Lattice Tool Settings", icon="MOD_LATTICE")
                box.prop(lattice_settings,'lattice_object')
                box.operator('mustardui.tools_latticesetup', text="Lattice Setup").mod = 0
                box.operator('mustardui.tools_latticesetup', text="Lattice Clean").mod = 1
        
        # External addons
        row = layout.row(align=False)
        row.prop(rig_settings, "external_addons_collapse", icon="TRIA_DOWN" if not rig_settings.external_addons_collapse else "TRIA_RIGHT", icon_only=True, emboss=False)
        row.label(text="External Add-ons",icon="DOCUMENTS")
        if not rig_settings.external_addons_collapse:
            box = layout.box()
            box.label(text="Enable Support", icon="MODIFIER")
            row = box.row()
            if settings.status_diffeomorphic != 2:
                row.enabled = False
            row.prop(rig_settings,"diffeomorphic_support")
            if rig_settings.diffeomorphic_support:
                
                box = layout.box()
                if settings.status_diffeomorphic == 1:
                    box.label(icon='ERROR',text="Debug: Diffeomorphic not enabled!")
                elif settings.status_diffeomorphic  == 0:
                    box.label(icon='ERROR', text="Debug: Diffeomorphic not installed!")
                else:
                    box.label(text="Diffeomorphic Settings", icon="OUTLINER_DATA_SURFACE")
                    box2 = box.box()
                    box2.prop(rig_settings, "diffeomorphic_emotions_units")
                    box2.prop(rig_settings, "diffeomorphic_emotions")
                    if rig_settings.diffeomorphic_emotions:
                        row = box2.row(align=True)
                        row.label(text="Custom morphs")
                        row.scale_x = row_scale
                        row.prop(rig_settings, "diffeomorphic_emotions_custom", text = "")
                    box2.prop(rig_settings, "diffeomorphic_facs_emotions_units")
                    box2.prop(rig_settings, "diffeomorphic_facs_emotions")
                    box2.prop(rig_settings, "diffeomorphic_body_morphs")
                    if rig_settings.diffeomorphic_body_morphs:
                        row = box2.row(align=True)
                        row.label(text="Custom morphs")
                        row.scale_x = row_scale
                        row.prop(rig_settings, "diffeomorphic_body_morphs_custom", text = "")
                    
                    box2 = box.box()
                    row = box2.row(align=True)
                    row.label(text="Model Version")
                    row.scale_x = row_scale
                    row.prop(rig_settings, "diffeomorphic_model_version", text="")
                    
                    if rig_settings.diffeomorphic_model_version == "1.5":
                        row = box2.row(align=True)
                        row.label(text="1.5 Support Script")
                        row.scale_x = row_scale
                        row.prop(rig_settings, "diffeomorphic_1_5_script", text="")
                    
                    box = box.box()
                    box.label(text="  Current morphs number: " + str(rig_settings.diffeomorphic_morphs_number))
                    box.operator('mustardui.dazmorphs_checkmorphs')
        
        # Links
        row = layout.row(align=False)
        row.prop(rig_settings, "url_config_collapse", icon="TRIA_DOWN" if not rig_settings.url_config_collapse else "TRIA_RIGHT", icon_only=True, emboss=False)
        row.label(text="Links",icon="WORLD")
        
        if not rig_settings.url_config_collapse:
            box = layout.box()
            
            row = box.row(align=True)
            row.label(text="Website")
            row.scale_x = row_scale
            row.prop(rig_settings,'url_website', text="")
            
            row = box.row(align=True)
            row.label(text="Patreon")
            row.scale_x = row_scale
            row.prop(rig_settings,'url_patreon', text="")
            
            row = box.row(align=True)
            row.label(text="Twitter")
            row.scale_x = row_scale
            row.prop(rig_settings,'url_twitter', text="")
            
            row = box.row(align=True)
            row.label(text="Smutba.se")
            row.scale_x = row_scale
            row.prop(rig_settings,'url_smutbase', text="")
            
            row = box.row(align=True)
            row.label(text="Documentation")
            row.scale_x = row_scale
            row.prop(rig_settings,'url_documentation', text="")
            
            row = box.row(align=True)
            row.label(text="Report Bug")
            row.scale_x = row_scale
            row.prop(rig_settings,'url_reportbug', text="")
        
        # Various properties
        row = layout.row(align=False)
        row.prop(rig_settings, "various_config_collapse", icon="TRIA_DOWN" if not rig_settings.various_config_collapse else "TRIA_RIGHT", icon_only=True, emboss=False)
        row.label(text="Others",icon="SETTINGS")
        if not rig_settings.various_config_collapse:
            
            box = layout.box()
            box.label(text="Naming", icon="OUTLINER_DATA_FONT")
            box.prop(rig_settings,"model_MustardUI_naming_convention")
            box = layout.box()
            
            box.label(text="User informations", icon="INFO")
            row = box.row(align=True)
            row.label(text="Model version")
            row.scale_x = row_scale
            row.prop(rig_settings,"model_version",text="")
        
        if settings.debug:
            row = layout.row(align=False)
            row.prop(rig_settings, "debug_config_collapse", icon="TRIA_DOWN" if not rig_settings.debug_config_collapse else "TRIA_RIGHT", icon_only=True, emboss=False)
            row.label(text="Debug Informations",icon="INFO")
            
            if not rig_settings.debug_config_collapse:
                box = layout.box()
                box.enabled = False
                box.prop(rig_settings,"model_armature_object", text = "Armature Object")
                box.prop(rig_settings,"model_rig_type", text = "Rig Type")
        
        # Configuration button
        layout.separator()
        layout.prop(settings,"debug")
        if not obj.MustardUI_created:
            layout.prop(settings,"viewport_model_selection_after_configuration")
        layout.operator('mustardui.configuration', text="End the configuration")
        

# Panels for users
class PANEL_PT_MustardUI_Body(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Body"
    bl_label = "Body"
    bl_options = {"DEFAULT_CLOSED"}
    
    @classmethod
    def poll(cls, context):
        
        res, arm = mustardui_active_object(context, config = 0)
        
        if arm != None:
            rig_settings = arm.MustardUI_RigSettings
            custom_props = arm.MustardUI_CustomProperties
            
            # Check if there is any property to show
            prop_to_show = rig_settings.body_enable_subdiv or rig_settings.body_enable_smoothcorr or rig_settings.body_enable_norm_autosmooth or rig_settings.body_enable_material_normal_nodes or rig_settings.body_enable_preserve_volume
            
            return res and (prop_to_show or len(custom_props)>0)
        
        else:
            return res

    def draw(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        
        poll, obj = mustardui_active_object(context, config = 0)
        rig_settings = obj.MustardUI_RigSettings
        custom_props = obj.MustardUI_CustomProperties
        
        layout = self.layout
        
        if rig_settings.body_enable_smoothcorr or rig_settings.body_enable_norm_autosmooth or rig_settings.body_enable_material_normal_nodes or rig_settings.body_enable_preserve_volume:
            
            box = layout.box()
            box.label(text="Global settings", icon="OUTLINER_OB_ARMATURE")
            
            if rig_settings.body_enable_preserve_volume or rig_settings.body_enable_smoothcorr:
                
                col = box.column(align=True)
                
                if rig_settings.body_enable_preserve_volume:
                    col.prop(rig_settings,"body_preserve_volume")
                
                if rig_settings.body_enable_smoothcorr:
                    col.prop(rig_settings,"body_smooth_corr")
            
            if rig_settings.body_enable_norm_autosmooth or rig_settings.body_enable_material_normal_nodes:
                col = box.column(align=True)
                
                if rig_settings.body_enable_norm_autosmooth:
                    col.prop(rig_settings,"body_norm_autosmooth")
                
                if rig_settings.body_enable_material_normal_nodes:
                    col.prop(settings,"material_normal_nodes")
        
        if rig_settings.body_enable_subdiv:
            
            box = layout.box()
            
            box.label(text="Subdivision surface", icon = "MOD_SUBSURF")
            
            col = box.column(align=True)
            
            row = col.row(align=True)
            row.prop(rig_settings,"body_subdiv_view", text="Viewport")
            row.scale_x=0.7
            row.prop(rig_settings,"body_subdiv_view_lv")
            
            row = col.row(align=True)
            row.prop(rig_settings,"body_subdiv_rend", text="Render")
            row.scale_x=0.7
            row.prop(rig_settings,"body_subdiv_rend_lv")
        
        if len(custom_props)>0:
            
            unsorted_props = [x for x in custom_props if x.section == ""]
            if len(unsorted_props)>0:
                box = layout.box()
                box.label(text = "Un-sorted properties", icon = "LIBRARY_DATA_BROKEN")
                for prop in [x for x in custom_props if x.section == ""]:
                    row = box.row()
                    if rig_settings.body_custom_properties_icons:
                        row.label(text = prop.name, icon = prop.icon if prop.icon != "NONE" else "DOT")
                    else:
                        row.label(text=prop.name)
                    if prop.is_bool and prop.is_animatable:
                        row.prop(prop, 'bool_value', text="")
                    elif not prop.is_animatable:
                        try:
                            row.prop(eval(prop.rna), prop.path, text="")
                        except:
                            row.prop(settings, 'custom_properties_error_nonanimatable', icon = "ERROR", text="", icon_only = True, emboss = False)
                    else:
                        if prop.prop_name in obj.keys():
                            row.prop(obj, '["' + prop.prop_name + '"]', text="")
                        else:
                            row.prop(settings, 'custom_properties_error', icon = "ERROR", text="", icon_only = True, emboss = False)
                     
            for i_sec in sorted([x for x in range(0,len(rig_settings.body_custom_properties_sections))], key = lambda x:rig_settings.body_custom_properties_sections[x].id):
                section = rig_settings.body_custom_properties_sections[i_sec]
                if rig_settings.body_custom_properties_name_order:
                    custom_properties_section = sorted([x for x in custom_props if x.section == section.name], key = lambda x:x.name)
                else:
                    custom_properties_section = [x for x in custom_props if x.section == section.name]
                if len(custom_properties_section) > 0 and (not section.advanced or (section.advanced and settings.advanced)):
                    box = layout.box()
                    row = box.row(align=False)
                    if section.collapsable:
                        row.prop(section, "collapsed", icon="TRIA_DOWN" if not section.collapsed else "TRIA_RIGHT", icon_only=True, emboss=False)
                    if section.icon != "" and section.icon != "NONE":
                        row.label(text = section.name, icon = section.icon)
                    else:
                        row.label(text = section.name)
                    if not section.collapsed:
                        for prop in custom_properties_section:
                            row = box.row()
                            if rig_settings.body_custom_properties_icons:
                                row.label(text=prop.name, icon = prop.icon if prop.icon != "NONE" else "DOT")
                            else:
                                row.label(text=prop.name)
                            if prop.is_bool and prop.is_animatable:
                                row.prop(prop, 'bool_value', text="")
                            elif not prop.is_animatable:
                                try:
                                    row.prop(eval(prop.rna), prop.path, text="")
                                except:
                                    row.prop(settings, 'custom_properties_error_nonanimatable', icon = "ERROR", text="", icon_only = True, emboss = False)
                            else:
                                if prop.prop_name in obj.keys():
                                    row.prop(obj, '["' + prop.prop_name + '"]', text="")
                                else:
                                    row.prop(settings, 'custom_properties_error', icon = "ERROR", text="", icon_only = True, emboss = False)

class PANEL_PT_MustardUI_ExternalMorphs(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_ExternalMorphs"
    bl_label = "Morphs"
    bl_options = {"DEFAULT_CLOSED"}
    
    def morph_filter(self, morph, rig_settings):
        
        # Check null filter
        check1 = (rig_settings.diffeomorphic_filter_null and eval('rig_settings.model_armature_object[\"' + morph.path + '\"]') > 0.) or not rig_settings.diffeomorphic_filter_null
        
        # Check search filter
        check2 = rig_settings.diffeomorphic_search.lower() in morph.name.lower()
        
        return check1 and check2
    
    @classmethod
    def poll(cls, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        
        res, arm = mustardui_active_object(context, config = 0)
        
        if arm != None:
            rig_settings = arm.MustardUI_RigSettings
            
            # Check if at least one panel is available
            panels = rig_settings.diffeomorphic_emotions or rig_settings.diffeomorphic_emotions_units or rig_settings.diffeomorphic_facs_emotions_units or rig_settings.diffeomorphic_facs_emotions or rig_settings.diffeomorphic_body_morphs
        
            return res and rig_settings.diffeomorphic_support and panels and rig_settings.diffeomorphic_morphs_number > 0
        
        else:
            return res
    
    def draw_header(self,context):
        
        settings = bpy.context.scene.MustardUI_Settings
        
        poll, obj = mustardui_active_object(context, config = 0)
        rig_settings = obj.MustardUI_RigSettings
        
        if settings.status_diffeomorphic > 1 or rig_settings.diffeomorphic_model_version == "1.6":
            layout = self.layout
            layout.enabled = context.active_object == rig_settings.model_armature_object or rig_settings.diffeomorphic_model_version == "1.6"
            layout.prop(rig_settings, "diffeomorphic_enable", text = "", toggle = False)

    def draw(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        
        poll, obj = mustardui_active_object(context, config = 0)
        rig_settings = obj.MustardUI_RigSettings
        
        layout = self.layout
        layout.enabled = rig_settings.diffeomorphic_enable
        
        if rig_settings.diffeomorphic_model_version != "1.6":
            if settings.status_diffeomorphic == 1:
                layout.label(icon='ERROR',text="Diffeomorphic not enabled!")
                return
            elif settings.status_diffeomorphic == 0:
                layout.label(icon='ERROR', text="Diffeomorphic not installed!")
                return
        
        # Check Diffeomorphic version and inform the user about possible issues
        if rig_settings.diffeomorphic_model_version == "1.5" and (settings.status_diffeomorphic_version[0],settings.status_diffeomorphic_version[1],settings.status_diffeomorphic_version[2]) >= (1,6,0):
            box = layout.box()
            box.label(icon='ERROR', text="Diffeomorphic version not correct!")
            box.label(icon='BLANK1', text="Please install version 1.5.1.")
        
        row = layout.row()    
        row.prop(rig_settings, 'diffeomorphic_search', icon = "VIEWZOOM")
        row = row.row(align=True)
        row.prop(rig_settings, 'diffeomorphic_filter_null', icon = "FILTER", text = "")
        row.operator('mustardui.dazmorphs_defaultvalues', icon = "LOOP_BACK", text = "")
        row.operator('mustardui.dazmorphs_clearpose', icon = "OUTLINER_OB_ARMATURE", text = "")
        
        # Emotions Units
        if rig_settings.diffeomorphic_emotions_units:
            box = layout.box()
            row = box.row(align=False)
            row.prop(rig_settings, "diffeomorphic_emotions_units_collapse", icon="TRIA_DOWN" if not rig_settings.diffeomorphic_emotions_units_collapse else "TRIA_RIGHT", icon_only=True, emboss=False)
            
            emotion_units_morphs = [x for x in rig_settings.diffeomorphic_morphs_list if x.type == 0 and self.morph_filter(x, rig_settings)]
            row.label(text="Emotion Units (" + str(len(emotion_units_morphs)) + ")")
            
            if not rig_settings.diffeomorphic_emotions_units_collapse:
                
                for morph in emotion_units_morphs:
                    if hasattr(rig_settings.model_armature_object,'[\"' + morph.path + '\"]'):
                        box.prop(rig_settings.model_armature_object, '[\"' + morph.path + '\"]', text = morph.name)
                    else:
                        row = box.row(align=False)
                        row.label(text = morph.name)
                        row.prop(settings, 'daz_morphs_error', text = "", icon = "ERROR", emboss=False, icon_only = True)
        
        # Emotions
        if rig_settings.diffeomorphic_emotions:
            box = layout.box()
            row = box.row(align=False)
            row.prop(rig_settings, "diffeomorphic_emotions_collapse", icon="TRIA_DOWN" if not rig_settings.diffeomorphic_emotions_collapse else "TRIA_RIGHT", icon_only=True, emboss=False)
            emotion_morphs = [x for x in rig_settings.diffeomorphic_morphs_list if x.type == 1 and self.morph_filter(x, rig_settings)]
            row.label(text="Emotions (" + str(len(emotion_morphs)) + ")")
            
            if not rig_settings.diffeomorphic_emotions_collapse:
                for morph in emotion_morphs:
                    if hasattr(rig_settings.model_armature_object,'[\"' + morph.path + '\"]'):
                        box.prop(rig_settings.model_armature_object, '[\"' + morph.path + '\"]', text = morph.name)
                    else:
                        row = box.row(align=False)
                        row.label(text = morph.name)
                        row.prop(settings, 'daz_morphs_error', text = "", icon = "ERROR", emboss=False, icon_only = True)
        
         # FACS Emotions Units
        if rig_settings.diffeomorphic_facs_emotions_units:
            box = layout.box()
            row = box.row(align=False)
            row.prop(rig_settings, "diffeomorphic_facs_emotions_units_collapse", icon="TRIA_DOWN" if not rig_settings.diffeomorphic_facs_emotions_units_collapse else "TRIA_RIGHT", icon_only=True, emboss=False)
            facs_emotion_units_morphs = [x for x in rig_settings.diffeomorphic_morphs_list if x.type == 2 and self.morph_filter(x, rig_settings)]
            row.label(text="FACS Emotion Units (" + str(len(facs_emotion_units_morphs)) + ")")
            
            if not rig_settings.diffeomorphic_facs_emotions_units_collapse:
                
                for morph in facs_emotion_units_morphs:
                    if hasattr(rig_settings.model_armature_object,'[\"' + morph.path + '\"]'):
                        box.prop(rig_settings.model_armature_object, '[\"' + morph.path + '\"]', text = morph.name)
                    else:
                        row = box.row(align=False)
                        row.label(text = morph.name)
                        row.prop(settings, 'daz_morphs_error', text = "", icon = "ERROR", emboss=False, icon_only = True)
        
        # FACS Emotions
        if rig_settings.diffeomorphic_facs_emotions:
            box = layout.box()
            row = box.row(align=False)
            row.prop(rig_settings, "diffeomorphic_facs_emotions_collapse", icon="TRIA_DOWN" if not rig_settings.diffeomorphic_facs_emotions_collapse else "TRIA_RIGHT", icon_only=True, emboss=False)
            facs_emotion_morphs = [x for x in rig_settings.diffeomorphic_morphs_list if x.type == 3 and self.morph_filter(x, rig_settings)]
            row.label(text="FACS Emotions (" + str(len(facs_emotion_morphs)) + ")")
            
            if not rig_settings.diffeomorphic_facs_emotions_collapse:
                
                for morph in facs_emotion_morphs:
                    if hasattr(rig_settings.model_armature_object,'[\"' + morph.path + '\"]'):
                        box.prop(rig_settings.model_armature_object, '[\"' + morph.path + '\"]', text = morph.name)
                    else:
                        row = box.row(align=False)
                        row.label(text = morph.name)
                        row.prop(settings, 'daz_morphs_error', text = "", icon = "ERROR", emboss=False, icon_only = True)
        
        # Body Morphs
        if rig_settings.diffeomorphic_body_morphs:
            box = layout.box()
            row = box.row(align=False)
            row.prop(rig_settings, "diffeomorphic_body_morphs_collapse", icon="TRIA_DOWN" if not rig_settings.diffeomorphic_body_morphs_collapse else "TRIA_RIGHT", icon_only=True, emboss=False)
            body_morphs = [x for x in rig_settings.diffeomorphic_morphs_list if x.type == 4 and self.morph_filter(x, rig_settings)]
            row.label(text="Body (" + str(len(body_morphs)) + ")")
            
            if not rig_settings.diffeomorphic_body_morphs_collapse:
                
                for morph in body_morphs:
                    if hasattr(rig_settings.model_armature_object,'[\"' + morph.path + '\"]'):
                        box.prop(rig_settings.model_armature_object, '[\"' + morph.path + '\"]', text = morph.name)
                    else:
                        row = box.row(align=False)
                        row.label(text = morph.name)
                        row.prop(settings, 'daz_morphs_error', text = "", icon = "ERROR", emboss=False, icon_only = True)

def mustardui_custom_properties_print(arm, settings, rig_settings, custom_properties, box, icons_show):
        
        box2 = box.box()
        for prop in custom_properties:
            row2 = box2.row(align=True)
            if icons_show:
                row2.label(text=prop.name, icon = prop.icon if prop.icon != "NONE" else "DOT")
            else:
                row2.label(text=prop.name)
            if prop.is_bool and prop.is_animatable:
                row2.prop(prop, 'bool_value', text="")
            elif not prop.is_animatable:
                try:
                    row2.prop(eval(prop.rna), prop.path, text="")
                except:
                    row2.prop(settings, 'custom_properties_error_nonanimatable', icon = "ERROR", text="", icon_only = True, emboss = False)
            else:
                if prop.prop_name in arm.keys():
                    row2.prop(arm, '["' + prop.prop_name + '"]', text="")
                else:
                    row2.prop(settings, 'custom_properties_error', icon = "ERROR", text="", icon_only = True, emboss = False)
        
        return
        
class PANEL_PT_MustardUI_Outfits(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Outfits"
    bl_label = "Outfits"
    bl_options = {"DEFAULT_CLOSED"}
    
    @classmethod
    def poll(cls, context):
        
        res, arm = mustardui_active_object(context, config = 0)
        
        if arm != None:
            
            rig_settings = arm.MustardUI_RigSettings
            
            # Check if one of these should be shown in the UI
            outfits_avail = len([x for x in rig_settings.outfits_collections if x.collection != None])>0
            
            extras_avail = len(rig_settings.extras_collection.objects)>0 if rig_settings.extras_collection != None else False
        
            return res and (outfits_avail or extras_avail) if arm != None else False
        
        else:
            
            return res

    def draw(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        
        poll, arm = mustardui_active_object(context, config = 0)
        rig_settings = arm.MustardUI_RigSettings
        
        layout = self.layout
        
        # Outfit list
        if len([x for x in rig_settings.outfits_collections if x.collection != None])>0:
            
            box = layout.box()
            box.label(text="Outfits list", icon="MOD_CLOTH")
            row = box.row(align=True)
            row.prop(rig_settings,"outfits_list", text="")
            
            if rig_settings.outfits_list != "Nude":
                if len(bpy.data.collections[rig_settings.outfits_list].objects)>0:
                    
                    # Global outfit custom properties
                    if rig_settings.outfit_custom_properties_name_order:
                        custom_properties = sorted([x for x in arm.MustardUI_CustomPropertiesOutfit if x.outfit == bpy.data.collections[rig_settings.outfits_list] and x.outfit_piece == None], key = lambda x:x.name)
                    else:
                        custom_properties = [x for x in arm.MustardUI_CustomPropertiesOutfit if x.outfit == bpy.data.collections[rig_settings.outfits_list] and x.outfit_piece == None]
                    
                    if len(custom_properties)>0 and rig_settings.outfit_additional_options:
                        row.prop(rig_settings,"outfit_global_custom_properties_collapse", text="", toggle=True, icon="PREFERENCES")
                        if rig_settings.outfit_global_custom_properties_collapse:
                            mustardui_custom_properties_print(arm, settings, rig_settings, custom_properties, box, rig_settings.outfit_custom_properties_icons)
                    
                    for obj in bpy.data.collections[rig_settings.outfits_list].objects:
                        
                        col = box.column(align=True)
                        row = col.row(align=True)
                        
                        if rig_settings.model_MustardUI_naming_convention:
                            row.operator("mustardui.object_visibility",text=obj.name[len(rig_settings.outfits_list + ' - '):], icon='OUTLINER_OB_'+obj.type, depress = not obj.hide_viewport).obj = obj.name
                        else:
                            row.operator("mustardui.object_visibility",text=obj.name, icon='OUTLINER_OB_'+obj.type, depress = not obj.hide_viewport).obj = obj.name
                        
                        # Outfit custom properties
                        if rig_settings.outfit_custom_properties_name_order:
                            custom_properties_obj = sorted([x for x in arm.MustardUI_CustomPropertiesOutfit if x.outfit == bpy.data.collections[rig_settings.outfits_list] and x.outfit_piece == obj], key = lambda x:x.name)
                        else:
                            custom_properties_obj = [x for x in arm.MustardUI_CustomPropertiesOutfit if x.outfit == bpy.data.collections[rig_settings.outfits_list] and x.outfit_piece == obj]
                        
                        if len(custom_properties_obj)>0 and rig_settings.outfit_additional_options:
                            row.prop(obj,"MustardUI_additional_options_show", toggle=True, icon="PREFERENCES")
                            if obj.MustardUI_additional_options_show:
                                mustardui_custom_properties_print(arm, settings, rig_settings, custom_properties_obj, col, rig_settings.outfit_custom_properties_icons)
                        
                        row.prop(obj,"MustardUI_outfit_lock",toggle=True, icon='LOCKED' if obj.MustardUI_outfit_lock else 'UNLOCKED')
                
                else:
                    box.label(text="This Collection seems empty", icon="ERROR")
            
            # Locked objects list
            locked_objects = []
            for coll in [x for x in rig_settings.outfits_collections if x.collection != None]:
                for obj in coll.collection.objects:
                    if obj.MustardUI_outfit_lock:
                        locked_objects.append(obj)
            if len(locked_objects)>0:
                box.separator()
                box.label(text="Locked objects:", icon="LOCKED")
                for obj in locked_objects:
                    
                    col = box.column(align=True)
                    row = col.row(align=True)
                    
                    if rig_settings.model_MustardUI_naming_convention:
                        row.operator("mustardui.object_visibility",text=obj.name[len(rig_settings.model_name):], icon='OUTLINER_OB_'+obj.type, depress = not obj.hide_viewport).obj = obj.name
                    else:
                        row.operator("mustardui.object_visibility",text=obj.name, icon='OUTLINER_OB_'+obj.type, depress = not obj.hide_viewport).obj = obj.name
                    
                    if rig_settings.outfit_custom_properties_name_order:
                        custom_properties_obj = sorted([x for x in arm.MustardUI_CustomPropertiesOutfit if x.outfit_piece == obj], key = lambda x:x.name)
                    else:
                        custom_properties_obj = [x for x in arm.MustardUI_CustomPropertiesOutfit if x.outfit_piece == obj]
                    if len(custom_properties_obj)>0 and rig_settings.outfit_additional_options:
                        row.prop(bpy.data.objects[obj.name],"MustardUI_additional_options_show_lock", toggle=True, icon="PREFERENCES")
                        if obj.MustardUI_additional_options_show_lock:
                            mustardui_custom_properties_print(arm, settings, rig_settings, custom_properties_obj, col, rig_settings.outfit_custom_properties_icons)
                    
                    row.prop(obj,"MustardUI_outfit_lock",toggle=True, icon='LOCKED' if obj.MustardUI_outfit_lock else 'UNLOCKED')
        
            # Outfit global properties
            if rig_settings.outfits_enable_global_smoothcorrection or rig_settings.outfits_enable_global_shrinkwrap or rig_settings.outfits_enable_global_mask or rig_settings.outfits_enable_global_normalautosmooth:
                
                box = layout.box()
                row = box.row(align=True)
                row.label(text="Outfits global properties", icon="MODIFIER")
                row.operator('mustardui.switchglobal_outfits', text="", icon="RESTRICT_VIEW_OFF").enable = True
                row.operator('mustardui.switchglobal_outfits', text="", icon="RESTRICT_VIEW_ON").enable = False
                col = box.column(align=True)
                if rig_settings.outfits_enable_global_subsurface:
                    col.prop(rig_settings,"outfits_global_subsurface")
                if rig_settings.outfits_enable_global_smoothcorrection:
                    col.prop(rig_settings,"outfits_global_smoothcorrection")
                if rig_settings.outfits_enable_global_shrinkwrap:
                    col.prop(rig_settings,"outfits_global_shrinkwrap")
                if rig_settings.outfits_enable_global_mask:
                    col.prop(rig_settings,"outfits_global_mask")
                if rig_settings.outfits_enable_global_solidify:
                    col.prop(rig_settings,"outfits_global_solidify")
                if rig_settings.outfits_enable_global_triangulate:
                    col.prop(rig_settings,"outfits_global_triangulate")
                if rig_settings.outfits_enable_global_normalautosmooth:
                    col.prop(rig_settings,"outfits_global_normalautosmooth")
        
        # Extras
        if rig_settings.extras_collection != None:
            
            if len(rig_settings.extras_collection.objects)>0:
            
                box = layout.box()
                
                if rig_settings.extras_collapse_enable:
                    row = box.row(align=False)
                    row.prop(rig_settings, "extras_collapse", icon="TRIA_DOWN" if not rig_settings.extras_collapse else "TRIA_RIGHT", icon_only=True, emboss=False)
                    row.label(text="Extras")
                else:
                    box.label(text="Extras", icon="PLUS")
                
                if not rig_settings.extras_collapse or not rig_settings.extras_collapse_enable:
                    # Global outfit custom properties
                    for obj in sorted(rig_settings.extras_collection.objects, key=lambda x:x.name):
                        
                        col = box.column(align=True)
                        row = col.row(align=True)
                        
                        if rig_settings.model_MustardUI_naming_convention:
                            row.operator("mustardui.object_visibility",text=obj.name[len(rig_settings.extras_collection.name + ' - '):], icon='OUTLINER_OB_'+obj.type, depress = not obj.hide_viewport).obj = obj.name
                        else:
                            row.operator("mustardui.object_visibility",text=obj.name, icon='OUTLINER_OB_'+obj.type, depress = not obj.hide_viewport).obj = obj.name
                        if rig_settings.outfit_custom_properties_name_order:
                            custom_properties_obj = sorted([x for x in arm.MustardUI_CustomPropertiesOutfit if x.outfit == rig_settings.extras_collection and x.outfit_piece == obj], key = lambda x:x.name)
                        else:
                            custom_properties_obj = [x for x in arm.MustardUI_CustomPropertiesOutfit if x.outfit == rig_settings.extras_collection and x.outfit_piece == obj]
                        if len(custom_properties_obj)>0 and rig_settings.outfit_additional_options:
                            row.prop(obj,"MustardUI_additional_options_show", toggle=True, icon="PREFERENCES")
                            if obj.MustardUI_additional_options_show:
                                mustardui_custom_properties_print(arm, settings, rig_settings, custom_properties_obj, col, rig_settings.outfit_custom_properties_icons)

class PANEL_PT_MustardUI_Hair(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Hair"
    bl_label = "Hair"
    bl_options = {"DEFAULT_CLOSED"}
    
    @classmethod
    def poll(cls, context):
        
        res, arm = mustardui_active_object(context, config = 0)
        
        if arm != None:
            
            rig_settings = arm.MustardUI_RigSettings
            
            # Check if one of these should be shown in the UI
            hair_avail = len([x for x in rig_settings.hair_collection.objects if x.type == "MESH"])>1 if rig_settings.hair_collection != None else False
            
            particle_avail = len([x for x in rig_settings.model_body.modifiers if x.type == "PARTICLE_SYSTEM"])>0 and rig_settings.particle_systems_enable if rig_settings.model_body != None else False
        
            return res and (hair_avail or particle_avail) if arm != None else False
        
        else:
            
            return res

    def draw(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        
        poll, arm = mustardui_active_object(context, config = 0)
        rig_settings = arm.MustardUI_RigSettings
        
        layout = self.layout
        
        # Hair
        if rig_settings.hair_collection != None:
            
            obj = bpy.data.objects[rig_settings.hair_list]
            
            if len([x for x in rig_settings.hair_collection.objects if x.type == "MESH"])>1:
                
                box = layout.box()
                row = box.row(align=True)
                row.label(text="Hair list", icon="STRANDS")
                row.prop(rig_settings.hair_collection, "hide_viewport", text="")
                row.prop(rig_settings.hair_collection, "hide_render", text="")
                
                row = box.row(align=True)
                row.prop(rig_settings,"hair_list", text="")
            
            else:
                box = layout.box()
                row = box.row(align=True)
                row.label(text="Hair", icon="STRANDS")
                row.prop(rig_settings.hair_collection, "hide_viewport", text="")
                row.prop(rig_settings.hair_collection, "hide_render", text="")
            
            if rig_settings.outfit_custom_properties_name_order:
                custom_properties_obj = sorted([x for x in arm.MustardUI_CustomPropertiesHair if x.hair == obj], key = lambda x:x.name)
            else:
                custom_properties_obj = [x for x in arm.MustardUI_CustomPropertiesHair if x.hair == obj]
            if len(custom_properties_obj)>0 and rig_settings.outfit_additional_options:
                row.prop(obj,"MustardUI_additional_options_show", toggle=True, icon="PREFERENCES")
                if obj.MustardUI_additional_options_show:
                    mustardui_custom_properties_print(arm, settings, rig_settings, custom_properties_obj, box, rig_settings.hair_custom_properties_icons)
        
        # Particle systems
        mod_particle_system = [x for x in rig_settings.model_body.modifiers if x.type == "PARTICLE_SYSTEM"]
        if rig_settings.particle_systems_enable  and len(mod_particle_system )> 0:
            box = layout.box()
            box.label(text="Hair particles", icon="PARTICLES")
            box2=box.box()
            for mod in mod_particle_system:
                row=box2.row()
                row.label(text=mod.particle_system.name)
                row2=row.row(align=True)
                row2.prop(mod, "show_viewport", text="")
                row2.prop(mod, "show_render", text="")

class PANEL_PT_MustardUI_Armature(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Armature"
    bl_label = "Armature"
    bl_options = {"DEFAULT_CLOSED"}
    
    def toggleFKIK(self, row, value, op):
        if value > 0.5:
            row.operator(op, text="IK")
        else:
            row.operator(op, text="FK")
        return
    
    @classmethod
    def poll(cls, context):
        
        res, obj = mustardui_active_object(context, config = 0)
        
        if obj != None:
            rig_settings = obj.MustardUI_RigSettings
            armature_settings = obj.MustardUI_ArmatureSettings
            
            if len(armature_settings.layers)<1:
                return False
            
            enabled_layers = [x for x in range(0,32) if armature_settings.config_layer[x] and not armature_settings.layers[x].outfit_switcher_enable]
            enabled_IKFK = armature_settings.enable_ik_fk and rig_settings.model_rig_type == "mhx" and rig_settings.model_armature_object != None
            
            if rig_settings.hair_collection != None:
                return res and (len(enabled_layers)>0 or (len([x for x in rig_settings.hair_collection.objects if x.type == "ARMATURE"])>1 and armature_settings.enable_automatic_hair) or enabled_IKFK)
            else:
                return res and (len(enabled_layers)>0 or enabled_IKFK)
        else:
            return res

    def draw(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        poll, obj = mustardui_active_object(context, config = 0)
        rig_settings = obj.MustardUI_RigSettings
        armature_settings = obj.MustardUI_ArmatureSettings
        
        layout = self.layout
        
        if rig_settings.hair_collection != None and armature_settings.enable_automatic_hair:
            if len([x for x in rig_settings.hair_collection.objects if x.type == "ARMATURE"])>0:
                box = layout.box()
                box.label(text='Hair Armature', icon="STRANDS")
                box.prop(armature_settings, "hair",toggle=True)
        
        enabled_layers = [x for x in range(0,32) if armature_settings.config_layer[x] and not armature_settings.layers[x].outfit_switcher_enable]
        if len(enabled_layers)>0:
            box = layout.box()
            box.label(text='Body Armature Layers', icon="ARMATURE_DATA")
            for i in sorted([x for x in range(0,32) if armature_settings.config_layer[x] and not armature_settings.layers[x].outfit_switcher_enable], key = lambda x:armature_settings.layers[x].id):
                if (armature_settings.layers[i].advanced and settings.advanced) or not armature_settings.layers[i].advanced:
                    if armature_settings.layers[i].mirror and armature_settings.layers[i].mirror_left:
                        row = box.row()
                        row.prop(armature_settings.layers[i], "show", text = armature_settings.layers[i].name, toggle=True)
                        row.prop(armature_settings.layers[armature_settings.layers[i].mirror_layer], "show", text = armature_settings.layers[armature_settings.layers[i].mirror_layer].name, toggle=True)
                    elif not armature_settings.layers[i].mirror:
                        box.prop(armature_settings.layers[i], "show", text = armature_settings.layers[i].name, toggle=True)
        
        if armature_settings.enable_ik_fk and rig_settings.model_rig_type == "mhx" and rig_settings.model_armature_object != None:
            
            if settings.status_diffeomorphic > 1:
                
                if (settings.status_diffeomorphic_version[0],settings.status_diffeomorphic_version[1],settings.status_diffeomorphic_version[2]) >= (1,6,0) or not hasattr(rig_settings.model_armature_object, '["MhaArmIk_L"]'):
                    return
                
                box = layout.box()
            
                row = box.row(align=False)
                row.prop(armature_settings, "ik_fk_collapse", icon="TRIA_DOWN" if not armature_settings.ik_fk_collapse else "TRIA_RIGHT", icon_only=True, emboss=False)
                row.label(text="IK/FK Settings")
                
                if not armature_settings.ik_fk_collapse:
                
                    box.label(text = "FK/IK switch")
                    row = box.row()
                    row.enabled = bpy.context.active_object == rig_settings.model_armature_object
                    row.label(text = "Arm")
                    self.toggle(row, rig_settings.model_armature_object, "MhaArmIk_L", " 3", " 2")
                    self.toggle(row, rig_settings.model_armature_object, "MhaArmIk_R", " 19", " 18")
                    row = box.row()
                    row.enabled = bpy.context.active_object == rig_settings.model_armature_object
                    row.label(text = "Leg")
                    self.toggle(row, rig_settings.model_armature_object, "MhaLegIk_L", " 5", " 4")
                    self.toggle(row, rig_settings.model_armature_object, "MhaLegIk_R", " 21", " 20")
                    
                    box.label(text = "IK Influence")
                    row = box.row()
                    row.label(text = "Arm")
                    row.enabled = bpy.context.active_object == rig_settings.model_armature_object
                    row.prop(rig_settings.model_armature_object, '["MhaArmIk_L"]', text="")
                    row.prop(rig_settings.model_armature_object, '["MhaArmIk_R"]', text="")
                    row = box.row()
                    row.label(text = "Leg")
                    row.enabled = bpy.context.active_object == rig_settings.model_armature_object
                    row.prop(rig_settings.model_armature_object, '["MhaLegIk_L"]', text="")
                    row.prop(rig_settings.model_armature_object, '["MhaLegIk_R"]', text="")
                    
                    if armature_settings.enable_ik_fk_snap:
                        
                        box.separator()
                        box.label(text = "Snap Arm Bones")
                        row = box.row()
                        row.enabled = bpy.context.active_object == rig_settings.model_armature_object and bpy.context.active_object.mode == "POSE"
                        row.label(text = "FK Arm")
                        row.operator("daz.snap_fk_ik", text="Snap L FK Arm").data = "MhaArmIk_L 2 3 12"
                        row.operator("daz.snap_fk_ik", text="Snap R FK Arm").data = "MhaArmIk_R 18 19 28"
                        row = box.row()
                        row.label(text = "IK Arm")
                        row.enabled = bpy.context.active_object == rig_settings.model_armature_object and bpy.context.active_object.mode == "POSE"
                        row.operator("daz.snap_ik_fk", text="Snap L IK Arm").data = "MhaArmIk_L 2 3 12"
                        row.operator("daz.snap_ik_fk", text="Snap R IK Arm").data = "MhaArmIk_R 18 19 28"

                        box.label(text = "Snap Leg Bones")
                        row = box.row()
                        row.enabled = bpy.context.active_object == rig_settings.model_armature_object and bpy.context.active_object.mode == "POSE"
                        row.label(text = "FK Leg")
                        row.operator("daz.snap_fk_ik", text="Snap L FK Leg").data = "MhaLegIk_L 4 5 12"
                        row.operator("daz.snap_fk_ik", text="Snap R FK Leg").data = "MhaLegIk_R 20 21 28"
                        row = box.row()
                        row.enabled = bpy.context.active_object == rig_settings.model_armature_object and bpy.context.active_object.mode == "POSE"
                        row.label(text = "IK Leg")
                        row.operator("daz.snap_ik_fk", text="Snap L IK Leg").data = "MhaLegIk_L 4 5 12"
                        row.operator("daz.snap_ik_fk", text="Snap R IK Leg").data = "MhaLegIk_R 20 21 28"
            
            else:
                box = layout.box()
                
                box.label(text="IK/FK Settings")
                box.label(text="Diffeomorphic not installed", icon = "ERROR")
                
    
    def toggle(self, row, rig, prop, fk, ik):
        if getattr(rig, prop) > 0.5:
            row.operator("daz.toggle_fk_ik", text="IK").toggle = prop + " 0" + fk + ik
        else:
            row.operator("daz.toggle_fk_ik", text="FK").toggle = prop + " 1" + ik + fk

class PANEL_PT_MustardUI_Tools_Physics(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Tools_Physics"
    bl_label = "Physics"
    bl_options = {"DEFAULT_CLOSED"}
    
    @classmethod
    def poll(cls, context):
        
        res, obj = mustardui_active_object(context, config = 0)
        
        if obj != None:
            
            physics_settings = obj.MustardUI_PhysicsSettings
        
            return res and len(physics_settings.physics_items) > 0
        
        else:
            return res
    
    def draw_header(self,context):
        
        poll, obj = mustardui_active_object(context, config = 0)
        physics_settings = obj.MustardUI_PhysicsSettings
        
        self.layout.prop(physics_settings, "physics_enable", text = "", toggle = False)
    
    def draw(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        poll, obj = mustardui_active_object(context, config = 0)
        rig_settings = obj.MustardUI_RigSettings
        physics_settings = obj.MustardUI_PhysicsSettings
        naming_convention = rig_settings.model_MustardUI_naming_convention
        
        layout = self.layout
        
        box = layout.box()
        box.label(text="Item settings", icon="OBJECT_DATA")
        box.prop(physics_settings, "physics_items_list", text = "")
        
        if not physics_settings.physics_enable:
            layout.enabled = False
        
        if physics_settings.physics_items_list == "":
            box.label(text="Item not selected.", icon="ERROR")
            return
        
        # Cage specific settings
        cage = bpy.data.objects[physics_settings.physics_items_list]
        
        try:
            cage_settings = [x for x in physics_settings.physics_items if x.cage_object.name == cage.name][0]
        except:
            box.label(text = "Item not found.", icon = "ERROR")
            box.operator('mustardui.tools_physics_deleteitem', text = "Fix Issues", icon = "HELP").cage_object_name = ""
            return
        
        try:
            mod = [x for x in cage.modifiers if x.type == "CLOTH"][0]
        except:
            box.label(text="Cloth modifier not found.", icon="ERROR")
            return
        
        cage_cloth = mod.settings
        cage_collisions = mod.collision_settings
        cage_cache = mod.point_cache
        
        box.prop(cage_settings, "physics_enable")
        
        box2 = box.box()
        box2.enabled = not cage_cache.is_baked and cage_settings.physics_enable
        
        box2.label(text = "Physical Properties" , icon = "PHYSICS")
        box2.prop(cage_cloth, "time_scale")
        box2.prop(cage_cloth.effector_weights, "gravity")
        
        box2 = box.box()
        box2.enabled = not cage_cache.is_baked and cage_settings.physics_enable
        
        box2.label(text = "Structural Properties" , icon = "MOD_EXPLODE")
        if cage_settings.MustardUI_preset:
            
            box2.prop(cage_settings, "inertia")
            box2.prop(cage_settings, "stiffness")
            box2.prop(cage_settings, "bounciness")
        
        else:
            
            col = box2.column(align = False)
            
            row = col.row(align=True)
            row.label(text="")
            row.scale_x=1.
            row.label(text='Stiffness')
            row.scale_x=1.
            row.label(text='Damping')
            
            row = col.row(align=True)
            row.label(text="Structural")
            row.scale_x=1.
            row.prop(cage_cloth,"tension_stiffness", text = "")
            row.scale_x=1.
            row.prop(cage_cloth,"tension_damping", text = "")
            
            row = col.row(align=True)
            row.label(text="Compression")
            row.scale_x=1.
            row.prop(cage_cloth,"compression_stiffness", text = "")
            row.scale_x=1.
            row.prop(cage_cloth,"compression_damping", text = "")
            
            row = col.row(align=True)
            row.label(text="Shear")
            row.scale_x=1.
            row.prop(cage_cloth,"shear_stiffness", text = "")
            row.scale_x=1.
            row.prop(cage_cloth,"shear_damping", text = "")
            
            row = col.row(align=True)
            row.label(text="Bending")
            row.scale_x=1.
            row.prop(cage_cloth,"bending_stiffness", text = "")
            row.scale_x=1.
            row.prop(cage_cloth,"bending_damping", text = "")
            
            if cage_cloth.vertex_group_bending != "":
                box2.prop(cage_cloth,"bending_stiffness_max", text = "Max Bending")
            
            #box2.separator()
            
            #box2.label(text = "Internal Springs Properties" , icon = "FORCE_MAGNETIC")
            box2.prop(cage_cloth,"use_internal_springs", text = "Enable Internal Springs")
            
            col = box2.column(align = False)
            col.enabled = cage_cloth.use_internal_springs
            
            row = col.row(align=True)
            row.label(text="")
            row.scale_x=1.
            row.label(text='Value')
            row.scale_x=1.
            row.label(text='Max')
            
            row = col.row(align=True)
            row.label(text="Tension")
            row.scale_x=1.
            row.prop(cage_cloth,"internal_tension_stiffness", text = "")
            row.scale_x=1.
            row.prop(cage_cloth,"internal_tension_stiffness_max", text = "")
            
            row = col.row(align=True)
            row.label(text="Compression")
            row.scale_x=1.
            row.prop(cage_cloth,"internal_compression_stiffness", text = "")
            row.scale_x=1.
            row.prop(cage_cloth,"internal_compression_stiffness_max", text = "")
            
            #box2.separator()
            
            #box2.label(text = "Pressure Properties" , icon = "MOD_SOFT")
            box2.prop(cage_cloth,"use_pressure", text = "Enable Pressure")
            
            col = box2.column(align = False)
            col.enabled = cage_cloth.use_pressure
            
            col.prop(cage_cloth, 'uniform_pressure_force', text = "Force")
        
        box2 = box.box()
        box2.enabled = not cage_cache.is_baked and cage_settings.physics_enable
        
        box2.label(text = "Collision Properties" , icon = "MOD_PHYSICS")
        box2.prop(cage_collisions, "use_collision")
        row = box2.row(align = True)
        row.enabled = cage_collisions.use_collision
        row.prop(cage_collisions, 'collision_quality')
        row = box2.row(align=True)
        row.enabled = cage_collisions.use_collision
        row.prop(cage_collisions, "distance_min")
        row = box2.row(align=True)
        row.enabled = cage_collisions.use_collision
        row.prop(cage_collisions, "impulse_clamp")
        
        box2 = box.box()
        box2.enabled = cage_settings.physics_enable
        
        box2.label(text = "Item Simulation" , icon = "FILE_CACHE")
        row = box2.row(align = True)
        row.enabled = not cage_cache.is_baked
        row.prop(cage_cloth, 'quality')
        box2.separator()
        row = box2.row(align = True)
        row.prop(cage_cache, "frame_start", text = "Start")
        row.prop(cage_cache, "frame_end", text = "End")
        cache_info = cage_cache.info
        if cache_info and settings.debug:
            col = box2.column(align=True)
            col.alignment = 'CENTER'
            col.label(text='Info: ' + cache_info)
        bake_op = box2.operator('mustardui.tools_physics_simulateobject', text = "Bake Single Item Physics" if not cage_cache.is_baked else "Delete Single Item Bake", icon = "PHYSICS" if not cage_cache.is_baked else "X", depress = cage_cache.is_baked).cage_object_name = physics_settings.physics_items_list
        
        # Global simulation
        box = layout.box()
        box.label(text = "Global Simulation" , icon = "FILE_CACHE")
        box.prop(physics_settings, 'simulation_quality')
        box.separator()
        row = box.row(align = True)
        row.prop(physics_settings, "simulation_start", text = "Start")
        row.prop(physics_settings, "simulation_end", text = "End")
        box.operator('ptcache.bake_all', icon="PHYSICS").bake = True
        box.operator('ptcache.free_bake_all', icon="X")
        
        if settings.maintenance:
            box = layout.box()
            box.label(text = "Maintenance" , icon = "SETTINGS")
            box.operator('mustardui.tools_physics_rebind', text = "Re-bind Cages", icon="MOD_MESHDEFORM")

class PANEL_PT_MustardUI_Tools_Lattice(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Tools_Lattice"
    bl_label = "Body Shape"
    bl_options = {"DEFAULT_CLOSED"}
    
    @classmethod
    def poll(cls, context):
        
        res, obj = mustardui_active_object(context, config = 0)
        
        if obj != None:
            lattice_settings = obj.MustardUI_LatticeSettings
            poll = lattice_settings.lattice_panel_enable
        
            return poll and res
        
        else:
            return res
    
    def draw_header(self,context):
        
        poll, obj = mustardui_active_object(context, config = 0)
        lattice_settings = obj.MustardUI_LatticeSettings
        
        self.layout.prop(lattice_settings, "lattice_enable", text="", toggle=False)
    
    def draw(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        poll, obj = mustardui_active_object(context, config = 0)
        lattice_settings = obj.MustardUI_LatticeSettings
        
        layout = self.layout
        
        if not lattice_settings.lattice_enable:
            layout.enabled = False
        
        box = layout.box()
        box.label(text="Shape settings", icon="MOD_LATTICE")
        row = box.row(align=True)
        row.label(text="Shape")
        row.scale_x=2.
        row.prop(lattice_settings,"lattice_keys")
        row = box.row(align=True)
        if lattice_settings.lattice_keys == "Base":
            row.enabled = False
        row.prop(lattice_settings,"lattice_key_value")
        if settings.advanced:
            row = box.row(align=True)
            if lattice_settings.lattice_keys == "Base":
                row.enabled = False
            row.label(text="Interpolation")
            row.scale_x=2.
            row.prop(lattice_settings,"lattice_interpolation")
        
        box = layout.box()
        box.label(text="Custom Lattice Shape", icon="PLUS")
        box.label(text="   - Run Custom Shape")
        box.label(text="   - Move the vertices")
        box.label(text="   - Apply shape")
        if lattice_settings.lattice_mod_status:
            box.operator("mustardui.tools_lattice", text="Apply shape", depress=True, icon="EDITMODE_HLT").mod = 1
        else:
            row = box.row(align=True)
            if lattice_settings.lattice_keys != lattice_settings.lattice_modifiers_name + "Custom":
                row.enabled = False
            row.operator("mustardui.tools_lattice", text="Custom shape", icon="EDITMODE_HLT").mod = 0
        row = box.row(align=True)
        if lattice_settings.lattice_keys != lattice_settings.lattice_modifiers_name + "Custom":
            row.enabled = False
        row.operator("mustardui.tools_lattice", text="Reset Custom shape", icon="CANCEL").mod = 2



class PANEL_PT_MustardUI_Tools(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Tools"
    bl_label = "Tools"
    bl_options = {"DEFAULT_CLOSED"}
    
    @classmethod
    def poll(cls, context):
        
        res, arm = mustardui_active_object(context, config = 0)
        if arm != None:
            rig_settings = arm.MustardUI_RigSettings
            return res and (arm.MustardUI_ToolsSettings.childof_enable or (arm.MustardUI_ToolsSettings.lips_shrinkwrap_enable and rig_settings.model_rig_type in ["arp", "mhx"]))
        else:
            return res
    
    def draw(self, context):
        
        layout = self.layout

class PANEL_PT_MustardUI_Tools_ChildOf(MainPanel, bpy.types.Panel):
    bl_parent_id = "PANEL_PT_MustardUI_Tools"
    bl_idname = "PANEL_PT_MustarUI_Tools_ChildOf"
    bl_label = "Parent bones"
    bl_options = {"DEFAULT_CLOSED"}
    
    @classmethod
    def poll(cls, context):
        
        res, arm = mustardui_active_object(context, config = 0)
        if arm != None:
            return res and arm.MustardUI_ToolsSettings.childof_enable
        else:
            return res
    
    def draw(self, context):
        
        poll, arm = mustardui_active_object(context, config = 0)
        tools_settings = arm.MustardUI_ToolsSettings
        
        layout = self.layout
        
        layout.label(text="Force one Bone to follow another Bone.")
        
        box = layout.box()
        column = box.column(align=True)
        column.label(text="Select two bones:", icon="BONE_DATA")
        column.label(text="  - the first will be the parent,")
        column.label(text="  - the second will be the child.")
        box.prop(tools_settings, "childof_influence")
        layout.operator('mustardui.tools_childof', text="Enable").clean = 0
        
        layout.operator('mustardui.tools_childof', text="Remove Parent instances", icon="X").clean = 1

class PANEL_PT_MustardUI_Tools_AutoBreath(MainPanel, bpy.types.Panel):
    bl_parent_id = "PANEL_PT_MustardUI_Tools"
    bl_idname = "PANEL_PT_MustarUI_Tools_AutoBreath"
    bl_label = "Auto Breath"
    bl_options = {"DEFAULT_CLOSED"}
    
    @classmethod
    def poll(cls, context):
        
        res, arm = mustardui_active_object(context, config = 0)
        if arm != None:
            if hasattr(arm.MustardUI_ToolsSettings, "autobreath_enable"):
                return res and arm.MustardUI_ToolsSettings.autobreath_enable
            else:
                return False
        else:
            return res
    
    def draw(self, context):
        
        poll, arm = mustardui_active_object(context, config = 0)
        tools_settings = arm.MustardUI_ToolsSettings
        
        layout = self.layout
        
        box = layout.box()
        column = box.column(align=True)
        column.label(text="Select one bone:", icon="BONE_DATA")
        column.label(text="  - Unlocked transformation are animated")
        column.label(text="  - Rest value should be 1")
        column.label(text="  - Max value should be 2")
        column = box.column(align=True)
        column.prop(tools_settings, "autobreath_frequency")
        column.prop(tools_settings, "autobreath_amplitude")
        column.prop(tools_settings, "autobreath_random")
        column.prop(tools_settings, "autobreath_sampling")
        
        layout.operator('mustardui.tools_autobreath')

class PANEL_PT_MustardUI_Tools_AutoEyelid(MainPanel, bpy.types.Panel):
    bl_parent_id = "PANEL_PT_MustardUI_Tools"
    bl_idname = "PANEL_PT_MustarUI_Tools_AutoEyelid"
    bl_label = "Auto Blink"
    bl_options = {"DEFAULT_CLOSED"}
    
    @classmethod
    def poll(cls, context):
        
        res, arm = mustardui_active_object(context, config = 0)
        if arm != None:
            if hasattr(arm.MustardUI_ToolsSettings, "autoeyelid_enable"):
                return res and arm.MustardUI_ToolsSettings.autoeyelid_enable
            else:
                return False
        else:
            return res
    
    def draw(self, context):
        
        poll, arm = mustardui_active_object(context, config = 0)
        tools_settings = arm.MustardUI_ToolsSettings
        
        layout = self.layout
        
        box = layout.box()
        column = box.column(align=True)
        column.label(text="Eyelid blink settings", icon="HIDE_OFF")
        column = box.column(align=True)
        column.prop(tools_settings, "autoeyelid_blink_length")
        column.prop(tools_settings, "autoeyelid_blink_rate_per_minute")
        
        layout.operator('mustardui.tools_autoeyelid')

class PANEL_PT_MustardUI_Tools_LipsShrinkwrap(MainPanel, bpy.types.Panel):
    bl_parent_id = "PANEL_PT_MustardUI_Tools"
    bl_idname = "PANEL_PT_MustardUI_Tools_LipsShrinkwrap"
    bl_label = "Lips Shrinkwrap"
    bl_options = {"DEFAULT_CLOSED"}
    
    @classmethod
    def poll(cls, context):
        
        res, arm = mustardui_active_object(context, config = 0)
        if arm != None:
            rig_settings = arm.MustardUI_RigSettings
            return res and arm.MustardUI_ToolsSettings.lips_shrinkwrap_enable and rig_settings.model_rig_type in ["arp", "mhx"]
        else:
            return res
    
    def draw(self, context):
    
        poll, arm = mustardui_active_object(context, config = 0)
        tools_settings = arm.MustardUI_ToolsSettings
            
        layout = self.layout
        
        layout.label(text = "Force the lips bones to stay outside the Object.")
        
        box = layout.box()
        
        box.label(text="Main properties.", icon="MODIFIER")
        box.prop(tools_settings, "lips_shrinkwrap_obj")
        column = box.column(align=True)
        column.prop(tools_settings, "lips_shrinkwrap_dist")
        column.prop(tools_settings, "lips_shrinkwrap_dist_corr")
        
        box = layout.box()
        
        box.label(text="Friction properties.", icon="FORCE_TURBULENCE")
        row = box.row(align=True)
        row.prop(tools_settings, "lips_shrinkwrap_friction")
        row.scale_x=0.8
        row.prop(tools_settings, "lips_shrinkwrap_friction_infl")
        box.prop(tools_settings, "lips_shrinkwrap_obj_fric")
        if tools_settings.lips_shrinkwrap_obj_fric:
            if tools_settings.lips_shrinkwrap_obj_fric.type == "MESH":
                box.prop_search(tools_settings, "lips_shrinkwrap_obj_fric_sec", tools_settings.lips_shrinkwrap_obj_fric,"vertex_groups")
            if tools_settings.lips_shrinkwrap_obj_fric.type == "ARMATURE":
                box.prop_search(tools_settings, "lips_shrinkwrap_obj_fric_sec", tools_settings.lips_shrinkwrap_obj_fric.pose,"bones")
        
        row = layout.row()
        if tools_settings.lips_shrinkwrap:
            row.prop(tools_settings, "lips_shrinkwrap",text="Disable", toggle=True, icon="CANCEL")
        else:
            row.prop(tools_settings, "lips_shrinkwrap",toggle=True)




class PANEL_PT_MustardUI_SettingsPanel(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_SettingsPanel"
    bl_label = "Settings"
    bl_options = {"DEFAULT_CLOSED"}
    
    @classmethod
    def poll(cls, context):
        
        res, arm = mustardui_active_object(context, config = 0)
        return res
    
    def draw(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        poll, obj = mustardui_active_object(context, config = 0)
        rig_settings = obj.MustardUI_RigSettings
        
        layout = self.layout
        
        # Main Settings
        box = layout.box()
        col = box.column(align=True)
        
        col.prop(settings,"advanced")
        col.prop(settings,"maintenance")
        col.prop(settings,"debug")
        
        if settings.viewport_model_selection:
            box.operator('mustardui.viewportmodelselection', text="Viewport Model Selection", icon = "VIEW3D", depress = True)
        else:
            box.operator('mustardui.viewportmodelselection', text="Viewport Model Selection", icon = "VIEW3D", depress = False)
        
        if settings.maintenance:
            box = layout.box()
            box.label(text="Maintenance Tools", icon="SETTINGS")
            box.operator('mustardui.configuration', text="UI Configuration", icon = "PREFERENCES")
            
            box.operator('mustardui.property_rebuild', icon = "MOD_BUILD", text = "Re-build Custom Properties")
            
            if obj.MustardUI_script_file == None:
                box.operator('mustardui.registeruifile', text="Register UI Script", icon = "TEXT").register = True
            else:
                box.operator('mustardui.registeruifile', text="Un-register UI Script", icon = "TEXT").register = False
            
            box.operator('mustardui.cleanmodel', text="Clean model", icon = "BRUSH_DATA")
            box.operator('mustardui.debug_log', text="Create Log file", icon = "FILE_TEXT")
            box.operator('mustardui.remove', text="UI Removal", icon = "X")
            if platform.system() == 'Windows':
                box.separator()
                box.operator('wm.console_toggle', text="Toggle System Console", icon = "TOPBAR")
        
        box = layout.box()
        box.label(text="Version", icon="INFO")
        if rig_settings.model_version!='':
            box.label(text="Model:           " + rig_settings.model_version)
        box.label(text="MustardUI:    " + str(bl_info["version"][0]) + '.' + str(bl_info["version"][1]) + '.' + str(bl_info["version"][2]) + '.' + str(mustardui_buildnum))
        
        if (rig_settings.model_rig_type == "arp" and settings.status_rig_tools == 0) or (rig_settings.model_rig_type == "arp" and settings.status_rig_tools == 1) or (settings.status_diffeomorphic == 0 and rig_settings.diffeomorphic_support) or (settings.status_diffeomorphic == 1 and rig_settings.diffeomorphic_support):
            box = layout.box()
            
            if rig_settings.model_rig_type == "arp" and settings.status_rig_tools == 1:
                box.label(icon='ERROR',text="rig_tools not enabled!")
            elif rig_settings.model_rig_type == "arp" and settings.status_rig_tools == 0:
                box.label(icon='ERROR', text="rig_tools not installed!")
            
            if settings.status_diffeomorphic == 1 and rig_settings.diffeomorphic_support:
                box.label(icon='ERROR',text="Diffeomorphic not enabled!")
            elif settings.status_diffeomorphic == 0 and rig_settings.diffeomorphic_support:
                box.label(icon='ERROR', text="Diffeomorphic not installed!")

class PANEL_PT_MustardUI_Links(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Links"
    bl_label = "Links"
    bl_options = {"DEFAULT_CLOSED"}
    
    @classmethod
    def poll(cls, context):
        
        res, arm = mustardui_active_object(context, config = 0)
        return res
    
    def draw(self, context):
        
        poll, obj = mustardui_active_object(context, config = 0)
        rig_settings = obj.MustardUI_RigSettings
        
        layout = self.layout
        
        if rig_settings.url_website!='' or rig_settings.url_patreon!='' or rig_settings.url_twitter!='' or rig_settings.url_smutbase!='' or rig_settings.url_documentation!='' or rig_settings.url_reportbug!='':
            
            box = layout.box()
            box.label(text="Social profiles/contacts", icon="BOOKMARKS")
        
            if rig_settings.url_website!='':
                box.operator('mustardui.openlink', text="Website", icon = "WORLD").url = rig_settings.url_website
            if rig_settings.url_patreon!='':
                box.operator('mustardui.openlink', text="Patreon", icon = "WORLD").url = rig_settings.url_patreon
            if rig_settings.url_twitter!='':
                box.operator('mustardui.openlink', text="Twitter", icon = "WORLD").url = rig_settings.url_twitter
            if rig_settings.url_smutbase!='':
                box.operator('mustardui.openlink', text="SmutBase", icon = "WORLD").url = rig_settings.url_smutbase
            if rig_settings.url_documentation!='':
                box.operator('mustardui.openlink', text="Documentation", icon = "WORLD").url = rig_settings.url_documentation
            if rig_settings.url_reportbug!='':
                box.operator('mustardui.openlink', text="Report a Bug", icon = "WORLD").url = rig_settings.url_reportbug
        
        box = layout.box()
        box.label(text="MustardUI References", icon="INFO")
        box.operator('mustardui.openlink', text="MustardUI - Tutorial", icon = "WORLD").url = rig_settings.url_MustardUItutorial
        box.operator('mustardui.openlink', text="MustardUI - Report Bug", icon = "WORLD").url = rig_settings.url_MustardUI_reportbug
        box.operator('mustardui.openlink', text="MustardUI - GitHub", icon = "WORLD").url = rig_settings.url_MustardUI
        

# Registration of classes
# If you add new classes (or operators), add the class in the list below

# Register

classes = (
    # Configuration Operators
    MustardUI_Configuration,
    MustardUI_Configuration_SmartCheck,
    MustardUI_RemoveUI,
    MustardUI_RegisterUIFile,
    # Model switch support operators
    MustardUI_ViewportModelSelection,
    MustardUI_SwitchModel,
    # Armature operators
    MustardUI_Armature_Initialize,
    MustardUI_Armature_Sort,
    # Custom properties operators
    MustardUI_Property_MenuAdd,
    MustardUI_Property_MenuLink,
    OUTLINER_MT_MustardUI_PropertySectionMenu,
    OUTLINER_MT_MustardUI_PropertyOutfitMenu,
    OUTLINER_MT_MustardUI_PropertyOutfitPieceMenu,
    OUTLINER_MT_MustardUI_PropertyHairMenu,
    MUSTARDUI_MT_Property_LinkMenu,
    MUSTARDUI_UL_Property_UIList,
    MUSTARDUI_UL_Property_UIListOutfits,
    MUSTARDUI_UL_Property_UIListHair,
    MustardUI_Property_Switch,
    MustardUI_Property_Remove,
    MustardUI_Property_RemoveLinked,
    MustardUI_Property_Settings,
    MustardUI_Property_Rebuild,
    MustardUI_Property_SmartCheck,
    WM_MT_button_context,
    # Body custom properties sections operators
    MustardUI_Body_AddSection,
    MustardUI_Body_DeleteSection,
    MustardUI_Body_SettingsSection,
    MustardUI_Body_SwapSection,
    MustardUI_Body_PropertyAddToSection,
    # Diffeomorphic support operators
    MustardUI_DazMorphs_CheckMorphs,
    MustardUI_DazMorphs_DefaultValues,
    MustardUI_DazMorphs_DisableDrivers,
    MustardUI_DazMorphs_EnableDrivers,
    MustardUI_DazMorphs_ClearPose,
    # Outfit operators
    MustardUI_OutfitVisibility,
    MustardUI_GlobalOutfitPropSwitch,
    # Normal map optimization operator
    MustardUI_Material_NormalMap_Nodes,
    # Clean model operator
    MustardUI_CleanModel,
    # Debug
    MustardUI_Debug_Log,
    # Others
    MustardUI_LinkButton,
    # Outfit add/remove operators
    MustardUI_AddOutfit,
    MustardUI_RemoveOutfit,
    # Tools
    MustardUI_Tools_LatticeSetup,
    MustardUI_Tools_LatticeModify,
    MustardUI_Tools_ChildOf,
    MustardUI_Tools_AutoBreath,
    MustardUI_Tools_AutoEyelid,
    MustardUI_Tools_Physics_CreateItem,
    MustardUI_Tools_Physics_DeleteItem,
    MustardUI_Tools_Physics_Clean,
    MustardUI_Tools_Physics_ReBind,
    MustardUI_Tools_Physics_SimulateObject,
    # Panel classes
    PANEL_PT_MustardUI_InitPanel,
    PANEL_PT_MustardUI_SelectModel,
    PANEL_PT_MustardUI_Body,
    PANEL_PT_MustardUI_ExternalMorphs,
    PANEL_PT_MustardUI_Outfits,
    PANEL_PT_MustardUI_Hair,
    PANEL_PT_MustardUI_Armature,
    PANEL_PT_MustardUI_Tools_Physics,
    PANEL_PT_MustardUI_Tools_Lattice,
    PANEL_PT_MustardUI_Tools,
    PANEL_PT_MustardUI_Tools_ChildOf,
    PANEL_PT_MustardUI_Tools_AutoBreath,
    PANEL_PT_MustardUI_Tools_AutoEyelid,
    PANEL_PT_MustardUI_Tools_LipsShrinkwrap,
    PANEL_PT_MustardUI_SettingsPanel,
    PANEL_PT_MustardUI_Links
)

def register():
    
    bpy.types.Armature.MustardUI_script_file = PointerProperty(type=bpy.types.Text)
    
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    
    bpy.types.Scene.mustardui_property_uilist_index = IntProperty(name = "", default = 0)
    bpy.types.Scene.mustardui_property_uilist_outfits_index = IntProperty(name = "", default = 0)
    bpy.types.Scene.mustardui_property_uilist_hair_index = IntProperty(name = "", default = 0)
    
    bpy.types.OUTLINER_MT_collection.append(mustardui_collection_menu)
    bpy.types.WM_MT_button_context.append(mustardui_property_menuadd)
    bpy.types.WM_MT_button_context.append(mustardui_property_link)

def unregister():
    
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    
    bpy.types.OUTLINER_MT_collection.remove(mustardui_collection_menu)
    bpy.types.WM_MT_button_context.remove(mustardui_property_menuadd)
    bpy.types.WM_MT_button_context.remove(mustardui_property_link)

if __name__ == "__main__":
    register()