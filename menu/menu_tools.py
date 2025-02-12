import bpy
from . import MainPanel
from ..model_selection.active_object import *
from ..warnings.ops_fix_old_UI import check_old_UI
from ..settings.rig import *


class PANEL_PT_MustardUI_Tools(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Tools"
    bl_label = "Tools"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):

        if check_old_UI():
            return False

        res, arm = mustardui_active_object(context, config=0)
        if arm is not None:
            return res and (arm.MustardUI_ToolsSettings.autobreath_enable or arm.MustardUI_ToolsSettings.autoeyelid_enable)
        return res

    def draw(self, context):
        pass


class PANEL_PT_MustardUI_Tools_AutoBreath(MainPanel, bpy.types.Panel):
    bl_parent_id = "PANEL_PT_MustardUI_Tools"
    bl_idname = "PANEL_PT_MustarUI_Tools_AutoBreath"
    bl_label = "Auto Breath"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):

        res, arm = mustardui_active_object(context, config=0)
        if arm:
            if hasattr(arm.MustardUI_ToolsSettings, "autobreath_enable"):
                return res and arm.MustardUI_ToolsSettings.autobreath_enable
            else:
                return False
        else:
            return res

    def draw(self, context):

        poll, arm = mustardui_active_object(context, config=0)
        tools_settings = arm.MustardUI_ToolsSettings

        layout = self.layout

        box = layout.box()
        column = box.column(align=True)
        column.label(text="Select one bone:", icon="BONE_DATA")
        column.label(text="  - Unlocked transformation are animated")
        column.label(text="  - Rest value should be 1")
        column.label(text="  - Max value should be 2")
        column = box.column(align=True)
        column.prop(tools_settings, "autobreath_frequency")
        column.prop(tools_settings, "autobreath_amplitude")
        column.prop(tools_settings, "autobreath_random")
        column.prop(tools_settings, "autobreath_sampling")

        layout.operator('mustardui.tools_autobreath')


class PANEL_PT_MustardUI_Tools_AutoEyelid(MainPanel, bpy.types.Panel):
    bl_parent_id = "PANEL_PT_MustardUI_Tools"
    bl_idname = "PANEL_PT_MustarUI_Tools_AutoEyelid"
    bl_label = "Auto Blink"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):

        res, arm = mustardui_active_object(context, config=0)
        if arm:
            if hasattr(arm.MustardUI_ToolsSettings, "autoeyelid_enable"):
                return res and arm.MustardUI_ToolsSettings.autoeyelid_enable
            else:
                return False
        else:
            return res

    def draw(self, context):

        poll, arm = mustardui_active_object(context, config=0)
        tools_settings = arm.MustardUI_ToolsSettings

        layout = self.layout

        box = layout.box()
        column = box.column(align=True)
        column.label(text="Auto Blink settings", icon="HIDE_OFF")
        column = box.column(align=True)
        column.prop(tools_settings, "autoeyelid_blink_length")
        column.prop(tools_settings, "autoeyelid_blink_rate_per_minute")

        layout.operator('mustardui.tools_autoeyelid')


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_Tools)
    bpy.utils.register_class(PANEL_PT_MustardUI_Tools_AutoBreath)
    bpy.utils.register_class(PANEL_PT_MustardUI_Tools_AutoEyelid)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Tools_AutoEyelid)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Tools_AutoBreath)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Tools)
