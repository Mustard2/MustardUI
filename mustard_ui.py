# MustardUI script
# Refer to the documentation to implement this to other models

import bpy
import addon_utils
import sys
from bpy.props import *
from mathutils import Vector, Color
import webbrowser

# ------------------------------------------------------------------------
#    Definitions (can be tweaked)
# ------------------------------------------------------------------------

# The name of the model. All the relevant quantities should be renamed with this name
model_name = 'Jill'

# Model version
model_version = '5 - 30/03/2020'

# List of the body materials
BodyPartsList = ['Torso','Face','Arms','Legs','Genitals','Neck']

# List of outfits to be imported by the UI
OutCollList = ['Original','Sport','Bikini','RE1','RE3','RE5','Sheriff']

# List of hair to be imported by the UI
# If there is only one hair_style in the list, the hair selection interface will be hidden by default
HairObjList = ['Hair']

# Choose which options to show on the UI
# Enable smooth correction modifier switcher for the main body mesh
enable_smoothcorr = True

# Enable subdivision surface modifier switcher for the main body mesh
enable_subdiv = True

# Enable subsurface scattering slider
enable_sss = True
# Default subsurface scattering value
default_sss = 0.044

# Enable translucency slider
enable_transl = False
# Default translucency value
default_transl = 0.0

# Enable wet effect slider
enable_skinwet = True
# If this is enabled, you can control non-body materials with the wet slider
enable_wet = False

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
enable_scratches = True

# Enable dirt effect slider
enable_skindirt = True
# If this is enabled, you can control non-body materials with the dirt slider
enable_dirt = True

# Enable smooth correction modifier switcher for the outfits
enable_smooth_corr_out = True
# Enable shrinkwrap modifier switcher for the outfits
enable_shrink_out = True
# Enable masks switcher for the outfits
enable_masks_out = True

# List of the links which will be shown in the Link tab
url_patreon = "https://www.patreon.com/mustardsfm"
url_twitter = "https://twitter.com/MustardSFM"
url_smutbase = "https://smutba.se/user/10157/"

# Additional maintenance tool
# WARNING: Read the documentation before enabling these tools!
optimization_tools = False

# Debug mode
enable_debug_mode = True

# ------------------------------------------------------------------------
#    Internal Definitions (do not change them)
# ------------------------------------------------------------------------

# UI version
UI_version = '0.3.3 - 30/03/2020'

OutCollListAvail = []
OutCollListOptions = [("Nude","Nude","Nude")]
LockCollList = []
MatWithTextSel = []
MatWithTextSelCount = []

HairObjListAvail = []
HairObjListOptions = []

ExtrasObjListAvail = []

MaskList=[]

bpy.types.WindowManager.out_sel_ID = 0

url_MustardUI = "https://github.com/Mustard2/MustardUI"
url_MustardUItutorial = "https://github.com/Mustard2/MustardUI/wiki/Tutorial"

# Valued of the already stored variables
# Vector entries:
#   stored_sss
#   stored_smoothcorr
#   stored_subdiv_ren
#   stored_subdiv_ren_lv
#   stored_subdiv_view
#   stored_subdiv_view_lv

StoredOptions = [0.,0.,0.,0.,0.,0.]

# ------------------------------------------------------------------------
#    Preliminary operations definitions
# ------------------------------------------------------------------------
#
# Here some preliminary operations are defined.
#

# This function checks that the rig_tools addon is installed and enabled.
def addon_check():
    addon_name = "auto_rig_pro-master"
    addon_name2 = "rig_tools"
    
    rig_tools_status = 0
    
    addon_utils.modules_refresh()
    
    if addon_name not in addon_utils.addons_fake_modules and addon_name2 not in addon_utils.addons_fake_modules:
        print("%s: Add-on not installed." % addon_name)
    else:
        default, state = addon_utils.check(addon_name)
        default, state2 = addon_utils.check(addon_name2)
        if (not state and not state2):
            rig_tools_status = 1
            print("%s: Add-on installed but not enabled." % addon_name )
        else:
            rig_tools_status = 2
            print("%s: Add-on enabled and running." % addon_name)
    return rig_tools_status

# These definitions are necessary for the first time run of UI on a model
bpy.types.Object.outfit = bpy.props.BoolProperty(default = True,
                                                        name="",
                                                        description="")
bpy.types.Object.outfit_lock = bpy.props.BoolProperty(default = False,
                                                        name="",
                                                        description="Lock/unlock the outfit")

