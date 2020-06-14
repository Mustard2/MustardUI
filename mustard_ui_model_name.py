# MustardUI script
# Refer to the documentation to implement this to other models
# https://github.com/Mustard2/MustardUI/wiki

import bpy
import addon_utils
import sys
import os
import re
import time
from bpy.props import *
from mathutils import Vector, Color
import webbrowser

# ------------------------------------------------------------------------
#    Initialization Definitions (can be tweaked)
# ------------------------------------------------------------------------

# MAIN MODEL DEFINITIONS

# Model version
model_version = ''

# List of outfits to be imported by the UI
OutCollList = ['Outfit 1','Outfit 2']

# List of hair to be imported by the UI
# If there is only one hair_style in the list, the hair selection interface will be hidden by default
HairObjList = ['Hair']


# BODY SETTINGS

# Enable smooth correction modifier switcher for the main body mesh
enable_smoothcorr = True
# Enable subdivision surface modifier switcher for the main body mesh
enable_subdiv = True
# Enable normals Auto Smooth switcher for the main body mesh
enable_norm_autosmooth = True

# Enable subsurface scattering slider
enable_sss = False
# Default subsurface scattering value
default_sss = 0.

# Enable translucency slider
enable_transl = False
# Default translucency value
default_transl = 0.

# Enable wet effect slider
enable_skinwet = False

# Enable tan effect slider
enable_tan = False
# Enable tan lines effect slider
enable_tanlines = False

# Enable blush effect slider
enable_blush = False

# Enable makeup effect slider
enable_makeup = False
# Enable runny makeup switcher (only works if enable_makeup is True)
enable_runny_makeup = False

# Enable scratches effect slider
enable_scratches = False

# Enable dirt effect slider
enable_skindirt = False
# If this is enabled, you can control non-body materials with the dirt slider
enable_dirt = False

# Enable nails color picker
enable_nailscolor = False
# Enable nails color picker
default_nailscolor = (1.,1.,1.,1.)


# OUTFIT SETTINGS

# Enable smooth correction modifier switcher for the outfits
enable_smooth_corr_out = True
# Enable shrinkwrap modifier switcher for the outfits
enable_shrink_out = True
# Enable masks switcher for the outfits
enable_masks_out = True
# Enable normals Auto Smooth switcher for the outfits
enable_norm_autosmooth_out = True
# If this is enabled, you can control non-body materials with the wet slider
enable_wet = False


# PHYSICS

# Enable Physics panel
enable_physics_panel = False
# Global default options (these will be used if single default options are not specified and for the object without any single default option)
physics_default_global = (2.9,1.0,1.0,1.0,0.2,0.2)
# Single default options (leave it [] if you don't want to set them)
physics_default = [("Breasts",2.9,1.0,1.0,1.0,0.2,0.2),("Bottom",1.9,1.0,1.0,1.0,0.2,0.2)]
# Default simulations step value
physics_default_steps = 7
# Default speed multiplier
physics_default_speed = 0.95


# LATTICE

# Enable Body Shape panel
enable_lattice_panel = False


# TOOLS

# Enable Pre-render Checks Tool
enable_prerender_checks = True
# Enable Lips Shrinkwrap Tool
enable_lips_shrinkwrap = True
# Enable ChildOf Tool
enable_childof = True


# LINKS

# List of the links which will be shown in the Link tab
# Leave them to "" if you don't want to show them
url_website = "https://sites.google.com/view/mustardsfm/home-page"
url_patreon = "https://www.patreon.com/mustardsfm"
url_twitter = "https://twitter.com/MustardSFM"
url_smutbase = "https://smutba.se/user/10157/"
url_reportbug = "https://discord.com/channels/538864175561179147/653909183657148416"

# ------------------------------------------------------------------------
#    Internal Definitions (do not change them)
# ------------------------------------------------------------------------

# UI version
UI_version = '0.10.2 - 14/06/2020'

# Initialization variables
OutCollListOptionsIni = [("Nude","Nude","Nude")]
HairObjListOptionsIni = []
PhysicsObjListOptionsIni = []
LatticeKeyListOptionsIni = [("Base","Base","Base shape.\nThe body without modifications.")]

# Valued of the already stored variables
# Vector entries:
#   stored_sss
#   stored_smoothcorr
#   stored_subdiv_ren
#   stored_subdiv_ren_lv
#   stored_subdiv_view
#   stored_subdiv_view_lv

StoredOptions = [0.,0.,0.,0.,0.,0.]

# Other useful links
bpy.types.Armature.url_MustardUI = bpy.props.StringProperty(default = "https://github.com/Mustard2/MustardUI")
bpy.types.Armature.url_MustardUItutorial = bpy.props.StringProperty(default = "https://github.com/Mustard2/MustardUI/wiki/Tutorial")
bpy.types.Armature.url_denoiser = bpy.props.StringProperty(default = "https://sites.google.com/view/mustardsfm/support/faq#h.cwjx3ttjbpxu")

# Names of the modifiers created by the tools
bpy.types.Armature.lips_shrink_constr_name = bpy.props.StringProperty(default = "MustardUI_lips_shrink_constr")
bpy.types.Armature.childof_contr_name = bpy.props.StringProperty(default = 'MustardUI_ChildOf')


# Function to extract the model name from the script file name
def model_name():
    
    s = re.search('mustard_ui_(.*).py', os.path.basename(__file__)).group(1)
    s = s[0].upper() + s[1:]
    
    return s

# ------------------------------------------------------------------------
#    Global model definitions
# ------------------------------------------------------------------------

# TODO: create dedicated class

# Model definitions
bpy.types.Armature.model_version = bpy.props.StringProperty(default = "",
                                                        name="Model version",
                                                        description="")

# Settings definitions
bpy.types.Armature.settings_advanced = bpy.props.BoolProperty(default = False,
                                                        name="Advanced Settings",
                                                        description="Enable advanced features.\nSome additional properties will appear throughout the UI.\nDo not modify them if you are not sure what you are doing")
bpy.types.Armature.settings_experimental = bpy.props.BoolProperty(default = False,
                                                        name="Experimental Settings",
                                                        description="Enable experimental features.\nThese features are labelled as [Exp].\nUse them at your own risk!")
bpy.types.Armature.settings_additional_options = bpy.props.BoolProperty(default = True,
                                                        name="Additional Outfit Options",
                                                        description="Enable additional outfit options, which can be accessed with the cogwheel near the outfit pieces.\nDisabling this will disable the additional settings, but it will not revert the settings to the default ones")
bpy.types.Armature.settings_maintenance = bpy.props.BoolProperty(default = False,
                                                        name="Maintenance Tools",
                                                        description="Enable Maintenance Tools.\nUse them at your risk! Enable and use them only if you know what you are doing")
bpy.types.Armature.settings_debug = bpy.props.BoolProperty(default = False,
                                                        name="Debug mode",
                                                        description="Enable Debug mode.\nThis will write more messages in the console, to help debug errors.\nEnable it only if needed, because it can decrease the performance")

bpy.types.Armature.enable_smoothcorr = bpy.props.BoolProperty(default = False)
bpy.types.Armature.enable_subdiv = bpy.props.BoolProperty(default = False)
bpy.types.Armature.enable_norm_autosmooth = bpy.props.BoolProperty(default = False)
bpy.types.Armature.enable_sss = bpy.props.BoolProperty(default = False)
bpy.types.Armature.enable_transl = bpy.props.BoolProperty(default = False)
bpy.types.Armature.enable_skinwet = bpy.props.BoolProperty(default = False)
bpy.types.Armature.enable_tan = bpy.props.BoolProperty(default = False)
bpy.types.Armature.enable_tanlines = bpy.props.BoolProperty(default = False)
bpy.types.Armature.enable_blush = bpy.props.BoolProperty(default = False)
bpy.types.Armature.enable_makeup = bpy.props.BoolProperty(default = False)
bpy.types.Armature.enable_runny_makeup = bpy.props.BoolProperty(default = False)
bpy.types.Armature.enable_scratches = bpy.props.BoolProperty(default = False)
bpy.types.Armature.enable_skindirt = bpy.props.BoolProperty(default = False)
bpy.types.Armature.enable_dirt = bpy.props.BoolProperty(default = False)
bpy.types.Armature.enable_nailscolor = bpy.props.BoolProperty(default = False)

bpy.types.Armature.enable_smooth_corr_out = bpy.props.BoolProperty(default = False)
bpy.types.Armature.enable_shrink_out = bpy.props.BoolProperty(default = False)
bpy.types.Armature.enable_masks_out = bpy.props.BoolProperty(default = False)
bpy.types.Armature.enable_norm_autosmooth_out = bpy.props.BoolProperty(default = False)
bpy.types.Armature.enable_wet = bpy.props.BoolProperty(default = False)

bpy.types.Armature.enable_physics_panel = bpy.props.BoolProperty(default = False)
bpy.types.Armature.enable_lattice_panel = bpy.props.BoolProperty(default = False)

bpy.types.Armature.enable_prerender_checks = bpy.props.BoolProperty(default = False)
bpy.types.Armature.enable_lips_shrinkwrap = bpy.props.BoolProperty(default = False)
bpy.types.Armature.enable_childof = bpy.props.BoolProperty(default = False)

bpy.types.Armature.settings_UI_version = bpy.props.StringProperty(default = "",
                                                        name="UI version",
                                                        description="")
bpy.types.Armature.url_website = bpy.props.StringProperty(default="")
bpy.types.Armature.url_patreon = bpy.props.StringProperty(default="")
bpy.types.Armature.url_twitter = bpy.props.StringProperty(default="")
bpy.types.Armature.url_smutbase = bpy.props.StringProperty(default="")
bpy.types.Armature.url_reportbug = bpy.props.StringProperty(default="")

# Rig-tools addon status definition
bpy.types.Armature.status_rig_tools = bpy.props.IntProperty(default = 0,
                                                        name="rig_tools addon status",
                                                        description="")
bpy.types.Armature.enable_sss = bpy.props.BoolProperty(default = False,
                                                        name="Model SSS switcher",
                                                        description="")
bpy.types.Armature.enable_transl = bpy.props.BoolProperty(default = False,
                                                        name="Model Translucency switcher",
                                                        description="")
bpy.types.Armature.enable_subdiv = bpy.props.BoolProperty(default = False,
                                                        name="Model Subdivision switcher",
                                                        description="")
bpy.types.Armature.enable_smoothcorr = bpy.props.BoolProperty(default = False,
                                                        name="Model Smooth Correction switcher",
                                                        description="")
bpy.types.Armature.enable_norm_autosmooth = bpy.props.BoolProperty(default = False,
                                                        name="Model Normals Auto Smooth switcher",
                                                        description="")

# These definitions are necessary for the first time run of UI on a model
bpy.types.Object.outfit = bpy.props.BoolProperty(default = True,
                                                        name="",
                                                        description="")
bpy.types.Object.outfit_lock = bpy.props.BoolProperty(default = False,
                                                        name="",
                                                        description="Lock/unlock the outfit")
bpy.types.Armature.out_sel_ID = bpy.props.IntProperty(default = 0,
                                                        name="",
                                                        description="")

# Custom string vector CollectionProperty and definitions

# Custom string property group for collection
class VectorStringItem(bpy.types.PropertyGroup):
    string_item : bpy.props.StringProperty(name="String")
bpy.utils.register_class(VectorStringItem)

# Function to remove a specific element from the collection
def remove_collection_item(collection, item):
    i=-1
    for el in collection:
        i=i+1
        if el.string_item==item:
            break
    collection.remove(i)

# Function to add a specific element to the collection, if not already there
def add_collection_item(collection, item):
    i=True
    for el in collection:
        if el.string_item==item:
            i=False
            break
    if i:
        add_item = collection.add()
        add_item.string_item = item

# Function to check the presence of a specific element to the collection
def check_collection_item(collection, item):
    i=False
    for el in collection:
        if el.string_item==item:
            i=True
            break
    return i

# Function to find the value of the i-th element to the collection
def extract_collection_item(collection, i):
    j=0
    res=""
    for el in collection:
        if j==i:
            res=el.string_item
            break
        j=j+1
    
    return res

# Function to check the presence of a specific element to the collection
def len_collection(collection):
    i=0
    for el in collection:
        i=i+1
    return i

def print_collection(collection):
    
    for el in collection:
        print(el.string_item)

bpy.types.Armature.mask_list = bpy.props.CollectionProperty(type=VectorStringItem)
bpy.data.armatures[model_name()+'_rig'].mask_list.clear()
bpy.types.Armature.lock_coll_list = bpy.props.CollectionProperty(type=VectorStringItem)
bpy.types.Armature.mat_text_sel = bpy.props.CollectionProperty(type=VectorStringItem)
bpy.data.armatures[model_name()+'_rig'].mat_text_sel.clear()
bpy.types.Armature.phys_obj_disabled = bpy.props.CollectionProperty(type=VectorStringItem)

#  Update function for additional options
def additional_options_update(self, context):
    
    obj = self.option_object
    
    if obj != None:
        
        if self.option_type == 0 or self.option_type == 1:
        
            for mat in obj.data.materials:
                for j in range(len(mat.node_tree.nodes)):
                    if mat.node_tree.nodes[j].name == "MustardUI Float - "+self.option_name and mat.node_tree.nodes[j].type=="VALUE":
                        mat.node_tree.nodes["MustardUI Float - "+self.option_name].outputs[0].default_value = self.option_value
                    elif mat.node_tree.nodes[j].name == "MustardUI Bool - "+self.option_name and mat.node_tree.nodes[j].type=="VALUE":
                        mat.node_tree.nodes["MustardUI Bool - "+self.option_name].outputs[0].default_value = self.option_value_bool
        
        else:
            
            for shape_key in obj.data.shape_keys.key_blocks:
                if shape_key.name == "MustardUI Float - "+self.option_name:
                    shape_key.value = self.option_value
                elif shape_key.name == "MustardUI Bool - "+self.option_name:
                    shape_key.value = self.option_value_bool
    
    return

# Custom Option property for additional outfit options
class OptionItem(bpy.types.PropertyGroup):
    option_name : bpy.props.StringProperty(name="Option name")
    option_value : bpy.props.FloatProperty(name="Option value",
                                            min=0.,max=1.,
                                            update=additional_options_update,
                                            description="Value of the property")
    option_value_bool : bpy.props.IntProperty(name="Option value",min=0,max=1,
                                            update=additional_options_update,
                                            description="Value of the property")
    option_object : bpy.props.PointerProperty(name="Option Object", type=bpy.types.Object)
    # Types: 0 - Material Float, 1 - Material Bool, 2 - Shape Key Float, 3 - Shape Key Bool
    option_type : bpy.props.IntProperty(default=0)
bpy.utils.register_class(OptionItem)

bpy.types.Object.additional_options_show = bpy.props.BoolProperty(name="",default=False, description="Show additional options")
bpy.types.Object.additional_options = bpy.props.CollectionProperty(type=OptionItem)

