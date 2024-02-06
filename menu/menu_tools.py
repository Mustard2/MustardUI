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
            rig_settings = arm.MustardUI_RigSettings
            return res and (arm.MustardUI_ToolsSettings.childof_enable or (
                    arm.MustardUI_ToolsSettings.lips_shrinkwrap_enable and rig_settings.model_rig_type in ["arp",
                                                                                                           "mhx"]))
        return res

    def draw(self, context):

        layout = self.layout


class PANEL_PT_MustardUI_Tools_ChildOf(MainPanel, bpy.types.Panel):
    bl_parent_id = "PANEL_PT_MustardUI_Tools"
    bl_idname = "PANEL_PT_MustarUI_Tools_ChildOf"
    bl_label = "Parent bones"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):

        res, arm = mustardui_active_object(context, config=0)
        if arm != None:
            return res and arm.MustardUI_ToolsSettings.childof_enable
        else:
            return res

    def draw(self, context):

        poll, arm = mustardui_active_object(context, config=0)
        tools_settings = arm.MustardUI_ToolsSettings

        layout = self.layout

        layout.label(text="Force one Bone to follow another Bone.")

        box = layout.box()
        column = box.column(align=True)
        column.label(text="Select two bones:", icon="BONE_DATA")
        column.label(text="  - the first will be the parent,")
        column.label(text="  - the second will be the child.")
        box.prop(tools_settings, "childof_influence")
        layout.operator('mustardui.tools_childof', text="Enable").clean = 0

        layout.operator('mustardui.tools_childof', text="Remove Parent instances", icon="X").clean = 1


class PANEL_PT_MustardUI_Tools_AutoBreath(MainPanel, bpy.types.Panel):
    bl_parent_id = "PANEL_PT_MustardUI_Tools"
    bl_idname = "PANEL_PT_MustarUI_Tools_AutoBreath"
    bl_label = "Auto Breath"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):

        res, arm = mustardui_active_object(context, config=0)
        if arm != None:
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
        if arm != None:
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


class PANEL_PT_MustardUI_Tools_LipsShrinkwrap(MainPanel, bpy.types.Panel):
    bl_parent_id = "PANEL_PT_MustardUI_Tools"
    bl_idname = "PANEL_PT_MustardUI_Tools_LipsShrinkwrap"
    bl_label = "Lips Shrinkwrap"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):

        res, arm = mustardui_active_object(context, config=0)
        if arm != None:
            rig_settings = arm.MustardUI_RigSettings
            return res and arm.MustardUI_ToolsSettings.lips_shrinkwrap_enable and rig_settings.model_rig_type in ["arp",
                                                                                                                  "mhx"]
        else:
            return res

    def draw(self, context):

        poll, arm = mustardui_active_object(context, config=0)
        tools_settings = arm.MustardUI_ToolsSettings

        layout = self.layout

        layout.label(text="Force the lips bones to stay outside the Object.")

        box = layout.box()

        box.label(text="Main properties.", icon="MODIFIER")
        box.prop(tools_settings, "lips_shrinkwrap_obj")
        column = box.column(align=True)
        column.prop(tools_settings, "lips_shrinkwrap_dist")
        column.prop(tools_settings, "lips_shrinkwrap_dist_corr")

        box = layout.box()

        box.label(text="Friction properties.", icon="FORCE_TURBULENCE")
        row = box.row(align=True)
        row.prop(tools_settings, "lips_shrinkwrap_friction")
        row.scale_x = 0.8
        row.prop(tools_settings, "lips_shrinkwrap_friction_infl")
        box.prop(tools_settings, "lips_shrinkwrap_obj_fric")
        if tools_settings.lips_shrinkwrap_obj_fric:
            if tools_settings.lips_shrinkwrap_obj_fric.type == "MESH":
                box.prop_search(tools_settings, "lips_shrinkwrap_obj_fric_sec", tools_settings.lips_shrinkwrap_obj_fric,
                                "vertex_groups")
            if tools_settings.lips_shrinkwrap_obj_fric.type == "ARMATURE":
                box.prop_search(tools_settings, "lips_shrinkwrap_obj_fric_sec",
                                tools_settings.lips_shrinkwrap_obj_fric.pose, "bones")

        row = layout.row()
        if tools_settings.lips_shrinkwrap:
            row.prop(tools_settings, "lips_shrinkwrap", text="Disable", toggle=True, icon="CANCEL")
        else:
            row.prop(tools_settings, "lips_shrinkwrap", toggle=True)


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_Tools)
    bpy.utils.register_class(PANEL_PT_MustardUI_Tools_AutoBreath)
    bpy.utils.register_class(PANEL_PT_MustardUI_Tools_AutoEyelid)
    bpy.utils.register_class(PANEL_PT_MustardUI_Tools_ChildOf)
    bpy.utils.register_class(PANEL_PT_MustardUI_Tools_LipsShrinkwrap)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Tools)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Tools_ChildOf)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Tools_LipsShrinkwrap)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Tools_AutoEyelid)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Tools_AutoBreath)
