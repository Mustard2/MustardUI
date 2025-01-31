import bpy
from . import MainPanel
from ..model_selection.active_object import *
from ..warnings.ops_fix_old_UI import check_old_UI
from .. import __package__ as base_package
from .menu_configure import row_scale


class PANEL_PT_MustardUI_InitPanel_Hair(MainPanel, bpy.types.Panel):
    bl_label = "Hair"
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
        layout.label(text="", icon="OUTLINER_OB_CURVES")

    def draw(self, context):

        layout = self.layout
        scene = context.scene

        settings = bpy.context.scene.MustardUI_Settings
        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings

        box = layout.box()
        box.label(text="Hair Collection", icon="OUTLINER_COLLECTION")
        box.prop(rig_settings, "hair_collection", text="")

        if rig_settings.hair_collection is not None:
            if len(rig_settings.hair_collection.objects) > 0:

                if settings.advanced:
                    box = layout.box()
                    box.label(text="General Settings", icon="MODIFIER")
                    col = box.column(align=True)
                    col.prop(rig_settings, "hair_switch_armature_disable")
                    col.prop(rig_settings, "hair_update_tag_on_switch")

                # Global properties
                box = layout.box()
                box.label(text="Global properties", icon="MODIFIER")
                col = box.column(align=True)
                col.prop(rig_settings, "hair_enable_global_subsurface")
                col.prop(rig_settings, "hair_enable_global_smoothcorrection")
                col.prop(rig_settings, "hair_enable_global_solidify")
                col.prop(rig_settings, "hair_enable_global_particles")
                col.prop(rig_settings, "hair_enable_global_normalautosmooth")

                # Custom properties
                box = layout.box()
                row = box.row()
                row.label(text="Custom properties", icon="PRESET_NEW")

                if len(arm.MustardUI_CustomPropertiesHair) > 0:
                    row = box.row()
                    row.template_list("MUSTARDUI_UL_Property_UIListHair", "The_List", arm,
                                      "MustardUI_CustomPropertiesHair", scene,
                                      "mustardui_property_uilist_hair_index")
                    col = row.column()
                    col.operator('mustardui.property_settings', icon="PREFERENCES", text="").type = "HAIR"
                    col.separator()
                    col2 = col.column(align=True)
                    opup = col2.operator('mustardui.property_switch', icon="TRIA_UP", text="")
                    opup.direction = "UP"
                    opup.type = "HAIR"
                    opdown = col2.operator('mustardui.property_switch', icon="TRIA_DOWN", text="")
                    opdown.direction = "DOWN"
                    opdown.type = "HAIR"
                    col.separator()
                    col.operator('mustardui.property_remove', icon="X", text="").type = "HAIR"

                    col = box.column(align=True)
                    col.prop(rig_settings, 'hair_custom_properties_icons')
                    col.prop(rig_settings, 'hair_custom_properties_name_order')

                else:
                    box = box.box()
                    box.label(text="No property added yet", icon="ERROR")
            else:
                box = layout.box()
                box.label(text="No Hair Objects in the collection.", icon="ERROR")

        box = layout.box()
        box.label(text="Other Hair", icon="OUTLINER_OB_CURVES")
        col = box.column()
        col.prop(rig_settings, "curves_hair_enable", text="Show Curves Hair")
        col.prop(rig_settings, "particle_systems_enable", text="Show Particle Systems")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_InitPanel_Hair)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_InitPanel_Hair)
