import bpy
from ..model_selection.active_object import *


class MustardUI_Outfit_SmartCheck(bpy.types.Operator):
    """Search for Outfits"""
    bl_idname = "mustardui.outfits_smartcheck"
    bl_label = "Outfit Smart Search."
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):

        res, arm = mustardui_active_object(context, config=1)

        if arm is not None:
            rig_settings = arm.MustardUI_RigSettings
            return rig_settings.model_MustardUI_naming_convention and rig_settings.model_body is not None and rig_settings.model_name != ""
        else:
            return False

    def execute(self, context):

        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings
        addon_prefs = context.preferences.addons["MustardUI"].preferences

        # Search for oufit collections
        if addon_prefs.debug:
            print('\nMustardUI - Smart Check - Searching for outfits\n')

        outfits_collections = [x for x in bpy.data.collections if
                               (rig_settings.model_name in x.name) and (not 'Hair' in x.name) and (
                                   not 'Extras' in x.name) and (not 'Physics' in x.name) and (
                                   not rig_settings.model_name == x.name) and (not '_' in x.name)]

        for collection in outfits_collections:

            add_collection = True
            for el in rig_settings.outfits_collections:
                if el.collection == collection:
                    add_collection = False
                    break

            if addon_prefs.debug:
                print('MustardUI - Smart Check - ' + collection.name + ' added: ' + str(add_collection))

            if add_collection:
                add_item = rig_settings.outfits_collections.add()
                add_item.collection = collection

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_Outfit_SmartCheck)


def unregister():
    bpy.utils.unregister_class(MustardUI_Outfit_SmartCheck)
