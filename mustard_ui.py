# MustardUI addon
# GitHub page: https://github.com/Mustard2/MustardUI

# Add-on informations
bl_info = {
    "name": "MustardUI",
    "description": "Create a MustardUI for a human character.",
    "author": "Mustard",
    "version": (0, 20, 8),
    "blender": (2, 93, 0),
    "warning": "",
    "wiki_url": "https://github.com/Mustard2/MustardUI",
    "category": "User Interface",
}

import bpy
import addon_utils
import sys
import os
import re
import time
import math
import platform
import itertools
from bpy.types import Header, Menu, Panel
from bpy.props import *
from bpy.app.handlers import persistent
from mathutils import Vector, Color
import webbrowser

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
    def addon_check(addon_name, addon_name2):
        
        result = 0
        
        addon_utils.modules_refresh()
        
        if addon_name not in addon_utils.addons_fake_modules and addon_name2 not in addon_utils.addons_fake_modules:
            print("MustardUI - %s add-on not installed." % addon_name)
        else:
            default, state = addon_utils.check(addon_name)
            default, state2 = addon_utils.check(addon_name2)
            if (not state and not state2):
                result = 1
                print("MustardUI - %s add-on installed but not enabled." % addon_name )
            else:
                result = 2
                print("MustardUI - %s add-on enabled and running." % addon_name)
        
        return result

    
    # Rig-tools addon status definition
    status_rig_tools: bpy.props.IntProperty(default = addon_check("auto_rig_pro-master", "rig_tools"),
                        name = "rig_tools addon status")
    # Rig-tools addon status definition
    status_diffeomorphic: bpy.props.IntProperty(default = addon_check("import_daz", "import_daz"),
                        name = "rig_tools addon status")
    
    # Property for additional properties errors
    additional_properties_error: bpy.props.BoolProperty(name = "",
                        description = "Can not find the property.\nRe-run the Check Additional Option operator in the Configuration menu to solve this")
    
    # Property for morphs errors
    daz_morphs_error: bpy.props.BoolProperty(name = "",
                        description = "Can not find the Daz Morph.\nRe-run the Check Morphs operator in the Configuration menu to solve this")

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

# Properties and functions for lock functionality
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
#    Body additional options definition
# ------------------------------------------------------------------------

# Update function for additional properties
def mustardui_body_additional_options_update(self, context):
    
    poll, arm = mustardui_active_object(context, config = 0)
    rig_settings = arm.MustardUI_RigSettings
    obj = rig_settings.model_body
    
    if obj != None:
        
        if self.type in [2,3,4]:
        
            # Material properties update
            for mat in obj.data.materials:
                for j in range(len(mat.node_tree.nodes)):
                    if mat.node_tree.nodes[j].name == "MustardUI Float - "+self.name and mat.node_tree.nodes[j].type == "VALUE":
                        mat.node_tree.nodes["MustardUI Float - "+self.name].outputs[0].default_value = self.body_float_value
                    elif mat.node_tree.nodes[j].name == "MustardUI Bool - "+self.name and mat.node_tree.nodes[j].type == "VALUE":
                        mat.node_tree.nodes["MustardUI Bool - "+self.name].outputs[0].default_value = self.body_bool_value
                    elif mat.node_tree.nodes[j].name == "MustardUI - "+self.name and mat.node_tree.nodes[j].type == "RGB":
                        mat.node_tree.nodes["MustardUI - "+self.name].outputs[0].default_value = self.body_color_value
        
        else:
            
            # Shape keys update
            for shape_key in obj.data.shape_keys.key_blocks:
                if shape_key.name == "MustardUI Float - "+self.name:
                    shape_key.value = self.body_value_float
                elif shape_key.name == "MustardUI Bool - "+self.name:
                    shape_key.value = self.body_value_bool
    
    return

# Update function for bool properties
# Note that since everything is saved as paths, we should use exec()
def mustardui_additional_option_bool_update(self,context):
    try:
        exec(self.path + '.' + self.id + '= self.bool_value')
    except:
        print("MustardUI - Can not find the property. Re-run the Check Additional Option operator in the Configuration menu to solve this")

# Custom Option property for additional outfit options
#
# - Outfits: All the outfits additional properties are saved with path and id,
#            but the bool properties are evaluated separately in order to obtain a check button in the UI instead of a slider
# - Body   : The properties are saved with additional property definitions.
#            This choice is made to allow evaluation of more material/shape-keys properties with the same name, using one property
class MustardUI_OptionItem(bpy.types.PropertyGroup):
    
    # Name of the property (shown in the UI)
    name: bpy.props.StringProperty(name = "Option name")
    
    # Property Blender path
    path: bpy.props.StringProperty(name = "Property Path")
    
    # Property Blender ID
    id: bpy.props.StringProperty(name = "Property Identifier")
    
    # Object where the property is defined
    object: bpy.props.PointerProperty(name = "Option Object",
                        type = bpy.types.Object)
    
    # Bool Shape Key: 0 - Float Shape Key: 1 - Bool: 2 - Float: 3 - Color: 4
    type: bpy.props.IntProperty(default = 3)
    
    # Outfit: Bool property defined to allow checks instead of sliders if Bool is written in the property name
    bool_value: bpy.props.BoolProperty(default = False,
                        name = "",
                        update = mustardui_additional_option_bool_update)
    
    # Body additional properties
    body_float_value : bpy.props.FloatProperty(min = 0., max = 1.,
                        name = "Option value",
                        update = mustardui_body_additional_options_update,
                        description = "Value of the property")
    
    body_bool_value : bpy.props.BoolProperty(name = "Option value",
                        update = mustardui_body_additional_options_update,
                        description = "Value of the property")
    
    body_color_value : bpy.props.FloatVectorProperty(default = [1.,1.,1.,1.],
                        size = 4,
                        min = 0.0, max = 1.0,
                        name = "Option value",
                        subtype = 'COLOR',
                        update = mustardui_body_additional_options_update,
                        description="Value of the property")
    
