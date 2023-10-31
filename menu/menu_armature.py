import bpy
from . import MainPanel
from ..model_selection.active_object import *
from ..settings.rig import *


class PANEL_PT_MustardUI_Armature(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Armature"
    bl_label = "Armature"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):

        res, obj = mustardui_active_object(context, config=0)

        if obj is not None:
            rig_settings = obj.MustardUI_RigSettings
            armature_settings = obj.MustardUI_ArmatureSettings
            bcolls = obj.collections

            if len(bcolls) < 1:
                return False

            enabled_colls = [x for x in obj.collections if x.MustardUI_ArmatureBoneCollection.is_in_UI]

            if rig_settings.hair_collection is not None:
                return res and (len(enabled_colls) > 0 or (len([x for x in rig_settings.hair_collection.objects if
                                                                 x.type == "ARMATURE"]) > 1 and armature_settings.enable_automatic_hair))
            else:
                return res and len(enabled_colls) > 0
        else:
            return res

    def draw(self, context):

        settings = bpy.context.scene.MustardUI_Settings
        poll, obj = mustardui_active_object(context, config=0)
        armature_settings = obj.MustardUI_ArmatureSettings
        rig_settings = obj.MustardUI_RigSettings

        box = self.layout

        draw_separator = False
        if rig_settings.hair_collection is not None and armature_settings.enable_automatic_hair:
            if len([x for x in rig_settings.hair_collection.objects if x.type == "ARMATURE"]) > 0:
                box.prop(armature_settings, "hair", toggle=True, icon="CURVES")
                draw_separator = True

        if len(rig_settings.outfits_list) > 0:
            if len([x for x in obj.collections if x.MustardUI_ArmatureBoneCollection.outfit_switcher_enable]):
                box.prop(armature_settings, "outfits", toggle=True, icon="MOD_CLOTH")
                draw_separator = True

        if draw_separator:
            box.separator()

        enabled_colls = [x for x in obj.collections if x.MustardUI_ArmatureBoneCollection.is_in_UI]

        for bcoll in enabled_colls:
            bcoll_settings = bcoll.MustardUI_ArmatureBoneCollection
            if (bcoll_settings.advanced and settings.advanced) or not bcoll_settings.advanced:
                row = box.row()
                row.prop(bcoll, "is_visible", text=bcoll.name, toggle=True)

        # settings = bpy.context.scene.MustardUI_Settings
        # poll, obj = mustardui_active_object(context, config=0)
        # rig_settings = obj.MustardUI_RigSettings
        # armature_settings = obj.MustardUI_ArmatureSettings
        #
        # box = self.layout
        #
        # draw_separator = False
        # if rig_settings.hair_collection is not None and armature_settings.enable_automatic_hair:
        #     if len([x for x in rig_settings.hair_collection.objects if x.type == "ARMATURE"]) > 0:
        #         box.prop(armature_settings, "hair", toggle=True, icon="CURVES")
        #         draw_separator = True
        #
        # if len(rig_settings.outfits_list) > 0:
        #     if len([x for x in armature_settings.layers if (
        #             x.outfit_switcher_enable and x.outfit_switcher_collection == bpy.data.collections[
        #                 rig_settings.outfits_list] if rig_settings.outfits_list != "Nude" else True)]):
        #         box.prop(armature_settings, "outfits", toggle=True, icon="MOD_CLOTH")
        #         draw_separator = True
        #
        # if draw_separator:
        #     box.separator()
        #
        # enabled_layers = [x for x in range(0, 32) if
        #                   armature_settings.config_layer[x] and not armature_settings.layers[x].outfit_switcher_enable]
        # if len(enabled_layers) > 0:
        #     for i in sorted([x for x in range(0, 32) if
        #                      armature_settings.config_layer[x] and not armature_settings.layers[
        #                          x].outfit_switcher_enable], key=lambda x: armature_settings.layers[x].id):
        #         if (armature_settings.layers[i].advanced and settings.advanced) or not armature_settings.layers[i].advanced:
        #             if armature_settings.layers[i].mirror and armature_settings.layers[i].mirror_left:
        #                 row = box.row()
        #                 row.prop(armature_settings.layers[i], "show", text=armature_settings.layers[i].name,
        #                          toggle=True)
        #                 row.prop(armature_settings.layers[armature_settings.layers[i].mirror_layer], "show",
        #                          text=armature_settings.layers[armature_settings.layers[i].mirror_layer].name,
        #                          toggle=True)
        #             elif not armature_settings.layers[i].mirror:
        #                 row = box.row()
        #                 row.prop(armature_settings.layers[i], "show", text=armature_settings.layers[i].name,
        #                          toggle=True)


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_Armature)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Armature)