# Function to remove a specific element from the collection
def remove_option_item(collection, item):
    i=-1
    for el in collection:
        i=i+1
        if el.option_name==item:
            break
    collection.remove(i)

# Function to add a specific element to the collection, if not already there
def add_option_item(collection, item):
    i=True
    for el in collection:
        if el.option_name==item[0]:
            i=False
            break
    if i:
        add_item = collection.add()
        add_item.option_name = item[0]
        add_item.option_value = item[1]
        add_item.option_value_bool = item[2]
        add_item.option_object = item[3]
        add_item.option_type = item[4]

# Function to clean the additional options properties
def clean_options():
    for obj in bpy.data.objects:
        obj.additional_options.clear()

# Function to print the options
def print_options():
    for obj in bpy.data.objects:
        for el in obj.additional_options:
            print(el.option_object.name + ": "+el.option_name+" "+str(el.option_value))

# Function to check the presence of a specific element to the collection
def check_option_item(collection, item):
    i=False
    for el in collection:
        if el.option_name==item:
            i=True
            break
    return i

# ------------------------------------------------------------------------
#    Preliminary operations definitions
# ------------------------------------------------------------------------
#
# Here some preliminary operations are defined.
#

def po_check_settings():
    
    arm = bpy.data.armatures[model_name()+'_rig']
    
    arm.enable_subdiv = False
    arm.enable_smoothcorr = False
    arm.enable_sss = False
    arm.enable_transl = False
    
    for modifier in bpy.data.objects[model_name()+' Body'].modifiers:
        if modifier.type == "SUBSURF" and enable_subdiv:
            arm.enable_subdiv = True
        if modifier.type == "CORRECTIVE_SMOOTH" and enable_smoothcorr:
            arm.enable_smoothcorr = True
    
    for mat in bpy.data.objects[model_name()+' Body'].data.materials:
        for node in mat.node_tree.nodes:
            if node.name == 'Subsurface' and node.type=="VALUE" and enable_sss:
                arm.enable_sss = True
            if node.name == 'Translucency' and node.type=="VALUE" and enable_transl:
                arm.enable_transl = True
    
    arm.enable_norm_autosmooth = enable_norm_autosmooth
    
    # TODO: complete checks
    arm.enable_skinwet = enable_skinwet
    arm.enable_tan = enable_tan
    arm.enable_tanlines = enable_tanlines
    arm.enable_blush = enable_blush
    arm.enable_makeup = enable_makeup
    arm.enable_runny_makeup = enable_runny_makeup
    arm.enable_scratches = enable_scratches
    arm.enable_skindirt = enable_skindirt
    arm.enable_dirt = enable_dirt
    arm.enable_nailscolor = enable_nailscolor

    arm.enable_smooth_corr_out = enable_smooth_corr_out
    arm.enable_shrink_out = enable_shrink_out
    arm.enable_masks_out = enable_masks_out
    arm.enable_norm_autosmooth_out = enable_norm_autosmooth_out
    arm.enable_wet = enable_wet
    
    arm.enable_physics_panel = enable_physics_panel
    arm.enable_lattice_panel = enable_lattice_panel
    
    arm.enable_prerender_checks = enable_prerender_checks
    arm.enable_lips_shrinkwrap = enable_lips_shrinkwrap
    arm.enable_childof = enable_childof
    
    arm.model_version = model_version
    arm.settings_UI_version = UI_version
    arm.url_website = url_website
    arm.url_patreon = url_patreon
    arm.url_twitter = url_twitter
    arm.url_smutbase = url_smutbase
    arm.url_reportbug = url_reportbug
    
    return

# This function checks that the rig_tools addon is installed and enabled.
def addon_check():
    addon_name = "auto_rig_pro-master"
    addon_name2 = "rig_tools"
    
    arm = bpy.data.armatures[model_name()+'_rig']
    
    arm.status_rig_tools = 0
    
    addon_utils.modules_refresh()
    
    if addon_name not in addon_utils.addons_fake_modules and addon_name2 not in addon_utils.addons_fake_modules:
        print("MustardUI: %s add-on not installed." % addon_name)
    else:
        default, state = addon_utils.check(addon_name)
        default, state2 = addon_utils.check(addon_name2)
        if (not state and not state2):
            arm.status_rig_tools = 1
            print("MustardUI: %s add-on installed but not enabled." % addon_name )
        else:
            arm.status_rig_tools = 2
            if arm.settings_debug:
                print("MustardUI: %s add-on enabled and running." % addon_name)
    
    return arm.status_rig_tools

# This function checks which hair styles are available.
def po_check_hair():
    
    HairObjListName = [];
    
    enable_debug_mode = bpy.data.armatures[model_name()+'_rig'].settings_debug
    
    for i in range(len(HairObjList)):
        HairObjListName.append(model_name()+' '+HairObjList[i])

    for collection in bpy.data.collections:
        for obj in collection.objects:
            data=(obj.name[len(model_name())+1:]),(obj.name[len(model_name())+1:]),(obj.name[len(model_name())+1:])
            if obj.name in HairObjListName and data not in HairObjListOptionsIni:
                HairObjListOptionsIni.append(data)
    
    if enable_debug_mode:
        print("\n")
        print("MustardUI: Hair found")
        print(HairObjListOptionsIni)

# This function checks if the outfits are available.
# Moreover it checks if more Textures are available with Texture Selectors. If this is the case, it counts how many textures are available.
def po_check_collections():
    
    OutCollListName = [];
    
    arm = bpy.data.armatures[model_name()+'_rig']
    
    enable_debug_mode = arm.settings_debug
    
    for i in range(len(OutCollList)):
        OutCollListName.append(model_name()+' '+OutCollList[i])

    for collection in bpy.data.collections:
        if collection.name in OutCollListName:
            data=(collection.name[len(model_name())+1:]),(collection.name[len(model_name())+1:]),"Outfit "+(collection.name[len(model_name())+1:])
            OutCollListOptionsIni.append(data)
    
    if enable_debug_mode:
        print("\n")
        print("MustardUI: Outfits found")
        print(OutCollListOptionsIni)
    
    for i in range(len(bpy.data.materials)):
        bpy.data.materials[i].use_nodes=True
        for j in range(len(bpy.data.materials[i].node_tree.nodes)):
            if "Main Texture Selector" in bpy.data.materials[i].node_tree.nodes[j].name:
                for n in OutCollListOptionsIni:
                    n=n[0]
                    if n=="Nude":
                        continue
                    if n in bpy.data.materials[i].name[len(model_name())+1:]:
                        add_collection_item(arm.mat_text_sel,n)
                break
    
    if enable_debug_mode:
        print("\n")
        print("MustardUI: Materials with texture selectors found")
        print_collection(arm.mat_text_sel)
    
    for obj in bpy.data.objects:
        for outfit in OutCollListOptionsIni:
            outfit=outfit[0]
            if outfit=="Nude":
                continue
            if model_name() in obj.name and outfit in obj.name:
                coll = obj.users_collection[0].name[len(model_name())+1:]
                if obj.outfit_lock:
                    add_collection_item(arm.lock_coll_list,coll)
                    obj.hide_viewport = False
                    obj.hide_render = False
                    obj.outfit=True
    
    add_collection_item(arm.mask_list, model_name()+' Body')
    for obj in HairObjListOptionsIni:
        obj=obj[0]
        add_collection_item(arm.mask_list, model_name()+' '+obj)
    if enable_debug_mode:
        print("\n")
        print("MustardUI: Objects with masks")
        print_collection(arm.mask_list)

# This function will check for additional options for the outfits
def po_check_additional_options():
    
    clean_options()
    
    arm = bpy.data.armatures[model_name()+'_rig']
    
    enable_debug_mode = arm.settings_debug
    
    OutCollListName = [];
    
    for i in range(len(OutCollList)):
        OutCollListName.append(model_name()+' '+OutCollList[i])
    
    for collection in bpy.data.collections:
        if collection.name in OutCollListName or collection.name == model_name()+" Extras":
            for obj in collection.objects:
                if obj.type == "MESH":
                    for mat in obj.data.materials:
                        for j in range(len(mat.node_tree.nodes)):
                            if "MustardUI Float" in mat.node_tree.nodes[j].name and mat.node_tree.nodes[j].type=="VALUE":
                                add_option_item(obj.additional_options, [mat.node_tree.nodes[j].name[len("MustardUI Float - "):],mat.node_tree.nodes[j].outputs[0].default_value, False, obj, 0])
                            elif "MustardUI Bool" in mat.node_tree.nodes[j].name and mat.node_tree.nodes[j].type=="VALUE":
                                add_option_item(obj.additional_options, [mat.node_tree.nodes[j].name[len("MustardUI Bool - "):],0., int(mat.node_tree.nodes[j].outputs[0].default_value), obj, 1])
                    if obj.data.shape_keys != None:
                        for shape_key in obj.data.shape_keys.key_blocks:
                            if "MustardUI Float" in shape_key.name:
                                add_option_item(obj.additional_options, [shape_key.name[len("MustardUI Float - "):], shape_key.value, False, obj, 2])
                            elif "MustardUI Bool" in shape_key.name:
                                add_option_item(obj.additional_options, [shape_key.name[len("MustardUI Bool - "):], 0., int(shape_key.value), obj, 3])
                            
    if enable_debug_mode:
        print("\n")
        print("MustardUI: Additional options found")
        print_options()

# This function check the already available options and use them as the initial values for the variables
def po_check_current_options():
    
    enable_debug_mode = bpy.data.armatures[model_name()+'_rig'].settings_debug
    
    # Stored SSS
    for mat in bpy.data.objects[model_name()+' Body'].data.materials:
        for node in mat.node_tree.nodes:
            if node.name == 'Subsurface':
                StoredOptions[0] = node.outputs[0].default_value
                break
    
    for modifier in bpy.data.objects[model_name()+' Body'].modifiers:
        if modifier.type == "CORRECTIVE_SMOOTH":
            StoredOptions[1] = modifier.show_render
            break
    
    for modifier in bpy.data.objects[model_name()+' Body'].modifiers:
        if modifier.type == "SUBSURF":
            StoredOptions[2] = modifier.show_render
            StoredOptions[3] = modifier.render_levels
            StoredOptions[4] = modifier.show_viewport
            StoredOptions[5] = modifier.levels
            break
    
    if enable_debug_mode:
        print("\n")
        print("MustardUI: Stored informations found")
        print(StoredOptions)

def po_check_physics():
    
    enable_debug_mode = bpy.data.armatures[model_name()+'_rig'].settings_debug
    
    for object in bpy.data.collections[model_name()+' Physics'].objects:
        for modifier in object.modifiers:
            if modifier.type == 'CLOTH' and "MustardUI" in modifier.name:
                name=object.name[len(model_name()+' Physics - '):]
                data=(name),(name),(name)
                PhysicsObjListOptionsIni.append(data)
    
    if enable_debug_mode:
        print("\n")
        print("MustardUI: Physics-ready objects found")
        print(PhysicsObjListOptionsIni)
    
    return

def po_check_lattice():
    
    enable_debug_mode = bpy.data.armatures[model_name()+'_rig'].settings_debug
    
    latt = bpy.data.objects[model_name() + " Body - Lattice"]
    
    for key in latt.data.shape_keys.key_blocks:
        if "MustardUI" in key.name:
            name=key.name[len("MustardUI - "):]
            data=(name),(name),(name)
            LatticeKeyListOptionsIni.append(data)
    
    if enable_debug_mode:
        print("\n")
        print("MustardUI: Lattice shape keys found")
        print(LatticeKeyListOptionsIni)
    
    return

# ------------------------------------------------------------------------
#    Preliminary operations run
# ------------------------------------------------------------------------
#
# Here the preliminary operations functions runs
if bpy.data.armatures[model_name()+'_rig'].settings_debug:
    print("\n")
    print("MustardUI: Initializing MustardUI...\n")

po_check_settings()
po_check_hair()
po_check_collections()
po_check_additional_options()
po_check_current_options()

if bpy.data.armatures[model_name()+'_rig'].enable_physics_panel:
    po_check_physics()

if bpy.data.armatures[model_name()+'_rig'].enable_lattice_panel:
    po_check_lattice()

if bpy.data.armatures[model_name()+'_rig'].settings_debug:
    print("\n")

rig_tools_status = addon_check()

# ------------------------------------------------------------------------
#    Various Tools
# ------------------------------------------------------------------------

def ShowMessageBox(message = "", title = "Message Box", icon = 'INFO'):

    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)

# These two functions are needed to extract possible entries of EnumProperty
def enum_members_from_type(rna_type, prop_str):
    prop = rna_type.bl_rna.properties[prop_str]
    return [e.identifier for e in prop.enum_items]
def enum_entries(rna_item, prop_str):
    return enum_members_from_type(type(rna_item), prop_str)

# ------------------------------------------------------------------------
#    Model Properties
# ------------------------------------------------------------------------

def subdiv_rend_update(self, context):
    
    for modifier in bpy.data.objects[model_name()+' Body'].modifiers:
            if modifier.type == "SUBSURF":
                if self.subdiv_rend == True:
                    modifier.show_render = True
                else:
                    modifier.show_render = False
    return

bpy.types.Armature.subdiv_rend = bpy.props.BoolProperty(default = True,
                                                            name="Subdivision Surface (Render)",
                                                            description="Enable/disable the subdivision surface during rendering. \nThis won't affect the viewport or the viewport rendering preview. \nNote that, depending on the complexity of the model, enabling this can greatly affect rendering times",
                                                            update = subdiv_rend_update)
bpy.data.armatures[model_name()+'_rig'].subdiv_rend = StoredOptions[2]

def subdiv_rend_lv_update(self, context):
    
    for modifier in bpy.data.objects[model_name()+' Body'].modifiers:
            if modifier.type == "SUBSURF":
                modifier.render_levels = self.subdiv_rend_lv
    return

bpy.types.Armature.subdiv_rend_lv = bpy.props.IntProperty(default = 1,min=0,max=4,
                                                            name="Level",
                                                            description="Set the subdivision surface level during rendering. \nNote that, depending on the complexity of the model, increasing this can greatly affect rendering times",
                                                            update = subdiv_rend_lv_update)
bpy.data.armatures[model_name()+'_rig'].subdiv_rend_lv = StoredOptions[3]

def subdiv_view_update(self, context):
    
    for modifier in bpy.data.objects[model_name()+' Body'].modifiers:
            if modifier.type == "SUBSURF":
                if self.subdiv_view == True:
                    modifier.show_viewport = True
                else:
                    modifier.show_viewport = False
    return

bpy.types.Armature.subdiv_view = bpy.props.BoolProperty(default = False,
                                                            name="Subdivision Surface (Viewport)",
                                                            description="Enable/disable the subdivision surface in the viewport. \nSince it's really computationally expensive, use this only for previews and do NOT enable it during posing. \nNote that it might require a lot of time to activate, and Blender will freeze during this",
                                                            update = subdiv_view_update)
bpy.data.armatures[model_name()+'_rig'].subdiv_view = StoredOptions[4]

