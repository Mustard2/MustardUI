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
model_name = 'Honoka'

# Model version
model_version = '2 - 06/02/2020'

# List of the body materials
BodyPartsList = ['Torso','Neck','Face']

# List of outfits to be imported by the UI
OutCollList = ['Ninja','Deluxe','Bikini','Shinovi Master Swimsuit','School','SciFi','Hip Hop']

# List of hair to be imported by the UI
# If there is only one hair_style in the list, the hair selection interface will be hidden by default
HairObjList = ['Hair']

# Choose which options to show on the UI
enable_smoothcorr = True
enable_sss = True
enable_transl = True
enable_tan = True
enable_tanlines = True

# List of the links which will be shown in the Link tab
url_patreon = "https://www.patreon.com/mustardsfm"
url_twitter = "https://twitter.com/MustardSFM"
url_smutbase = "https://smutba.se/user/10157/"

# ------------------------------------------------------------------------
#    Internal Definitions (do not change them)
# ------------------------------------------------------------------------

# UI version
UI_version = '0.1.2 - 07/02/2020'

OutCollListAvail = []
OutCollListOptions = [("Nude","Nude","Nude")]
MatWithTextSel = []
MatWithTextSelCount = []

HairObjListAvail = []
HairObjListOptions = []

bpy.types.WindowManager.out_sel_ID = 0

# ------------------------------------------------------------------------
#    Preliminary operations definitions
# ------------------------------------------------------------------------

def addon_check():
    addon_name = "auto_rig_pro-master"
    addon_name2 = "rig_tools"
    
    rig_tools_status = 0
    
    addon_utils.modules_refresh()
    
    if (addon_name or addon_name2) not in addon_utils.addons_fake_modules:
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

def po_check_collections():
    
    OutCollListName = [];
    
    for i in range(len(OutCollList)):
        OutCollListName.append(model_name+' '+OutCollList[i])

    for collection in bpy.data.collections:
        if collection.name in OutCollListName:
            OutCollListAvail.append(collection.name[len(model_name)+1:])
            data=(collection.name[len(model_name)+1:]),(collection.name[len(model_name)+1:]),"Outfit "+(collection.name[len(model_name)+1:])
            OutCollListOptions.append(data)
    
    for i in range(len(bpy.data.materials)):
        bpy.data.materials[i].use_nodes=True
        for j in range(len(bpy.data.materials[i].node_tree.nodes)):
            if "Texture Selector" in bpy.data.materials[i].node_tree.nodes[j].name:
                for n in OutCollListAvail:
                    if n in bpy.data.materials[i].name[len(model_name)+1:]:
                        MatWithTextSel.append(n)
                for k in range(9):
                    k=k+1
                    if not bpy.data.materials[i].node_tree.nodes[j].inputs[k].links:
                        MatWithTextSelCount.append(k)
                        break
                break
        
def po_check_hair():
    
    HairObjListName = [];
    
    for i in range(len(HairObjList)):
        HairObjListName.append(model_name+' '+HairObjList[i])

    for collection in bpy.data.collections:
            for obj in collection.all_objects:
                data=(obj.name[len(model_name)+1:]),(obj.name[len(model_name)+1:]),(obj.name[len(model_name)+1:])
                if obj.name in HairObjListName and data not in HairObjListOptions:
                    HairObjListAvail.append(obj.name[len(model_name)+1:])
                    HairObjListOptions.append(data)

# ------------------------------------------------------------------------
#    Preliminary operations run
# ------------------------------------------------------------------------

po_check_collections()
po_check_hair()
rig_tools_status = addon_check()

# ------------------------------------------------------------------------
#    Model Properties
# ------------------------------------------------------------------------

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

bpy.types.WindowManager.smooth_corr = bpy.props.BoolProperty(default = True,
                                                            name="Smooth Correction",
                                                            description="Enable/disable the smooth correction",
                                                            update = smooth_corr_update)

def sss_update(self, context):
    
    for mat in BodyPartsList:
        bpy.data.materials[model_name+' '+mat].node_tree.nodes['Principled BSDF'].inputs[1].default_value = self.sss
    return