# This function checks which hair styles are available.
def po_check_hair():
    
    HairObjListName = [];
    
    for i in range(len(HairObjList)):
        HairObjListName.append(model_name+' '+HairObjList[i])

    for collection in bpy.data.collections:
            for obj in collection.objects:
                data=(obj.name[len(model_name)+1:]),(obj.name[len(model_name)+1:]),(obj.name[len(model_name)+1:])
                if obj.name in HairObjListName and data not in HairObjListOptions:
                    HairObjListAvail.append(obj.name[len(model_name)+1:])
                    HairObjListOptions.append(data)
    
    if enable_debug_mode:
        print("Hair found")
        print(HairObjListAvail)

# This function checks if the outfits are available.
# Moreover it checks if more Textures are available with Texture Selectors. If this is the case, it counts how many textures are available.
def po_check_collections():
    
    OutCollListName = [];
    
    for i in range(len(OutCollList)):
        OutCollListName.append(model_name+' '+OutCollList[i])

    for collection in bpy.data.collections:
        if collection.name in OutCollListName:
            OutCollListAvail.append(collection.name[len(model_name)+1:])
            data=(collection.name[len(model_name)+1:]),(collection.name[len(model_name)+1:]),"Outfit "+(collection.name[len(model_name)+1:])
            OutCollListOptions.append(data)
    
    if enable_debug_mode:
        print("Outfits found")
        print(OutCollListOptions)
    
    for i in range(len(bpy.data.materials)):
        bpy.data.materials[i].use_nodes=True
        for j in range(len(bpy.data.materials[i].node_tree.nodes)):
            if "Main Texture Selector" in bpy.data.materials[i].node_tree.nodes[j].name:
                for n in OutCollListAvail:
                    if n in bpy.data.materials[i].name[len(model_name)+1:]:
                        MatWithTextSel.append(n)
                for k in range(9):
                    if not bpy.data.materials[i].node_tree.nodes[j].inputs[k].links:
                        MatWithTextSelCount.append(k)
                        break
                break
    
    if enable_debug_mode:
        print("Materials with texture selectors found")
        print(MatWithTextSel)
        print("with count")
        print(MatWithTextSelCount)
    
    for obj in bpy.data.objects:
        for outfit in OutCollListAvail:
            if model_name in obj.name and outfit in obj.name:
                coll = obj.users_collection[0].name[len(model_name)+1:]
                if obj.outfit_lock:
                    LockCollList.append(coll)
                    obj.hide_viewport = False
                    obj.hide_render = False
                    obj.outfit=True
    
    MaskList.append(model_name+' Body')
    for obj in HairObjListAvail:
        MaskList.append(model_name+' '+obj)
    if enable_debug_mode:
        print("Objects with masks")
        print(MaskList)
 
# This functions finds the available extras
def po_check_extras():
    if model_name+' Extras' in bpy.data.collections:
        for obj in bpy.data.collections[model_name+' Extras'].objects:
            ExtrasObjListAvail.append(obj.name)
    
    if enable_debug_mode:
        print("Extras found")
        print(ExtrasObjListAvail)

# This function check the already available options and use them as the initial values for the variables
def po_check_options():
    
    # Stored SSS
    StoredOptions[0] = bpy.data.materials[model_name+' '+BodyPartsList[0]].node_tree.nodes['Principled BSDF'].inputs[1].default_value
    
    for modifier in bpy.data.objects[model_name+' Body'].modifiers:
            if modifier.type == "CORRECTIVE_SMOOTH":
                StoredOptions[1] = modifier.show_render
                break
    
    for modifier in bpy.data.objects[model_name+' Body'].modifiers:
            if modifier.type == "SUBSURF":
                StoredOptions[2] = modifier.show_render
                StoredOptions[3] = modifier.render_levels
                StoredOptions[4] = modifier.show_viewport
                StoredOptions[5] = modifier.levels
                break
    
    if enable_debug_mode:
        print("Stored informations found")
        print(StoredOptions)
        print("\n")

# ------------------------------------------------------------------------
#    Preliminary operations run
# ------------------------------------------------------------------------
#
# Here the preliminary operations functions runs
po_check_hair()
po_check_collections()
po_check_extras()
po_check_options()
rig_tools_status = addon_check()

# ------------------------------------------------------------------------
#    Model Properties
# ------------------------------------------------------------------------

def subdiv_rend_update(self, context):
    
    for modifier in bpy.data.objects[model_name+' Body'].modifiers:
            if modifier.type == "SUBSURF":
                if self.subdiv_rend == True:
                    modifier.show_render = True
                else:
                    modifier.show_render = False
    return

