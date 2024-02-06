import bpy

from . import MainPanel
from ..model_selection.active_object import *
from ..misc.prop_utils import *
from ..warnings.ops_fix_old_UI import check_old_UI
from ..warnings.ops_fix_eevee_normals import check_eevee_normals


class PANEL_PT_MustardUI_Warnings(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Warnings"
    bl_label = "Warnings"
    bl_icon = "ERROR"

    @classmethod
    def poll(cls, context):

        settings = bpy.context.scene.MustardUI_Settings
        poll, obj = mustardui_active_object(context, config=0)

        if obj is not None:
            # If an old script is available, only this warning is shown
            # Fix for: https://github.com/Mustard2/MustardUI/issues/150
            if check_old_UI():
                return poll

            rig_settings = obj.MustardUI_RigSettings
            check_arp = rig_settings.model_rig_type == "arp" and settings.status_rig_tools != 2
            check_diffeomorphic = (rig_settings.diffeomorphic_support and settings.status_diffeomorphic == 2 and
                                   (settings.status_diffeomorphic_version[0], settings.status_diffeomorphic_version[1],
                                    settings.status_diffeomorphic_version[2]) <= (1, 6, 0)
                                   and settings.status_diffeomorphic_version[0] > -1)
            check_mhx = rig_settings.diffeomorphic_support and settings.status_mhx != 2
            return poll and (property_value(settings, "mustardui_update_available") or check_eevee_normals(context.scene, settings) or check_arp or check_diffeomorphic or check_mhx)

        return poll

    def draw_header(self, context):
        self.layout.label(text="", icon="ERROR")

    def draw(self, context):

        settings = bpy.context.scene.MustardUI_Settings
        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings

        layout = self.layout

        # Old UI scripts
        if check_old_UI():
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Old UI script found!", icon="ERROR")
            col.label(text="Save and restart after using this!", icon="BLANK1")
            box.operator("mustardui.warnings_fix_old_ui")
            # Fix for: https://github.com/Mustard2/MustardUI/issues/150
            return

        # New MustardUI version available
        if property_value(settings, "mustardui_update_available"):
            box = layout.box()
            col = box.column(align=True)
            col.label(text="MustardUI update available!", icon="ERROR")
            col.label(text="Remember to restart after updating.", icon="BLANK1")
            box.operator("mustardui.openlink", icon="URL").url = "github.com/Mustard2/MustardUI/releases/latest"

        # Eevee normals enabled in Cycles
        if check_eevee_normals(context.scene, settings):
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Eevee Optimed Normals are active with Cycles!", icon="ERROR")
            box.operator("mustardui.warnings_fix_eevee_normals")

        # ARP support without rig_tools installed
        if rig_settings.model_rig_type == "arp":
            if settings.status_rig_tools == 1:
                box = layout.box()
                col = box.column(align=True)
                col.label(icon='ERROR', text="rig_tools not enabled!")
            elif settings.status_rig_tools == 0:
                box = layout.box()
                col = box.column(align=True)
                col.label(icon='ERROR', text="rig_tools not installed!")

        # Diffeomorphic support checks on versions
        if rig_settings.diffeomorphic_support and settings.status_diffeomorphic == 2 and  (settings.status_diffeomorphic_version[0], settings.status_diffeomorphic_version[1],
            settings.status_diffeomorphic_version[2]) <= (1, 6, 0) and settings.status_diffeomorphic_version[0] > -1:
            box = layout.box()
            box.label(icon='ERROR', text="Diffeomorphic 1.5 or below are not supported!")
            box.operator("mustardui.openlink", text="Update Diffeomorphic", icon="URL").url = "https://bitbucket.org/Diffeomorphic/import_daz/wiki/Home"

        # MHX Runtime
        if rig_settings.diffeomorphic_support and settings.status_mhx != 2:
            if settings.status_mhx == 1:
                box = layout.box()
                col = box.column(align=True)
                col.label(icon='ERROR', text="MHX runtime not enabled!")
            elif settings.status_mhx == 0:
                box = layout.box()
                col = box.column(align=True)
                col.label(icon='ERROR', text="MHX runtime not installed!")
                box.operator("mustardui.openlink", text="Install MHX", icon="URL").url = "https://bitbucket.org/Diffeomorphic/mhx_rts/wiki/Home"


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_Warnings)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Warnings)