bpy.utils.register_class(MustardUI_OptionItem)
bpy.types.Object.mustardui_additional_options = bpy.props.CollectionProperty(type = MustardUI_OptionItem)

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
                if self.body_smooth_corr == True:
                    modifier.show_viewport = True
                    modifier.show_render = True
                else:
                    modifier.show_viewport = False
                    modifier.show_render = False
        return
    
    # Update function for Auto-smooth function
    def update_norm_autosmooth(self, context):
        
        obj = self.model_body
        
        if obj.type == "MESH":
        
            if self.body_norm_autosmooth == True:
                obj.data.use_auto_smooth = True
            else:
                obj.data.use_auto_smooth = False
        
        return
    
    # Update function for Subsurface Scattering in materials
    def update_sss(self, context):
        
        for mat in self.model_body.data.materials:
            for node in mat.node_tree.nodes:
                if node.name=='Subsurface':
                    node.outputs[0].default_value = self.body_sss
        return
    
    # Subsurface scattering
    body_enable_sss: bpy.props.BoolProperty(default = True,
                        name = "Subsurface Scattering",
                        description = "")
    
    body_sss: bpy.props.FloatProperty(default = 0.02,
                        min = 0.0,
                        max = 1.0,
                        name = "Subsurface Scattering",
                        description = "Set the subsurface scattering intensity.\nThis effect will allow some light rays to go through the body skin. Be sure to set a correct value. If you are not sure, restore to the default value",
                        update = update_sss)
    
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
    
    
    # Additional properties
    # Store number of additional properties
    body_additional_properties_number: bpy.props.IntProperty(default = 0,
                        name = "")
    
    # List of the collections from which to extract the outfits
    body_additional_properties: bpy.props.CollectionProperty(type = MustardUI_OptionItem)
    
    # ------------------------------------------------------------------------
    #    Outfit properties
    # ------------------------------------------------------------------------
    
    # Property for collapsing outfit list section
    outfit_config_collapse: bpy.props.BoolProperty(default = True,
                        name = "")
    
    # Property for collapsing outfit properties section
    outfit_config_prop_collapse: bpy.props.BoolProperty(default = True)
    
    # Global outfit properties
    outfits_enable_global_smoothcorrection: bpy.props.BoolProperty(default = True,
                        name = "Smooth Correction modifiers")
    
    outfits_enable_global_shrinkwrap: bpy.props.BoolProperty(default = True,
                        name = "Shrinkwrap modifiers")
    
    outfits_enable_global_mask: bpy.props.BoolProperty(default = True,
                        name = "Mask modifiers")
    
    outfits_enable_global_normalautosmooth: bpy.props.BoolProperty(default = True,
                        name = "Normals Auto Smooth properties")
    
    # OUTFITS FUNCTIONS AND DATA
        
    # Function to create an array of tuples for Outfit enum collections
    def outfits_list_make(self, context):
        
        naming_conv = self.model_MustardUI_naming_convention
        
        items = []
        
        for el in self.outfits_collections:
            if hasattr(el.collection, 'name'):
                if naming_conv:
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
        rig_settings = obj.MustardUI_RigSettings
        armature_settings = obj.MustardUI_ArmatureSettings
        
        outfits_list = rig_settings.outfits_list
        
        # Update the objects and masks visibility
        for collection in rig_settings.outfits_collections:
            
            locked_collection = len([x for x in collection.collection.objects if x.MustardUI_outfit_lock])>0
            
            collection.collection.hide_viewport = not (collection.collection.name == outfits_list or locked_collection)
            collection.collection.hide_render = not (collection.collection.name == outfits_list or locked_collection)
            
            for obj in collection.collection.objects:
                    
                if locked_collection and collection.collection.name != outfits_list:
                    
                    obj.hide_viewport = obj.MustardUI_outfit_visibility if obj.MustardUI_outfit_lock else not obj.MustardUI_outfit_lock
                    obj.hide_render = obj.MustardUI_outfit_visibility if obj.MustardUI_outfit_lock else not obj.MustardUI_outfit_lock
                
                elif collection.collection.name == outfits_list:
                    
                    obj.hide_viewport = obj.MustardUI_outfit_visibility
                    obj.hide_render = obj.MustardUI_outfit_visibility
            
                for modifier in rig_settings.model_body.modifiers:
                    if modifier.type == "MASK" and obj.name in modifier.name:
                        modifier.show_viewport = ( (collection.collection.name == outfits_list or obj.MustardUI_outfit_lock) and not obj.hide_viewport and rig_settings.outfits_global_mask)
                        modifier.show_render = ( (collection.collection.name == outfits_list or obj.MustardUI_outfit_lock) and not obj.hide_viewport and rig_settings.outfits_global_mask)

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
        
        for collection in self.outfits_collections:
            for obj in collection.collection.objects:
                
                if obj.type == "MESH":
                    obj.data.use_auto_smooth = self.outfits_global_normalautosmooth
                
                for modifier in obj.modifiers:
                    if modifier.type == "CORRECTIVE_SMOOTH":
                        modifier.show_viewport = self.outfits_global_smoothcorrection
                        modifier.show_render = self.outfits_global_smoothcorrection
                    elif modifier.type == "MASK":
                        modifier.show_viewport = self.outfits_global_mask
                        modifier.show_render = self.outfits_global_mask
                    elif modifier.type == "SHRINKWRAP":
                        modifier.show_viewport = self.outfits_global_shrinkwrap
                        modifier.show_render = self.outfits_global_shrinkwrap
        
                for modifier in self.model_body.modifiers:
                    if modifier.type == "MASK" and obj.name in modifier.name:
                        modifier.show_viewport = ( (collection.collection.name == self.outfits_list or obj.MustardUI_outfit_lock) and not obj.hide_viewport and self.outfits_global_mask)
                        modifier.show_render = ( (collection.collection.name == self.outfits_list or obj.MustardUI_outfit_lock) and not obj.hide_viewport and self.outfits_global_mask)
            
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
    # Additional options check
    outfit_additional_options: bpy.props.BoolProperty(default = True,
                        name = "Additional Outfit Options",
                        description = "Enable the additional outfits options.\nThese options will appear when clicking on the cogwheel near the outfits pieces.\nCheck the documentation for setting them up")
    
    # Global outfit properties
    outfits_global_smoothcorrection: bpy.props.BoolProperty(default = True,
                        name = "Smooth Correction",
                        update = outfits_global_options_update)
    
    outfits_global_shrinkwrap: bpy.props.BoolProperty(default = True,
                        name = "Shrinkwrap",
                        update = outfits_global_options_update)
                        
    outfits_global_mask: bpy.props.BoolProperty(default = True,
                        name = "Mask",
                        update = outfits_global_options_update)
                        
    outfits_global_normalautosmooth: bpy.props.BoolProperty(default = True,
                        name = "Normals Auto Smooth",
                        update = outfits_global_options_update)
    
    # Store number of additional properties
    outfits_additional_properties_number: bpy.props.IntProperty(default = 0,
                        name = "")
    
    # Extras
    extras_collection: bpy.props.PointerProperty(name = "Extras Collection",
                        type = bpy.types.Collection)

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
    # Particle system enable
    particle_systems_enable: bpy.props.BoolProperty(default = True,
                        name = "Particle Systems",
                        description = "Show Particle Systems in the UI.\nIf enabled, particle systems on the body mesh will automatically be added to the UI")
    
    # ------------------------------------------------------------------------
    #    Diffeomorphic support
    # ------------------------------------------------------------------------
    
    # Function to update global collection properties
    def diffeomorphic_enable_update(self, context):
        
        if self.diffeomorphic_enable:
            bpy.ops.mustardui.dazmorphs_enabledrivers()
        else:
            bpy.ops.mustardui.dazmorphs_disabledrivers()
        
        return
    
    # Diffeomorphic support
    diffeomorphic_support: bpy.props.BoolProperty(default = False,
                        name = "Diffeomorphic Support (Experimental)",
                        description = "Enable Diffeomorphic support.\nIf enabled, standard morphs from Diffomorphic will be added to the UI")
    
    diffeomorphic_enable: bpy.props.BoolProperty(default = True,
                        name = "Enable Diffeomorphic morphs",
                        description = "Enable Diffeomorphic morphs.\nNote that this might affect performance",
                        update = diffeomorphic_enable_update)
    
    diffeomorphic_morphs_list: bpy.props.CollectionProperty(name = "Daz Morphs List",
                        type=MustardUI_DazMorph)
    
    # Additional properties
    # Store number of additional properties
    diffeomorphic_morphs_number: bpy.props.IntProperty(default = 0,
                        name = "")
    
    diffeomorphic_emotions: bpy.props.BoolProperty(default = False,
                        name = "Diffeomorphic Emotions",
                        description = "Search for Diffeomorphic emotions")
    diffeomorphic_emotions_collapse: bpy.props.BoolProperty(default = True)
    diffeomorphic_emotions_custom: bpy.props.StringProperty(default = "",
                        name = "Custom morphs",
                        description = "Add strings to add custom morphs (they should map the initial part of the name of the morph), separated by commas.\nNote: spaces and order are considered")
    
    diffeomorphic_facs_emotions: bpy.props.BoolProperty(default = False,
                        name = "Diffeomorphic FACS Emotions",
                        description = "Search for Diffeomorphic FACS emotions")
    diffeomorphic_facs_emotions_collapse: bpy.props.BoolProperty(default = True)
    
    diffeomorphic_emotions_units: bpy.props.BoolProperty(default = False,
                        name = "Diffeomorphic Emotions Units",
                        description = "Search for Diffeomorphic emotions units")
    diffeomorphic_emotions_units_collapse: bpy.props.BoolProperty(default = True)
    
    diffeomorphic_facs_emotions_units: bpy.props.BoolProperty(default = False,
                        name = "Diffeomorphic FACS Emotions Units",
                        description = "Search for Diffeomorphic FACS emotions units")
    diffeomorphic_facs_emotions_units_collapse: bpy.props.BoolProperty(default = True)
    
    diffeomorphic_body_morphs: bpy.props.BoolProperty(default = False,
                        name = "Diffeomorphic Body Morphs",
                        description = "Search for Diffeomorphic Body morphs")
    diffeomorphic_body_morphs_collapse: bpy.props.BoolProperty(default = True)
    diffeomorphic_body_morphs_custom: bpy.props.StringProperty(default = "",
                        name = "Custom morphs",
                        description = "Add strings to add custom morphs (they should map the initial part of the name of the morph), separated by commas.\nNote: spaces and order are considered")
    
    diffeomorphic_search: bpy.props.StringProperty(name = "",
                        description = "Search for a specific morph",
                        default = "")
    
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
#    Particle systems definitions
# ------------------------------------------------------------------------

# Particle systems functions
def mustardui_particle_hair_update(self, context):
    
    poll, obj = mustardui_active_object(context, config = 0)
    rig_settings = obj.MustardUI_RigSettings
    
    for psys in rig_settings.model_body.particle_systems:
        if psys.settings.name == self.name:
            rig_settings.model_body.modifiers[psys.name].show_render = self.mustardui_particle_hair_enable
            rig_settings.model_body.modifiers[psys.name].show_viewport = self.mustardui_particle_hair_enable_viewport
            break
    
    return

