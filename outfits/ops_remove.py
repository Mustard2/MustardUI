import bpy
from ..custom_properties.misc import mustardui_clean_prop, mustardui_reassign_default
from ..model_selection.active_object import *
from .. import __package__ as base_package


class MustardUI_RemoveOutfit(bpy.types.Operator):
    """Remove the selected Outfit from the UI.\nThe collection is not deleted"""
    bl_idname = "mustardui.remove_outfit"
    bl_label = "Remove Outfit Collection"
    bl_options = {'UNDO'}

    is_config: bpy.props.BoolProperty(default=True)

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings
        addon_prefs = context.preferences.addons[base_package].preferences

        uilist = rig_settings.outfits_collections

        if not self.is_config:
            col = bpy.data.collections[rig_settings.outfits_list]

            # Find the id to remove the Outfit from the outfit list
            outfit_id = -1
            for id, outfit in enumerate(rig_settings.outfits_collections):
                if col == outfit.collection:
                    outfit_id = id
                    break

            context.scene.mustardui_outfits_uilist_index = outfit_id

        index = context.scene.mustardui_outfits_uilist_index

        if index < 0:
            self.report({'INFO'}, 'MustardUI - The Outfit to remove was not found.')
            return {'FINISHED'}

        if len(uilist) <= index:
            return {'FINISHED'}

        # Remove the custom properties
        outfit_cp = arm.MustardUI_CustomPropertiesOutfit

        to_remove = []

        # FIXME: Even this is disabled things works as expected, and I think this should not be used,
        # because there is no way you can predict the default value for everything, and reverting it
        # to that 'default' value may cause things to reset, ie: the thing we try to fix!!!

        # Firstly set the custom property to their default value
        # for i, cp in enumerate(outfit_cp):
        #     if (not uilist[index].collection and not cp.outfit) or (uilist[index].collection and cp.outfit.name == uilist[index].collection.name):
        #         mustardui_reassign_default(arm, outfit_cp, i, addon_prefs)

        # Update everything
        if rig_settings.model_armature_object:
            rig_settings.model_armature_object.update_tag()
        bpy.context.view_layer.update()

        # And then delete data
        for i, cp in enumerate(outfit_cp):
            if (not uilist[index].collection and not cp.outfit) or (
                    uilist[index].collection and cp.outfit.name == uilist[index].collection.name):
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