def subdiv_view_lv_update(self, context):
    
    for modifier in bpy.data.objects[model_name()+' Body'].modifiers:
            if modifier.type == "SUBSURF":
                modifier.levels = self.subdiv_view_lv
    return

bpy.types.Armature.subdiv_view_lv = bpy.props.IntProperty(default = 0,min=0,max=4,
                                                            name="Level",
                                                            description="Set the subdivision surface level in viewport. \nNote that, depending on the complexity of the model, increasing this can greatly affect viewport performances. Moreover, each time you change this value with Subdivision Surface (Viewport) enabled, Blender will freeze while applying the modification",
                                                            update = subdiv_view_lv_update)
bpy.data.armatures[model_name()+'_rig'].subdiv_view_lv = StoredOptions[5]

def smooth_corr_update(self, context):
    
    for modifier in bpy.data.objects[model_name()+' Body'].modifiers:
            if modifier.type == "CORRECTIVE_SMOOTH":
                if self.smooth_corr == True:
                    modifier.show_viewport = True
                    modifier.show_render = True
                else:
                    modifier.show_viewport = False
                    modifier.show_render = False
    return

bpy.types.Armature.smooth_corr = bpy.props.BoolProperty(default = True,
                                                            name="Smooth Correction",
                                                            description="Enable/disable the smooth correction. \nDisable it to increase the performance in viewport, and re-enable it before rendering",
                                                            update = smooth_corr_update)
bpy.data.armatures[model_name()+'_rig'].smooth_corr = StoredOptions[1]

def norm_autosmooth_update(self, context):
    
    obj = bpy.data.objects[model_name()+' Body']
    
    if obj.type == "MESH":
    
        if self.norm_autosmooth == True:
            obj.data.use_auto_smooth = True
        else:
            obj.data.use_auto_smooth = False
    
    else:
        
        print("MustardUI: Error in setting normal auto smooth. It seems that "+model_name()+ " Body is not a mesh object.")
    
    return

bpy.types.Armature.norm_autosmooth = bpy.props.BoolProperty(default = True,
                                                            name="Normals Auto Smooth",
                                                            description="Enable/disable the auto-smooth for body normals. \nDisable it to increase the performance in viewport, and re-enable it before rendering",
                                                            update = norm_autosmooth_update)

def sss_update(self, context):
    
    for mat in bpy.data.objects[model_name()+' Body'].data.materials:
        for node in mat.node_tree.nodes:
            if node.name=='Subsurface':
                node.outputs[0].default_value = self.sss
    return

bpy.types.Armature.sss = bpy.props.FloatProperty(default = default_sss,
                                                    min = 0.0,
                                                    max = 1.0,
                                                    name = "Subsurface Scattering",
                                                    description = "Set the subsurface scattering intensity.\nThis effect will allow some light rays to go through the body skin. Be sure to set a correct value. If you are not sure, restore to the default value",
                                                    update = sss_update)
bpy.data.armatures[model_name()+'_rig'].sss = StoredOptions[0]

def transluc_update(self, context):
    
    for mat in bpy.data.objects[model_name()+' Body'].data.materials:
        for node in mat.node_tree.nodes:
            if node.name=='Translucency':
                node.outputs[0].default_value = self.transluc
    return

bpy.types.Armature.transluc = bpy.props.FloatProperty(default = default_transl,
                                                            min = 0.0,
                                                            max = 1.0,
                                                            name = "Translucency",
                                                            description = "Set the translucency effect intensity.\nThis effect can help to obtain a better subsurface scattering effect in some light situations. Do not use this unless you know what you are doing",
                                                            update = transluc_update)

def skinwet_update(self, context):
    
    arm = bpy.data.armatures[model_name()+'_rig']
    
    if arm.enable_skinwet and not arm.enable_wet:
        for mat in bpy.data.objects[model_name()+' Body'].data.materials:
            for node in mat.node_tree.nodes:
                if node.name=='Wet':
                    node.outputs[0].default_value = self.skinwet
    elif arm.enable_skinwet and arm.enable_wet:
        for i in range(len(bpy.data.materials)):
            if bpy.data.materials[i].node_tree.nodes:
                for node in bpy.data.materials[i].node_tree.nodes:
                    if node.name=='Wet':
                        node.outputs[0].default_value = self.skinwet
    return

bpy.types.Armature.skinwet = bpy.props.FloatProperty(default = 0.0,
                                                            min = 0.0,
                                                            max = 1.0,
                                                            name = "Wet",
                                                            description = "Set the intensity of the wet effect",
                                                            update = skinwet_update)

def tan_update(self, context):
    
    for mat in bpy.data.objects[model_name()+' Body'].data.materials:
        for node in mat.node_tree.nodes:
                if node.name=='Tan':
                    node.outputs[0].default_value = self.tan
    return

bpy.types.Armature.tan = bpy.props.FloatProperty(default = 0.0,
                                                            min = 0.0,
                                                            max = 1.0,
                                                            name = "Tan",
                                                            description = "Set the intensity of the tan",
                                                            update = tan_update)

def tanlines_update(self, context):
    
    for mat in bpy.data.objects[model_name()+' Body'].data.materials:
        for node in mat.node_tree.nodes:
                if node.name=='Tan Lines':
                    node.outputs[0].default_value = self.tanlines
    return

bpy.types.Armature.tanlines = bpy.props.FloatProperty(default = 0.0,
                                                            min = 0.0,
                                                            max = 1.0,
                                                            name = "Tan Lines",
                                                            description = "Set the intensity of the tan lines",
                                                            update = tanlines_update)
                                                            
def blush_update(self, context):
    
    for mat in bpy.data.objects[model_name()+' Body'].data.materials:
        for node in mat.node_tree.nodes:
            if node.name=='Blush':
                node.outputs[0].default_value = self.blush
            
    return

bpy.types.Armature.blush = bpy.props.FloatProperty(default = 0.0,
                                                            min = 0.0,
                                                            max = 1.0,
                                                            name = "Blush",
                                                            description = "Set the intensity of the blush",
                                                            update = blush_update)

def makeup_update(self, context):
    
    for mat in bpy.data.objects[model_name()+' Body'].data.materials:
        for node in mat.node_tree.nodes:
            if node.name=='Makeup':
                node.outputs[0].default_value = self.makeup
                
    return

bpy.types.Armature.makeup = bpy.props.FloatProperty(default = 0.0,
                                                            min = 0.0,
                                                            max = 1.0,
                                                            name = "Makeup",
                                                            description = "Set the intensity of the makeup",
                                                            update = makeup_update)

def runny_makeup_update(self, context):
    
    for mat in bpy.data.objects[model_name()+' Body'].data.materials:
        for node in mat.node_tree.nodes:
            if node.name=='Runny Makeup':
                if self.runny_makeup==True:
                    node.outputs[0].default_value = 0.0
                else:
                    node.outputs[0].default_value = 1.0
                
    return

bpy.types.Armature.runny_makeup = bpy.props.BoolProperty(default = False,
                                                            name="Runny Makeup",
                                                            description="Enable/disable runny makeup. It works only if makeup intensity is not null",
                                                            update = runny_makeup_update)

def scratches_update(self, context):
    
    for mat in bpy.data.objects[model_name()+' Body'].data.materials:
        for node in mat.node_tree.nodes:
            if node.name=='Scratches':
                node.outputs[0].default_value = self.scratches
                
    return

bpy.types.Armature.scratches = bpy.props.FloatProperty(default = 0.0,
                                                            min = 0.0,
                                                            max = 1.0,
                                                            name = "Scratches",
                                                            description = "Set the intensity of the scratches",
                                                            update = scratches_update)

def skindirt_update(self, context):
    
    arm = bpy.data.armatures[model_name()+'_rig']
    
    if arm.enable_skindirt and not arm.enable_dirt:
        for mat in bpy.data.objects[model_name()+' Body'].data.materials:
            for node in mat.node_tree.nodes:
                if node.name=='Dirt':
                    node.outputs[0].default_value = self.skindirt
    elif arm.enable_skindirt and arm.enable_dirt:
        for i in range(len(bpy.data.materials)):
            if bpy.data.materials[i].node_tree.nodes:
                for node in bpy.data.materials[i].node_tree.nodes:
                    if node.name=='Dirt':
                        node.outputs[0].default_value = self.skindirt
    return

bpy.types.Armature.skindirt = bpy.props.FloatProperty(default = 0.0,
                                                            min = 0.0,
                                                            max = 1.0,
                                                            name = "Dirt",
                                                            description = "Set the intensity of the dirt effects",
                                                            update = skindirt_update)

def nailscolor_update(self, context):
    
    
    
    if self.custom_nails_color:
        
        for mat in bpy.data.materials:
            if "nails" in mat.name or "Nails" in mat.name:
                for node in mat.node_tree.nodes:
                    if node.name=='Nails Default':
                        node.outputs[0].default_value = 0.
                    if node.name=='Nails Color':
                        node.outputs[0].default_value = self.nails_color
    
    else:
        
        for mat in bpy.data.materials:
            if "nails" in mat.name or "Nails" in mat.name:
                for node in mat.node_tree.nodes:
                    if node.name=='Nails Default':
                        node.outputs[0].default_value = 1.
    
    return

bpy.types.Armature.custom_nails_color = bpy.props.BoolProperty(default = False,
                                                            name = "Nail Varnish",
                                                            description="Enable/disable custom color for the nails",
                                                            update=nailscolor_update)

bpy.types.Armature.nails_color = bpy.props.FloatVectorProperty(name = "",
                                                            subtype='COLOR_GAMMA',
                                                            default=default_nailscolor,
                                                            size=4,
                                                            min=0.0,
                                                            max=1.0,
                                                            description="Set the nails color",
                                                            update=nailscolor_update)

# ------------------------------------------------------------------------
#    Outfit Properties
# ------------------------------------------------------------------------

def outfit_text_update(self, context):
    
    arm = bpy.data.armatures[model_name()+'_rig']
    
    for i in range(len(bpy.data.materials)):
        sel_ID = bpy.data.armatures[model_name()+'_rig'].out_sel_ID
        if extract_collection_item(arm.mat_text_sel, sel_ID) in bpy.data.materials[i].name:
            for j in range(len(bpy.data.materials[i].node_tree.nodes)):
                if "Main Texture Selector" in bpy.data.materials[i].node_tree.nodes[j].name:
                    bpy.data.materials[i].node_tree.nodes[j].inputs[9].default_value=self.outfit_text
    return

bpy.types.Armature.outfits = bpy.props.EnumProperty(name="",
                                                        description="Outfit selected",
                                                        items=OutCollListOptionsIni)

def masks_out_update(self, context):
    
    arm = bpy.data.armatures[model_name()+'_rig']
    
    current_outfit = arm.outfits
    enable_masks = arm.masks_out
    
    OutCollListOptions = enum_entries(arm, "outfits")
    OutCollListOptions.remove('Nude')
    
    if self.masks_out:
        
        if current_outfit=='Nude':
            for mask_obj in arm.mask_list:
                mask_obj = mask_obj.string_item
                for modifier in bpy.data.objects[mask_obj].modifiers:
                    for col in OutCollListOptions:
                        for obj in bpy.data.collections[model_name()+' '+col].objects:
                            if modifier.type == "MASK" and col in modifier.name and obj.name in modifier.name and obj.outfit_lock == True and obj.outfit:
                                modifier.show_viewport = True
                                modifier.show_render = True
        
        else:
            for mask_obj in arm.mask_list:
                mask_obj = mask_obj.string_item
                for modifier in bpy.data.objects[mask_obj].modifiers:
                    for obj in bpy.data.objects:
                        if modifier.type == "MASK" and self.outfits in modifier.name and obj.name in modifier.name and obj.hide_viewport==False:
                            modifier.show_viewport = True
                            modifier.show_render = True
                            break
                        elif modifier.type == "MASK" and obj.name in modifier.name and obj.outfit_lock == True and enable_masks == True and obj.outfit:
                            modifier.show_viewport = True
                            modifier.show_render = True
                            break
                        elif modifier.type == "MASK" and obj.name not in modifier.name and self.outfits not in modifier.name:
                            modifier.show_viewport = False
                            modifier.show_render = False
        
    else:
        for mask_obj in arm.mask_list:
            mask_obj = mask_obj.string_item
            for modifier in bpy.data.objects[mask_obj].modifiers:
                if modifier.type == "MASK":
                    modifier.show_viewport = False
                    modifier.show_render = False
    return

bpy.types.Armature.masks_out = bpy.props.BoolProperty(default = True,
                                                            name="Masks",
                                                            description="Enable/disable the body masks. \nDisable it to increase the performance in viewport, and re-enable it before rendering. \nNote: some outfits might experience major clipping with the body if this is disabled. Therefore remember to re-enable it before rendering and for quick previews",
                                                            update = masks_out_update)

def outfits_update(self, context):
    
    arm = bpy.data.armatures[model_name()+'_rig']
    
    enable_masks = arm.masks_out
    
    OutCollListOptions = enum_entries(arm,"outfits")
    OutCollListOptions.remove('Nude')
    
    if self.outfits=='Nude':
        for col in OutCollListOptions:
            if check_collection_item(arm.lock_coll_list,col):
                for obj in bpy.data.collections[model_name()+' '+col].objects:
                    if obj.outfit_lock and obj.outfit:
                        obj.hide_viewport = False
                        obj.hide_render = False
                    else:
                        obj.hide_viewport = True
                        obj.hide_render = True
            else:
                bpy.data.collections[model_name()+' '+col].hide_viewport = True
                bpy.data.collections[model_name()+' '+col].hide_render = True
        
        for mask_obj in arm.mask_list:
            mask_obj = mask_obj.string_item
            for modifier in bpy.data.objects[mask_obj].modifiers:
                if modifier.type == "MASK":
                    modifier.show_viewport = False
                    modifier.show_render = False
            
                for col in OutCollListOptions:
                    for obj in bpy.data.collections[model_name()+' '+col].objects:
                        if modifier.type == "MASK" and col in modifier.name and obj.name in modifier.name and obj.outfit_lock == True and enable_masks == True and obj.outfit:
                            modifier.show_viewport = True
                            modifier.show_render = True
                
    else:
        for col in OutCollListOptions:
            if check_collection_item(arm.lock_coll_list,col) and col!=self.outfits:
                for obj in bpy.data.collections[model_name()+' '+col].objects:
                    if obj.outfit_lock and obj.outfit:
                        obj.hide_viewport = False
                        obj.hide_render = False
                    else:
                        obj.hide_viewport = True
                        obj.hide_render = True
            else:
                bpy.data.collections[model_name()+' '+col].hide_viewport = True
                bpy.data.collections[model_name()+' '+col].hide_render = True
        
        bpy.data.collections[model_name()+' '+self.outfits].hide_viewport = False
        bpy.data.collections[model_name()+' '+self.outfits].hide_render = False
        for obj in bpy.data.collections[model_name()+' '+self.outfits].objects:
            if obj.outfit:
                obj.hide_viewport = False
                obj.hide_render = False
            else:
                obj.hide_viewport = True
                obj.hide_render = True
        for mask_obj in arm.mask_list:
            mask_obj = mask_obj.string_item
            for modifier in bpy.data.objects[mask_obj].modifiers:
                for obj in bpy.data.objects:
                    if modifier.type == "MASK" and self.outfits in modifier.name and obj.name in modifier.name and obj.hide_viewport==False and enable_masks == True:
                        modifier.show_viewport = True
                        modifier.show_render = True
                        break
                    elif modifier.type == "MASK" and obj.name in modifier.name and obj.outfit_lock == True and enable_masks == True and obj.outfit:
                        modifier.show_viewport = True
                        modifier.show_render = True
                        break
                    elif modifier.type == "MASK" and obj.name not in modifier.name and self.outfits not in modifier.name:
                        modifier.show_viewport = False
                        modifier.show_render = False
    
    if len_collection(arm.mat_text_sel)>0:
    
        for i in range(len_collection(arm.mat_text_sel)):
            if extract_collection_item(arm.mat_text_sel, i)==self.outfits:
                bpy.data.armatures[model_name()+'_rig'].out_sel_ID = i
                break

        for mat in bpy.data.materials:
            if model_name() in mat.name and extract_collection_item(arm.mat_text_sel, bpy.data.armatures[model_name()+'_rig'].out_sel_ID) in mat.name:
                for j in range(len(mat.node_tree.nodes)):
                    if "Main Texture Selector" in mat.node_tree.nodes[j].name:
                        for k in range(9):
                            if not mat.node_tree.nodes[j].inputs[k].links:
                                text_count=k
                                break
                break
        
        bpy.types.Armature.outfit_text = bpy.props.IntProperty(default = 1,
                                                            min = 1,
                                                            max = text_count,
                                                            name = "Color",
                                                            description = "Choose the color of the outfit",
                                                            update = outfit_text_update)
    return

