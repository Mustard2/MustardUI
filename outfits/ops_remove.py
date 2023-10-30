import bpy
from ..custom_properties.misc import mustardui_clean_prop
from ..model_selection.active_object import *


class MustardUI_RemoveOutfit(bpy.types.Operator):
    """Remove the selected Outfit from the UI.\nThe collection is not deleted"""
    bl_idname = "mustardui.remove_outfit"
    bl_label = "Remove Outfit Collection"
    bl_options = {'UNDO'}

    col: bpy.props.StringProperty()

    def execute(self, context):

        settings = bpy.context.scene.MustardUI_Settings
        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings

        # Remove the custom properties
        outfit_cp = arm.MustardUI_CustomPropertiesOutfit

        to_remove = []
        for i, cp in enumerate(outfit_cp):
            if cp.outfit.name == self.col:
                mustardui_clean_prop(arm, outfit_cp, i, settings)
                to_remove.append(i)
        for i in reversed(to_remove):
            outfit_cp.remove(i)

        # Remove the collection from the Outfits Collections
        for i, el in enumerate(rig_settings.outfits_collections):
            if el.collection is not None:
                if el.collection.name == self.col:
                    rig_settings.outfits_collections.remove(i)
                    break

        if rig_settings.outfit_nude:
            rig_settings.outfits_list = "Nude"
        else:
            if len(rig_settings.outfits_list_make(context)) > 0:
                rig_settings.outfits_list = rig_settings.outfits_list_make(context)[0][0]

        self.report({'INFO'}, 'MustardUI - Outfit removed.')

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_RemoveOutfit)


def unregister():
    bpy.utils.unregister_class(MustardUI_RemoveOutfit)