bpy.types.Scene.subdiv_rend = bpy.props.BoolProperty(default = True,
                                                            name="Subdivision Surface (Render)",
                                                            description="Enable/disable the subdivision surface during rendering. \nThis won't affect the viewport or the viewport rendering preview. \nNote that, depending on the complexity of the model, enabling this can greatly affect rendering times",
                                                            update = subdiv_rend_update)
bpy.context.scene.subdiv_rend = StoredOptions[2]

def subdiv_rend_lv_update(self, context):
    
    for modifier in bpy.data.objects[model_name+' Body'].modifiers:
            if modifier.type == "SUBSURF":
                modifier.render_levels = self.subdiv_rend_lv
    return

bpy.types.Scene.subdiv_rend_lv = bpy.props.IntProperty(default = 1,min=0,max=4,
                                                            name="Level",
                                                            description="Set the subdivision surface level during rendering. \nNote that, depending on the complexity of the model, increasing this can greatly affect rendering times",
                                                            update = subdiv_rend_lv_update)
bpy.context.scene.subdiv_rend_lv = StoredOptions[3]

def subdiv_view_update(self, context):
    
    for modifier in bpy.data.objects[model_name+' Body'].modifiers:
            if modifier.type == "SUBSURF":
                if self.subdiv_view == True:
                    modifier.show_viewport = True
                else:
                    modifier.show_viewport = False
    return

bpy.types.Scene.subdiv_view = bpy.props.BoolProperty(default = False,
                                                            name="Subdivision Surface (Viewport)",
                                                            description="Enable/disable the subdivision surface in the viewport. \nSince it's really computationally expensive, use this only for previews and do NOT enable it during posing. \nNote that it might require a lot of time to activate, and Blender will freeze during this",
                                                            update = subdiv_view_update)
bpy.context.scene.subdiv_view = StoredOptions[4]

def subdiv_view_lv_update(self, context):
    
    for modifier in bpy.data.objects[model_name+' Body'].modifiers:
            if modifier.type == "SUBSURF":
                modifier.levels = self.subdiv_view_lv
    return

bpy.types.Scene.subdiv_view_lv = bpy.props.IntProperty(default = 0,min=0,max=4,
                                                            name="Level",
                                                            description="Set the subdivision surface level in viewport. \nNote that, depending on the complexity of the model, increasing this can greatly affect viewport performances. Moreover, each time you change this value with Subdivision Surface (Viewport) enabled, Blender will freeze while applying the modification",
                                                            update = subdiv_view_lv_update)
bpy.context.scene.subdiv_view_lv = StoredOptions[5]

def smooth_corr_update(self, context):
    
    for modifier in bpy.data.objects[model_name+' Body'].modifiers:
            if modifier.type == "CORRECTIVE_SMOOTH":
                if self.smooth_corr == True:
                    modifier.show_viewport = True
                    modifier.show_render = True
                else:
                    modifier.show_viewport = False
                    modifier.show_render = False
    return

bpy.types.Scene.smooth_corr = bpy.props.BoolProperty(default = True,
                                                            name="Smooth Correction",
                                                            description="Enable/disable the smooth correction. \nDisable it to increase the performance in viewport, and re-enable it before rendering",
                                                            update = smooth_corr_update)
bpy.context.scene.smooth_corr = StoredOptions[1]

def sss_update(self, context):
    
    for mat in BodyPartsList:
        bpy.data.materials[model_name+' '+mat].node_tree.nodes['Principled BSDF'].inputs[1].default_value = self.sss
    return

bpy.types.Scene.sss = bpy.props.FloatProperty(default = default_sss,
                                                    min = 0.0,
                                                    max = 1.0,
                                                    name = "Subsurface Scattering",
                                                    description = "Set the subsurface scattering intensity",
                                                    update = sss_update)
bpy.context.scene.sss = StoredOptions[0]

def transluc_update(self, context):
    
    for mat in BodyPartsList:
        bpy.data.materials[model_name+' '+mat].node_tree.nodes["Translucency Hue Saturation Value"].inputs[2].default_value = self.transluc
    return

bpy.types.Scene.transluc = bpy.props.FloatProperty(default = default_transl,
                                                            min = 0.0,
                                                            max = 1.0,
                                                            name = "Translucency",
                                                            description = "Set the translucency effect intensity",
                                                            update = transluc_update)

