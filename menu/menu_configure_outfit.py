import bpy
from . import MainPanel
from ..model_selection.active_object import *
from ..warnings.ops_fix_old_UI import check_old_UI
from .. import __package__ as base_package


class PANEL_PT_MustardUI_InitPanel_Outfit(MainPanel, bpy.types.Panel):
    bl_label = "Outfit"
    bl_parent_id = "PANEL_PT_MustardUI_InitPanel"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        if check_old_UI():
            return False

        res, arm = mustardui_active_object(context, config=1)
        addon_prefs = context.preferences.addons[base_package].preferences
        return res and addon_prefs.developer

    def draw_header(self, context):
        layout = self.layout
        layout.label(text="", icon="MOD_CLOTH")

    def draw(self, context):

        layout = self.layout
        scene = context.scene

        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings

        box = layout.box()
        box.label(text="General Settings", icon="MODIFIER")
        col = box.column(align=True)
        col.prop(rig_settings, "outfit_nude")
        col.prop(rig_settings, "outfit_physics_support", text="Physics Support")
        col.prop(rig_settings, "outfit_config_subcollections")

        box = layout.box()
        box.label(text="Optimization Settings", icon="FORCE_WIND")
        col = box.column(align=True)
        col.prop(rig_settings, "outfit_switch_armature_disable")
        col.prop(rig_settings, "outfit_switch_modifiers_disable")
        col.prop(rig_settings, "outfit_switch_shape_keys_disable")
        col.prop(rig_settings, "outfits_update_tag_on_switch")

        if len([x for x in rig_settings.outfits_collections if x.collection is not None]) > 0:
            box = layout.box()
            row = box.row()
            row.label(text="Outfits List", icon="OUTLINER_COLLECTION")
            row.operator("Mustardui.outfits_smartcheck", text="", icon="SHADERFX")

            # Outfits list panel
            box = box.box()
            row = box.row()
            row.template_list("MUSTARDUI_UL_Outfits_UIList", "The_List", rig_settings,
                              "outfits_collections", scene,
                              "mustardui_outfits_uilist_index")
            col = row.column()
            col2 = col.column(align=True)
            opup = col2.operator('mustardui.outfits_switch', icon="TRIA_UP", text="")
            opup.direction = "UP"
            opdown = col2.operator('mustardui.outfits_switch', icon="TRIA_DOWN", text="")
            opdown.direction = "DOWN"
            col.separator()
            col.operator("mustardui.rename_outfit", text="", icon="GREASEPENCIL").right_click_call = False
            col.operator("mustardui.remove_outfit", text="", icon="X").is_config = True
            col.operator("mustardui.delete_outfit", text="", icon="TRASH").is_config = True

            # Outfit properties
            box = layout.box()
            box.label(text="Global properties", icon="MODIFIER")
            col = box.column(align=True)
            col.prop(rig_settings, "outfits_enable_global_subsurface")
            col.prop(rig_settings, "outfits_enable_global_smoothcorrection")
            col.prop(rig_settings, "outfits_enable_global_shrinkwrap")
            col.prop(rig_settings, "outfits_enable_global_surfacedeform")
            col.prop(rig_settings, "outfits_enable_global_mask")
            col.prop(rig_settings, "outfits_enable_global_solidify")
            col.prop(rig_settings, "outfits_enable_global_triangulate")
            col.prop(rig_settings, "outfits_enable_global_normalautosmooth")

            # Custom properties
            box = layout.box()
            row = box.row()
            row.label(text="Custom properties", icon="PRESET_NEW")

            if len(arm.MustardUI_CustomPropertiesOutfit) > 0:
                row = box.row()
                row.template_list("MUSTARDUI_UL_Property_UIListOutfits", "The_List", arm,
                                  "MustardUI_CustomPropertiesOutfit", scene,
                                  "mustardui_property_uilist_outfits_index")
                col = row.column()
                col.operator('mustardui.property_settings', icon="PREFERENCES", text="").type = "OUTFIT"
                col.separator()
                col2 = col.column(align=True)
                opup = col2.operator('mustardui.property_switch', icon="TRIA_UP", text="")
                opup.direction = "UP"
                opup.type = "OUTFIT"
                opdown = col2.operator('mustardui.property_switch', icon="TRIA_DOWN", text="")
                opdown.direction = "DOWN"
                opdown.type = "OUTFIT"
                col.separator()
                col.operator('mustardui.property_remove', icon="X", text="").type = "OUTFIT"

                col = box.column(align=True)
                col.prop(rig_settings, 'outfit_custom_properties_icons')
                col.prop(rig_settings, 'outfit_custom_properties_name_order')

            else:
                box = box.box()
                box.label(text="No property added yet", icon="ERROR")

        else:
            box = layout.box()
            box.label(text="No Outfits added yet.", icon="ERROR")

        box = layout.box()

        # Extras list
        box.label(text="Extras", icon="PLUS")
        box.prop(rig_settings, "extras_collection", text="")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_InitPanel_Outfit)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_InitPanel_Outfit)