# Properties needed to create show/hide buttons in the UI
bpy.types.ParticleSettings.mustardui_particle_hair_enable = bpy.props.BoolProperty(default = False,
                    name = "",
                    description = "Enable particle hair effect during rendering",
                    update = mustardui_particle_hair_update)
bpy.types.ParticleSettings.mustardui_particle_hair_enable_viewport = bpy.props.BoolProperty(default = False,
                    name = "",
                    description = "Enable particle hair effect in viewport.\nThis will greatly affect performance and memory usage. Use it only for previews",
                    update = mustardui_particle_hair_update)

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
        
        return object in [x.collection for x in rig_settings.outfits_collections] or object == rig_settings.extras_collection
    
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
                    self.layers[i].id = 0
                        
        
        self.config_layer_store = self.config_layer
        
        return

    config_layer: bpy.props.BoolVectorProperty(subtype = "LAYER",
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
    
    # ------------------------------------------------------------------------
    #    Tools - Lips Shrinkwrap
    # ------------------------------------------------------------------------

    def lips_shrinkwrap_update(self, context):
        
        poll, arm = mustardui_active_object(context, config = 0)
        if self.lips_shrinkwrap_armature_object != None:
            armature = self.lips_shrinkwrap_armature_object
        else:
            ShowMessageBox("Fatal error", "MustardUI Information", icon = "ERROR")
        
        bones_lips = ['c_lips_smile.r','c_lips_top.r','c_lips_top_01.r','c_lips_top.x','c_lips_top.l','c_lips_top_01.l','c_lips_smile.l','c_lips_bot.r','c_lips_bot_01.r','c_lips_bot.x','c_lips_bot.l','c_lips_bot_01.l']
        
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
                
                if bone == 'c_lips_smile.r' or bone == 'c_lips_smile.l':
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
        if self.lips_shrinkwrap_armature_object != None and arm != None:
            armature = self.lips_shrinkwrap_armature_object
        else:
            ShowMessageBox("Fatal error", "MustardUI Information", icon = "ERROR")
            
        bones_lips = ['c_lips_smile.r','c_lips_top.r','c_lips_top_01.r','c_lips_top.x','c_lips_top.l','c_lips_top_01.l','c_lips_smile.l','c_lips_bot.r','c_lips_bot_01.r','c_lips_bot.x','c_lips_bot.l','c_lips_bot_01.l']
        
        if self.lips_shrinkwrap:
        
            for bone in bones_lips:
                
                constr = armature.pose.bones[bone].constraints[self.lips_shrink_constr_name]
                constr.distance = self.lips_shrinkwrap_dist
                
                if bone == 'c_lips_smile.r' or bone == 'c_lips_smile.l':
                    constr.distance = constr.distance * self.lips_shrinkwrap_dist_corr
        
        return

    def lips_shrinkwrap_friction_infl_update(self, context):
        
        poll, arm = mustardui_active_object(context, config = 0)
        if self.lips_shrinkwrap_armature_object != None and arm != None:
            armature = self.lips_shrinkwrap_armature_object
        else:
            ShowMessageBox("Fatal error", "MustardUI Information", icon = "ERROR")
        
        bones_lips = ['c_lips_smile.r','c_lips_top.r','c_lips_top_01.r','c_lips_top.x','c_lips_top.l','c_lips_top_01.l','c_lips_smile.l','c_lips_bot.r','c_lips_bot_01.r','c_lips_bot.x','c_lips_bot.l','c_lips_bot_01.l']
        
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
                                             description="Enable Lips shrinkwrap tool.\nThis can be added only on ARP rigs at the moment")
    
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
#    Body additional options components
# ------------------------------------------------------------------------

# Function to add a option to the object, if not already there
def mustardui_add_option_item_body(collection, item):
    
    for el in collection:
        if el.name == item[0] and el.type == item[2]:
            return
    
    add_item = collection.add()
    add_item.name = item[0]
    add_item.type = item[2]
    
    if item[2] in [0,2]:
        add_item.body_bool_value = item[1]
    elif item[2] in [1,3]:
        add_item.body_float_value = item[1]
    else:
        add_item.body_color_value = item[1]
    
    return

# This operator will check for additional options for the body
class MustardUI_Body_CheckAdditionalOptions(bpy.types.Operator):
    """Search for additional options to display in the UI Body panel"""
    bl_idname = "mustardui.body_checkadditionaloptions"
    bl_label = "Check Additional Options"

    @classmethod
    def poll(cls, context):
        
        res, arm = mustardui_active_object(context, config = 1)
        return res

    def execute(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config = 1)
        rig_settings = obj.MustardUI_RigSettings
        
        # Clean the additional options properties
        rig_settings.body_additional_properties.clear()
        
        for mat in rig_settings.model_body.data.materials:
            for j in range(len(mat.node_tree.nodes)):
                if "MustardUI Float" in mat.node_tree.nodes[j].name and mat.node_tree.nodes[j].type=="VALUE":
                    mustardui_add_option_item_body(rig_settings.body_additional_properties, [mat.node_tree.nodes[j].name[len("MustardUI Float - "):], mat.node_tree.nodes[j].outputs[0].default_value, 3])
                elif "MustardUI Bool" in mat.node_tree.nodes[j].name and mat.node_tree.nodes[j].type=="VALUE":
                    mustardui_add_option_item_body(rig_settings.body_additional_properties, [mat.node_tree.nodes[j].name[len("MustardUI Bool - "):], mat.node_tree.nodes[j].outputs[0].default_value, 2])
                if "MustardUI" in mat.node_tree.nodes[j].name and mat.node_tree.nodes[j].type=="RGB":
                    mustardui_add_option_item_body(rig_settings.body_additional_properties, [mat.node_tree.nodes[j].name[len("MustardUI - "):], mat.node_tree.nodes[j].outputs[0].default_value, 4])
        if rig_settings.model_body.data.shape_keys != None:
            for shape_key in rig_settings.model_body.data.shape_keys.key_blocks:
                if "MustardUI Float" in shape_key.name:
                    mustardui_add_option_item_body(rig_settings.body_additional_properties, [shape_key.name[len("MustardUI Float - "):], shape_key.value, 1])
                elif "MustardUI Bool" in shape_key.name:
                    mustardui_add_option_item_body(rig_settings.body_additional_properties, [shape_key.name[len("MustardUI Bool - "):], shape_key.value, 0])
        
        properties_number = 0                       
        if settings.debug:
            print("\nMustardUI - Additional Body options found\n")
        # Print the options
        for el in rig_settings.body_additional_properties:
            if settings.debug:
                print(el.name + ": type " + str(el.type))
            properties_number = properties_number + 1
        
        rig_settings.body_additional_properties_number = properties_number
        
        
        self.report({'INFO'}, 'MustardUI - Additional Body options check completed.')

        return {'FINISHED'}

# ------------------------------------------------------------------------
#    Outfits additional options components
# ------------------------------------------------------------------------

bpy.types.Object.mustardui_additional_options_show = bpy.props.BoolProperty(default = False,
                    name = "",
                    description = "Show additional options")
bpy.types.Object.mustardui_additional_options_show_lock = bpy.props.BoolProperty(default = False,
                    name = "",
                    description = "Show additional options")

# Function to add a option to the object, if not already there
def mustardui_add_option_item(collection, item):
    i=True
    for el in collection:
        if el.name == item[0] and el.path == item[1] and el.id == item[2]:
            i=False
            break
    if i:
        add_item = collection.add()
        add_item.name = item[0]
        add_item.path = item[1]
        add_item.id = item[2]
        add_item.object = item[3]
        add_item.type = item[4]