def skinwet_update(self, context):
    
    if enable_skinwet and not enable_wet:
        for mat in BodyPartsList:
            for node in bpy.data.materials[model_name+' '+mat].node_tree.nodes:
                if node.name=='Wet':
                    node.outputs[0].default_value = self.skinwet
    elif enable_skinwet and enable_wet:
        for i in range(len(bpy.data.materials)):
            if bpy.data.materials[i].node_tree.nodes:
                for node in bpy.data.materials[i].node_tree.nodes:
                    if node.name=='Wet':
                        node.outputs[0].default_value = self.skinwet
    return

bpy.types.Scene.skinwet = bpy.props.FloatProperty(default = 0.0,
                                                            min = 0.0,
                                                            max = 1.0,
                                                            name = "Wet",
                                                            description = "Set the intensity of the wet effect",
                                                            update = skinwet_update)

def tan_update(self, context):
    
    for mat in BodyPartsList:
        bpy.data.materials[model_name+' '+mat].node_tree.nodes[model_name+' Tan'].outputs[0].default_value = self.tan
    return

bpy.types.Scene.tan = bpy.props.FloatProperty(default = 0.0,
                                                            min = 0.0,
                                                            max = 1.0,
                                                            name = "Tan",
                                                            description = "Set the intensity of the tan",
                                                            update = tan_update)

def tanlines_update(self, context):
    
    for mat in BodyPartsList:
        bpy.data.materials[model_name+' '+mat].node_tree.nodes[model_name+' Tan Lines'].outputs[0].default_value = self.tanlines
    return

bpy.types.Scene.tanlines = bpy.props.FloatProperty(default = 0.0,
                                                            min = 0.0,
                                                            max = 1.0,
                                                            name = "Tan Lines",
                                                            description = "Set the intensity of the tan lines",
                                                            update = tanlines_update)
                                                            
def blush_update(self, context):
    
    for mat in BodyPartsList:
        for node in bpy.data.materials[model_name+' '+mat].node_tree.nodes:
            if node.name=='Blush':
                node.outputs[0].default_value = self.blush
            
    return

bpy.types.Scene.blush = bpy.props.FloatProperty(default = 0.0,
                                                            min = 0.0,
                                                            max = 1.0,
                                                            name = "Blush",
                                                            description = "Set the intensity of the blush",
                                                            update = blush_update)

def makeup_update(self, context):
    
    for mat in BodyPartsList:
        for node in bpy.data.materials[model_name+' '+mat].node_tree.nodes:
            if node.name=='Makeup':
                node.outputs[0].default_value = self.makeup
                
    return

bpy.types.Scene.makeup = bpy.props.FloatProperty(default = 0.0,
                                                            min = 0.0,
                                                            max = 1.0,
                                                            name = "Makeup",
                                                            description = "Set the intensity of the makeup",
                                                            update = makeup_update)

def runny_makeup_update(self, context):
    
    for mat in BodyPartsList:
        for node in bpy.data.materials[model_name+' '+mat].node_tree.nodes:
            if node.name=='Runny Makeup':
                if self.runny_makeup==True:
                    node.outputs[0].default_value = 0.0
                else:
                    node.outputs[0].default_value = 1.0
                
    return

bpy.types.Scene.runny_makeup = bpy.props.BoolProperty(default = False,
                                                            name="Runny Makeup",
                                                            description="Enable/disable runny makeup. It works only if makeup intensity is not null",
                                                            update = runny_makeup_update)

def scratches_update(self, context):
    
    for mat in BodyPartsList:
        for node in bpy.data.materials[model_name+' '+mat].node_tree.nodes:
            if node.name=='Scratches':
                node.outputs[0].default_value = self.scratches
                
    return

bpy.types.Scene.scratches = bpy.props.FloatProperty(default = 0.0,
                                                            min = 0.0,
                                                            max = 1.0,
                                                            name = "Scratches",
                                                            description = "Set the intensity of the scratches",
                                                            update = scratches_update)

def skindirt_update(self, context):
    
    if enable_skindirt and not enable_dirt:
        for mat in BodyPartsList:
            for node in bpy.data.materials[model_name+' '+mat].node_tree.nodes:
                if node.name=='Dirt':
                    node.outputs[0].default_value = self.skindirt
    elif enable_skindirt and enable_dirt:
        for i in range(len(bpy.data.materials)):
            if bpy.data.materials[i].node_tree.nodes:
                for node in bpy.data.materials[i].node_tree.nodes:
                    if node.name=='Dirt':
                        node.outputs[0].default_value = self.skindirt
    return

