import bpy

from .. import __package__ as base_package
from ..misc.geometry_nodes import draw_modifier_inputs
from ..model_selection.active_object import (
    ModelMode,
    active_object_operator_poll,
    mustardui_active_object,
)
from ..model_toolkit.effects.effect import (
    SETTINGS,
    effects_available,
    materials,
    shader_nodes,
)
from ..model_toolkit.effects.ops_squish import squish_draw_settings
from ..model_toolkit.effects.settings import EFFECTS
from ..model_toolkit.mesh.ops_smooth_shape_key import smooth_shape_key_draw_settings
from ..model_toolkit.outfits.ops_fit_to_body import fit_to_body_draw_settings
from . import MainPanel


class ModelToolkitSection(MainPanel):
    bl_category = "MustardUI Toolkit"
    bl_label = ""
    bl_options = {"DEFAULT_CLOSED", "HEADER_LAYOUT_EXPAND"}

    # Header label and icon, and page of the guide in the wiki
    header = ("", "NONE")
    guide = ""
    # Creator-only sections need a model, and are hidden once the model UI is enabled
    creator_only = False

    @classmethod
    def poll(cls, context):
        if not context.preferences.addons[base_package].preferences.model_toolkit:
            return False
        if not cls.creator_only:
            return True
        res, arm = mustardui_active_object(context, config=ModelMode.MODEL_TOOLKIT)
        return res and not arm.MustardUI_enable

    def draw_header(self, context):
        layout = self.layout
        layout.label(text=self.header[0], icon=self.header[1])
        if self.guide:
            layout.operator(
                "wm.url_open", text="", icon="QUESTION"
            ).url = f"https://github.com/Mustard2/MustardUI/wiki/Model-Toolkit-{self.guide}"


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

        layout.separator()

        row = layout.row(align=True)
        row.operator("mustardui.model_toolkit_scale_character", icon="CON_SIZELIKE")


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
        row.operator("mustardui.model_toolkit_add_outfit_from_file", icon="IMPORT")

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
        sub = row.row(align=True)
        # Without a model, it works on the selected objects
        sub.enabled = bool(context.selected_objects) or active_object_operator_poll(
            context, config=ModelMode.MODEL_TOOLKIT
        )
        sub.operator("mustardui.model_toolkit_select_preview_texture", icon="SHADING_SOLID")
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

        layout.separator()

        row = layout.row(align=True)
        row.operator(
            "mustardui.model_toolkit_particle_hair_to_curves",
            text="Convert Particle Hair to Curves",
            icon="CURVES",
        )