bpy.types.Armature.outfits = bpy.props.EnumProperty(name="",
                                                        description="Outfit selected",
                                                        items=OutCollListOptionsIni,
                                                        update = outfits_update)
                                                        
def outfit_show(self, context):
    
    arm = bpy.data.armatures[model_name()+'_rig']
    
    enable_masks = arm.masks_out
    
    if self.outfit:# or self.outfit_lock:
        self.hide_viewport = False
        self.hide_render = False
        for mask_obj in arm.mask_list:
            mask_obj = mask_obj.string_item
            for modifier in bpy.data.objects[mask_obj].modifiers:
                if modifier.type == "MASK" and modifier.name == "Mask "+self.name and enable_masks == True:
                    modifier.show_viewport = True
                    modifier.show_render = True
    else:
        self.hide_viewport = True
        self.hide_render = True
        for mask_obj in arm.mask_list:
            mask_obj = mask_obj.string_item
            for modifier in bpy.data.objects[mask_obj].modifiers:
                if modifier.type == "MASK" and modifier.name == "Mask "+self.name:
                    modifier.show_viewport = False
                    modifier.show_render = False
    
    return

bpy.types.Object.outfit = bpy.props.BoolProperty(default = True,
                                                        name="",
                                                        description="",
                                                        update = outfit_show)

def outfit_lock(self, context):
    
    if model_name() in self.name:
        coll = self.users_collection[0].name[len(model_name())+1:]
    
    arm = bpy.data.armatures[model_name()+'_rig']
    
    if self.outfit_lock:
        add_collection_item(arm.lock_coll_list,coll)
        self.hide_viewport = False
        self.hide_render = False
        self.outfit=True
    elif check_collection_item(arm.lock_coll_list,coll):
        n_lock_obj=0
        for obj in self.users_collection[0].objects:
            print(obj.name)
            if obj.outfit_lock:
                n_lock_obj += 1
        if n_lock_obj == 0:
            remove_collection_item(arm.lock_coll_list,coll)
        if coll != arm.outfits:
            self.hide_viewport = True
            self.hide_render = True
            self.outfit=False
    
    return

bpy.types.Object.outfit_lock = bpy.props.BoolProperty(default = False,
                                                        name="",
                                                        description="Lock/unlock the outfit",
                                                        update = outfit_lock)

def smooth_corr_out_update(self, context):
    
    OutCollListOptions = enum_entries(bpy.data.armatures[model_name()+'_rig'], "outfits")
    OutCollListOptions.remove('Nude')
    
    for col in OutCollListOptions:
        for obj in bpy.data.collections[model_name()+' '+col].objects:
            for modifier in obj.modifiers:
                if modifier.type == "CORRECTIVE_SMOOTH":
                    if self.smooth_corr_out == True:
                        modifier.show_viewport = True
                        modifier.show_render = True
                    else:
                        modifier.show_viewport = False
                        modifier.show_render = False
                        
    return

bpy.types.Armature.smooth_corr_out = bpy.props.BoolProperty(default = True,
                                                            name="Smooth Correction",
                                                            description="Enable/disable the smooth correction for the outfits. \nDisable it to increase the performance in viewport, and re-enable it before rendering",
                                                            update = smooth_corr_out_update)

def shrink_out_update(self, context):
    
    OutCollListOptions = enum_entries(bpy.data.armatures[model_name()+'_rig'], "outfits")
    OutCollListOptions.remove('Nude')
    
    for col in OutCollListOptions:
        for obj in bpy.data.collections[model_name()+' '+col].objects:
            for modifier in obj.modifiers:
                if modifier.type == "SHRINKWRAP":
                    if self.shrink_out == True:
                        modifier.show_viewport = True
                        modifier.show_render = True
                    else:
                        modifier.show_viewport = False
                        modifier.show_render = False
                        
    return

bpy.types.Armature.shrink_out = bpy.props.BoolProperty(default = True,
                                                            name="Shrinkwrap",
                                                            description="Enable/disable the shrinkwrap modifier for the outfits. \nDisable it to increase the performance in viewport, and re-enable it before rendering. \nNote: some outfits might experience clipping with the body if this is disabled",
                                                            update = shrink_out_update)

def norm_autosmooth_out_update(self, context):
    
    OutCollListOptions = enum_entries(bpy.data.armatures[model_name()+'_rig'], "outfits")
    OutCollListOptions.remove('Nude')
    
    for col in OutCollListOptions:
        for obj in bpy.data.collections[model_name()+' '+col].objects:
            if obj.type == "MESH":
                if self.norm_autosmooth_out == True:
                    obj.data.use_auto_smooth = True
                else:
                    obj.data.use_auto_smooth = False
    
    return

bpy.types.Armature.norm_autosmooth_out = bpy.props.BoolProperty(default = True,
                                                            name="Normals Auto Smooth",
                                                            description="Enable/disable the auto-smooth for body normals. \nDisable it to increase the performance in viewport, and re-enable it before rendering",
                                                            update = norm_autosmooth_out_update)

# ------------------------------------------------------------------------
#    Hair Properties
# ------------------------------------------------------------------------

def hair_update(self, context):
    
    HairObjListAvail = enum_entries(bpy.data.armatures[model_name()+'_rig'], "hair")
    
    for ob in HairObjListAvail:
        bpy.data.objects[model_name()+' '+ob].hide_viewport = True
        bpy.data.objects[model_name()+' '+ob].hide_render = True
        bpy.data.objects[model_name()+' '+ob+' Armature'].hide_viewport = True
        bpy.data.objects[model_name()+' '+ob+' Armature'].hide_render = True
    bpy.data.objects[model_name()+' '+self.hair].hide_viewport = False
    bpy.data.objects[model_name()+' '+self.hair].hide_render = False
    bpy.data.objects[model_name()+' '+self.hair+' Armature'].hide_viewport = False
    bpy.data.objects[model_name()+' '+self.hair+' Armature'].hide_render = False
    return

bpy.types.Armature.hair = bpy.props.EnumProperty(name="",
                                                        description="Hair selected",
                                                        items=HairObjListOptionsIni,
                                                        update = hair_update)

# ------------------------------------------------------------------------
#    Rig Properties
# ------------------------------------------------------------------------

def rig_visibility_update(self, context):
    
    armature = bpy.data.objects[model_name()+'_rig'].data
    HairObjListAvail = enum_entries(bpy.data.armatures[model_name()+'_rig'], "hair")
    
    if self.rig_main_std:
        armature.layers[0] = True
    else:
        armature.layers[0] = False
    
    if self.rig_main_adv:
        armature.layers[1] = True
    else:
        armature.layers[1] = False
    
    if self.rig_main_childof:
        armature.layers[10] = True
    else:
        armature.layers[10] = False
    
    if self.rig_main_extra:
        armature.layers[7] = True
    else:
        armature.layers[7] = False
    
    if self.rig_main_rig:
        armature.layers[31] = True
    else:
        armature.layers[31] = False
    
    for hair in HairObjListAvail:
        if self.rig_hair:
            bpy.data.objects[model_name()+' '+self.hair+' Armature'].hide_viewport = False
        else:
            bpy.data.objects[model_name()+' '+self.hair+' Armature'].hide_viewport = True
    
    return

bpy.types.Armature.rig_main_std = bpy.props.BoolProperty(default = True,
                                                            name="Standard",
                                                            description="Show/hide default body bones",
                                                            update = rig_visibility_update)
bpy.types.Armature.rig_main_adv = bpy.props.BoolProperty(default = False,
                                                            name="Advanced",
                                                            description="Show/hide advanced body bones.\nEnable this to show more armature bones. Most of them can help to correct difficult poses",
                                                            update = rig_visibility_update)
bpy.types.Armature.rig_main_childof = bpy.props.BoolProperty(default = False,
                                                            name="Parent-ready",
                                                            description="Show/hide \'parent-ready' bones.\nEnable this to show the bones that should be used as targets of Child Of modifiers",
                                                            update = rig_visibility_update)
bpy.types.Armature.rig_main_extra = bpy.props.BoolProperty(default = True,
                                                            name="Extra",
                                                            description="Show/hide extra body bones.\nEnable this to show, if any, genitals controllers, etc..",
                                                            update = rig_visibility_update)
bpy.types.Armature.rig_main_rig = bpy.props.BoolProperty(default = False,
                                                            name="Rig",
                                                            description="Show/hide extra rig bones.\nEnable this if you wish to weight paint the body and/or the outfits",
                                                            update = rig_visibility_update)
bpy.types.Armature.rig_hair = bpy.props.BoolProperty(default = True,
                                                            name="Hair",
                                                            description="Show/hide the hair armature",
                                                            update = rig_visibility_update)

# ------------------------------------------------------------------------
#    Physics
# ------------------------------------------------------------------------

@classmethod
def physics_panel_poll(cls, context):
    arm = bpy.data.armatures[model_name()+'_rig']
    return arm.enable_physics_panel

def physics_obj_update(self, context):
    
    modifier = bpy.data.objects[model_name()+' Physics - '+self.phy_objects].modifiers["MustardUI "+self.phy_objects+" Physics"]
    
    temp = [modifier.settings.tension_stiffness,modifier.settings.shear_stiffness,modifier.settings.bending_stiffness,
            modifier.settings.tension_damping,modifier.settings.shear_damping,modifier.settings.bending_damping,
            modifier.collision_settings.use_collision,modifier.collision_settings.distance_min,modifier.collision_settings.impulse_clamp]
    
    bpy.types.Armature.phy_stiff_struct = bpy.props.FloatProperty(default = physics_default_global[0], min = 0.0, name = "", description = "Set the structural stiffness value", update = physics_update)
    bpy.types.Armature.phy_stiff_shear = bpy.props.FloatProperty(default = physics_default_global[1], min = 0.0, name = "", description = "Set the shear stiffness value", update = physics_update)
    bpy.types.Armature.phy_stiff_bend = bpy.props.FloatProperty(default = physics_default_global[2], min = 0.0, name = "", description = "Set the bending stiffness value", update = physics_update)

    bpy.types.Armature.phy_damp_struct = bpy.props.FloatProperty(default = physics_default_global[3], min = 0.0, name = "", description = "Set the structural damping value", update = physics_update)
    bpy.types.Armature.phy_damp_shear = bpy.props.FloatProperty(default = physics_default_global[4], min = 0.0, name = "", description = "Set the shear damping value", update = physics_update)
    bpy.types.Armature.phy_damp_bend = bpy.props.FloatProperty(default = physics_default_global[5], min = 0.0, name = "", description = "Set the bending damping value", update = physics_update)
    
    for item in physics_default:
        if item[0] == self.phy_objects:
            bpy.types.Armature.phy_stiff_struct = bpy.props.FloatProperty(default = item[1], min = 0.0, name = "", description = "Set the structural stiffness value", update = physics_update)
            bpy.types.Armature.phy_stiff_shear = bpy.props.FloatProperty(default = item[2], min = 0.0, name = "", description = "Set the shear stiffness value", update = physics_update)
            bpy.types.Armature.phy_stiff_bend = bpy.props.FloatProperty(default = item[3], min = 0.0, name = "", description = "Set the bending stiffness value", update = physics_update)

            bpy.types.Armature.phy_damp_struct = bpy.props.FloatProperty(default = item[4], min = 0.0, name = "", description = "Set the structural damping value", update = physics_update)
            bpy.types.Armature.phy_damp_shear = bpy.props.FloatProperty(default = item[5], min = 0.0, name = "", description = "Set the shear damping value", update = physics_update)
            bpy.types.Armature.phy_damp_bend = bpy.props.FloatProperty(default = item[6], min = 0.0, name = "", description = "Set the bending damping value", update = physics_update)
            break
    
    self.phy_single_enable = modifier.show_render
    
    self.phy_stiff_struct = temp[0]
    self.phy_stiff_shear = temp[1]
    self.phy_stiff_bend = temp[2]
    
    self.phy_damp_struct = temp[3]
    self.phy_damp_shear = temp[4]
    self.phy_damp_bend = temp[5]
    
    self.phy_collisions = temp[6]
    self.phy_collisions_distance = temp[7]
    self.phy_collisions_clamping = temp[8]
    
    return

bpy.types.Armature.phy_objects = bpy.props.EnumProperty(name="",
                                                        description="Object selected",
                                                        items=PhysicsObjListOptionsIni,
                                                        update=physics_obj_update)

def physics_enable_update(self, context):
    
    arm = bpy.data.armatures[model_name()+'_rig']
    
    for object in bpy.data.collections[model_name()+' Physics'].objects:
        for modifier in object.modifiers:
            if modifier.type == 'CLOTH' and "MustardUI" in modifier.name:
                if self.phy_enable and not check_collection_item(arm.phys_obj_disabled, modifier.name[len("MustardUI "):-len(" Physics")]):
                    modifier.show_viewport = True
                    modifier.show_render = True
                else:
                    modifier.show_viewport = False
                    modifier.show_render = False
    
    for modifier in bpy.data.objects[model_name()+" Body"].modifiers:
        if modifier.type == 'MESH_DEFORM' and "Physics" in modifier.name:
            if self.phy_enable:
                modifier.show_viewport = True
                modifier.show_render = True
            else:
                modifier.show_viewport = False
                modifier.show_render = False
       
    return

