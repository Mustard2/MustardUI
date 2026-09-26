import bpy

from .. import __package__ as base_package
from ..model_selection.active_object import ModelMode, mustardui_active_object
from ..model_toolkit.mesh.ops_fit_to_body import fit_to_body_draw_settings
from ..model_toolkit.mesh.ops_squish import squish_draw_settings
from ..warnings.can_draw_ui import can_draw_ui
from . import MainPanel


class PANEL_PT_MustardUI_ToolsCreators(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_ToolsCreators"
    bl_label = "Model Toolkit"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        if can_draw_ui():
            return False

        res, arm = mustardui_active_object(context, config=ModelMode.ANY)
        addon_prefs = context.preferences.addons[base_package].preferences
        return res and addon_prefs.model_toolkit

    def draw(self, context):
        res, arm = mustardui_active_object(context, config=ModelMode.ANY)
        settings = bpy.context.scene.MustardUI_Settings

        if settings.viewport_model_selection and arm.MustardUI_created:
            layout = self.layout
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Viewport Model selection should be", icon="ERROR")
            col.label(text="disabled to use the Model Toolkit", icon="BLANK1")
            box.operator(
                "mustardui.viewportmodelselection",
                text="Viewport Model Selection",
                icon="VIEW3D",
                depress=settings.viewport_model_selection,
            ).config = 1
        elif settings.viewport_model_selection and not arm.MustardUI_created:
            layout = self.layout
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Complete the first configuration", icon="ERROR")
            col.label(text="to use the Model Toolkit", icon="BLANK1")


class PANEL_PT_MustardUI_ToolsCreators_Rig(MainPanel, bpy.types.Panel):
    bl_parent_id = "PANEL_PT_MustardUI_ToolsCreators"
    bl_label = ""
    bl_options = {"DEFAULT_CLOSED", "HEADER_LAYOUT_EXPAND"}

    url_MustardUI_ToolsGuide = "https://github.com/Mustard2/MustardUI/wiki/Creator-Tools-Armature"

    @classmethod
    def poll(cls, context):
        if can_draw_ui():
            return False

        res, arm = mustardui_active_object(context, config=ModelMode.MODEL_TOOLKIT)
        addon_prefs = context.preferences.addons[base_package].preferences
        return res and addon_prefs.model_toolkit

    def draw_header(self, context):
        layout = self.layout
        layout.label(text="Armature", icon="OUTLINER_DATA_ARMATURE")
        layout.operator("wm.url_open", text="", icon="QUESTION").url = self.url_MustardUI_ToolsGuide

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.operator("mustardui.tools_creators_face_controller", icon="USER")
        row.operator("mustardui.tools_creators_face_controller_remove", text="", icon="X")

        row = layout.row(align=True)
        row.operator(
            "mustardui.tools_creators_ikspline",
            text="Create IK Spline",
            icon="CON_SPLINEIK",
        )
        row.operator("mustardui.tools_creators_ikspline_clean", text="", icon="X")

        row = layout.row(align=True)
        row.operator(
            "mustardui.tools_creators_affect_transform",
            text="Affect Transform on Bone Constraints",
            icon="CONSTRAINT_BONE",
        ).enable = True
        row.operator("mustardui.tools_creators_affect_transform", text="", icon="X").enable = False


class PANEL_PT_MustardUI_ToolsCreators_Model(MainPanel, bpy.types.Panel):
    bl_parent_id = "PANEL_PT_MustardUI_ToolsCreators"
    bl_label = ""
    bl_options = {"DEFAULT_CLOSED", "HEADER_LAYOUT_EXPAND"}

    url_MustardUI_ToolsGuide = "https://github.com/Mustard2/MustardUI/wiki/Creator-Tools-Model"

    @classmethod
    def poll(cls, context):
        if can_draw_ui():
            return False

        res, arm = mustardui_active_object(context, config=ModelMode.MODEL_TOOLKIT)
        addon_prefs = context.preferences.addons[base_package].preferences
        return res and addon_prefs.model_toolkit

    def draw_header(self, context):
        layout = self.layout
        layout.label(text="Model", icon="ARMATURE_DATA")
        layout.operator("wm.url_open", text="", icon="QUESTION").url = self.url_MustardUI_ToolsGuide

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.operator("mustardui.tool_naming", icon="SMALL_CAPS", text="Enforce Naming on Data")
        row = layout.row(align=True)
        row.operator("mustardui.rename_image_nodes", icon="IMAGE_DATA")
        row = layout.row(align=True)
        row.operator("mustardui.rename_model", icon="GREASEPENCIL")


class PANEL_PT_MustardUI_ToolsCreators_Mesh(MainPanel, bpy.types.Panel):
    bl_parent_id = "PANEL_PT_MustardUI_ToolsCreators"
    bl_label = ""
    bl_options = {"DEFAULT_CLOSED", "HEADER_LAYOUT_EXPAND"}

    url_MustardUI_ToolsGuide = "https://github.com/Mustard2/MustardUI/wiki/Creator-Tools-Mesh"

    @classmethod
    def poll(cls, context):
        if can_draw_ui():
            return False

        res, arm = mustardui_active_object(context, config=ModelMode.MODEL_TOOLKIT)
        addon_prefs = context.preferences.addons[base_package].preferences
        return res and addon_prefs.model_toolkit

    def draw_header(self, context):
        layout = self.layout
        layout.label(text="Mesh", icon="MESH_DATA")
        layout.operator("wm.url_open", text="", icon="QUESTION").url = self.url_MustardUI_ToolsGuide

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.operator("mustardui.tools_creators_link_shape_keys", icon="DRIVER_TRANSFORM")

        row = layout.row(align=True)
        row.operator("mustardui.tools_creators_transfer_vertex_groups", icon="GROUP_VERTEX")

        row = layout.row(align=True)
        row.operator("mustardui.tools_creators_squish", icon="MOD_SHRINKWRAP")
        squish_draw_settings(layout, context)

        row = layout.row(align=True)
        row.operator("mustardui.tools_creators_fix_clipping", icon="MOD_CLOTH")
        fit_to_body_draw_settings(layout, context)


class PANEL_PT_MustardUI_ToolsCreators_Physics(MainPanel, bpy.types.Panel):
    bl_parent_id = "PANEL_PT_MustardUI_ToolsCreators"
    bl_label = ""
    bl_options = {"DEFAULT_CLOSED", "HEADER_LAYOUT_EXPAND"}

    url_MustardUI_ToolsGuide = "https://github.com/Mustard2/MustardUI/wiki/Creator-Tools-Physics"

    @classmethod
    def poll(cls, context):
        if can_draw_ui():
            return False

        res, arm = mustardui_active_object(context, config=ModelMode.MODEL_TOOLKIT)
        addon_prefs = context.preferences.addons[base_package].preferences
        return res and addon_prefs.model_toolkit

    def draw_header(self, context):
        layout = self.layout
        layout.label(text="Physics", icon="PHYSICS")
        layout.operator("wm.url_open", text="", icon="QUESTION").url = self.url_MustardUI_ToolsGuide

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.operator(
            "mustardui.tools_creators_create_jiggle",
            text="Create Jiggle Cage (Quick)",
            icon="OUTLINER_OB_FORCE_FIELD",
        )
        row.operator("mustardui.tools_creators_remove_jiggle", text="", icon="X")

        row = layout.row(align=True)
        row.operator(
            "mustardui.tools_creators_create_jiggle_accurate",
            text="Create Jiggle Cage (Accurate)",
            icon="SPHERE",
        )
        row.operator("mustardui.tools_creators_remove_jiggle_accurate", text="", icon="X")

        row = layout.row(align=True)
        row.operator(
            "mustardui.tools_creators_hair_cage",
            text="Create Hair Cage",
            icon="OUTLINER_OB_CURVES",
        )
        row.operator("mustardui.tools_creators_remove_hair_cage", text="", icon="X")

        row = layout.row(align=True)
        row.operator(
            "mustardui.tools_creators_accessory_physics",
            text="Create Accessory Physics",
            icon="LINKED",
        )
        row.operator("mustardui.tools_creators_remove_accessory_physics", text="", icon="X")

        row = layout.row(align=True)
        row.operator(
            "mustardui.tools_creators_bone_physics",
            text="Add Bone Physics",
            icon="BONE_DATA",
        )
        row.operator("mustardui.tools_creators_bone_physics_clean", text="", icon="X")

        row = layout.row(align=True)
        row.operator(
            "mustardui.tools_creators_create_collision_cage",
            text="Create Collision Cage",
            icon="MESH_UVSPHERE",
        )
        row.operator("mustardui.tools_creators_remove_collision_cage", text="", icon="X")

        layout.separator()
        row = layout.row(align=True)
        row.operator(
            "mustardui.tools_creators_assign_physics",
            text="Assign Physics",
            icon="PHYSICS",
        )


class PANEL_PT_MustardUI_ToolsCreators_Optimizations(MainPanel, bpy.types.Panel):
    bl_parent_id = "PANEL_PT_MustardUI_ToolsCreators"
    bl_label = ""
    bl_options = {"DEFAULT_CLOSED", "HEADER_LAYOUT_EXPAND"}

    url_MustardUI_ToolsGuide = (
        "https://github.com/Mustard2/MustardUI/wiki/Creator-Tools-Optimization"
    )

    @classmethod
    def poll(cls, context):
        if can_draw_ui():
            return False

        res, arm = mustardui_active_object(context, config=ModelMode.MODEL_TOOLKIT)
        addon_prefs = context.preferences.addons[base_package].preferences
        return res and addon_prefs.model_toolkit

    def draw_header(self, context):
        layout = self.layout
        layout.label(text="Optimizations", icon="FORCE_WIND")
        layout.operator("wm.url_open", text="", icon="QUESTION").url = self.url_MustardUI_ToolsGuide

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.operator(
            "mustardui.tools_creators_optimize_modifiers",
            icon="MOD_SMOOTH",
        )

        row = layout.row(align=True)
        row.operator(
            "mustardui.tools_creators_optimize_shaders",
            icon="SHADING_RENDERED",
        )

        row = layout.row(align=True)
        row.operator(
            "mustardui.tools_creators_optimize_shape_keys",
            icon="SHAPEKEY_DATA",
        ).revert = False
        row.operator(
            "mustardui.tools_creators_optimize_shape_keys", icon="LOOP_BACK", text=""
        ).revert = True

        row = layout.row(align=True)
        row.operator(
            "mustardui.tools_creators_select_preview_texture",
            icon="SHADING_SOLID",
        )


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_ToolsCreators)
    bpy.utils.register_class(PANEL_PT_MustardUI_ToolsCreators_Model)
    bpy.utils.register_class(PANEL_PT_MustardUI_ToolsCreators_Rig)
    bpy.utils.register_class(PANEL_PT_MustardUI_ToolsCreators_Mesh)
    bpy.utils.register_class(PANEL_PT_MustardUI_ToolsCreators_Physics)
    bpy.utils.register_class(PANEL_PT_MustardUI_ToolsCreators_Optimizations)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ToolsCreators_Optimizations)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ToolsCreators_Physics)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ToolsCreators_Mesh)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ToolsCreators_Rig)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ToolsCreators_Model)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ToolsCreators)
