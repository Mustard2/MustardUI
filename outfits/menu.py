import bpy
from .ops_add import MustardUI_AddOutfit
from ..model_selection.active_object import *
from .. import __package__ as base_package


class OUTLINER_MT_collection(bpy.types.Menu):
    bl_label = "Custom Action Collection"

    def draw(self, context):
        pass


def mustardui_collection_menu(self, context):

    res, arm = mustardui_active_object(context, config=1)
    rig_settings = arm.MustardUI_RigSettings
    addon_prefs = context.preferences.addons[base_package].preferences

    if res:
        if not context.collection in [x.collection for x in rig_settings.outfits_collections]:
            self.layout.separator()
            if addon_prefs.debug:
                self.layout.operator(MustardUI_AddOutfit.bl_idname, text="Add Outfit: " + repr(context.collection.name),
                                     icon="ADD")
            else:
                self.layout.operator(MustardUI_AddOutfit.bl_idname, icon="ADD")


def register():
    bpy.types.OUTLINER_MT_collection.append(mustardui_collection_menu)


def unregister():
    bpy.types.OUTLINER_MT_collection.remove(mustardui_collection_menu)