def physics_update(self, context):
    
    arm = bpy.data.armatures[model_name()+'_rig']
    
    for object in bpy.data.collections[model_name()+' Physics'].objects:
        for modifier in object.modifiers:
            if modifier.type == 'CLOTH' and "MustardUI" in modifier.name:
                
                modifier.point_cache.frame_start = self.phy_start_frame
                modifier.point_cache.frame_end = self.phy_end_frame
                modifier.settings.quality = self.phy_steps
                modifier.settings.time_scale = self.phy_speed
                modifier.collision_settings.collision_quality = self.phy_collisions_steps
                
                if self.phy_objects in modifier.name:
                    
                    modifier.collision_settings.use_collision = self.phy_collisions
                    
                    modifier.collision_settings.distance_min = self.phy_collisions_distance
                    modifier.collision_settings.impulse_clamp = self.phy_collisions_clamping
                
                    modifier.settings.tension_stiffness = self.phy_stiff_struct
                    modifier.settings.shear_stiffness = self.phy_stiff_shear
                    modifier.settings.bending_stiffness = self.phy_stiff_bend
    
                    modifier.settings.tension_damping = self.phy_damp_struct
                    modifier.settings.shear_damping = self.phy_damp_shear
                    modifier.settings.bending_damping = self.phy_damp_bend
                
                    if self.phy_single_enable:
                        modifier.show_viewport = True
                        modifier.show_render = True
                        if check_collection_item(arm.phys_obj_disabled, self.phy_objects):
                            remove_collection_item(arm.phys_obj_disabled,self.phy_objects)
                    else:
                        modifier.show_viewport = False
                        modifier.show_render = False
                        if not check_collection_item(arm.phys_obj_disabled, self.phy_objects):
                            add_collection_item(arm.phys_obj_disabled,self.phy_objects)
    
    return

class PhyBake(bpy.types.Operator):
    """Bake physics.\nWith this function you are saving the behaviour of the physics-ready objects.\nYou should redo this if you change the animation.\nNote that Blender will freeze will the simulation is performed. The time will depend on the quality, the number of frames and the number of objects"""
    bl_idname = "ops.phy_bake"
    bl_label = "Bake Physics"
    bl_options = {'REGISTER'}
    
    bake: BoolProperty(name='BAKE',
        description="Bake",
        default=True
    )

    def execute(self, context):
        
        i = 0
        
        for object in bpy.data.collections[model_name()+' Physics'].objects:
            for modifier in object.modifiers:
                if modifier.type == 'CLOTH' and "MustardUI" in modifier.name:
                    if modifier.show_render == True:
                        i = i + 1
                    
        if i>0:
            
            for object in bpy.data.collections[model_name()+' Physics'].objects:
                for modifier in object.modifiers:
                    if modifier.type == 'CLOTH' and "MustardUI" in modifier.name:
                    
                        override = {'scene': context.scene, 'active_object': object, 'point_cache': modifier.point_cache}
                    
                        if self.bake == True:
                            t0 = time.perf_counter()
                            bpy.ops.ptcache.bake(override, bake=True)
                            bpy.data.armatures[model_name()+'_rig'].phy_bake = True
                            t1 = time.perf_counter()
                            time_string = "%.2f" % float(t1-t0)
                            self.report({'INFO'}, 'Physics bake completed in ' + time_string + ' s.')
                        else:
                            bpy.ops.ptcache.free_bake(override)
                            bpy.data.armatures[model_name()+'_rig'].phy_bake = False
                            self.report({'INFO'}, 'MustardUI Physics Bake deleted.')
        
        else:
            self.report({'WARNING'}, 'Nothing to bake. Enable the Physics for at least one Object')
            
        
        return {'FINISHED'}

class PhyMeshCollision(bpy.types.Operator):
    """Add Collision to the selected object."""
    bl_idname = "ops.phy_mesh_collision"
    bl_label = "Add Collision"
    bl_options = {'REGISTER'}
    
    clean: BoolProperty(name='CLEAN',
        description="Delete collision",
        default=False
    )

    def execute(self, context):
        
        obj_list = bpy.context.selected_objects
        armature = bpy.data.armatures[model_name()+'_rig']
        
        if len(obj_list)>0:
            
            obj=obj_list[0]
        
            if obj.type == "MESH":
                
                if obj.name == model_name()+" Body":
                    
                    self.report({'WARNING'}, 'Body collisions are not supported at the moment')
                
                else:
                    
                    if self.clean == False:
                        mod_presence=False
                        for mod in obj.modifiers:
                            if mod.type=="COLLISION" and mod.name != 'MustardUI Collision':
                                mod_presence=True
                                self.report({'WARNING'}, 'A non-MustardUI collision modifier has been found. No modifier has been added')
                                break
                        obj.modifiers.new(type='COLLISION', name='MustardUI Collision')
                        obj.collision.damping = armature.phy_collisions_mesh_damp
                        obj.collision.thickness_outer = armature.phy_collisions_mesh_thick
                        obj.collision.cloth_friction = armature.phy_collisions_mesh_friction
                    else:
                        to_remove = obj.modifiers['MustardUI Collision']
                        obj.modifiers.remove(to_remove)
            else:
                self.report({'WARNING'}, 'Can not add collision to this Object. Select only one Mesh')
        
        else:
            self.report({'WARNING'}, 'Can not add collision to this Object. Select only one Mesh')
            
        
        return {'FINISHED'}

bpy.types.Armature.phy_enable = bpy.props.BoolProperty(default = False,
                                                        name="Enable Physics",
                                                        description="Enable/disable physics simulation.\nThis can greatly affect the performance in viewport, therefore enable it only for renderings or checks.\nNote that the baked physics will be deleted if you disable physics",
                                                        update = physics_enable_update)

bpy.types.Armature.phy_steps = bpy.props.IntProperty(default = physics_default_steps, min = 1, max = 80,
                                                        name="Simulation steps",
                                                        description="Set the steps per frame of the physics simulation.\nNote that higher will give better quality, but it will take longer to perform the bake",
                                                        update = physics_update)
bpy.types.Armature.phy_speed = bpy.props.FloatProperty(default = physics_default_speed,
                                                        min = 0.0, max = 10.0,
                                                        name = "Speed multiplier",
                                                        description = "Set the simulation speed.\nAll the simulation velocities will be multiplied by this value, effectively slowing (<1 values) or speeding up (>1 values) the whole simulation.\nConsider to change this value accordingly to the FPS of your animation",
                                                        update = physics_update)
bpy.types.Armature.phy_bake = bpy.props.BoolProperty(default = False,
                                                            name="Bake Physics",
                                                            description="Bake physics.\nWith this function you are saving the behaviour of the physics-ready objects.\nYou should redo this if you change the animation.\nNote that Blender will freeze will the simulation is performed. The time will depend on the quality, the number of frames and the number of objects",
                                                            update = physics_update)
bpy.types.Armature.phy_start_frame = bpy.props.IntProperty(default = 1,
                                                            name="Start",
                                                            description="Set the starting simulation frame",
                                                            update = physics_update)
bpy.types.Armature.phy_end_frame = bpy.props.IntProperty(default = 250,
                                                            name="End",
                                                            description="Set the ending simulation frame",
                                                            update = physics_update)

bpy.types.Armature.phy_stiff_struct = bpy.props.FloatProperty(default = physics_default_global[0], min = 0.0, name = "", description = "Set the structural stiffness value", update = physics_update)
bpy.types.Armature.phy_stiff_shear = bpy.props.FloatProperty(default = physics_default_global[1], min = 0.0, name = "", description = "Set the shear stiffness value", update = physics_update)
bpy.types.Armature.phy_stiff_bend = bpy.props.FloatProperty(default = physics_default_global[2], min = 0.0, name = "", description = "Set the bending stiffness value", update = physics_update)

bpy.types.Armature.phy_damp_struct = bpy.props.FloatProperty(default = physics_default_global[3], min = 0.0, name = "", description = "Set the structural damping value", update = physics_update)
bpy.types.Armature.phy_damp_shear = bpy.props.FloatProperty(default = physics_default_global[4], min = 0.0, name = "", description = "Set the shear damping value", update = physics_update)
bpy.types.Armature.phy_damp_bend = bpy.props.FloatProperty(default = physics_default_global[5], min = 0.0, name = "", description = "Set the bending damping value", update = physics_update)

bpy.types.Armature.phy_collisions = bpy.props.BoolProperty(default = False,
                                                        name="Enable this Object Collisions",
                                                        description="Enable/disable collisions for this Object.\nThis can greatly affect the performance in viewport and bake times.\nFor this work, you need to add collisions to the colliding objects.\nNote that enabling/disabling this, you have to re-bake the physics",
                                                        update = physics_update)
                                                        
bpy.types.Armature.phy_collisions_distance = bpy.props.FloatProperty(default = 0.001,
                                                        min=0.001,max=1.,
                                                        name="Collision distance",
                                                        description="Set the value of collision distance.\nMinimum distance bewteen the objects before the collision effect is computed",
                                                        update = physics_update)
bpy.types.Armature.phy_collisions_clamping = bpy.props.FloatProperty(default = 0.,
                                                        min=0.,max=100.,
                                                        name="Impulse clamping",
                                                        description="Set the value of the collision impulse clamping.\nIncrease this value to clamp collision impulses to avoid instabilities (0 to disable clamping)",
                                                        update = physics_update)
bpy.types.Armature.phy_collisions_steps = bpy.props.IntProperty(default = 5,
                                                            name="Collision Simulation steps",
                                                            description="Set the number of steps.\nThis option is enabled only if collisions are enabled for at least one object.\nNote that higher values means a more precise collision result, but also an increased bake time",
                                                            update = physics_update)

bpy.types.Armature.phy_collisions_mesh_thick = bpy.props.FloatProperty(default = 0.001,
                                                        min=0.001,max=1.,
                                                        name="Thickness Outer",
                                                        description="Set the value of outer face thickness.\nSet higher values to increase the distance from which the collision will start")
bpy.types.Armature.phy_collisions_mesh_damp = bpy.props.FloatProperty(default = 0.1,
                                                        min=0.,max=1.,
                                                        name="Damping",
                                                        description="Set the value of damping during collision")
bpy.types.Armature.phy_collisions_mesh_friction = bpy.props.FloatProperty(default = 5.,
                                                        min=0.,max=80.,
                                                        name="Friction",
                                                        description="Set the value of mesh friction")

bpy.types.Armature.phy_single_enable = bpy.props.BoolProperty(default = True,
                                                        name="Enable this Object Physics",
                                                        description="Enable/disable physics simulation for the single object. The other Objects will not be affected.\nNote that the baked physics WILL be deleted if you disable physics, only the modifiers will be disabled",
                                                        update = physics_update)

# ------------------------------------------------------------------------
#    Tools - Enable check
# ------------------------------------------------------------------------

@classmethod
def tools_poll(cls, context):
    arm = bpy.data.armatures[model_name()+'_rig']
    if arm.enable_prerender_checks or arm.enable_childof or arm.enable_lips_shrinkwrap:
        return True
    else:
        return False

# ------------------------------------------------------------------------
#    Tools - Lips Shrinkwrap
# ------------------------------------------------------------------------

@classmethod
def lips_shrinkwrap_poll(cls, context):
    arm = bpy.data.armatures[model_name()+'_rig']
    return arm.enable_lips_shrinkwrap

bones_lips = ['c_lips_smile.r','c_lips_top.r','c_lips_top_01.r','c_lips_top.x','c_lips_top.l','c_lips_top_01.l','c_lips_smile.l','c_lips_bot.r','c_lips_bot_01.r','c_lips_bot.x','c_lips_bot.l','c_lips_bot_01.l']
shrink_message="You must select any model armature bone ("+model_name()+"_rig), in Pose mode, to apply the friction."

def lips_shrinkwrap_update(self, context):
    
    armature = bpy.data.objects[model_name()+'_rig']
    arm = bpy.data.armatures[model_name()+'_rig']
    
    autorig_check = False
    for bone in armature.pose.bones:
        if bone.name == bones_lips[1]:
            autorig_check = True
            break
    
    if not autorig_check:
        ShowMessageBox("The armature is not an autorig one. Other armatures are not supported at the moment", "MustardUI Information")
        return
    
    ob = bpy.context.active_object
    
    if self.lips_shrinkwrap == True and self.lips_shrinkwrap_obj:
        
        for bone in bones_lips:
            
            constr_check = False
            
            if not (0 < len([m for m in armature.pose.bones[bone].constraints if m.type == "SHRINKWRAP"])):
                constr = armature.pose.bones[bone].constraints.new('SHRINKWRAP')
                constr.name = arm.lips_shrink_constr_name
                constr_check = True
            
            elif not constr_check:
                for c in armature.pose.bones[bone].constraints:
                    if c.name == arm.lips_shrink_constr_name:
                        constr_check = True
                        break
            
            if not constr_check:
                constr = armature.pose.bones[bone].constraints.new('SHRINKWRAP')
                constr.name = arm.lips_shrink_constr_name
            
            constr = armature.pose.bones[bone].constraints[arm.lips_shrink_constr_name]
            constr.target = self.lips_shrinkwrap_obj
            
            constr.wrap_mode = "OUTSIDE"
            constr.distance = self.lips_shrinkwrap_dist
            
            if bone == 'c_lips_smile.r' or bone == 'c_lips_smile.l':
                constr.distance = constr.distance * self.lips_shrinkwrap_dist_corr
        
        if self.lips_shrinkwrap_friction == True and ob == armature:
        
            for bone in bones_lips:
            
                constr_check = False
            
                if not (0 < len([m for m in armature.pose.bones[bone].constraints if m.type == "CHILD_OF"])):
                    constr = armature.pose.bones[bone].constraints.new('CHILD_OF')
                    constr.name = arm.lips_shrink_constr_name+'_fric'
                    constr_check = True
            
                elif not constr_check:
                    for c in armature.pose.bones[bone].constraints:
                        if c.name == arm.lips_shrink_constr_name+'_fric':
                            constr_check = True
                            break
            
                if not constr_check:
                    constr = armature.pose.bones[bone].constraints.new('CHILD_OF')
                    constr.name = arm.lips_shrink_constr_name+'_fric'
            
                constr = armature.pose.bones[bone].constraints[arm.lips_shrink_constr_name+'_fric']
                if self.lips_shrinkwrap_obj_fric:
                    constr.target = self.lips_shrinkwrap_obj_fric
                else:
                    constr.target = self.lips_shrinkwrap_obj
                constr.subtarget = self.lips_shrinkwrap_obj_fric_sec
                constr.use_scale_x = False
                constr.use_scale_y = False
                constr.use_scale_z = False
            
                context_py = bpy.context.copy()
                context_py["constraint"] = constr
            
                org_layers = ob.data.layers[:]
                for i in range(len(org_layers)):
                    ob.data.layers[i] = True
            
                ob.data.bones.active = armature.pose.bones[bone].bone
                bpy.ops.constraint.childof_set_inverse(context_py, constraint=arm.lips_shrink_constr_name+'_fric', owner='BONE')
            
                for i in range(len(org_layers)):
                    ob.data.layers[i] = org_layers[i]
            
                constr.influence = self.lips_shrinkwrap_friction_infl
    
        elif self.lips_shrinkwrap == True and self.lips_shrinkwrap_friction == True and ob != armature:
        
            ShowMessageBox(shrink_message, "MustardUI Information")
    
        else:
        
            for bone in bones_lips:
                for c in armature.pose.bones[bone].constraints:
                    if c.name == arm.lips_shrink_constr_name+'_fric':
                        to_remove = armature.pose.bones[bone].constraints[arm.lips_shrink_constr_name+'_fric']
                        armature.pose.bones[bone].constraints.remove(to_remove)
                        break
    
    elif self.lips_shrinkwrap == True and not self.lips_shrinkwrap_obj:
        
        self.lips_shrinkwrap = False
        ShowMessageBox("Select an Object. No modifier has been added", "MustardUI Information")
    
    else:
        
        for bone in bones_lips:
            for c in armature.pose.bones[bone].constraints:
                if c.name == arm.lips_shrink_constr_name:
                    to_remove = armature.pose.bones[bone].constraints[arm.lips_shrink_constr_name]
                    armature.pose.bones[bone].constraints.remove(to_remove)
                    break
    
    return

