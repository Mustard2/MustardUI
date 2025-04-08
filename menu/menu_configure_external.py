import bpy
from . import MainPanel
from ..model_selection.active_object import *
from ..warnings.ops_fix_old_UI import check_old_UI
from .. import __package__ as base_package
from .menu_configure import row_scale
from ..morphs.misc import DazCheckVersion


class PANEL_PT_MustardUI_InitPanel_External(MainPanel, bpy.types.Panel):
    bl_label = "Morphs (Diffeomorphic)"
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
        layout.label(text="", icon="EXPORT")

    def draw(self, context):

        layout = self.layout

        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings
        addon_prefs = context.preferences.addons[base_package].preferences

        box = layout.box()
        box.label(text="General", icon="MODIFIER")
        row = box.row()
        row.prop(rig_settings, "diffeomorphic_support", text="Enable Morph Panel")
        if rig_settings.diffeomorphic_support:
            box = layout.box()
            box.label(text="Categories", icon="SHAPEKEY_DATA")
            col = box.column()
            col.prop(rig_settings, "diffeomorphic_emotions_units")
            col.prop(rig_settings, "diffeomorphic_emotions")
            if rig_settings.diffeomorphic_emotions:
                row = col.row(align=True)
                row.label(text="Custom morphs")
                row.scale_x = row_scale
                row.prop(rig_settings, "diffeomorphic_emotions_custom", text="")
            col.prop(rig_settings, "diffeomorphic_facs_emotions_units")
            col.prop(rig_settings, "diffeomorphic_facs_emotions")
            col.prop(rig_settings, "diffeomorphic_body_morphs")
            if rig_settings.diffeomorphic_body_morphs:
                row = col.row(align=True)
                row.label(text="Custom morphs")
                row.scale_x = row_scale
                row.prop(rig_settings, "diffeomorphic_body_morphs_custom", text="")

            box.separator()
            row = box.row(align=True)
            row.label(text="Disable Exceptions")
            row.scale_x = row_scale
            row.prop(rig_settings, "diffeomorphic_disable_exceptions", text="")

            box = layout.box()
            box.label(text="Morphs added: " + str(rig_settings.diffeomorphic_morphs_number), icon="LINENUMBERS_ON")
            box.operator('mustardui.morphs_check', text="Search and Add Morphs", icon="ADD")

            if addon_prefs.debug:

                daz_id = DazCheckVersion(arm.MustardUI_RigSettings.model_armature_object)

                box = layout.box()
                if daz_id:
                    box.label(text="Genesis version: " + str(daz_id), icon="ARMATURE_DATA")
                else:
                    box.label(text="Genesis version not found", icon="ERROR")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_InitPanel_External)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_InitPanel_External)