bpy.types.Scene.skindirt = bpy.props.FloatProperty(default = 0.0,
                                                            min = 0.0,
                                                            max = 1.0,
                                                            name = "Dirt",
                                                            description = "Set the intensity of the dirt effects",
                                                            update = skindirt_update)

# ------------------------------------------------------------------------
#    Outfit Properties
# ------------------------------------------------------------------------

def outfit_text_update(self, context):
    
    for i in range(len(bpy.data.materials)):
        if MatWithTextSel[bpy.types.WindowManager.out_sel_ID] in bpy.data.materials[i].name:
            for j in range(len(bpy.data.materials[i].node_tree.nodes)):
                if "Main Texture Selector" in bpy.data.materials[i].node_tree.nodes[j].name:
                    bpy.data.materials[i].node_tree.nodes[j].inputs[9].default_value=self.outfit_text
    return

bpy.types.Scene.outfits = bpy.props.EnumProperty(name="",
                                                        description="Outfit selected",
                                                        items=OutCollListOptions)

def masks_out_update(self, context):
    
    current_outfit = bpy.context.scene.outfits
    
    if self.masks_out:
        
        if current_outfit=='Nude':
            for mask_obj in MaskList:
                for modifier in bpy.data.objects[mask_obj].modifiers:
                    for col in OutCollListAvail:
                        for obj in bpy.data.collections[model_name+' '+col].objects:
                            if modifier.type == "MASK" and col in modifier.name and obj.name in modifier.name and obj.outfit_lock == True:
                                modifier.show_viewport = True
                                modifier.show_render = True
        
        else:
            for mask_obj in MaskList:
                for modifier in bpy.data.objects[mask_obj].modifiers:
                    for obj in bpy.data.objects:
                        if modifier.type == "MASK" and self.outfits in modifier.name and obj.name in modifier.name and obj.hide_viewport==False:
                            modifier.show_viewport = True
                            modifier.show_render = True
                            break
                        elif modifier.type == "MASK" and obj.name in modifier.name and obj.outfit_lock == True and enable_masks == True:
                            modifier.show_viewport = True
                            modifier.show_render = True
                            break
                        elif modifier.type == "MASK" and obj.name not in modifier.name and self.outfits not in modifier.name:
                            modifier.show_viewport = False
                            modifier.show_render = False
        
    else:
        for mask_obj in MaskList:
            for modifier in bpy.data.objects[mask_obj].modifiers:
                if modifier.type == "MASK":
                    modifier.show_viewport = False
                    modifier.show_render = False
    return

bpy.types.Scene.masks_out = bpy.props.BoolProperty(default = True,
                                                            name="Masks",
                                                            description="Enable/disable the body masks. \nDisable it to increase the performance in viewport, and re-enable it before rendering. \nNote: some outfits might experience major clipping with the body if this is disabled. Therefore remember to re-enable it before rendering and for quick previews",
                                                            update = masks_out_update)