def lips_shrinkwrap_distance_update(self, context):
    
    armature = bpy.data.objects[model_name()+'_rig']
    
    if self.lips_shrinkwrap == True:
    
        for bone in bones_lips:
            
            constr = armature.pose.bones[bone].constraints[arm.lips_shrink_constr_name]
            constr.distance = self.lips_shrinkwrap_dist
            
            if bone == 'c_lips_smile.r' or bone == 'c_lips_smile.l':
                constr.distance = constr.distance * self.lips_shrinkwrap_dist_corr
    
    return

def lips_shrinkwrap_friction_infl_update(self, context):
    
    armature = bpy.data.objects[model_name()+'_rig']
    
    if self.lips_shrinkwrap_friction == True and self.lips_shrinkwrap == True:
    
        for bone in bones_lips:
            
            constr = armature.pose.bones[bone].constraints[arm.lips_shrink_constr_name+'_fric']
            constr.influence = self.lips_shrinkwrap_friction_infl
    
    return

def lips_shrinkwrap_obj_sec_poll(self, object):
    
    if self.lips_shrinkwrap_obj.type == 'MESH':
    
        return object.type == 'VERTEXGROUP'
    
    else:
        
        return object.type == 'EMPTY'
    
    return

bpy.types.Armature.lips_shrinkwrap = bpy.props.BoolProperty(default = False,
                                                        name="Enable",
                                                        description="Enable lips shrinkwrap",
                                                        update = lips_shrinkwrap_update)

bpy.types.Armature.lips_shrinkwrap_friction = bpy.props.BoolProperty(default = False,
                                                        name="Enable Friction",
                                                        description="Enable friction to lips shrinkwrap.\n"+shrink_message[:len(shrink_message)-1],
                                                        update = lips_shrinkwrap_update)

bpy.types.Armature.lips_shrinkwrap_dist = bpy.props.FloatProperty(default = 0.01,
                                                        min = 0.0,
                                                        name = "Distance",
                                                        description = "Set the distance of the lips bones to the Object",
                                                        update = lips_shrinkwrap_distance_update)

bpy.types.Armature.lips_shrinkwrap_dist_corr = bpy.props.FloatProperty(default = 1.0,
                                                        min = 0.0,
                                                        max = 2.0,
                                                        name = "Outer bones correction",
                                                        description = "Set the correction of the outer mouth bones to adjust the result.\nThis value is the fraction of the distance that will be applied to the outer bones shrinkwrap modifiers",
                                                        update = lips_shrinkwrap_distance_update)

bpy.types.Armature.lips_shrinkwrap_friction_infl = bpy.props.FloatProperty(default = 0.1,
                                                        min = 0.0,
                                                        max = 1.0,
                                                        name = "Coefficient",
                                                        description = "Set the friction coefficient of the lips shrinkwrap.\nIf the coefficient is 1, the bone will follow the Object completely",
                                                        update = lips_shrinkwrap_friction_infl_update)

bpy.types.Armature.lips_shrinkwrap_obj = bpy.props.PointerProperty(type=bpy.types.Object,
                                                                name="Object",
                                                                description="Select the object where to apply the lips shrinkwrap",
                                                                update = lips_shrinkwrap_update)

bpy.types.Armature.lips_shrinkwrap_obj_fric = bpy.props.PointerProperty(type=bpy.types.Object,
                                                                name="Object",
                                                                description="Select the object to use as a reference for the friction effect.\nIf no object is selected, the same object inserted in the main properties will be used",
                                                                update = lips_shrinkwrap_update)

bpy.types.Armature.lips_shrinkwrap_obj_fric_sec = bpy.props.StringProperty(name="Sub-target")

# ------------------------------------------------------------------------
#    Tools - Parent
# ------------------------------------------------------------------------

@classmethod
def childof_poll(cls, context):
    arm = bpy.data.armatures[model_name()+'_rig']
    return arm.enable_childof

class ChildOf(bpy.types.Operator):
    """Apply Child Of modifier"""
    bl_idname = "ops.childof"
    bl_label = "Apply Child Of modifier"
    bl_options = {'REGISTER'}
    
    clean: IntProperty(name='CLEAN',
        description="Clean action",
        default=0
    )

    def execute(self, context):
        
        arm = bpy.data.objects[model_name()+'_rig']
        arm2 = bpy.data.armatures[model_name()+'_rig']
        
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
                    constr.name = arm2.childof_contr_name
        
                    constr.target = parent_bone.id_data
                    constr.subtarget = parent_bone.name
            
                    context_py = bpy.context.copy()
                    context_py["constraint"] = constr
            
                    org_layers = ob.data.layers[:]
                    for i in range(len(org_layers)):
                        ob.data.layers[i] = True
            
                    ob.data.bones.active = child_bone.id_data.pose.bones[child_bone.name].bone
                    bpy.ops.constraint.childof_set_inverse(context_py, constraint=constr.name, owner='BONE')
            
                    for i in range(len(org_layers)):
                        ob.data.layers[i] = org_layers[i]
        
                    constr.influence = bpy.data.armatures[model_name()+'_rig'].childof_influence
        
                else:
                    self.report({'ERROR'}, 'You should select two Bones. No modifier has been added.')
                
            else:
                self.report({'ERROR'}, 'You should select two Bones. No modifier has been added.')
        
        else:
            
            mod_cont = 0
            for obj in bpy.data.objects:
                if obj.type=="ARMATURE":
                    for bone in obj.pose.bones:
                        for constr in bone.constraints:
                            if arm2.childof_contr_name in constr.name:
                                bone.constraints.remove(constr)
                                print('MustardUI: Constraint of '+bone.name+' in '+obj.name+' successfully removed.')
                                mod_cont=mod_cont+1
            
            if mod_cont>0:
                self.report({'INFO'}, str(mod_cont)+" modifiers successfully removed.")
            else:
                self.report({'INFO'}, 'No modifier was found. None was removed.')
        
        return {'FINISHED'}

bpy.types.Armature.childof_influence = bpy.props.FloatProperty(default = 1.0,
                                                        min = 0.0,
                                                        max = 1.0,
                                                        name = "Influence",
                                                        description = "Set the influence the parent Bone will have on the Child one")

# ------------------------------------------------------------------------
#    Pre-render checks
# ------------------------------------------------------------------------

@classmethod
def prerender_checks_poll(cls, context):
    arm = bpy.data.armatures[model_name()+'_rig']
    return arm.enable_prerender_checks

class RenderChecks_Eevee_SSR(bpy.types.Operator):
    """Enable Screen Space Reflections to fix bad eyes material behaviour"""
    bl_idname = "prc.eevee_ssr"
    bl_label = "Checks for Eevee rendering."
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        
        if bpy.context.scene.render.engine == "BLENDER_EEVEE":
            
            bpy.context.scene.eevee.use_ssr = True
            print("MustardUI: SSR enabled")
        
        else:
            print("MustardUI: Wrong engine check function engaged.")
        
        return {'FINISHED'}

class RenderChecks_Eevee_Refraction(bpy.types.Operator):
    """Enable Refraction to fix bad eyes material behaviour"""
    bl_idname = "prc.eevee_refraction"
    bl_label = "Checks for Eevee rendering."
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        
        if bpy.context.scene.render.engine == "BLENDER_EEVEE":
            
            bpy.context.scene.eevee.use_ssr_refraction = True
            print("MustardUI: SSR Refraction enabled")
        
        else:
            print("MustardUI: Wrong engine check function engaged.")
        
        return {'FINISHED'}

class RenderChecks_Cycles_Transparency(bpy.types.Operator):
    """Increase the number of transparency bounces to fix blocky hair textures during rendering"""
    bl_idname = "prc.cycles_transparency"
    bl_label = "Checks for Cycles rendering."
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        
        if bpy.context.scene.render.engine == "CYCLES":
            
            bpy.context.scene.cycles.transparent_max_bounces = 24
            print("MustardUI: Transparency bounces increased to 24")
        
        else:
            print("MustardUI: Wrong engine check function engaged.")
        
        return {'FINISHED'}

# ------------------------------------------------------------------------
#    Maintenance Tools
# ------------------------------------------------------------------------

class RegisterUI_Button(bpy.types.Operator):
    """Register the UI.\nPlease read the documentation before using this tool"""
    bl_idname = "ops.registerui_" + model_name().lower()
    bl_label = "Register the UI.\nPlease read the documentation before using this tool"
    
    def execute(self, context):
        
        bpy.data.armatures[model_name()+'_rig'].script_file = bpy.data.texts['mustard_ui_'+model_name().lower()+'.py']
        print("MustardUI: UI correctly registered in " + bpy.data.armatures[model_name()+'_rig'].name)
        self.report({'INFO'}, "MustardUI: UI correctly registered in " + bpy.data.armatures[model_name()+'_rig'].name)
        
        return {'FINISHED'}

class CleanUI_Button(bpy.types.Operator):
    """Clean UI settings and variables.\nPlease read the documentation before using this tool"""
    bl_idname = "ops.cleanui"
    bl_label = "Clean UI settings and variables.\nPlease read the documentation before using this tool"
    
    def execute(self, context):
        
        bpy.data.armatures[model_name()+'_rig'].mask_list.clear()
        bpy.data.armatures[model_name()+'_rig'].mat_text_sel.clear()
        bpy.data.armatures[model_name()+'_rig'].phys_obj_disabled.clear()
        bpy.data.armatures[model_name()+'_rig'].lock_coll_list.clear()
        
        self.report({'INFO'}, "MustardUI: UI variables reset")
        
        return {'FINISHED'}

class Optimize_Button(bpy.types.Operator):
    """Optimize the model.\nPlease read the documentation before using this tool"""
    bl_idname = "ops.optimize"
    bl_label = "Optimize the model. Please read the documentation before using this tool!"
    bl_options = {'REGISTER'}
    
    type: IntProperty(name='OPT_TYPE',
        description="Optimization Tipology",
        default=1
    )
    
    def execute(self, context):
        
        if self.type == 1:
            for obj in bpy.data.objects:
                for modifier in obj.modifiers:
                    if modifier.type == "SUBSURF" and obj.type == 'MESH':
                        modifier.show_viewport = False
        
        return {'FINISHED'}

# ------------------------------------------------------------------------
#    Link (thanks to Mets3D)
# ------------------------------------------------------------------------

class Link_Button(bpy.types.Operator):
    """Open links in a web browser"""
    bl_idname = "ops.open_link"
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
#    [Exp] Lattice
# ------------------------------------------------------------------------

@classmethod
def lattice_panel_poll(cls, context):
    arm = bpy.data.armatures[model_name()+'_rig']
    if arm.enable_lattice_panel and arm.settings_experimental:
        return True
    else:
        return False

class LatticeSetup(bpy.types.Operator):
    """Setup Lattice modification for all model Objects"""
    bl_idname = "ops.lattice_setup"
    bl_label = "Setup Lattice modification for all model Objects"
    bl_options = {'REGISTER'}
    
    mod: IntProperty(name='MOD',
        description="MOD",
        default=0
    )

    def execute(self, context):
        
        arm = bpy.data.armatures[model_name()+'_rig']
        
        OutCollListOptions = enum_entries(arm,"outfits")
        OutCollListOptions.remove('Nude')
        
        mod_name=model_name()+" Body Lattice"
        
        if self.mod==0:
            
            latt = bpy.data.objects[model_name() + " Body - Lattice"]
    
            for col in OutCollListOptions:
                for obj in bpy.data.collections[model_name()+' '+col].objects:
                    new_mod=True
                    for modifier in obj.modifiers:
                        if modifier.type == "LATTICE" and modifier.name == mod_name:
                            new_mod=False
                    if new_mod and obj.type=="MESH":        
                        mod = obj.modifiers.new(name=mod_name, type='LATTICE')
                        obj.modifiers[mod_name].object = latt
                        bpy.context.view_layer.objects.active = obj
                        while obj.modifiers.find(mod_name) != 0:
                            bpy.ops.object.modifier_move_up(modifier=mod_name)
            
            self.report({'INFO'}, "MustardUI: Lattice Setup complete")
        
        else:
            
            for col in OutCollListOptions:
                for obj in bpy.data.collections[model_name()+' '+col].objects:
                    if obj.type=="MESH":
                        obj.modifiers.remove(obj.modifiers.get(mod_name))
            
            self.report({'INFO'}, "MustardUI: Lattice Uninstallation complete")
        
        return {'FINISHED'}

class LatticeModify(bpy.types.Operator):
    """Create a custom Lattice modification"""
    bl_idname = "ops.lattice"
    bl_label = "Create a custom Lattice modification"
    bl_options = {'REGISTER'}
    
    mod: IntProperty(name='MOD',
        description="MOD",
        default=0
    )

    def execute(self, context):
        
        latt = bpy.data.objects[model_name() + " Body - Lattice"]
        arm = bpy.data.armatures[model_name()+'_rig']
        
        shape_key_custom_name = "MustardUI - Custom"
        
        if self.mod==0:
            
            arm.lattice_mod_status = True
            
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
            
            latt.data.shape_keys.key_blocks[shape_key_custom_name].value = 1                
            index = latt.data.shape_keys.key_blocks.find(shape_key_custom_name)
            latt.active_shape_key_index = index
            latt.hide_viewport = False
            try:
                bpy.ops.object.mode_set(mode='EDIT')
            except:
                self.report({'ERROR'}, "MustardUI: Be sure that "+model_name()+" Body - Lattice is not temporarily disabled in viewport (eye icon)!")
                arm.lattice_mod_status = False
        
        elif self.mod==1:
            
            bpy.context.view_layer.objects.active = latt
            bpy.ops.object.mode_set(mode='OBJECT')
            arm.lattice_mod_status = False
            latt.hide_viewport = True
        
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
                    
        return {'FINISHED'}