bpy.types.WindowManager.sss = bpy.props.FloatProperty(default = 0.084,
                                                    min = 0.0,
                                                    max = 1.0,
                                                    name = "Subsurface Scattering",
                                                    description = "Set the subsurface scattering intensity",
                                                    update = sss_update)

def transluc_update(self, context):
    
    for mat in BodyPartsList:
        bpy.data.materials[model_name+' '+mat].node_tree.nodes["Translucency Hue Saturation Value"].inputs[2].default_value = self.transluc
    return

bpy.types.WindowManager.transluc = bpy.props.FloatProperty(default = 0.4,
                                                            min = 0.0,
                                                            max = 1.0,
                                                            name = "Translucency",
                                                            description = "Set the translucency effect intensity",
                                                            update = transluc_update)

def tan_update(self, context):
    
    for mat in BodyPartsList:
        bpy.data.materials[model_name+' '+mat].node_tree.nodes[model_name+' Tan'].outputs[0].default_value = self.tan
    return

bpy.types.WindowManager.tan = bpy.props.FloatProperty(default = 0.0,
                                                            min = 0.0,
                                                            max = 1.0,
                                                            name = "Tan",
                                                            description = "Set the intensity of the tan",
                                                            update = tan_update)

def tanlines_update(self, context):
    
    for mat in BodyPartsList:
        bpy.data.materials[model_name+' '+mat].node_tree.nodes[model_name+' Tan Lines'].outputs[0].default_value = self.tanlines
    return

bpy.types.WindowManager.tanlines = bpy.props.FloatProperty(default = 0.0,
                                                            min = 0.0,
                                                            max = 1.0,
                                                            name = "Tan Lines",
                                                            description = "Set the intensity of the tan lines",
                                                            update = tanlines_update)
# ------------------------------------------------------------------------
#    Outfit Properties
# ------------------------------------------------------------------------

def outfit_text_update(self, context):
    
    for i in range(len(bpy.data.materials)):
        if MatWithTextSel[bpy.types.WindowManager.out_sel_ID] in bpy.data.materials[i].name:
            for j in range(len(bpy.data.materials[i].node_tree.nodes)):
                if "Texture Selector" in bpy.data.materials[i].node_tree.nodes[j].name:
                    bpy.data.materials[i].node_tree.nodes[j].inputs[9].default_value=self.outfit_text
    return

def outfits_update(self, context):
    
    if self.outfits=='Nude':
        for col in OutCollListAvail:
            bpy.data.collections[model_name+' '+col].hide_viewport = True
            bpy.data.collections[model_name+' '+col].hide_render = True
    else:
        for col in OutCollListAvail:
            bpy.data.collections[model_name+' '+col].hide_viewport = True
            bpy.data.collections[model_name+' '+col].hide_render = True
        bpy.data.collections[model_name+' '+self.outfits].hide_viewport = False
        bpy.data.collections[model_name+' '+self.outfits].hide_render = False
        
        for modifier in bpy.data.objects[model_name+' Body'].modifiers:
            for obj in bpy.data.collections[model_name+' '+self.outfits].all_objects:
                if modifier.type == "MASK" and obj.name in modifier.name and obj.name.hide_viewport==False:
                    modifier.show_viewport = True
                    modifier.show_render = True
                    break
                elif modifier.type == "MASK" and obj.name not in modifier.name:
                    modifier.show_viewport = False
                    modifier.show_render = False
        
    for i in range(len(MatWithTextSel)):
        if MatWithTextSel[i]==self.outfits:
            bpy.types.WindowManager.out_sel_ID = i
            break
    
    bpy.types.WindowManager.outfit_text = bpy.props.IntProperty(default = 1,
                                                            min = 1,
                                                            max = MatWithTextSelCount[bpy.types.WindowManager.out_sel_ID],
                                                            name = "Color",
                                                            description = "Choose the color of the outfit",
                                                            update = outfit_text_update)
    return

