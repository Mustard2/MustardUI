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
        res, arm = mustardui_active_object(context, config=1)
        settings = bpy.context.scene.MustardUI_Settings

        if settings.viewport_model_selection and arm.MustardUI_created:
            layout = self.layout
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Viewport Model selection should be", icon="ERROR")
            col.label(text="disabled to use Creator tools", icon="BLANK1")
            box.operator('mustardui.viewportmodelselection', text="Viewport Model Selection", icon="VIEW3D",
                         depress=settings.viewport_model_selection).config = 1
        elif settings.viewport_model_selection and not arm.MustardUI_created:
            layout = self.layout
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Complete the first configuration", icon="ERROR")
            col.label(text="to use Creator tools", icon="BLANK1")


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
        settings = bpy.context.scene.MustardUI_Settings
        return res and addon_prefs.developer and not settings.viewport_model_selection

    def draw_header(self, context):
        layout = self.layout
        layout.label(text="", icon="OUTLINER_DATA_ARMATURE")

    def draw(self, context):

        layout = self.layout

        row = layout.row(align=True)
        row.operator('mustardui.tools_creators_face_controller', icon="USER")
        row.operator('mustardui.tools_creators_face_controller_remove', text="", icon="X")

        row = layout.row(align=True)
        row.operator('mustardui.tools_creators_ikspline', text="Create IK Spline", icon="CON_SPLINEIK")
        row.operator('mustardui.tools_creators_ikspline_clean', text="", icon="X")

        row = layout.row(align=True)
        row.operator('mustardui.tools_creators_affect_transform', text="Affect Transform on Bone Constraints", icon="CONSTRAINT_BONE").enable = True
        row.operator('mustardui.tools_creators_affect_transform', text="", icon="X").enable = False


class PANEL_PT_MustardUI_ToolsCreators_Model(MainPanel, bpy.types.Panel):
    bl_parent_id = "PANEL_PT_MustardUI_ToolsCreators"
    bl_label = "Model"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        if check_old_UI():
            return False

        res, arm = mustardui_active_object(context, config=1)
        addon_prefs = context.preferences.addons[base_package].preferences
        settings = bpy.context.scene.MustardUI_Settings
        return res and addon_prefs.developer and not settings.viewport_model_selection

    def draw_header(self, context):
        layout = self.layout
        layout.label(text="", icon="ARMATURE_DATA")

    def draw(self, context):

        layout = self.layout

        row = layout.row(align=True)
        row.operator('mustardui.rename_model', icon="GREASEPENCIL")


class PANEL_PT_MustardUI_ToolsCreators_Mesh(MainPanel, bpy.types.Panel):
    bl_parent_id = "PANEL_PT_MustardUI_ToolsCreators"
    bl_label = "Mesh"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        if check_old_UI():
            return False

        res, arm = mustardui_active_object(context, config=1)
        addon_prefs = context.preferences.addons[base_package].preferences
        settings = bpy.context.scene.MustardUI_Settings
        return res and addon_prefs.developer and not settings.viewport_model_selection

    def draw_header(self, context):
        layout = self.layout
        layout.label(text="", icon="MESH_DATA")

    def draw(self, context):

        layout = self.layout

        row = layout.row(align=True)
        row.operator('mustardui.tools_creators_link_shape_keys', icon="DRIVER_TRANSFORM")

        row = layout.row(align=True)
        row.operator('mustardui.tools_creators_transfer_vertex_groups', icon="GROUP_VERTEX")


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
        settings = bpy.context.scene.MustardUI_Settings
        return res and addon_prefs.developer and not settings.viewport_model_selection

    def draw_header(self, context):
        layout = self.layout
        layout.label(text="", icon="PHYSICS")

    def draw(self, context):

        layout = self.layout

        row = layout.row(align=True)
        row.operator('mustardui.tools_creators_create_jiggle', text="Add Jiggle Cage", icon="OUTLINER_OB_FORCE_FIELD")
        row = layout.row(align=True)
        row.operator('mustardui.tools_creators_bone_physics', text="Add Bone Physics", icon="BONE_DATA")
        row.operator('mustardui.tools_creators_bone_physics_clean', text="", icon="X")
        row = layout.row(align=True)
        row.operator('mustardui.tools_creators_hair_cage', text="Create Hair Cage", icon="OUTLINER_OB_CURVES")
        row.operator('mustardui.tools_creators_add_cloth_to_hair', text="", icon="MOD_CLOTH")
        row = layout.row(align=True)
        row.operator('mustardui.tools_creators_create_collision_cage', text="Create Collision Cage", icon="MESH_UVSPHERE")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_ToolsCreators)
    bpy.utils.register_class(PANEL_PT_MustardUI_ToolsCreators_Model)
    bpy.utils.register_class(PANEL_PT_MustardUI_ToolsCreators_Rig)
    bpy.utils.register_class(PANEL_PT_MustardUI_ToolsCreators_Mesh)
    bpy.utils.register_class(PANEL_PT_MustardUI_ToolsCreators_Physics)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ToolsCreators_Physics)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ToolsCreators_Mesh)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ToolsCreators_Rig)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ToolsCreators_Model)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ToolsCreators)