# This operator will check for additional options for the outfits
class MustardUI_Outfits_CheckAdditionalOptions(bpy.types.Operator):
    """Search for additional options to display in the UI Outfit list"""
    bl_idname = "mustardui.outfits_checkadditionaloptions"
    bl_label = "Check Additional Options"

    @classmethod
    def poll(cls, context):
        
        res, arm = mustardui_active_object(context, config = 1)
        return res

    def execute(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        res, arm = mustardui_active_object(context, config = 1)
        rig_settings = arm.MustardUI_RigSettings
        
        # Clean the additional options properties
        for obj in bpy.data.objects:
            obj.mustardui_additional_options.clear()
        
        collections = [x.collection for x in rig_settings.outfits_collections if hasattr(x.collection, 'name')]
        if rig_settings.extras_collection != None:
            collections.append(rig_settings.extras_collection)
        
        for collection in collections:
            for obj in collection.objects:
                if obj.type == "MESH":
                    for mat in obj.data.materials:
                        for j in range(len(mat.node_tree.nodes)):
                            if "MustardUI Float" in mat.node_tree.nodes[j].name and mat.node_tree.nodes[j].type=="VALUE":
                                mustardui_add_option_item(obj.mustardui_additional_options, [mat.node_tree.nodes[j].name[len("MustardUI Float - "):], 'bpy.data.materials[\''+mat.name+'\'].node_tree.nodes[\''+mat.node_tree.nodes[j].name+'\'].outputs[0]', 'default_value', obj, 3])
                            elif "MustardUI Bool" in mat.node_tree.nodes[j].name and mat.node_tree.nodes[j].type=="VALUE":
                                mustardui_add_option_item(obj.mustardui_additional_options, [mat.node_tree.nodes[j].name[len("MustardUI Bool - "):], 'bpy.data.materials[\''+mat.name+'\'].node_tree.nodes[\''+mat.node_tree.nodes[j].name+'\'].outputs[0]', 'default_value', obj, 2])
                            if "MustardUI" in mat.node_tree.nodes[j].name and mat.node_tree.nodes[j].type=="RGB":
                                mustardui_add_option_item(obj.mustardui_additional_options, [mat.node_tree.nodes[j].name[len("MustardUI - "):], 'bpy.data.materials[\''+mat.name+'\'].node_tree.nodes[\''+mat.node_tree.nodes[j].name+'\'].outputs[0]', 'default_value', obj, 4])
                    if obj.data.shape_keys != None:
                        for shape_key in obj.data.shape_keys.key_blocks:
                            if "MustardUI Float" in shape_key.name:
                                mustardui_add_option_item(obj.mustardui_additional_options, [shape_key.name[len("MustardUI Float - "):], 'bpy.data.objects[\''+obj.name+'\'].data.shape_keys.key_blocks[\''+shape_key.name+'\']', 'value', obj, 1])
                            elif "MustardUI Bool" in shape_key.name:
                                mustardui_add_option_item(obj.mustardui_additional_options, [shape_key.name[len("MustardUI Bool - "):], 'bpy.data.objects[\''+obj.name+'\'].data.shape_keys.key_blocks[\''+shape_key.name+'\']', 'value', obj, 0])
        
        properties_number = 0                       
        if settings.debug:
            print("\nMustardUI - Additional Outfit options found\n")
            # Print the options
        for obj in bpy.data.objects:
            for el in obj.mustardui_additional_options:
                if settings.debug:
                    print(el.object.name + ": "+el.name+" with path "+el.path+'.'+el.id)
                properties_number = properties_number + 1
        
        rig_settings.outfits_additional_properties_number = properties_number
        
        
        self.report({'INFO'}, 'MustardUI - Additional Outfit options check completed.')

        return {'FINISHED'}

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
                for x in rig_settings.model_armature_object.keys():
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
                for x in rig_settings.model_armature_object.keys():
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
            exec('rig_settings.model_armature_object' + '[\"' + morph.path + '\"] = 0.')
        
        self.report({'INFO'}, 'MustardUI - Morphs values restored to default.')
        
        return {'FINISHED'}

class MustardUI_DazMorphs_DisableDrivers(bpy.types.Operator):
    """Disable drivers to improve performance (the correctives will not be disabled). This can be used only if the armature is selected"""
    bl_idname = "mustardui.dazmorphs_disabledrivers"
    bl_label = "Button"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        
        res, arm = mustardui_active_object(context, config = 0)
        
        return True
        
        if arm != None:
            rig_settings = arm.MustardUI_RigSettings
            
            if rig_settings.model_armature_object == None:
                return False
        
            return bpy.context.active_object == rig_settings.model_armature_object
        
        else:
            return True
 
    def execute(self, context):
        
        res, arm = mustardui_active_object(context, config = 0)
        rig_settings = arm.MustardUI_RigSettings
        
        objects = [rig_settings.model_body]
        
        aobj = context.active_object
        
        context.view_layer.objects.active = rig_settings.model_armature_object
        
        bpy.ops.daz.disable_drivers({object:rig_settings.model_armature_object})
        
        for collection in rig_settings.outfits_collections:
            for obj in collection.collection.objects:
                if obj.type == "MESH":
                    objects.append(obj)
        
        for obj in objects:
            if obj.data.shape_keys != None:
                for driver in obj.data.shape_keys.animation_data.drivers:
                    if not "pJCM" in driver.data_path:
                        driver.mute = True
        
        for driver in rig_settings.model_armature_object.animation_data.drivers:
            
            if "evalMorphs" in driver.driver.expression:
                    driver.mute = True
        
        rig_settings.diffeomorphic_emotions_units_collapse = True
        rig_settings.diffeomorphic_emotions_collapse = True
        rig_settings.diffeomorphic_facs_emotions_units_collapse = True
        rig_settings.diffeomorphic_facs_emotions_collapse = True
        rig_settings.diffeomorphic_body_morphs_collapse = True
        
        context.view_layer.objects.active = aobj
        
        return{'FINISHED'}

class MustardUI_DazMorphs_EnableDrivers(bpy.types.Operator):
    """Enable all drivers. This can be used only if the armature is selected"""
    bl_idname = "mustardui.dazmorphs_enabledrivers"
    bl_label = "Button"
    bl_options = {'REGISTER', 'UNDO'}
 
    @classmethod
    def poll(cls, context):
        
        res, arm = mustardui_active_object(context, config = 0)
        
        return True
        
        if arm != None:
            rig_settings = arm.MustardUI_RigSettings
        
            return bpy.context.active_object == rig_settings.model_armature_object
        
        else:
            return True
 
    def execute(self, context):
        
        res, arm = mustardui_active_object(context, config = 0)
        rig_settings = arm.MustardUI_RigSettings
        
        objects = [rig_settings.model_body]
        
        aobj = context.active_object
        
        context.view_layer.objects.active = rig_settings.model_armature_object
        
        bpy.ops.daz.enable_drivers()
        
        for collection in rig_settings.outfits_collections:
            for obj in collection.collection.objects:
                if obj.type == "MESH":
                    objects.append(obj)
        
        for obj in objects:
            if obj.data.shape_keys != None:
                for driver in obj.data.shape_keys.animation_data.drivers:
                    if not "pJCM" in driver.data_path:
                        driver.mute = False
        
        for driver in rig_settings.model_armature_object.animation_data.drivers:
            
            if "evalMorphs" in driver.driver.expression or driver.driver.expression == "0.0" or driver.driver.expression == "-0.0":
                    driver.mute = False
        
        context.view_layer.objects.active = aobj
        
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
            collections = [x for x in rig_settings.outfits_collections]
            
            for x in range(len(rig_settings.outfits_collections)):
                if not hasattr(rig_settings.outfits_collections[x].collection, 'name'):
                    rig_settings.outfits_collections.remove(x)
                    if settings.debug:
                        print('MustardUI - A ghost outfit collection has been removed.')
            
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
            if armature_settings.enable_ik_fk and rig_settings.model_rig_type == "mhx" and settings.status_diffeomorphic < 2:
                warnings = warnings + 1
                if settings.debug:
                    print('MustardUI - Configuration Warning - IK/FK support requested for MHX rig, but Diffeomorphic is not installed')
            
            if tools_settings.lips_shrinkwrap_armature_object != None and tools_settings.lips_shrinkwrap_enable:
                if not hasattr(tools_settings.lips_shrinkwrap_armature_object.data,'[\"arp_updated\"]'):
                    tools_settings.lips_shrinkwrap_armature_object = None
                    tools_settings.lips_shrinkwrap_enable = False
                    warnings = warnings + 1
                    if settings.debug:
                        print('MustardUI - Configuration Warning - Lips shrinkwrap Armature Object is not ARP. Select the correct armature. In the meanwhile, the tool has been disabled')                  
            
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
        bpy.ops.mustardui.body_checkadditionaloptions()
        
        if rig_settings.body_additional_properties_number < 1:
            print('\nMustardUI - Smart Check - No additional property found.')
        
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
        
        # Search for additional options
        if settings.debug:
            print('\nMustardUI - Smart Check - Searching for additional options.')
        
        bpy.ops.mustardui.outfits_checkadditionaloptions()

        if rig_settings.outfits_additional_properties_number < 1:
            print('\nMustardUI - Smart Check - No additional property found.')
        
        # Standard armature setup for Mustard models (Auto-Rig Pro based rigs)
        if hasattr(obj,'[\"arp_updated\"]'):
            if settings.debug:
                print('\nMustardUI - Smart Check - Found an ARP rig, version: \'' + obj["arp_updated"] + '\' .')
            print('\nMustardUI - Smart Check - Setting layers as for Mustard models.')
            
            preset_Mustard_models = [(0, "Main", False),
                                    (1, "Advanced", False),
                                    (7, "Extra", False),
                                    (10, "Child Of - Ready", False),
                                    (31, "Rigging - Ready", True)]
            
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
            obj.MustardUI_script_file = bpy.data.texts['mustard_ui.py']
            bpy.data.texts['mustard_ui.py'].use_module = True
            self.report({'INFO'}, "MustardUI: UI correctly registered in " + obj.name)
        else:
            obj.MustardUI_script_file = None
            bpy.data.texts['mustard_ui.py'].use_module = False
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
        bpy.data.objects[self.obj].hide_render = not bpy.data.objects[self.obj].hide_render
        bpy.data.objects[self.obj].MustardUI_outfit_visibility = bpy.data.objects[self.obj].hide_viewport
        
        poll, obj = mustardui_active_object(context, config = 0)
        rig_settings = obj.MustardUI_RigSettings
        armature_settings = obj.MustardUI_ArmatureSettings
        
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
        
        rig_settings.outfits_global_smoothcorrection = self.enable
        rig_settings.outfits_global_shrinkwrap = self.enable
        rig_settings.outfits_global_mask = self.enable
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
#                    try:
#                        bpy.ops.constraint.childof_set_inverse(context_py, constraint=constr.name, owner='BONE')
#                    except:
#                        self.report({'ERROR'}, 'MustardUI - Can not set Inverse.')
            
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
            for collection in rig_settings.outfits_collections:
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
            for collection in rig_settings.outfits_collections:
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
                bpy.ops.object.modifier_move_up({"object" : obj}, modifier = mod.name)
            
            bpy.ops.object.meshdeform_bind({"object" : obj}, modifier=mod.name)
            
            mod.show_viewport = physics_settings.physics_enable
            mod.show_render = physics_settings.physics_enable
        
        # Outfits add
        for collection in rig_settings.outfits_collections:
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
                        bpy.ops.object.modifier_move_up({"object" : obj}, modifier = mod.name)
                    
                    bpy.ops.object.meshdeform_bind({"object" : obj}, modifier=mod.name)
                    
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
            bpy.ops.object.modifier_move_up({"object" : obj}, modifier = mod.name)
        
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
        for collection in rig_settings.outfits_collections:
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
            for collection in rig_settings.outfits_collections:
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
            
            for collection in rig_settings.outfits_collections:
                for obj in collection.collection.objects:
                    for modifier in obj.modifiers:
                        if modifier.type == 'MESH_DEFORM' and physics_settings.physics_modifiers_name in modifier.name and "Cage" in modifier.name and cage.name in modifier.name:
                           bpy.ops.object.meshdeform_bind({"object" : obj}, modifier=modifier.name)
                           if not modifier.is_bound:
                               bpy.ops.object.meshdeform_bind({"object" : obj}, modifier=modifier.name)
            
            obj = rig_settings.model_body
            for modifier in rig_settings.model_body.modifiers:
                if modifier.type == 'MESH_DEFORM' and physics_settings.physics_modifiers_name in modifier.name and "Cage" in modifier.name and cage.name in modifier.name:
                    bpy.ops.object.meshdeform_bind({"object" : obj}, modifier=modifier.name)
                    if not modifier.is_bound:
                        bpy.ops.object.meshdeform_bind({"object" : obj}, modifier=modifier.name)
        
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
            if modifier.type == 'CLOTH' and "MustardUI" in modifier.name:
                modifier.show_viewport = physics_settings.physics_enable and cage.physics_enable
                modifier.show_render = physics_settings.physics_enable and cage.physics_enable
    
        for collection in rig_settings.outfits_collections:
            for obj in collection.collection.objects:
                for modifier in obj.modifiers:
                    if modifier.type == 'MESH_DEFORM' and physics_settings.physics_modifiers_name in modifier.name and "Cage" in modifier.name and cage.name in modifier.name:
                       modifier.show_viewport = physics_settings.physics_enable and cage.physics_enable
                       modifier.show_render = physics_settings.physics_enable and cage.physics_enable

        for modifier in rig_settings.model_body.modifiers:
            if modifier.type == 'MESH_DEFORM' and physics_settings.physics_modifiers_name in modifier.name and "Cage" in modifier.name and cage.name in modifier.name:
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
                        name = "MustardUI Definitions",
                        description = "Enable MustardUI definitions of physical settings.\nEnable this to substitute tension, compression, shear and bending with more 'human readable' settings")
    
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
                        name = "MustardUI Definitions",
                        description = "Enable MustardUI definitions of physical settings.\nEnable this to substitute tension, compression, shear and bending with more 'human readable' settings")
    
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
        layout.label(text="Properties",icon="MENU_PANEL")
        
        # Body mesh settings
        row = layout.row(align=False)
        row.prop(rig_settings, "body_config_collapse", icon="TRIA_DOWN" if not rig_settings.body_config_collapse else "TRIA_RIGHT", icon_only=True, emboss=False)
        row.label(text="Body",icon="OUTLINER_OB_ARMATURE")
        
        if not rig_settings.body_config_collapse:
            box = layout.box()
            box.label(text="Global properties", icon="MODIFIER")
            box.prop(rig_settings,"body_enable_sss")
            box.prop(rig_settings,"body_enable_subdiv")
            box.prop(rig_settings,"body_enable_smoothcorr")
            box.prop(rig_settings,"body_enable_norm_autosmooth")
            
            # Operator to check for additional options
            box = layout.box()
            box.label(text="Additional outfit options", icon="PRESET_NEW")
            box.label(text="  Current properties number: " + str(rig_settings.body_additional_properties_number))
            box.operator('mustardui.body_checkadditionaloptions')
        
        # Outfits properties
        row = layout.row(align=False)
        row.prop(rig_settings, "outfit_config_collapse", icon="TRIA_DOWN" if not rig_settings.outfit_config_collapse else "TRIA_RIGHT", icon_only=True, emboss=False)
        row.label(text="Outfits",icon="MOD_CLOTH")
        
        if not rig_settings.outfit_config_collapse:
            box = layout.box()
            box.label(text="General settings", icon="MODIFIER")
            box.prop(rig_settings,"outfit_nude")
            box.prop(rig_settings,"outfit_additional_options")
            if len(rig_settings.outfits_collections)>0:
                box = layout.box()
                # Outfit list
                box.label(text="Outfits List", icon="OUTLINER_COLLECTION")
                box = box.box()
                for collection in rig_settings.outfits_collections:
                    if hasattr(collection.collection, 'name'):
                        row = box.row()
                        row.label(text=collection.collection.name)
                        del_col = row.operator("mustardui.delete_outfit",text="",icon="X").col = collection.collection.name
                
                if rig_settings.outfit_additional_options:
                    # Operator to check for additional options
                    box = layout.box()
                    box.label(text="Additional outfit options", icon="PRESET_NEW")
                    box.label(text="  Current properties number: " + str(rig_settings.outfits_additional_properties_number))
                    box.operator('mustardui.outfits_checkadditionaloptions')
                
                # Outfit properties
                box = layout.box()
                box.label(text="Global properties", icon="MODIFIER")
                box.prop(rig_settings,"outfits_enable_global_smoothcorrection")
                box.prop(rig_settings,"outfits_enable_global_shrinkwrap")
                box.prop(rig_settings,"outfits_enable_global_mask")
                box.prop(rig_settings,"outfits_enable_global_normalautosmooth")
            
            else:
                box = layout.box()
                box.label(text="No Outfits added yet.", icon="ERROR")
            
            box = layout.box()
            # Extras list
            box.label(text="Extras", icon="PLUS")
            box.prop(rig_settings,"extras_collection", text="")
        
        # Hair
        row = layout.row(align=False)
        row.prop(rig_settings, "hair_config_collapse", icon="TRIA_DOWN" if not rig_settings.hair_config_collapse else "TRIA_RIGHT", icon_only=True, emboss=False)
        row.label(text="Hair",icon="HAIR")
        
        if not rig_settings.hair_config_collapse:
            box = layout.box()
            box.label(text="Hair Collection", icon="OUTLINER_COLLECTION")
            box.prop(rig_settings,"hair_collection", text="")
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
                box.operator('mustardui.armature_initialize', text = "Remove Armature Panel").clean = True
                
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
            box.label(text="Enable tools", icon="MODIFIER")
            box.prop(tools_settings,'childof_enable')
            row = box.row()
            if not rig_settings.model_rig_type == "arp" or not hasattr(obj,'[\"arp_updated\"]'):
                row.enabled = False
            row.prop(tools_settings,'lips_shrinkwrap_enable')
            box.prop(lattice_settings,'lattice_panel_enable')
            
            if lattice_settings.lattice_panel_enable:
                box = layout.box()
                box.label(text="Lattice tool settings", icon="MOD_LATTICE")
                box.prop(lattice_settings,'lattice_object')
                box.operator('mustardui.tools_latticesetup', text="Lattice Setup").mod = 0
                box.operator('mustardui.tools_latticesetup', text="Lattice Clean").mod = 1
        
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
            row.label(text="Report Bug")
            row.scale_x = row_scale
            row.prop(rig_settings,'url_reportbug', text="")
        
        # Various properties
        row = layout.row(align=False)
        row.prop(rig_settings, "various_config_collapse", icon="TRIA_DOWN" if not rig_settings.various_config_collapse else "TRIA_RIGHT", icon_only=True, emboss=False)
        row.label(text="Others",icon="SETTINGS")
        if not rig_settings.various_config_collapse:
            box = layout.box()
            box.label(text="External Add-ons", icon="DOCUMENTS")
            row = box.row()
            if settings.status_diffeomorphic != 2:
                row.enabled = False
            row.prop(rig_settings,"diffeomorphic_support")
            if rig_settings.diffeomorphic_support:
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
                
                if settings.status_diffeomorphic == 1:
                    box.label(icon='ERROR',text="Debug: Diffeomorphic not enabled!")
                elif settings.status_diffeomorphic  == 0:
                    box.label(icon='ERROR', text="Debug: Diffeomorphic not installed!")
                
                box3 = box.box()
                box3.label(text="Morphs options", icon="PRESET_NEW")
                box3.label(text="  Current morphs number: " + str(rig_settings.diffeomorphic_morphs_number))
                box3.operator('mustardui.dazmorphs_checkmorphs')
            
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
        
        # Configuration button
        layout.separator()
        layout.prop(settings,"debug")
        if not obj.MustardUI_created:
            layout.prop(settings,"viewport_model_selection_after_configuration")
        layout.operator('mustardui.configuration', text="End the configuration")
        