def outfits_update(self, context):
    
    enable_masks = bpy.context.scene.masks_out
    
    if self.outfits=='Nude':
        for col in OutCollListAvail:
            if col in LockCollList:
                for obj in bpy.data.collections[model_name+' '+col].objects:
                    if obj.outfit_lock:
                        obj.hide_viewport = False
                        obj.hide_render = False
                    else:
                        obj.hide_viewport = True
                        obj.hide_render = True
            else:
                bpy.data.collections[model_name+' '+col].hide_viewport = True
                bpy.data.collections[model_name+' '+col].hide_render = True
        
        for mask_obj in MaskList:
            for modifier in bpy.data.objects[mask_obj].modifiers:
                if modifier.type == "MASK":
                    modifier.show_viewport = False
                    modifier.show_render = False
            
                for col in OutCollListAvail:
                    for obj in bpy.data.collections[model_name+' '+col].objects:
                        if modifier.type == "MASK" and col in modifier.name and obj.name in modifier.name and obj.outfit_lock == True and enable_masks == True:
                            modifier.show_viewport = True
                            modifier.show_render = True
                
    else:
        for col in OutCollListAvail:
            if col in LockCollList and col!=self.outfits:
                for obj in bpy.data.collections[model_name+' '+col].objects:
                    if obj.outfit_lock:
                        obj.hide_viewport = False
                        obj.hide_render = False
                    else:
                        obj.hide_viewport = True
                        obj.hide_render = True
            else:
                bpy.data.collections[model_name+' '+col].hide_viewport = True
                bpy.data.collections[model_name+' '+col].hide_render = True
        
        bpy.data.collections[model_name+' '+self.outfits].hide_viewport = False
        bpy.data.collections[model_name+' '+self.outfits].hide_render = False
        for obj in bpy.data.collections[model_name+' '+self.outfits].objects:
            if obj.outfit:
                obj.hide_viewport = False
                obj.hide_render = False
            else:
                obj.hide_viewport = True
                obj.hide_render = True
        for mask_obj in MaskList:
            for modifier in bpy.data.objects[mask_obj].modifiers:
                for obj in bpy.data.objects:
                    if modifier.type == "MASK" and self.outfits in modifier.name and obj.name in modifier.name and obj.hide_viewport==False and enable_masks == True:
                        modifier.show_viewport = True
                        modifier.show_render = True
                        break
                    elif modifier.type == "MASK" and obj.name in modifier.name and obj.outfit_lock == True and enable_masks == True:
                        modifier.show_viewport = True
                        modifier.show_render = True
                        break
                    elif modifier.type == "MASK" and obj.name not in modifier.name and self.outfits not in modifier.name:
                        modifier.show_viewport = False
                        modifier.show_render = False
    
    if MatWithTextSel != []:
    
        for i in range(len(MatWithTextSel)):
            if MatWithTextSel[i]==self.outfits:
                bpy.types.WindowManager.out_sel_ID = i
                break
        
        bpy.types.Scene.outfit_text = bpy.props.IntProperty(default = 1,
                                                            min = 1,
                                                            max = MatWithTextSelCount[bpy.types.WindowManager.out_sel_ID],
                                                            name = "Color",
                                                            description = "Choose the color of the outfit",
                                                            update = outfit_text_update)
    return

bpy.types.Scene.outfits = bpy.props.EnumProperty(name="",
                                                        description="Outfit selected",
                                                        items=OutCollListOptions,
                                                        update = outfits_update)
                                                        
def outfit_show(self, context):
    
    enable_masks = bpy.context.scene.masks_out
    
    if self.outfit:# or self.outfit_lock:
        self.hide_viewport = False
        self.hide_render = False
        for mask_obj in MaskList:
            for modifier in bpy.data.objects[mask_obj].modifiers:
                if modifier.type == "MASK" and modifier.name == "Mask "+self.name and enable_masks == True:
                    modifier.show_viewport = True
                    modifier.show_render = True
    else:
        self.hide_viewport = True
        self.hide_render = True
        for mask_obj in MaskList:
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
    
    if model_name in self.name:
        coll = self.users_collection[0].name[len(model_name)+1:]
    
    wm = context.scene
    
    if self.outfit_lock:
        LockCollList.append(coll)
        self.hide_viewport = False
        self.hide_render = False
        self.outfit=True
    elif coll in LockCollList:
        LockCollList.remove(coll)
        if coll != wm.outfits:
            self.hide_viewport = True
            self.hide_render = True
            self.outfit=False
    
    return

bpy.types.Object.outfit_lock = bpy.props.BoolProperty(default = False,
                                                        name="",
                                                        description="Lock/unlock the outfit",
                                                        update = outfit_lock)

def smooth_corr_out_update(self, context):
    
    for col in OutCollListAvail:
        for obj in bpy.data.collections[model_name+' '+col].objects:
            for modifier in obj.modifiers:
                if modifier.type == "CORRECTIVE_SMOOTH":
                    if self.smooth_corr_out == True:
                        modifier.show_viewport = True
                        modifier.show_render = True
                    else:
                        modifier.show_viewport = False
                        modifier.show_render = False
                        
    return

bpy.types.Scene.smooth_corr_out = bpy.props.BoolProperty(default = True,
                                                            name="Smooth Correction",
                                                            description="Enable/disable the smooth correction for the outfits. \nDisable it to increase the performance in viewport, and re-enable it before rendering",
                                                            update = smooth_corr_out_update)

def shrink_out_update(self, context):
    
    for col in OutCollListAvail:
        for obj in bpy.data.collections[model_name+' '+col].objects:
            for modifier in obj.modifiers:
                if modifier.type == "SHRINKWRAP":
                    if self.shrink_out == True:
                        modifier.show_viewport = True
                        modifier.show_render = True
                    else:
                        modifier.show_viewport = False
                        modifier.show_render = False
                        
    return