bpy.types.WindowManager.outfits = bpy.props.EnumProperty(name="",
                                                        description="Outfit selected",
                                                        items=OutCollListOptions,
                                                        update = outfits_update)
                                                        
def outfit_show(self, context):
    
    if self.outfit:
        self.hide_viewport = False
        self.hide_render = False
        for modifier in bpy.data.objects[model_name+' Body'].modifiers:
            if modifier.type == "MASK" and modifier.name == "Mask "+self.name:
                modifier.show_viewport = True
                modifier.show_render = True
    else:
        self.hide_viewport = True
        self.hide_render = True
        for modifier in bpy.data.objects[model_name+' Body'].modifiers:
            if modifier.type == "MASK" and modifier.name == "Mask "+self.name:
                modifier.show_viewport = False
                modifier.show_render = False
    return

bpy.types.Object.outfit = bpy.props.BoolProperty(default = True,
                                                        name="",
                                                        description="",
                                                        update = outfit_show)

# ------------------------------------------------------------------------
#    Hair Properties
# ------------------------------------------------------------------------

def hair_update(self, context):
    
    wm = context.window_manager
    
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

bpy.types.WindowManager.hair = bpy.props.EnumProperty(name="",
                                                        description="Hair selected",
                                                        items=HairObjListOptions,
                                                        update = hair_update)

# ------------------------------------------------------------------------
#    Link (thanks to Mets3D)
# ------------------------------------------------------------------------

class Link_Button(bpy.types.Operator):
    """Open links in a web browser."""
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
    bl_options = {"DEFAULT_CLOSED"}


class MUSTARDUI_PT_Model(MainPanel, bpy.types.Panel):
    bl_idname = "MUSTARDUI_PT_Model"
    bl_label = "Model Settings"

    def draw(self, context):
        layout = self.layout
        wm = context.window_manager
        
        if enable_sss:
            layout.prop(wm,"sss")
        if enable_transl:
            layout.prop(wm,"transluc")
        
        for modifier in bpy.data.objects[model_name+' Body'].modifiers:
            if modifier.type == "CORRECTIVE_SMOOTH" and enable_smoothcorr:
                layout.prop(wm,"smooth_corr")
                break
        
        layout.separator()
        if enable_tan:
            layout.prop(wm,"tan")
        if enable_tanlines:
            layout.prop(wm,"tanlines")


class MUSTARDUI_PT_Outfits(MainPanel, bpy.types.Panel):
    bl_idname = "MUSTARDUI_PT_Outfits"
    bl_label = "Outfits & Hair"

    def draw(self, context):
        layout = self.layout
        wm = context.window_manager
        
        layout.label(text="Choose the outfit to enable.")
        layout.prop(wm,"outfits")
        
        if wm.outfits in MatWithTextSel:
            layout.prop(wm,"outfit_text")
        
        if wm.outfits!="Nude":
            OutfitListTemp = []
            for obj in bpy.data.collections[model_name+' '+wm.outfits].all_objects:
                OutfitListTemp.append(obj.name)
            for obj_name in sorted(OutfitListTemp):
                layout.prop(bpy.data.objects[obj_name],"outfit",toggle=True, text=obj_name[len(model_name+' '+wm.outfits+' - '):], icon='OUTLINER_OB_'+bpy.data.objects[obj_name].type)
        
        layout.separator()
        
        if len(HairObjListAvail) > 1:
            layout.label(text="Choose the hair style to enable.")
            layout.prop(wm,"hair")


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

      
class MUSTARDUI_PT_Info(MainPanel, bpy.types.Panel):
    bl_idname = "MUSTARDUI_PT_Informations"
    bl_label = "Informations"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        if model_version!='':
            layout.label(text="Model version: "+model_version)
        layout.label(text="UI version: "+UI_version)
        if rig_tools_status is 1:
            layout.label(icon='ERROR',text="Debug: rig_tools not enabled!")
        elif rig_tools_status is 0:
            layout.label(icon='ERROR', text="Debug: rig_tools not installed!")


# ------------------------------------------------------------------------
#    Register
# ------------------------------------------------------------------------

classes = (
    Link_Button,
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
