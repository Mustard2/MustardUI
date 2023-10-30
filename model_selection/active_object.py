import bpy
#from ..settings.addon import *


# Function to decide the active object for showing properties in the UI
def mustardui_active_object(context, config=0):
    settings = bpy.context.scene.MustardUI_Settings

    # If Viewport Model Selection is enabled, the active object will be the active object
    # only if it is an armature
    if settings.viewport_model_selection:

        if context.active_object is None:
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
