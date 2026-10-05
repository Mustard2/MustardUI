import bpy

from .. import __package__ as base_package
from ..model_selection.active_object import ModelMode, mustardui_active_object
from ..model_toolkit.effects.ops_squish import squish_draw_settings
from ..model_toolkit.mesh.ops_smooth_shape_key import smooth_shape_key_draw_settings
from ..model_toolkit.outfits.ops_fit_to_body import fit_to_body_draw_settings
from ..warnings.can_draw_ui import can_draw_ui
from . import MainPanel


class PANEL_PT_MustardUI_ModelToolkit(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_ModelToolkit"
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


class ModelToolkitSection(MainPanel):
    bl_parent_id = "PANEL_PT_MustardUI_ModelToolkit"
    bl_label = ""
    bl_options = {"DEFAULT_CLOSED", "HEADER_LAYOUT_EXPAND"}

    # Header label and icon, and page of the guide in the wiki
    header = ("", "NONE")
    guide = ""
    # Creator-only sections are hidden once the model UI is enabled for users
    creator_only = False

    @classmethod
    def poll(cls, context):
        if can_draw_ui():
            return False

        res, arm = mustardui_active_object(context, config=ModelMode.MODEL_TOOLKIT)
        addon_prefs = context.preferences.addons[base_package].preferences
        return res and addon_prefs.model_toolkit and not (cls.creator_only and arm.MustardUI_enable)

    def draw_header(self, context):
        layout = self.layout
        layout.label(text=self.header[0], icon=self.header[1])
        if self.guide:
            layout.operator(
                "wm.url_open", text="", icon="QUESTION"
            ).url = f"https://github.com/Mustard2/MustardUI/wiki/Creator-Tools-{self.guide}"


class PANEL_PT_MustardUI_ModelToolkit_Rig(ModelToolkitSection, bpy.types.Panel):
    header = ("Armature", "OUTLINER_DATA_ARMATURE")
    guide = "Armature"

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.operator(
            "mustardui.model_toolkit_ikspline",
            text="Create IK Spline",
            icon="CON_SPLINEIK",
        )
        row.operator("mustardui.model_toolkit_ikspline_clean", text="", icon="X")

        row = layout.row(align=True)
        row.operator("mustardui.model_toolkit_face_controller", icon="USER")
        row.operator("mustardui.model_toolkit_face_controller_remove", text="", icon="X")


class PANEL_PT_MustardUI_ModelToolkit_Model(ModelToolkitSection, bpy.types.Panel):
    header = ("Model", "ARMATURE_DATA")
    guide = "Model"
    creator_only = True

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.operator("mustardui.rename_model", icon="GREASEPENCIL")

        layout.separator()

        row = layout.row(align=True)
        row.operator("mustardui.tool_naming", icon="SMALL_CAPS", text="Enforce Naming on Data")

        row = layout.row(align=True)
        row.operator("mustardui.rename_image_nodes", icon="IMAGE_DATA")


class PANEL_PT_MustardUI_ModelToolkit_Outfits(ModelToolkitSection, bpy.types.Panel):
    header = ("Outfits", "MOD_CLOTH")
    guide = "Outfits"

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.operator("mustardui.model_toolkit_add_outfit", icon="ADD")

        row = layout.row(align=True)
        row.operator("mustardui.model_toolkit_export_outfits", icon="EXPORT")

        layout.separator()

        row = layout.row(align=True)
        row.operator("mustardui.model_toolkit_fit_to_body", icon="MOD_CLOTH")
        fit_to_body_draw_settings(layout, context)


class PANEL_PT_MustardUI_ModelToolkit_Mesh(ModelToolkitSection, bpy.types.Panel):
    header = ("Mesh", "MESH_DATA")
    guide = "Mesh"

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.operator("mustardui.model_toolkit_transfer_shape_keys", icon="SHAPEKEY_DATA")

        row = layout.row(align=True)
        row.operator("mustardui.model_toolkit_link_shape_keys", icon="DRIVER_TRANSFORM")

        row = layout.row(align=True)
        row.operator("mustardui.model_toolkit_smooth_shape_key", icon="MOD_SMOOTH")
        smooth_shape_key_draw_settings(layout, context)

        layout.separator()

        row = layout.row(align=True)
        row.operator("mustardui.model_toolkit_transfer_vertex_groups", icon="GROUP_VERTEX")

        layout.separator()

        row = layout.row(align=True)
        row.operator("mustardui.model_toolkit_select_preview_texture", icon="SHADING_SOLID")
        row.operator(
            "mustardui.model_toolkit_select_preview_texture", text="", icon="SCENE_DATA"
        ).scene = True


class PANEL_PT_MustardUI_ModelToolkit_Physics(ModelToolkitSection, bpy.types.Panel):
    header = ("Physics", "PHYSICS")
    guide = "Physics"

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.operator(
            "mustardui.model_toolkit_create_jiggle",
            text="Create Jiggle Cage (Quick)",
            icon="OUTLINER_OB_FORCE_FIELD",
        )
        row.operator("mustardui.model_toolkit_remove_jiggle", text="", icon="X")

        row = layout.row(align=True)
        row.operator(
            "mustardui.model_toolkit_create_jiggle_accurate",
            text="Create Jiggle Cage (Accurate)",
            icon="SPHERE",
        )
        row.operator("mustardui.model_toolkit_remove_jiggle_accurate", text="", icon="X")

        layout.separator()

        row = layout.row(align=True)
        row.operator(
            "mustardui.model_toolkit_hair_cage",
            text="Create Hair Cage",
            icon="OUTLINER_OB_CURVES",
        )
        row.operator("mustardui.model_toolkit_remove_hair_cage", text="", icon="X")

        row = layout.row(align=True)
        row.operator(
            "mustardui.model_toolkit_accessory_physics",
            text="Create Accessory Physics",
            icon="LINKED",
        )
        row.operator("mustardui.model_toolkit_remove_accessory_physics", text="", icon="X")

        row = layout.row(align=True)
        row.operator(
            "mustardui.model_toolkit_bone_physics",
            text="Add Bone Physics",
            icon="BONE_DATA",
        )
        row.operator("mustardui.model_toolkit_bone_physics_clean", text="", icon="X")

        layout.separator()

        row = layout.row(align=True)
        row.operator(
            "mustardui.model_toolkit_create_collision_cage",
            text="Create Collision Cage",
            icon="MESH_UVSPHERE",
        )
        row.operator("mustardui.model_toolkit_remove_collision_cage", text="", icon="X")

        layout.separator()

        row = layout.row(align=True)
        row.operator(
            "mustardui.model_toolkit_assign_physics",
            text="Assign Physics",
            icon="PHYSICS",
        )


class PANEL_PT_MustardUI_ModelToolkit_Effects(ModelToolkitSection, bpy.types.Panel):
    header = ("Effects", "SHADERFX")
    guide = "Effects"

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.label(text="", icon="SHAPEKEY_DATA")
        row.separator()
        row.operator("mustardui.model_toolkit_squish", icon="MOD_SHRINKWRAP")
        squish_draw_settings(layout, context)

        row = layout.row(align=True)
        row.label(text="", icon="GEOMETRY_NODES")
        row.separator()
        row.operator("mustardui.model_toolkit_ripple", text="Ripple", icon="MOD_WAVE")
        row.operator("mustardui.model_toolkit_remove_ripple", text="", icon="X")

        layout.separator()

        row = layout.row(align=True)
        row.label(text="", icon="GEOMETRY_NODES")
        row.separator()
        row.operator(
            "mustardui.model_toolkit_sticky_strands", text="Sticky Strands", icon="STRANDS"
        )
        row.operator("mustardui.model_toolkit_remove_sticky_strands", text="", icon="X")

        layout.separator()

        row = layout.row(align=True)
        row.label(text="", icon="GEOMETRY_NODES")
        row.separator()
        row.operator(
            "mustardui.model_toolkit_disintegration", text="Disintegration", icon="PARTICLES"
        )
        row.operator("mustardui.model_toolkit_remove_disintegration", text="", icon="X")

        row = layout.row(align=True)
        row.label(text="", icon="NODE_MATERIAL")
        row.separator()
        row.operator(
            "mustardui.model_toolkit_hex_dissolve", text="Hex Dissolve", icon="MESH_ICOSPHERE"
        )
        row.operator("mustardui.model_toolkit_remove_hex_dissolve", text="", icon="X")

        layout.separator()

        row = layout.row(align=True)
        row.label(text="", icon="GEOMETRY_NODES")
        row.separator()
        row.operator("mustardui.model_toolkit_rope", text="Rope", icon="CURVE_BEZCIRCLE")
        row.operator("mustardui.model_toolkit_remove_rope", text="", icon="X")

        row = layout.row(align=True)
        row.label(text="", icon="GEOMETRY_NODES")
        row.separator()
        row.operator("mustardui.model_toolkit_tape", text="Tape", icon="MOD_THICKNESS")
        row.operator("mustardui.model_toolkit_remove_tape", text="", icon="X")

        layout.separator()

        row = layout.row(align=True)
        row.label(text="", icon="GEOMETRY_NODES")
        row.separator()
        row.operator("mustardui.model_toolkit_fireball", text="Fireball", icon="LIGHT_SUN")
        row.operator("mustardui.model_toolkit_remove_fireball", text="", icon="X")


class PANEL_PT_MustardUI_ModelToolkit_Optimizations(ModelToolkitSection, bpy.types.Panel):
    header = ("Optimizations", "FORCE_WIND")
    guide = "Optimization"
    creator_only = True

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.operator(
            "mustardui.model_toolkit_optimize_modifiers",
            icon="MOD_SMOOTH",
        )

        row = layout.row(align=True)
        row.operator(
            "mustardui.model_toolkit_optimize_shaders",
            icon="SHADING_RENDERED",
        )

        row = layout.row(align=True)
        row.operator(
            "mustardui.model_toolkit_optimize_shape_keys",
            icon="SHAPEKEY_DATA",
        )

        row = layout.row(align=True)
        row.operator(
            "mustardui.model_toolkit_convert_images",
            icon="IMAGE_DATA",
        )


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_ModelToolkit)
    bpy.utils.register_class(PANEL_PT_MustardUI_ModelToolkit_Model)
    bpy.utils.register_class(PANEL_PT_MustardUI_ModelToolkit_Rig)
    bpy.utils.register_class(PANEL_PT_MustardUI_ModelToolkit_Outfits)
    bpy.utils.register_class(PANEL_PT_MustardUI_ModelToolkit_Mesh)
    bpy.utils.register_class(PANEL_PT_MustardUI_ModelToolkit_Physics)
    bpy.utils.register_class(PANEL_PT_MustardUI_ModelToolkit_Effects)
    bpy.utils.register_class(PANEL_PT_MustardUI_ModelToolkit_Optimizations)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ModelToolkit_Optimizations)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ModelToolkit_Effects)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ModelToolkit_Physics)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ModelToolkit_Mesh)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ModelToolkit_Outfits)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ModelToolkit_Rig)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ModelToolkit_Model)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ModelToolkit)