def lattice_enable_update(self, context):
    
    for object in bpy.data.objects:
        for modifier in object.modifiers:
            if modifier.type == "LATTICE" and modifier.name == model_name()+" Body Lattice":
                if self.lattice_enable:
                    modifier.show_render = True
                    modifier.show_viewport = True
                else:
                    modifier.show_render = False
                    modifier.show_viewport = False
    return

bpy.types.Armature.lattice_enable = bpy.props.BoolProperty(default = False,
                                                            name="Lattice body modification",
                                                            description="Enable lattice body modifications.\nDisable if not used to increase viewport performance",
                                                            update = lattice_enable_update)
bpy.types.Armature.lattice_mod_status = bpy.props.BoolProperty(default = False)
bpy.data.armatures[model_name()+'_rig'].lattice_mod_status = False

def lattice_shapekey_update(self, context):
    
    latt = bpy.data.objects[model_name() + " Body - Lattice"]
    
    for key in latt.data.shape_keys.key_blocks:
        if "MustardUI" in key.name:
            key.value=0.
    
    if self.lattice_keys != "Base":
        self.lattice_key_value = 1.
    
    return

def lattice_prop_update(self, context):
    
    latt = bpy.data.objects[model_name() + " Body - Lattice"]
    
    latt.data.interpolation_type_u = self.lattice_interpolation
    latt.data.interpolation_type_v = self.lattice_interpolation
    latt.data.interpolation_type_w = self.lattice_interpolation
    
    if self.lattice_keys != "Base":
        latt.data.shape_keys.key_blocks["MustardUI - "+self.lattice_keys].value = self.lattice_key_value
    
    return


bpy.types.Armature.lattice_keys = bpy.props.EnumProperty(name="",
                                                        description="Key selected",
                                                        items=LatticeKeyListOptionsIni,
                                                        update=lattice_shapekey_update)
bpy.types.Armature.lattice_key_value = bpy.props.FloatProperty(name="Deformation Intensity",
                                                        default=0.,
                                                        min=0.,max=1.,
                                                        description="Intensity of lattice deformation",
                                                        update=lattice_prop_update)
bpy.types.Armature.lattice_interpolation = bpy.props.EnumProperty(name = "",
                                                            description="",
                                                            items = [("KEY_BSPLINE","BSpline","BSpline"),("KEY_LINEAR","Linear","Linear"),("KEY_CARDINAL","Cardinal","Cardinal"),("KEY_CATMULL_ROM","Catmull-Rom","Catmull-Rom")],
                                                            update = lattice_prop_update)

# ------------------------------------------------------------------------
#    UI
# ------------------------------------------------------------------------

class MainPanel:
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MustardUI"
    #bl_options = {"DEFAULT_CLOSED"}


class MUSTARDUI_PT_Model(MainPanel, bpy.types.Panel):
    bl_idname = "MUSTARDUI_PT_Model"
    bl_label = "Body Settings"

    def draw(self, context):
        
        layout = self.layout
        arm = bpy.data.armatures[model_name()+'_rig']
        
        if arm.enable_sss or arm.enable_transl or arm.enable_subdiv or arm.enable_smoothcorr or arm.enable_norm_autosmooth:
            
            box = layout.box()
            box.label(text="Body properties", icon="OUTLINER_OB_ARMATURE")
        
            if arm.enable_subdiv:
                row = box.row(align=True)
                row.prop(arm,"subdiv_view")
                row.scale_x=0.4
                row.prop(arm,"subdiv_view_lv")
                
                row = box.row(align=True)
                row.prop(arm,"subdiv_rend")
                row.scale_x=0.4
                row.prop(arm,"subdiv_rend_lv")
        
            if arm.enable_smoothcorr:
                box.prop(arm,"smooth_corr")
            
            if arm.enable_norm_autosmooth:
                box.prop(arm,"norm_autosmooth")
            
            if arm.enable_sss:
                box.prop(arm,"sss")
            
            if arm.enable_transl:
                box.prop(arm,"transluc")
            
        if arm.enable_tan or arm.enable_skinwet or arm.enable_scratches or arm.enable_skindirt or arm.enable_nailscolor:
            
            box = layout.box()
            box.label(text="Skin properties", icon="OUTLINER_OB_SURFACE")
            
            if arm.enable_skinwet:
                box.prop(arm,"skinwet")
            if arm.enable_tan:
                box.prop(arm,"tan")
                if arm.enable_tanlines:
                    box.prop(arm,"tanlines")
            if arm.enable_scratches:
                box.prop(arm,"scratches")
            if arm.enable_skindirt:
                box.prop(arm,"skindirt")
            if arm.enable_nailscolor:
                row = box.row(align=True)
                row.prop(arm,"custom_nails_color")
                row.scale_x=0.6
                row.prop(arm,"nails_color")
        
        if arm.enable_blush or arm.enable_makeup:
            
            box = layout.box()
            box.label(text="Face properties", icon="USER")
            
        if arm.enable_blush:
            box.prop(arm,"blush")
        if arm.enable_makeup:
            box.prop(arm,"makeup")
            if arm.enable_runny_makeup:
                box.prop(arm,"runny_makeup")


class MUSTARDUI_PT_Outfits(MainPanel, bpy.types.Panel):
    bl_idname = "MUSTARDUI_PT_Outfits"
    bl_label = "Outfits & Hair Settings"

    def draw(self, context):
        layout = self.layout
        arm = bpy.data.armatures[model_name()+'_rig']
        
        OutCollListOptions = enum_entries(bpy.data.armatures[model_name()+'_rig'], "outfits")
        OutCollListOptions.remove('Nude')
        HairObjListAvail = enum_entries(bpy.data.armatures[model_name()+'_rig'], "hair")
        
        if len(OutCollListOptions) > 0:
            box = layout.box()
            box.label(text="Outfits list", icon="MOD_CLOTH")
            box.prop(arm,"outfits")
            
            if check_collection_item(arm.mat_text_sel, arm.outfits):
                box.prop(arm,"outfit_text")
            
            if arm.outfits!="Nude":
                OutfitListTemp = []
                for obj in bpy.data.collections[model_name()+' '+arm.outfits].objects:
                    OutfitListTemp.append(obj.name)
                for obj_name in sorted(OutfitListTemp):
                    coll = obj.users_collection[0].name
                    col = box.column(align=True)
                    row = col.row(align=True)
                    row.prop(bpy.data.objects[obj_name],"outfit",toggle=True, text=obj_name[len(model_name()+' '+arm.outfits+' - '):], icon='OUTLINER_OB_'+bpy.data.objects[obj_name].type)
                    if len_collection(bpy.data.objects[obj_name].additional_options)>0 and arm.settings_additional_options:
                        row.prop(bpy.data.objects[obj_name],"additional_options_show", toggle=True, icon="PREFERENCES")
                        if bpy.data.objects[obj_name].additional_options_show:
                            for el in bpy.data.objects[obj_name].additional_options:
                                if el.option_type == 0:
                                    col.prop(el,"option_value",text="Material - "+el.option_name)
                                elif el.option_type == 1:
                                    col.prop(el,"option_value_bool",text="Material - "+el.option_name)
                            for el in bpy.data.objects[obj_name].additional_options:
                                if el.option_type == 2:
                                    col.prop(el,"option_value",text="Shape - "+el.option_name)
                                elif el.option_type == 3:
                                    col.prop(el,"option_value_bool",text="Shape - "+el.option_name)
                    row.scale_x=1
                    if bpy.data.objects[obj_name].outfit_lock:
                        row.prop(bpy.data.objects[obj_name],"outfit_lock",toggle=True, icon='LOCKED')
                    else:
                        row.prop(bpy.data.objects[obj_name],"outfit_lock",toggle=True, icon='UNLOCKED')
            
            if len_collection(arm.lock_coll_list)>0:
                OutfitListTemp = []
                box.separator()
                box.label(text="Locked objects:", icon="LOCKED")
                for obj in bpy.data.objects:
                    if obj.outfit_lock:
                        OutfitListTemp.append(obj.name)
                for obj_name in sorted(OutfitListTemp):
                    row = box.row(align=True)
                    row.prop(bpy.data.objects[obj_name],"outfit",toggle=True, text=obj_name[len(model_name()):], icon='OUTLINER_OB_'+bpy.data.objects[obj_name].type)
                    row.scale_x=1
                    row.prop(bpy.data.objects[obj_name],"outfit_lock",toggle=True, icon='LOCKED')
            
            if arm.enable_smooth_corr_out or arm.enable_shrink_out or arm.enable_masks_out or arm.enable_norm_autosmooth_out:
                box = layout.box()
                box.label(text="Outfits global properties", icon="MODIFIER")
                if arm.enable_smooth_corr_out:
                    box.prop(arm,"smooth_corr_out")
                if arm.enable_shrink_out:
                    box.prop(arm,"shrink_out")
                if arm.enable_masks_out:
                    box.prop(arm,"masks_out")
                if arm.enable_norm_autosmooth_out:
                    box.prop(arm,"norm_autosmooth_out")
        
        if len(HairObjListAvail) > 1:
            box = layout.box()
            box.label(text="Hair list and properties", icon="HAIR")
            box.prop(arm,"hair")
        
        if model_name()+' Extras' in bpy.data.collections:
            box = layout.box()
            box.label(text="Extras list", icon="PLUS")
            for obj in bpy.data.collections[model_name()+' Extras'].objects:
                col = box.column(align=True)
                row = col.row(align=True)
                row.prop(bpy.data.objects[obj.name],"outfit",toggle=True, text=obj.name[len(model_name()+' Extras - '):], icon='OUTLINER_OB_'+bpy.data.objects[obj.name].type)
                if len_collection(obj.additional_options)>0 and arm.settings_additional_options:
                    row.prop(obj,"additional_options_show", toggle=True, icon="PREFERENCES")
                    if obj.additional_options_show:
                        for el in obj.additional_options:
                            if el.option_type == 0:
                                col.prop(el,"option_value",text="Material - "+el.option_name)
                            elif el.option_type == 1:
                                col.prop(el,"option_value_bool",text="Material - "+el.option_name, toggle=True)
                        for el in obj.additional_options:
                            if el.option_type == 2:
                                col.prop(el,"option_value",text="Shape - "+el.option_name)
                            elif el.option_type == 3:
                                col.prop(el,"option_value_bool",text="Shape - "+el.option_name)


class MUSTARDUI_PT_Rig(MainPanel, bpy.types.Panel):
    bl_idname = "MUSTARDUI_PT_Rig"
    bl_label = "Armature Settings"
    
    def draw(self, context):
        
        layout = self.layout
        arm = bpy.data.armatures[model_name()+'_rig']
        
        box = layout.box()
        box.label(text='Hair Armature', icon="HAIR")
        box.prop(arm, "rig_hair",toggle=True)
        box = layout.box()
        box.label(text='Body Armature Layers', icon="ARMATURE_DATA")
        box.prop(arm, "rig_main_std",toggle=True)
        box.prop(arm, "rig_main_adv",toggle=True)
        box.prop(arm, "rig_main_childof",toggle=True)
        box.prop(arm, "rig_main_extra",toggle=True)
        if arm.settings_advanced:
            box.prop(arm, "rig_main_rig",toggle=True)


class MUSTARDUI_PT_Lattice(MainPanel, bpy.types.Panel):
    bl_idname = "MUSTARDUI_PT_Lattice"
    bl_label = "[Exp] Body Shape"
    bl_options = {"DEFAULT_CLOSED"}
    
    poll = lattice_panel_poll
    
    def draw_header(self,context):
        
        arm = bpy.data.armatures[model_name()+'_rig']
        
        self.layout.prop(arm, "lattice_enable", text="", toggle=False)
    
    def draw(self, context):
        
        arm = bpy.data.armatures[model_name()+'_rig']
        
        layout = self.layout
        if not arm.lattice_enable:
            layout.enabled = False
        
        box = layout.box()
        box.label(text="Shape settings", icon="MOD_LATTICE")
        row = box.row(align=True)
        row.label(text="Shape")
        row.scale_x=2.
        row.prop(arm,"lattice_keys")
        row = box.row(align=True)
        if arm.lattice_keys == "Base":
            row.enabled = False
        row.prop(arm,"lattice_key_value")
        if arm.settings_advanced:
            row = box.row(align=True)
            if arm.lattice_keys == "Base":
                row.enabled = False
            row.label(text="Interpolation")
            row.scale_x=2.
            row.prop(arm,"lattice_interpolation")
        
        box = layout.box()
        box.label(text="Custom Lattice Shape", icon="PLUS")
        box.label(text="    - Run Custom Shape")
        box.label(text="    - Move the vertices")
        box.label(text="    - Apply shape")
        if arm.lattice_mod_status:
            box.operator("ops.lattice", text="Apply shape", depress=True, icon="EDITMODE_HLT").mod = 1
        else:
            row = box.row(align=True)
            if arm.lattice_keys != "Custom":
                row.enabled = False
            row.operator("ops.lattice", text="Custom shape", icon="EDITMODE_HLT").mod = 0
        row = box.row(align=True)
        if arm.lattice_keys != "Custom":
            row.enabled = False
        row.operator("ops.lattice", text="Reset Custom shape", icon="CANCEL").mod = 2


