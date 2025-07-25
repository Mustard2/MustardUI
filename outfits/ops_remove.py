import bpy
from ..custom_properties.misc import mustardui_clean_prop
from ..model_selection.active_object import *
from .. import __package__ as base_package


class MustardUI_RemoveOutfit(bpy.types.Operator):
    """Remove the selected Outfit from the UI.\nThe collection is not deleted"""
    bl_idname = "mustardui.remove_outfit"
    bl_label = "Remove Outfit Collection"
    bl_options = {'UNDO'}

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings
        addon_prefs = context.preferences.addons[base_package].preferences

        uilist = rig_settings.outfits_collections
        index = context.scene.mustardui_outfits_uilist_index

        if len(uilist) <= index:
            return {'FINISHED'}

        # Remove the custom properties
        outfit_cp = arm.MustardUI_CustomPropertiesOutfit

        to_remove = []
        for i, cp in enumerate(outfit_cp):
            if (not uilist[index].collection and not cp.outfit) or (uilist[index].collection and cp.outfit.name == uilist[index].collection.name):
                mustardui_clean_prop(arm, outfit_cp, i, addon_prefs)
                to_remove.append(i)
        for i in reversed(to_remove):
            outfit_cp.remove(i)

        # Remove the collection from the Outfits Collections
        uilist.remove(index)

        if rig_settings.outfit_nude:
            rig_settings.outfits_list = "Nude"
        else:
            if len(rig_settings.outfits_list_make(context)) > 0:
                rig_settings.outfits_list = rig_settings.outfits_list_make(context)[0][0]

        index = min(max(0, index - 1), len(uilist) - 1)
        context.scene.mustardui_outfits_uilist_index = index

        arm.update_tag()

        self.report({'INFO'}, 'MustardUI - Outfit removed.')

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_RemoveOutfit)


def unregister():
    bpy.utils.unregister_class(MustardUI_RemoveOutfit)