# Effects in the panel, by group
EFFECT_GROUPS = (
    ("Ripple", "Jiggle"),
    ("Sticky Strands", "Sticky Liquid", "Sticky Spurts"),
    ("Wet", "Dirt", "Foam", "Marks"),
    ("Cloth Tear", "Cloth Rip", "Disintegration", "Hex Dissolve", "Aura"),
    (
        "Shatter",
        "Shockwave",
        "Crush",
        "Billow Dust",
        "Imprints",
        "Bulge",
        "Shrinkwrap",
        "Dust Puff",
        "Wet Footprints",
    ),
    ("Rope", "Tape", "Chain"),
    ("Fireball",),
    ("Dust Motes", "Rain"),
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

        experimental = context.preferences.addons[base_package].preferences.experimental
        for group in EFFECT_GROUPS:
            names = [x for x in group if experimental or not EFFECTS[x].experimental]
            # The first group goes right below Squish
            if names and group is not EFFECT_GROUPS[0]:
                layout.separator()
            for name in names:
                effect = EFFECTS[name]
                add = effect.remove.removeprefix("remove_")
                row = layout.row(align=True)
                row.label(text="", icon="GEOMETRY_NODES" if effect.node_group else "NODE_MATERIAL")
                row.separator()
                row.operator(f"mustardui.model_toolkit_{add}", text=name, icon=effect.icon)
                if name.startswith("Sticky"):
                    row.operator(
                        f"mustardui.model_toolkit_convert_{add}", text="", icon="MESH_DATA"
                    )
                elif name == "Shrinkwrap":
                    row.operator(
                        f"mustardui.model_toolkit_{add}", text="", icon="MESH_TORUS"
                    ).opening = True
                row.operator(f"mustardui.model_toolkit_{effect.remove}", text="", icon="X")


class PANEL_PT_MustardUI_ModelToolkit_SceneEffects(ModelToolkitSection, bpy.types.Panel):
    header = ("Scene Effects", "SCENE_DATA")
    guide = "Effects"

    @classmethod
    def poll(cls, context):
        return (
            effects_available()
            and super().poll(context)
            and len(context.scene.MustardUI_SceneEffects) > 0
        )

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        effects = scene.MustardUI_SceneEffects

        row = layout.row()
        row.template_list(
            "MUSTARDUI_UL_ModelToolkit_UIList_SceneEffects",
            "",
            scene,
            "MustardUI_SceneEffects",
            scene,
            "mustardui_scene_effects_uilist_index",
        )

        index = scene.mustardui_scene_effects_uilist_index
        item = effects[index] if index < len(effects) else None
        if item is None or item.object is None:
            return

        col = row.column(align=True)
        col.operator(
            "mustardui.model_toolkit_select_object", text="", icon="RESTRICT_SELECT_OFF"
        ).name = item.object.name
        col.separator()
        op = col.operator("mustardui.model_toolkit_remove_scene_effect", text="", icon="X")
        op.effect, op.name = item.effect, item.object.name

        modifier = item.object.modifiers.get(item.modifier)
        if modifier is not None and modifier.node_group is not None:
            header, body = layout.panel("MustardUI_SceneEffects_GeometryNodes")
            header.label(text="Geometry Nodes", icon="GEOMETRY_NODES")
            if body:
                draw_modifier_inputs(body, modifier, select_objects=True)

        material_group = EFFECTS[item.effect].material_group
        if material_group is None:
            return
        # The materials sharing the settings once, the effects added before alone
        shared = {}
        for material in sorted(materials([item.object]), key=lambda x: x.name):
            for node in shader_nodes(material, material_group):
                shared.setdefault(node.node_tree.nodes.get(SETTINGS) or node, material)
        for settings, material in shared.items():
            header, body = layout.panel(f"MustardUI_SceneEffects_Shader_{material.name}")
            label = "Shader" if settings.name == SETTINGS else f"Shader: {material.name}"
            header.label(text=label, icon="NODE_MATERIAL")
            for socket in settings.inputs if body else ():
                if not (socket.is_linked or socket.hide_value):
                    body.row().prop(socket, "default_value", text=socket.name)


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

        row = layout.row(align=True)
        row.operator(
            "mustardui.model_toolkit_memory_report",
            icon="MEMORY",
        )


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_ModelToolkit_Model)
    bpy.utils.register_class(PANEL_PT_MustardUI_ModelToolkit_Rig)
    bpy.utils.register_class(PANEL_PT_MustardUI_ModelToolkit_Outfits)
    bpy.utils.register_class(PANEL_PT_MustardUI_ModelToolkit_Mesh)
    bpy.utils.register_class(PANEL_PT_MustardUI_ModelToolkit_Physics)
    bpy.utils.register_class(PANEL_PT_MustardUI_ModelToolkit_Effects)
    bpy.utils.register_class(PANEL_PT_MustardUI_ModelToolkit_SceneEffects)
    bpy.utils.register_class(PANEL_PT_MustardUI_ModelToolkit_Optimizations)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ModelToolkit_Optimizations)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ModelToolkit_SceneEffects)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ModelToolkit_Effects)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ModelToolkit_Physics)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ModelToolkit_Mesh)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ModelToolkit_Outfits)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ModelToolkit_Rig)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ModelToolkit_Model)