bpy.types.Scene.shrink_out = bpy.props.BoolProperty(default = True,
                                                            name="Shrinkwrap",
                                                            description="Enable/disable the shrinkwrap modifier for the outfits. \nDisable it to increase the performance in viewport, and re-enable it before rendering. \nNote: some outfits might experience clipping with the body if this is disabled",
                                                            update = shrink_out_update)

# ------------------------------------------------------------------------
#    Hair Properties
# ------------------------------------------------------------------------

def hair_update(self, context):
    
    wm = context.scene
    
    for ob in HairObjListAvail:
        bpy.data.objects[model_name+' '+ob].hide_viewport = True
        bpy.data.objects[model_name+' '+ob].hide_render = True
        bpy.data.objects[model_name+' '+ob+' Armature'].hide_viewport = True
        bpy.data.objects[model_name+' '+ob+' Armature'].hide_render = True
    bpy.data.objects[model_name+' '+self.hair].hide_viewport = False
    bpy.data.objects[model_name+' '+self.hair].hide_render = False
    bpy.data.objects[model_name+' '+self.hair+' Armature'].hide_viewport = False
    bpy.data.objects[model_name+' '+self.hair+' Armature'].hide_render = False
    return

bpy.types.Scene.hair = bpy.props.EnumProperty(name="",
                                                        description="Hair selected",
                                                        items=HairObjListOptions,
                                                        update = hair_update)

# ------------------------------------------------------------------------
#    Optimization
# ------------------------------------------------------------------------

class Optimize_Button(bpy.types.Operator):
    """Optimize the model. Please read the documentation before using this tool"""
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
#    UI
# ------------------------------------------------------------------------

class MainPanel:
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MustardUI"
    #bl_options = {"DEFAULT_CLOSED"}

# TODO: make better disposition
# https://blender.stackexchange.com/questions/44061/is-there-a-blender-python-ui-code-to-draw-a-horizontal-line-or-vertical-space

class MUSTARDUI_PT_Model(MainPanel, bpy.types.Panel):
    bl_idname = "MUSTARDUI_PT_Model"
    bl_label = "Body Settings"

    def draw(self, context):
        layout = self.layout
        wm = context.scene
        
        layout.label(text="Body properties")
        
        if enable_sss:
            layout.prop(wm,"sss")
        if enable_transl:
            layout.prop(wm,"transluc")
        
        for modifier in bpy.data.objects[model_name+' Body'].modifiers:
            if modifier.type == "CORRECTIVE_SMOOTH" and enable_smoothcorr:
                layout.prop(wm,"smooth_corr")
                break
        for modifier in bpy.data.objects[model_name+' Body'].modifiers:
            if modifier.type == "SUBSURF" and enable_subdiv:
                
                row = layout.row(align=True)
                row.prop(wm,"subdiv_rend")
                row.scale_x=0.4
                row.prop(wm,"subdiv_rend_lv")
                
                row = layout.row(align=True)
                row.prop(wm,"subdiv_view")
                row.scale_x=0.4
                row.prop(wm,"subdiv_view_lv")
                
                break
            
        if enable_tan or enable_skinwet or enable_scratches or enable_dirt:
            layout.separator()
            layout.label(text="Skin properties")
            if enable_skinwet:
                layout.prop(wm,"skinwet")
            if enable_tan:
                layout.prop(wm,"tan")
                if enable_tanlines:
                    layout.prop(wm,"tanlines")
            if enable_scratches:
                layout.prop(wm,"scratches")
            if enable_skindirt:
                layout.prop(wm,"skindirt")
        
        if enable_blush or enable_makeup:
            layout.separator()
            layout.label(text="Face properties")
        if enable_blush:
            layout.prop(wm,"blush")
        if enable_makeup:
            layout.prop(wm,"makeup")
            if enable_runny_makeup:
                layout.prop(wm,"runny_makeup")