class MUSTARDUI_PT_Physics(MainPanel, bpy.types.Panel):
    bl_idname = "MUSTARDUI_PT_Physics"
    bl_label = "Physics"
    bl_options = {"DEFAULT_CLOSED"}
    
    poll = physics_panel_poll
    
    def draw_header(self,context):
        
        arm = bpy.data.armatures[model_name()+'_rig']
        
        self.layout.prop(arm, "phy_enable", text="", toggle=False)
    
    def draw(self, context):
        
        arm = bpy.data.armatures[model_name()+'_rig']
        
        layout = self.layout
        if not arm.phy_enable:
            layout.enabled = False
        
        box = layout.box()
        
        box.label(text='Physics settings', icon="PHYSICS")
        box.prop(arm,"phy_objects")
            
        box.prop(arm,"phy_single_enable")
        
        row = box.row(align=True)
        if not arm.phy_single_enable:
            row.enabled = False
        row.label(text="")
        row.scale_x=1.
        row.label(text='Stiffness')
        row.scale_x=1.
        row.label(text='Damping')
        
        row = box.row(align=True)
        if not arm.phy_single_enable:
            row.enabled = False
        row.label(text="Structural")
        row.scale_x=1.
        row.prop(arm,"phy_stiff_struct")
        row.scale_x=1.
        row.prop(arm,"phy_damp_struct")
        
        row = box.row(align=True)
        if not arm.phy_single_enable:
            row.enabled = False
        row.label(text="Shear")
        row.scale_x=1.
        row.prop(arm,"phy_stiff_shear")
        row.scale_x=1.
        row.prop(arm,"phy_damp_shear")
        
        row = box.row(align=True)
        if not arm.phy_single_enable:
            row.enabled = False
        row.label(text="Bending")
        row.scale_x=1.
        row.prop(arm,"phy_stiff_bend")
        row.scale_x=1.
        row.prop(arm,"phy_damp_bend")
            
        row = box.column(align=True)
        if not arm.phy_single_enable:
            row.enabled = False  
        row.prop(arm,"phy_collisions")
            
        row = box.column(align=True)
        if not arm.phy_single_enable or not arm.phy_collisions:
            row.enabled = False
        row.prop(arm,"phy_collisions_distance")
        row = box.column(align=True)
        if not arm.phy_single_enable or not arm.phy_collisions:
            row.enabled = False
        row.prop(arm,"phy_collisions_clamping")
            
        box = layout.box()
        
        box.label(text='External Object collision', icon="MOD_PHYSICS")
            
        box.label(text='Select a Mesh Object to add collision.')
            
        mod_presence = False
        ui_disable = False
        if len(bpy.context.selected_objects)==1:
            if bpy.context.selected_objects[0].type == "MESH":
                for mod in bpy.context.selected_objects[0].modifiers:
                    if mod.type=="COLLISION" and mod.name == 'MustardUI Collision':
                        mod_presence = True
                        break
            else:
                ui_disable = True
        else:
            ui_disable = True
            
        row = box.column(align=True)
        if mod_presence or ui_disable:
            row.enabled = False
        row.prop(arm,"phy_collisions_mesh_damp")
        row = box.column(align=True)
        if mod_presence or ui_disable:
            row.enabled = False
        row.prop(arm,"phy_collisions_mesh_thick")
        row = box.column(align=True)
        if mod_presence or ui_disable:
            row.enabled = False
        row.prop(arm,"phy_collisions_mesh_friction")
            
        if mod_presence:
            box.operator('ops.phy_mesh_collision', text="Disable selected Object Collision", depress=True, icon="CANCEL").clean = True
        else:
            box.operator('ops.phy_mesh_collision', text="Enable selected Object Collision").clean = False
            
        box = layout.box()
        
        box.label(text='Simulation settings', icon="MODIFIER")
        box.prop(arm,"phy_steps")
        box.prop(arm,"phy_speed")
            
        row = box.column(align=True)
        row.enabled = False
        phy_int=0
        for object in bpy.data.collections[model_name()+' Physics'].objects:
            if phy_int > 0:
                break
            for modifier in object.modifiers:
                if modifier.type == 'CLOTH' and "MustardUI" in modifier.name:
                    if modifier.collision_settings.use_collision and modifier.show_render:
                        row.enabled = True
                        phy_int=1
                        break
        row.prop(arm,"phy_collisions_steps")
        
        box.label(text='Simulation frame range')
        row = box.row(align=True)
        row.prop(arm, "phy_start_frame")
        row.scale_x=1.
        row.prop(arm, "phy_end_frame")
        
        if arm.phy_bake:
            layout.operator('ops.phy_bake', text="Delete Bake", depress=True, icon="CANCEL").bake = False
        else:
            layout.operator('ops.phy_bake', text="Bake Physics").bake = True


class MUSTARDUI_PT_Tools(MainPanel, bpy.types.Panel):
    bl_idname = "MUSTARDUI_PT_Tools"
    bl_label = "Tools"
    poll = tools_poll
    
    def draw(self, context):
        
        layout = self.layout
        arm = bpy.data.armatures[model_name()+'_rig']
        
        #layout.label(text="Tools list")


class MUSTARDUI_PT_Tools_PreRenderChecks(MainPanel, bpy.types.Panel):
    bl_parent_id = "MUSTARDUI_PT_Tools"
    bl_idname = "MUSTARDUI_PT_Tools_PreRenderChecks"
    bl_label = "Pre-render Checks"
    bl_options = {"DEFAULT_CLOSED"}
    poll = prerender_checks_poll
    
    def draw(self, context):
        
        layout = self.layout
        arm = bpy.data.armatures[model_name()+'_rig']
        
        layout.label(text="List of checks to control before rendering.")
        
        box = layout.box()
        
        if bpy.context.scene.render.engine == "CYCLES":
            
            box.label(text="Rendering engine: Cycles", icon="MODIFIER")
            
            cycles = bpy.context.scene.cycles
            
            if cycles.transparent_max_bounces < 20:
                box.label(text="Transparency bounces number is too low",icon="CHECKBOX_DEHLT")
                box.operator('prc.cycles_transparency', text="Increase Transparency bounces")
            else:
                box.label(text="Transparency bounces number is sufficient.",icon="CHECKBOX_HLT")
            
            if bpy.context.scene.view_layers['View Layer'].cycles.use_denoising == False:
                found_compositor=False
                if bpy.context.scene.use_nodes:
                    tree = bpy.context.scene.node_tree
                    for node in tree.nodes:
                        if node.type == "DENOISE":
                            box.label(text="Denoiser seems to be in the compositor.",icon="CHECKBOX_HLT")
                            found_compositor=True
                            break
                        elif node.type == "GROUP":
                            if "Denoise" in tree.nodes['Group'].node_tree.name:
                                box.label(text="Denoiser seems to be in the compositor.",icon="CHECKBOX_HLT")
                                found_compositor=True
                                break
                    if found_compositor == False:
                        box.label(text="Denoiser not configured.",icon="CHECKBOX_DEHLT")
                        box.operator('ops.open_link', text="How to enable it?", icon = "WORLD").url = arm.url_denoiser
                else:
                    box.label(text="Denoiser not configured.",icon="CHECKBOX_DEHLT")
                    box.operator('ops.open_link', text="How to enable it?", icon = "WORLD").url = arm.url_denoiser
            else:
                found_compositor=False
                if bpy.context.scene.use_nodes:
                    tree = bpy.context.scene.node_tree
                    for node in tree.nodes:
                        if node.type == "DENOISE":
                            box.label(text="Both Blender and Compositor denoisers enabled.",icon="CHECKBOX_HLT")
                            box.label(text="      Are you sure you need both?")
                            found_compositor=True
                            break
                        elif node.type == "GROUP":
                            if "Denoise" in tree.nodes['Group'].node_tree.name:
                                box.label(text="Both Blender and Compositor denoisers enabled.",icon="CHECKBOX_HLT")
                                box.label(text="      Are you sure you need both?")
                                found_compositor=True
                                break
                    if found_compositor == False:
                        box.label(text="Blender Denoiser enabled.",icon="CHECKBOX_HLT")
                else:
                        box.label(text="Blender Denoiser enabled.",icon="CHECKBOX_HLT")
            
        
        elif bpy.context.scene.render.engine == "BLENDER_EEVEE":
            
            box.label(text="Rendering engine: Eevee", icon="MODIFIER")
            
            eevee = bpy.context.scene.eevee
            
            if eevee.use_ssr == False:
                box.label(text="Screen space reflections is disabled.",icon="CHECKBOX_DEHLT")
                box.operator('prc.eevee_ssr', text="Enable SSR")
            else:
                box.label(text="Screen space reflections enabled",icon="CHECKBOX_HLT")
            
            if eevee.use_ssr_refraction == False:
                box.label(text="Refraction is disabled.",icon="CHECKBOX_DEHLT")
                box.operator('prc.eevee_refraction', text="Enable Refraction")
            else:
                box.label(text="Refraction enabled",icon="CHECKBOX_HLT")
                
        else:
            
            box.label(text="Rendering engine: " + bpy.context.scene.render.engine + " not supported", icon="MODIFIER")


class MUSTARDUI_PT_Tools_Lips_Shrinkwrap(MainPanel, bpy.types.Panel):
    bl_parent_id = "MUSTARDUI_PT_Tools"
    bl_idname = "MUSTARDUI_PT_Tools_Lips_Shrinkwrap"
    bl_label = "Lips Shrinkwrap"
    bl_options = {"DEFAULT_CLOSED"}
    
    poll = lips_shrinkwrap_poll
    
    def draw(self, context):
        
        layout = self.layout
        arm = bpy.data.armatures[model_name()+'_rig']
        
        layout.label(text="Force the lips bones to stay outside the Object.")
        
        box = layout.box()
        
        box.label(text="Main properties.", icon="MODIFIER")
        box.prop(arm, "lips_shrinkwrap_obj")
        box.prop(arm, "lips_shrinkwrap_dist")
        box.prop(arm, "lips_shrinkwrap_dist_corr")
        
        box = layout.box()
        
        box.label(text="Friction properties.", icon="FORCE_TURBULENCE")
        row = box.row(align=True)
        row.prop(arm, "lips_shrinkwrap_friction")
        row.scale_x=0.8
        row.prop(arm, "lips_shrinkwrap_friction_infl")
        box.prop(arm, "lips_shrinkwrap_obj_fric")
        if arm.lips_shrinkwrap_obj_fric:
            if arm.lips_shrinkwrap_obj_fric.type == "MESH":
                box.prop_search(arm, "lips_shrinkwrap_obj_fric_sec",arm.lips_shrinkwrap_obj_fric,"vertex_groups")
            if arm.lips_shrinkwrap_obj_fric.type == "ARMATURE":
                box.prop_search(arm, "lips_shrinkwrap_obj_fric_sec",arm.lips_shrinkwrap_obj_fric.pose,"bones")
        
        row = layout.row()
        if arm.lips_shrinkwrap:
            row.prop(arm, "lips_shrinkwrap",text="Disable", toggle=True, icon="CANCEL")
        else:
            row.prop(arm, "lips_shrinkwrap",toggle=True) 


class MUSTARDUI_PT_Tools_ChildOf(MainPanel, bpy.types.Panel):
    bl_parent_id = "MUSTARDUI_PT_Tools"
    bl_idname = "MUSTARDUI_PT_Tools_ChildOf"
    bl_label = "Parent bones"
    bl_options = {"DEFAULT_CLOSED"}
    
    poll = childof_poll
    
    def draw(self, context):
        
        layout = self.layout
        arm = bpy.data.armatures[model_name()+'_rig']
        
        layout.label(text="Force one Bone to follow another Bone.")
        
        box = layout.box()
        box.label(text="Select two bones:", icon="BONE_DATA")
        box.label(text="        - the first will be the parent,")
        box.label(text="        - the second will be the child.")
        box.prop(arm, "childof_influence")
        layout.operator('ops.childof', text="Enable").clean = 0
        
        box = layout.box()
        
        box.label(text="Remove Parent instances.", icon="X")
        box.label(text="Note: this clean the UI generated modifiers only.")
        layout.operator('ops.childof', text="Clean").clean = 1


class MUSTARDUI_PT_Settings(MainPanel, bpy.types.Panel):
    bl_idname = "MUSTARDUI_PT_Settings"
    bl_label = "Settings"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        
        box = layout.box()
        box.label(text="Settings", icon="SETTINGS")
        
        arm = bpy.data.armatures[model_name()+'_rig']
        
        #row = box.row(align=True)
        #row.enabled = False
        box.prop(arm,"settings_advanced")
        #row = box.row(align=True)
        #row.enabled = False
        box.prop(arm,"settings_experimental")
        box.prop(arm,"settings_additional_options")
        box.prop(arm,"settings_debug")
        box.prop(arm,"settings_maintenance")
        
        if arm.settings_maintenance:
            box = layout.box()
            box.label(text="Maintenance Tools", icon="SETTINGS")
            box.label(text="UI tools", icon="MODIFIER")
            box.operator("ops.registerui_" + model_name().lower(), text="Register UI")
            box.operator("ops.cleanui", text="Reset UI")
            box.label(text="Scene tools", icon="SCENE_DATA")
            box.operator('ops.optimize', text="Viewport Optimization").type = 1
            box.label(text="Lattice setup", icon="MOD_LATTICE")
            box.operator('ops.lattice_setup', text="Lattice Setup").mod = 0
            box.operator('ops.lattice_setup', text="Lattice Clean").mod = 1
            box.label(icon='ERROR', text="Use at your own risk!")
        
        box = layout.box()
        box.label(text="Versions", icon="INFO")
        
        if model_version!='':
            box.label(text="       - Model: " + arm.model_version)
        box.label(text="       - MustardUI: " + arm.settings_UI_version)
        
        if arm.status_rig_tools == 1 or arm.status_rig_tools == 0:
            box = layout.box()
            if arm.status_rig_tools is 1:
                box.label(icon='ERROR',text="Debug: rig_tools not enabled!")
            elif arm.status_rig_tools is 0:
                box.label(icon='ERROR', text="Debug: rig_tools not installed!")


class MUSTARDUI_PT_Links(MainPanel, bpy.types.Panel):
    bl_idname = "MUSTARDUI_PT_Links"
    bl_label = "Links"
    bl_options = {"DEFAULT_CLOSED"}
    
    def draw(self, context):
        layout = self.layout
        
        arm = bpy.data.armatures[model_name()+'_rig']
        
        if arm.url_website!='' or url_patreon!='' or url_twitter!='' or url_smutbase!='' or arm.url_reportbug!='':
            
            box = layout.box()
            box.label(text="Social profiles/contacts", icon="BOOKMARKS")
        
            if arm.url_website!='':
                box.operator('ops.open_link', text="Website", icon = "WORLD").url = arm.url_website
            if arm.url_patreon!='':
                box.operator('ops.open_link', text="Patreon", icon = "WORLD").url = arm.url_patreon
            if arm.url_twitter!='':
                box.operator('ops.open_link', text="Twitter", icon = "WORLD").url = arm.url_twitter
            if arm.url_smutbase!='':
                box.operator('ops.open_link', text="SmutBase", icon = "WORLD").url = arm.url_smutbase
            if arm.url_reportbug!='':
                box.operator('ops.open_link', text="Report a Bug", icon = "WORLD").url = arm.url_reportbug
        
        box = layout.box()
        box.label(text="UI useful references", icon="INFO")
        box.operator('ops.open_link', text="MustardUI - Tutorial", icon = "WORLD").url = arm.url_MustardUItutorial
        box.operator('ops.open_link', text="MustardUI - GitHub", icon = "WORLD").url = arm.url_MustardUI


# ------------------------------------------------------------------------
#    Register
# ------------------------------------------------------------------------

classes = (
    PhyBake,
    LatticeSetup,
    LatticeModify,
    PhyMeshCollision,
    ChildOf,
    Link_Button,
    RenderChecks_Eevee_SSR,
    RenderChecks_Eevee_Refraction,
    RenderChecks_Cycles_Transparency,
    Optimize_Button,
    RegisterUI_Button,
    CleanUI_Button,
    MUSTARDUI_PT_Model,
    MUSTARDUI_PT_Outfits,
    MUSTARDUI_PT_Rig,
    MUSTARDUI_PT_Physics,
    MUSTARDUI_PT_Lattice,
    MUSTARDUI_PT_Tools,
    MUSTARDUI_PT_Tools_PreRenderChecks,
    MUSTARDUI_PT_Tools_Lips_Shrinkwrap,
    MUSTARDUI_PT_Tools_ChildOf,
    MUSTARDUI_PT_Settings,
    MUSTARDUI_PT_Links
)

def register():
    from bpy.utils import register_class
    
    bpy.types.Armature.script_file = PointerProperty(type=bpy.types.Text)
    
    for cls in classes:
        register_class(cls)

def unregister():
    
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

if __name__ == "__main__":
    register()
