import bpy

from ..model_selection.active_object import mustardui_active_object
from ..warnings.ops_fix_old_UI import check_old_UI
from .menu_panel import MainPanel


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
            return res and (
                arm.MustardUI_ToolsSettings.autobreath_enable
                or arm.MustardUI_ToolsSettings.autoeyelid_enable
                or arm.MustardUI_ToolsSettings.bone_shrinkwrap_enable
            )
        return res

    def draw(self, context):
        pass


class PANEL_PT_MustardUI_Tools_AutoBreath(MainPanel, bpy.types.Panel):
    bl_parent_id = "PANEL_PT_MustardUI_Tools"
    bl_idname = "PANEL_PT_MustardUI_Tools_AutoBreath"
    bl_label = "Auto Breath"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)

        if not arm:
            return False

        if hasattr(arm.MustardUI_ToolsSettings, "autobreath_enable"):
            return res and arm.MustardUI_ToolsSettings.autobreath_enable

        return False

    def draw(self, context):

        poll, arm = mustardui_active_object(context, config=0)
        tools_settings = arm.MustardUI_ToolsSettings

        layout = self.layout

        column = layout.column(align=True)
        column.label(text="Select one bone:", icon="BONE_DATA")
        column.label(text="  - Unlocked transformation are animated")
        column.label(text="  - Rest value should be 1")
        column.label(text="  - Max value should be 2")
        column = layout.column(align=True)
        column.prop(tools_settings, "autobreath_frequency")
        column.prop(tools_settings, "autobreath_amplitude")
        column.prop(tools_settings, "autobreath_random")
        column.prop(tools_settings, "autobreath_sampling")

        layout.operator("mustardui.tools_autobreath", icon="FORCE_WIND")


class PANEL_PT_MustardUI_Tools_AutoEyelid(MainPanel, bpy.types.Panel):
    bl_parent_id = "PANEL_PT_MustardUI_Tools"
    bl_idname = "PANEL_PT_MustardUI_Tools_AutoEyelid"
    bl_label = "Auto Blink"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)

        if not arm:
            return False

        if hasattr(arm.MustardUI_ToolsSettings, "autoeyelid_enable"):
            return res and arm.MustardUI_ToolsSettings.autoeyelid_enable

        return False

    def draw(self, context):

        poll, arm = mustardui_active_object(context, config=0)
        tools_settings = arm.MustardUI_ToolsSettings

        layout = self.layout

        column = layout.column(align=True)
        column.prop(tools_settings, "autoeyelid_blink_length")
        column.prop(tools_settings, "autoeyelid_blink_rate_per_minute")

        layout.operator("mustardui.tools_autoeyelid", icon="HIDE_OFF")


class PANEL_PT_MustardUI_Tools_BonesShrinkwrap(MainPanel, bpy.types.Panel):
    bl_parent_id = "PANEL_PT_MustardUI_Tools"
    bl_idname = "PANEL_PT_MustardUI_Tools_BonesShrinkwrap"
    bl_label = "Lips Shrinkwrap"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)

        if not arm:
            return False

        if hasattr(arm.MustardUI_ToolsSettings, "bone_shrinkwrap_enable"):
            return res and arm.MustardUI_ToolsSettings.bone_shrinkwrap_enable

        return False

    def draw(self, context):

        poll, arm = mustardui_active_object(context, config=0)
        tools_settings = arm.MustardUI_ToolsSettings

        layout = self.layout

        # --------------------------------------------------
        # LIPS SHRINKWRAP
        # --------------------------------------------------

        col = layout.column()

        col.prop(tools_settings, "bone_shrinkwrap_target")

        col.separator()

        col2 = col.column(align=True)
        col2.prop(tools_settings, "bone_shrinkwrap_distance")
        col2.prop(tools_settings, "bone_shrinkwrap_corner_correction")

        col.separator()

        col.prop(tools_settings, "bone_shrinkwrap_enable_friction")
        col2 = col.column()
        col2.enabled = tools_settings.bone_shrinkwrap_enable_friction
        col2.prop(tools_settings, "bone_shrinkwrap_friction_influence")

        col2 = col.column(align=True)
        col2.enabled = tools_settings.bone_shrinkwrap_enable_friction
        col2.prop(tools_settings, "bone_shrinkwrap_target_friction")

        target = tools_settings.bone_shrinkwrap_target_friction
        if target:
            if target.type == "MESH":
                col2.prop_search(
                    tools_settings,
                    "bone_shrinkwrap_target_friction_subtarget",
                    target,
                    "vertex_groups",
                    text="Vertex Group",
                )

            elif target.type == "ARMATURE":
                col2.prop_search(
                    tools_settings,
                    "bone_shrinkwrap_target_friction_subtarget",
                    target.pose,
                    "bones",
                    text="Bone",
                )

        layout.separator()

        row = layout.row(align=True)
        row.operator("mustardui.constraints_apply", icon="MOD_SHRINKWRAP", text="Apply")
        row.operator("mustardui.constraints_clear", icon="X", text="")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_Tools)
    bpy.utils.register_class(PANEL_PT_MustardUI_Tools_AutoBreath)
    bpy.utils.register_class(PANEL_PT_MustardUI_Tools_AutoEyelid)
    bpy.utils.register_class(PANEL_PT_MustardUI_Tools_BonesShrinkwrap)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Tools_BonesShrinkwrap)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Tools_AutoEyelid)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Tools_AutoBreath)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Tools)