class MUSTARDUI_PT_Outfits(MainPanel, bpy.types.Panel):
    bl_idname = "MUSTARDUI_PT_Outfits"
    bl_label = "Outfits & Hair Settings"

    def draw(self, context):
        layout = self.layout
        wm = context.scene
        
        if len(OutCollListAvail) > 0:
            box = layout.box()
            box.label(text="Outfits list")
            box.prop(wm,"outfits")
            
            if wm.outfits in MatWithTextSel:
                box.prop(wm,"outfit_text")
            
            if wm.outfits!="Nude":
                OutfitListTemp = []
                for obj in bpy.data.collections[model_name+' '+wm.outfits].objects:
                    OutfitListTemp.append(obj.name)
                for obj_name in sorted(OutfitListTemp):
                    coll = obj.users_collection[0].name
                    row = box.row(align=True)
                    row.prop(bpy.data.objects[obj_name],"outfit",toggle=True, text=obj_name[len(model_name+' '+wm.outfits+' - '):], icon='OUTLINER_OB_'+bpy.data.objects[obj_name].type)
                    row.scale_x=1
                    if bpy.data.objects[obj_name].outfit_lock:
                        row.prop(bpy.data.objects[obj_name],"outfit_lock",toggle=True, icon='LOCKED')
                    else:
                        row.prop(bpy.data.objects[obj_name],"outfit_lock",toggle=True, icon='UNLOCKED')
            
            if LockCollList != []:
                OutfitListTemp = []
                box.separator()
                box.label(text="Locked objects:")
                for obj in bpy.data.objects:
                    if obj.outfit_lock:
                        OutfitListTemp.append(obj.name)
                for obj_name in sorted(OutfitListTemp):
                    row = box.row(align=True)
                    row.prop(bpy.data.objects[obj_name],"outfit",toggle=True, text=obj_name[len(model_name):], icon='OUTLINER_OB_'+bpy.data.objects[obj_name].type)
                    row.scale_x=1
                    row.prop(bpy.data.objects[obj_name],"outfit_lock",toggle=True, icon='LOCKED')
            
            if enable_smooth_corr_out or enable_shrink_out or enable_masks_out:
                box = layout.box()
                box.label(text="Outfits global properties")
                if enable_smooth_corr_out:
                    box.prop(wm,"smooth_corr_out")
                if enable_shrink_out:
                    box.prop(wm,"shrink_out")
                if enable_masks_out:
                    box.prop(wm,"masks_out")
                box.label(text="Read the descriptions before using these!",icon="ERROR")
        
            #if LockCollList != []:
            #    layout.operator('ops.clean_lock', text='Clean Locked')
        
        if len(HairObjListAvail) > 1:
            box = layout.box()
            box.label(text="Hair list and properties")
            box.prop(wm,"hair")
        
        if len(ExtrasObjListAvail) > 0:
            box = layout.box()
            box.label(text="Extras list")
            for obj_name in sorted(ExtrasObjListAvail):
                box.prop(bpy.data.objects[obj_name],"outfit",toggle=True, text=obj_name[len(model_name+' Extras - '):], icon='OUTLINER_OB_'+bpy.data.objects[obj_name].type)


class MUSTARDUI_PT_Links(MainPanel, bpy.types.Panel):
    bl_idname = "MUSTARDUI_PT_Links"
    bl_label = "Links"
    
    def draw(self, context):
        layout = self.layout
        
        if url_patreon!='':
            layout.operator('ops.open_link', text="Patreon").url = url_patreon
        if url_twitter!='':
            layout.operator('ops.open_link', text="Twitter").url = url_twitter
        if url_smutbase!='':
            layout.operator('ops.open_link', text="SmutBase").url = url_smutbase
        
        layout.separator()
        
        layout.operator('ops.open_link', text="MustardUI - Tutorial").url = url_MustardUItutorial
        layout.operator('ops.open_link', text="MustardUI - GitHub").url = url_MustardUI

      
class MUSTARDUI_PT_Info(MainPanel, bpy.types.Panel):
    bl_idname = "MUSTARDUI_PT_Informations"
    bl_label = "Maintenance"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        if optimization_tools:
            layout.label(text="Maintenance Tools")
            layout.operator('ops.optimize', text="Viewport Optimization").type = 1
            layout.label(icon='ERROR', text="Use at your own risk!")
            layout. separator()
        layout.label(text="Versions:")
        if model_version!='':
            layout.label(text="  - Model: " + model_version)
        layout.label(text="  - MustardUI: " + UI_version)
        if rig_tools_status is 1:
            layout. separator()
            layout.label(icon='ERROR',text="Debug: rig_tools not enabled!")
        elif rig_tools_status is 0:
            layout. separator()
            layout.label(icon='ERROR', text="Debug: rig_tools not installed!")


# ------------------------------------------------------------------------
#    Register
# ------------------------------------------------------------------------

classes = (
    Link_Button,
    Optimize_Button,
    MUSTARDUI_PT_Model,
    MUSTARDUI_PT_Outfits, 
    MUSTARDUI_PT_Links,
    MUSTARDUI_PT_Info
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

if __name__ == "__main__":
    register()