# Panels for users
class PANEL_PT_MustardUI_Body(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Body"
    bl_label = "Body Settings"
    bl_options = {"DEFAULT_CLOSED"}
    
    @classmethod
    def poll(cls, context):
        
        res, arm = mustardui_active_object(context, config = 0)
        
        if arm != None:
            rig_settings = arm.MustardUI_RigSettings
            
            # Check if there is any property to show
            prop_to_show = rig_settings.body_enable_sss or rig_settings.body_enable_subdiv or rig_settings.body_enable_smoothcorr or rig_settings.body_enable_norm_autosmooth
        
            return res and prop_to_show
        
        else:
            return res

    def draw(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        
        poll, obj = mustardui_active_object(context, config = 0)
        rig_settings = obj.MustardUI_RigSettings
        
        layout = self.layout
        
        if rig_settings.body_enable_sss or rig_settings.body_enable_subdiv or rig_settings.body_enable_smoothcorr or rig_settings.body_enable_norm_autosmooth:
            
            box = layout.box()
            box.label(text="Body properties", icon="OUTLINER_OB_ARMATURE")
        
            if rig_settings.body_enable_subdiv:
                row = box.row(align=True)
                row.prop(rig_settings,"body_subdiv_view")
                row.scale_x=0.4
                row.prop(rig_settings,"body_subdiv_view_lv")
                
                row = box.row(align=True)
                row.prop(rig_settings,"body_subdiv_rend")
                row.scale_x=0.4
                row.prop(rig_settings,"body_subdiv_rend_lv")
        
            if rig_settings.body_enable_smoothcorr:
                box.prop(rig_settings,"body_smooth_corr")
            
            if rig_settings.body_enable_norm_autosmooth:
                box.prop(rig_settings,"body_norm_autosmooth")
            
            if rig_settings.body_enable_sss:
                box.prop(rig_settings,"body_sss")
                
        if len(rig_settings.body_additional_properties) > 0:
            
            additional_properties_sk = sorted([x for x in rig_settings.body_additional_properties if x.type in [0,1]], key = lambda x:x.name)
            additional_properties_mat = sorted([x for x in rig_settings.body_additional_properties if x.type in [2,3,4]], key = lambda x:x.name)
            
            if len(additional_properties_sk) > 0:
                box = layout.box()
                box.label(text = "Body Shape", icon="SHAPEKEY_DATA")
                for aprop in additional_properties_sk:
                    row = box.row()
                    row.label(text=aprop.name)
                    if aprop.type == 0:
                        row.prop(aprop, 'body_bool_value', text = "")
                    else:
                        row.prop(aprop, 'body_float_value', text = "")
            
            if len(additional_properties_mat) > 0:
                box = layout.box()
                box.label(text = "Skin properties", icon="OUTLINER_OB_SURFACE")
                for aprop in additional_properties_mat:
                    row = box.row()
                    row.label(text=aprop.name)
                    if aprop.type == 2:
                        row.prop(aprop, 'body_bool_value', text = "")
                    elif aprop.type == 3:
                        row.prop(aprop, 'body_float_value', text = "")
                    else:
                        row.prop(aprop, 'body_color_value', text = "")

class PANEL_PT_MustardUI_ExternalMorphs(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_ExternalMorphs"
    bl_label = "External Morphs"
    bl_options = {"DEFAULT_CLOSED"}
    
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
        
        poll, obj = mustardui_active_object(context, config = 0)
        rig_settings = obj.MustardUI_RigSettings
        
        self.layout.prop(rig_settings, "diffeomorphic_enable", text = "", toggle = False)

    def draw(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        
        poll, obj = mustardui_active_object(context, config = 0)
        rig_settings = obj.MustardUI_RigSettings
        
        layout = self.layout
        layout.enabled = rig_settings.diffeomorphic_enable
        
        if settings.status_diffeomorphic == 1:
            layout.label(icon='ERROR',text="Diffeomorphic not enabled!")
            return
        elif settings.status_diffeomorphic == 0:
            layout.label(icon='ERROR', text="Diffeomorphic not installed!")
            return
        
        row = layout.row()    
        row.prop(rig_settings, 'diffeomorphic_search', icon = "VIEWZOOM")
        row = row.row(align=True)
        row.operator('mustardui.dazmorphs_defaultvalues', icon = "LOOP_BACK", text = "")
        
        # Emotions Units
        if rig_settings.diffeomorphic_emotions_units:
            box = layout.box()
            row = box.row(align=False)
            row.prop(rig_settings, "diffeomorphic_emotions_units_collapse", icon="TRIA_DOWN" if not rig_settings.diffeomorphic_emotions_units_collapse else "TRIA_RIGHT", icon_only=True, emboss=False)
            row.label(text="Emotion Units")
            
            if not rig_settings.diffeomorphic_emotions_units_collapse:
                
                for morph in [x for x in rig_settings.diffeomorphic_morphs_list if x.type == 0 and rig_settings.diffeomorphic_search.lower() in x.name.lower()]:
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
            row.label(text="Emotions")
            
            if not rig_settings.diffeomorphic_emotions_collapse:
                for morph in [x for x in rig_settings.diffeomorphic_morphs_list if x.type == 1 and rig_settings.diffeomorphic_search.lower() in x.name.lower()]:
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
            row.label(text="FACS Emotion Units")
            
            if not rig_settings.diffeomorphic_facs_emotions_units_collapse:
                
                for morph in [x for x in rig_settings.diffeomorphic_morphs_list if x.type == 2 and rig_settings.diffeomorphic_search.lower() in x.name.lower()]:
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
            row.label(text="FACS Emotions")
            
            if not rig_settings.diffeomorphic_facs_emotions_collapse:
                
                for morph in [x for x in rig_settings.diffeomorphic_morphs_list if x.type == 3 and rig_settings.diffeomorphic_search.lower() in x.name.lower()]:
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
            row.label(text="Body Morphs")
            
            if not rig_settings.diffeomorphic_body_morphs_collapse:
                
                for morph in [x for x in rig_settings.diffeomorphic_morphs_list if x.type == 4 and rig_settings.diffeomorphic_search.lower() in x.name.lower()]:
                    if hasattr(rig_settings.model_armature_object,'[\"' + morph.path + '\"]'):
                        box.prop(rig_settings.model_armature_object, '[\"' + morph.path + '\"]', text = morph.name)
                    else:
                        row = box.row(align=False)
                        row.label(text = morph.name)
                        row.prop(settings, 'daz_morphs_error', text = "", icon = "ERROR", emboss=False, icon_only = True)

                
class PANEL_PT_MustardUI_Outfits(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Outfits"
    bl_label = "Outfits & Hair Settings"
    bl_options = {"DEFAULT_CLOSED"}
    
    @classmethod
    def poll(cls, context):
        
        res, arm = mustardui_active_object(context, config = 0)
        
        if arm != None:
            
            rig_settings = arm.MustardUI_RigSettings
            
            # Check if one of these should be shown in the UI
            outfits_avail = len(rig_settings.outfits_collections)>0
            
            if rig_settings.hair_collection != None:
                hair_avail = len([x for x in rig_settings.hair_collection.objects if x.type == "MESH"])>1
            else:
                hair_avail = False
            
            if rig_settings.extras_collection != None:
                extras_avail = len(rig_settings.extras_collection.objects)>0
            else:
                extras_avail = False
            
            if rig_settings.model_body != None:
                particle_avail = len(rig_settings.model_body.particle_systems)>0 and rig_settings.particle_systems_enable
            else:
                particle_avail = False
        
            return res and (hair_avail or outfits_avail or extras_avail or particle_avail)
        
        else:
            return res

    def draw(self, context):
        
        settings = bpy.context.scene.MustardUI_Settings
        
        poll, obj = mustardui_active_object(context, config = 0)
        rig_settings = obj.MustardUI_RigSettings
        
        layout = self.layout
        
        # Outfit list
        if len(rig_settings.outfits_collections)>0:
            
            box = layout.box()
            box.label(text="Outfits list", icon="MOD_CLOTH")
            box.prop(rig_settings,"outfits_list", text="")
            
            if rig_settings.outfits_list != "Nude":
                if len(bpy.data.collections[rig_settings.outfits_list].objects)>0:
                    for obj in bpy.data.collections[rig_settings.outfits_list].objects:
                        row = box.row(align=True)
                        
                        if rig_settings.model_MustardUI_naming_convention:
                            row.operator("mustardui.object_visibility",text=obj.name[len(rig_settings.outfits_list + ' - '):], icon='OUTLINER_OB_'+obj.type, depress = not obj.hide_viewport).obj = obj.name
                        else:
                            row.operator("mustardui.object_visibility",text=obj.name, icon='OUTLINER_OB_'+obj.type, depress = not obj.hide_viewport).obj = obj.name

                        if len(obj.mustardui_additional_options)>0 and rig_settings.outfit_additional_options:
                            row.prop(bpy.data.objects[obj.name],"mustardui_additional_options_show", toggle=True, icon="PREFERENCES")
                            if bpy.data.objects[obj.name].mustardui_additional_options_show:
                                box2 = box.box()
                                for aprop in sorted(obj.mustardui_additional_options, key = lambda x:x.type):
                                    row2 = box2.row(align=True)
                                    
                                    # Icon choice
                                    if aprop.type in [0,1]:
                                        row2.label(text=aprop.name, icon="SHAPEKEY_DATA")
                                    else:
                                        row2.label(text=aprop.name, icon="MATERIAL")
                                    
                                    row2.scale_x=0.95
                                    
                                    if aprop.type in [0,2]:
                                        row2.prop(aprop, 'bool_value', text = "")
                                    else:
                                        try:
                                            row2.prop(eval(aprop.path), aprop.id, text = "")
                                        except:
                                            row2.prop(settings, 'additional_properties_error', text = "", icon = "ERROR", emboss=False, icon_only = True)
                        
                        if obj.MustardUI_outfit_lock:
                            row.prop(obj,"MustardUI_outfit_lock",toggle=True, icon='LOCKED')
                        else:
                            row.prop(obj,"MustardUI_outfit_lock",toggle=True, icon='UNLOCKED')
                else:
                    box.label(text="This Collection seems empty", icon="ERROR")
            
            # Locked objects list
            locked_objects = [x for x in bpy.data.objects if x.MustardUI_outfit_lock]
            if len(locked_objects)>0:
                box.separator()
                box.label(text="Locked objects:", icon="LOCKED")
                for obj in locked_objects:
                    row = box.row(align=True)
                    
                    if rig_settings.model_MustardUI_naming_convention:
                        row.operator("mustardui.object_visibility",text=obj.name[len(rig_settings.model_name):], icon='OUTLINER_OB_'+obj.type, depress = not obj.hide_viewport).obj = obj.name
                    else:
                        row.operator("mustardui.object_visibility",text=obj.name, icon='OUTLINER_OB_'+obj.type, depress = not obj.hide_viewport).obj = obj.name
                    
                    if len(obj.mustardui_additional_options)>0 and rig_settings.outfit_additional_options:
                        row.prop(bpy.data.objects[obj.name],"mustardui_additional_options_show_lock", toggle=True, icon="PREFERENCES")
                        if bpy.data.objects[obj.name].mustardui_additional_options_show_lock:
                            box2 = box.box()
                            for aprop in sorted(obj.mustardui_additional_options, key = lambda x:x.type):
                                row2 = box2.row(align=True)
                                
                                # Icon choice
                                if aprop.type in [0,1]:
                                    row2.label(text=aprop.name, icon="SHAPEKEY_DATA")
                                else:
                                    row2.label(text=aprop.name, icon="MATERIAL")
                                
                                row2.scale_x=0.9
                                
                                if aprop.type in [0,2]:
                                    row2.prop(aprop, 'bool_value', text = "")
                                else:
                                    try:
                                        row2.prop(eval(aprop.path), aprop.id, text = "")
                                    except:
                                        row2.prop(settings, 'additional_properties_error', text = "", icon = "ERROR", emboss=False, icon_only = True)
                    
                    if obj.MustardUI_outfit_lock:
                        row.prop(obj,"MustardUI_outfit_lock",toggle=True, icon='LOCKED')
                    else:
                        row.prop(obj,"MustardUI_outfit_lock",toggle=True, icon='UNLOCKED')
        
            # Outfit global properties
            if rig_settings.outfits_enable_global_smoothcorrection or rig_settings.outfits_enable_global_shrinkwrap or rig_settings.outfits_enable_global_mask or rig_settings.outfits_enable_global_normalautosmooth:
                
                box = layout.box()
                row = box.row(align=True)
                row.label(text="Outfits global properties", icon="MODIFIER")
                row.operator('mustardui.switchglobal_outfits', text="", icon="RESTRICT_VIEW_OFF").enable = True
                row.operator('mustardui.switchglobal_outfits', text="", icon="RESTRICT_VIEW_ON").enable = False
                if rig_settings.outfits_enable_global_smoothcorrection:
                    box.prop(rig_settings,"outfits_global_smoothcorrection")
                if rig_settings.outfits_enable_global_shrinkwrap:
                    box.prop(rig_settings,"outfits_global_shrinkwrap")
                if rig_settings.outfits_enable_global_mask:
                    box.prop(rig_settings,"outfits_global_mask")
                if rig_settings.outfits_enable_global_normalautosmooth:
                    box.prop(rig_settings,"outfits_global_normalautosmooth")
        
        # Extras
        if rig_settings.extras_collection != None:
            
            if len(rig_settings.extras_collection.objects)>0:
            
                box = layout.box()
                box.label(text="Extras", icon="PLUS")
                
                for obj in rig_settings.extras_collection.objects:
                    row = box.row(align=True)
                    
                    if rig_settings.model_MustardUI_naming_convention:
                        row.operator("mustardui.object_visibility",text=obj.name[len(rig_settings.extras_collection.name + ' - '):], icon='OUTLINER_OB_'+obj.type, depress = not obj.hide_viewport).obj = obj.name
                    else:
                        row.operator("mustardui.object_visibility",text=obj.name, icon='OUTLINER_OB_'+obj.type, depress = not obj.hide_viewport).obj = obj.name
                    
                    if len(obj.mustardui_additional_options)>0 and rig_settings.outfit_additional_options:
                        row.prop(bpy.data.objects[obj.name],"mustardui_additional_options_show", toggle=True, icon="PREFERENCES")
                        if bpy.data.objects[obj.name].mustardui_additional_options_show:
                            box2 = box.box()
                            for aprop in sorted(obj.mustardui_additional_options, key = lambda x:x.type):
                                row2 = box2.row(align=True)
                                
                                # Icon choice
                                if aprop.type in [0,1]:
                                    row2.label(text=aprop.name, icon="SHAPEKEY_DATA")
                                else:
                                    row2.label(text=aprop.name, icon="MATERIAL")
                                
                                row2.scale_x=0.9
                                
                                if aprop.type in [0,2]:
                                    row2.prop(aprop, 'bool_value', text = "")
                                else:
                                    try:
                                        row2.prop(eval(aprop.path), aprop.id, text = "")
                                    except:
                                        row2.prop(settings, 'additional_properties_error', text = "", icon = "ERROR", emboss=False, icon_only = True)
        
        # Hair
        if rig_settings.hair_collection != None:
            
            if len([x for x in rig_settings.hair_collection.objects if x.type == "MESH"])>1:
                
                box = layout.box()
                box.label(text="Hair list", icon="HAIR")
                box.prop(rig_settings,"hair_list", text="")
        
        # Particle systems
        if len(rig_settings.model_body.particle_systems)>0 and rig_settings.particle_systems_enable:
            box = layout.box()
            box.label(text="Hair particles", icon="PARTICLES")
            box2=box.box()
            for psys in rig_settings.model_body.particle_systems:
                row=box2.row()
                row.label(text=psys.name)
                row2=row.row(align=True)
                if psys.settings.mustardui_particle_hair_enable:
                    row2.prop(psys.settings, "mustardui_particle_hair_enable", text="", toggle=True, icon="RESTRICT_RENDER_OFF")
                else:
                    row2.prop(psys.settings, "mustardui_particle_hair_enable", text="", toggle=True, icon="RESTRICT_RENDER_ON")
                if psys.settings.mustardui_particle_hair_enable_viewport:
                    row2.prop(psys.settings, "mustardui_particle_hair_enable_viewport", text="", toggle=True, icon="RESTRICT_VIEW_OFF")
                else:
                    row2.prop(psys.settings, "mustardui_particle_hair_enable_viewport", text="", toggle=True, icon="RESTRICT_VIEW_ON")

class PANEL_PT_MustardUI_Armature(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Armature"
    bl_label = "Armature Settings"
    bl_options = {"DEFAULT_CLOSED"}
    
    @classmethod
    def poll(cls, context):
        
        res, obj = mustardui_active_object(context, config = 0)
        if obj != None:
            rig_settings = obj.MustardUI_RigSettings
            armature_settings = obj.MustardUI_ArmatureSettings
            
            enabled_layers = [x for x in range(0,32) if armature_settings.config_layer[x] and not armature_settings.layers[x].outfit_switcher_enable]
            
            if rig_settings.hair_collection != None:
                return res and (len(enabled_layers)>0 or (len([x for x in rig_settings.hair_collection.objects if x.type == "ARMATURE"])>1 and armature_settings.enable_automatic_hair))
            else:
                return res and len(enabled_layers)>0
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
                box.label(text='Hair Armature', icon="HAIR")
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
            
            box = layout.box()
            
            if settings.status_diffeomorphic > 1:
            
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
            return res and (arm.MustardUI_ToolsSettings.childof_enable or (arm.MustardUI_ToolsSettings.lips_shrinkwrap_enable and rig_settings.model_rig_type == "arp"))
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
        box.label(text="Select two bones:", icon="BONE_DATA")
        box.label(text="  - the first will be the parent,")
        box.label(text="  - the second will be the child.")
        box.prop(tools_settings, "childof_influence")
        layout.operator('mustardui.tools_childof', text="Enable").clean = 0
        
        layout.operator('mustardui.tools_childof', text="Remove Parent instances", icon="X").clean = 1

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
            return res and arm.MustardUI_ToolsSettings.lips_shrinkwrap_enable and rig_settings.model_rig_type == "arp"
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
        box.prop(tools_settings, "lips_shrinkwrap_dist")
        box.prop(tools_settings, "lips_shrinkwrap_dist_corr")
        
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
        
        box.prop(settings,"advanced")
        box.prop(settings,"maintenance")
        box.prop(settings,"debug")
        if settings.viewport_model_selection:
            box.operator('mustardui.viewportmodelselection', text="Viewport Model Selection", depress = True)
        else:
            box.operator('mustardui.viewportmodelselection', text="Viewport Model Selection", depress = False)
        
        if settings.maintenance:
            box = layout.box()
            box.label(text="Maintenance Tools", icon="SETTINGS")
            box.operator('mustardui.configuration', text="UI Configuration", icon = "PREFERENCES")
            
            if obj.MustardUI_script_file == None:
                box.operator('mustardui.registeruifile', text="Register UI Script", icon = "TEXT").register = True
            else:
                box.operator('mustardui.registeruifile', text="Un-register UI Script", icon = "TEXT").register = False
            
            box.operator('mustardui.remove', text="UI Removal", icon = "X")
            if platform.system() == 'Windows':
                box.separator()
                box.operator('wm.console_toggle', text="Toggle System Console", icon = "TOPBAR")
        
        box = layout.box()
        box.label(text="Version", icon="INFO")
        if rig_settings.model_version!='':
            box.label(text="Model:           " + rig_settings.model_version)
        box.label(text="MustardUI:    " + str(bl_info["version"][0]) + '.' + str(bl_info["version"][1]) + '.' + str(bl_info["version"][2]))
        
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
        
        if rig_settings.url_website!='' or rig_settings.url_patreon!='' or rig_settings.url_twitter!='' or rig_settings.url_smutbase!='' or rig_settings.url_reportbug!='':
            
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
            if rig_settings.url_reportbug!='':
                box.operator('mustardui.openlink', text="Report a Bug", icon = "WORLD").url = rig_settings.url_reportbug
        
        box = layout.box()
        box.label(text="UI useful references", icon="INFO")
        box.operator('mustardui.openlink', text="MustardUI - Tutorial", icon = "WORLD").url = rig_settings.url_MustardUItutorial
        box.operator('mustardui.openlink', text="MustardUI - Report Bug", icon = "WORLD").url = rig_settings.url_MustardUI_reportbug
        box.operator('mustardui.openlink', text="MustardUI - GitHub", icon = "WORLD").url = rig_settings.url_MustardUI
        

# Registration of classes
# If you add new classes (or operators), add the class in the list below

# Register

classes = (
    # Operators
    MustardUI_Configuration,
    MustardUI_Configuration_SmartCheck,
    MustardUI_RemoveUI,
    MustardUI_RegisterUIFile,
    MustardUI_ViewportModelSelection,
    MustardUI_SwitchModel,
    MustardUI_Armature_Initialize,
    MustardUI_Armature_Sort,
    MustardUI_Body_CheckAdditionalOptions,
    MustardUI_Outfits_CheckAdditionalOptions,
    MustardUI_DazMorphs_CheckMorphs,
    MustardUI_DazMorphs_DefaultValues,
    MustardUI_DazMorphs_DisableDrivers,
    MustardUI_DazMorphs_EnableDrivers,
    MustardUI_OutfitVisibility,
    MustardUI_GlobalOutfitPropSwitch,
    MustardUI_LinkButton,
    # Outfit add/remove operators
    MustardUI_AddOutfit,
    MustardUI_RemoveOutfit,
    # Tools
    MustardUI_Tools_LatticeSetup,
    MustardUI_Tools_LatticeModify,
    MustardUI_Tools_ChildOf,
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
    PANEL_PT_MustardUI_Armature,
    PANEL_PT_MustardUI_Tools_Physics,
    PANEL_PT_MustardUI_Tools_Lattice,
    PANEL_PT_MustardUI_Tools,
    PANEL_PT_MustardUI_Tools_ChildOf,
    PANEL_PT_MustardUI_Tools_LipsShrinkwrap,
    PANEL_PT_MustardUI_SettingsPanel,
    PANEL_PT_MustardUI_Links
)

def register():
    
    bpy.types.Armature.MustardUI_script_file = PointerProperty(type=bpy.types.Text)
    
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    
    bpy.types.OUTLINER_MT_collection.append(mustardui_collection_menu)

def unregister():
    
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    
    bpy.types.OUTLINER_MT_collection.remove(mustardui_collection_menu)

if __name__ == "__main__":
    register()