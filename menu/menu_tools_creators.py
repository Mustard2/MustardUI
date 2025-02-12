import bpy
from . import MainPanel
from ..model_selection.active_object import *
from ..warnings.ops_fix_old_UI import check_old_UI
from .. import __package__ as base_package


class PANEL_PT_MustardUI_ToolsCreators(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_ToolsCreators"
    bl_label = "Creator Tools"

    @classmethod
    def poll(cls, context):
        if check_old_UI():
            return False

        res, arm = mustardui_active_object(context, config=1)
        addon_prefs = context.preferences.addons[base_package].preferences
        return res and addon_prefs.developer

    def draw(self, context):
        pass


class PANEL_PT_MustardUI_ToolsCreators_Physics(MainPanel, bpy.types.Panel):
    bl_parent_id = "PANEL_PT_MustardUI_ToolsCreators"
    bl_label = "Physics"
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
        layout.label(text="", icon="PHYSICS")

    def draw(self, context):

        layout = self.layout

        row = layout.row(align=True)
        row.operator('mustardui.tools_creators_create_jiggle', text="Add Jiggle Cage", icon="OUTLINER_OB_FORCE_FIELD")
        row.operator('mustardui.tools_creators_bone_physics_clean', text="", icon="X")
        row = layout.row(align=True)
        row.operator('mustardui.tools_creators_bone_physics', text="Add Bone Physics", icon="BONE_DATA")
        row = layout.row(align=True)
        row.operator('mustardui.tools_creators_hair_cage', text="Create Hair Cage", icon="OUTLINER_OB_CURVES")
        row.operator('mustardui.tools_creators_add_cloth_to_hair', text="", icon="MOD_CLOTH")
        row = layout.row(align=True)
        row.operator('mustardui.tools_creators_create_collision_cage', text="Create Collision Cage", icon="MESH_UVSPHERE")


class PANEL_PT_MustardUI_ToolsCreators_Rig(MainPanel, bpy.types.Panel):
    bl_parent_id = "PANEL_PT_MustardUI_ToolsCreators"
    bl_label = "Armature"
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
        layout.label(text="", icon="OUTLINER_DATA_ARMATURE")

    def draw(self, context):

        layout = self.layout

        row = layout.row(align=True)
        row.operator('mustardui.tools_creators_ikspline', text="Create IK Spline", icon="CON_SPLINEIK")
        row.operator('mustardui.tools_creators_ikspline_clean', text="", icon="X")
        row = layout.row(align=True)
        row.operator('mustardui.tools_creators_affect_transform', text="Affect Transform on Bone Constraints", icon="CONSTRAINT_BONE").enable = True
        row.operator('mustardui.tools_creators_affect_transform', text="", icon="X").enable = False


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_ToolsCreators)
    bpy.utils.register_class(PANEL_PT_MustardUI_ToolsCreators_Physics)
    bpy.utils.register_class(PANEL_PT_MustardUI_ToolsCreators_Rig)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ToolsCreators_Rig)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ToolsCreators_Physics)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ToolsCreators)
