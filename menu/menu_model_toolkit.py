import bpy

from .. import __package__ as base_package
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


class PANEL_PT_MustardUI_ModelToolkit(MainPanel, bpy.types.Panel):
    bl_category = "MustardUI Toolkit"
    bl_label = "Model Toolkit"
    bl_options = {"HIDE_HEADER"}

    @classmethod
    def poll(cls, context):
        return (
            context.preferences.addons[base_package].preferences.model_toolkit
            and any(x.MustardUI_created for x in bpy.data.armatures)
            and not active_object_operator_poll(context, config=ModelMode.MODEL_TOOLKIT)
        )

    def draw(self, context):
        res, arm = mustardui_active_object(context, config=ModelMode.ANY)
        settings = context.scene.MustardUI_Settings

        box = self.layout.box()
        col = box.column(align=True)
        if settings.viewport_model_selection and arm is not None and arm.MustardUI_created:
            col.label(text="Disable Viewport Model Selection", icon="INFO")
            col.label(text="to use all the Model Toolkit tools", icon="BLANK1")
            box.operator(
                "mustardui.viewportmodelselection",
                text="Viewport Model Selection",
                icon="VIEW3D",
                depress=settings.viewport_model_selection,
            ).config = 1
        else:
            col.label(text="Select a MustardUI model", icon="INFO")
            col.label(text="to use all the Model Toolkit tools", icon="BLANK1")


class ModelToolkitSection(MainPanel):
    bl_category = PANEL_PT_MustardUI_ModelToolkit.bl_category
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
        row.operator("mustardui.model_toolkit_convert_sticky_strands", text="", icon="MESH_DATA")
        row.operator("mustardui.model_toolkit_remove_sticky_strands", text="", icon="X")

        row = layout.row(align=True)
        row.label(text="", icon="GEOMETRY_NODES")
        row.separator()
        row.operator(
            "mustardui.model_toolkit_sticky_liquid", text="Sticky Liquid", icon="MOD_FLUIDSIM"
        )
        row.operator("mustardui.model_toolkit_convert_sticky_liquid", text="", icon="MESH_DATA")
        row.operator("mustardui.model_toolkit_remove_sticky_liquid", text="", icon="X")

        layout.separator()

        row = layout.row(align=True)
        row.label(text="", icon="GEOMETRY_NODES")
        row.separator()
        row.operator("mustardui.model_toolkit_wet", text="Wet", icon="MATFLUID")
        row.operator("mustardui.model_toolkit_remove_wet", text="", icon="X")

        row = layout.row(align=True)
        row.label(text="", icon="GEOMETRY_NODES")
        row.separator()
        row.operator("mustardui.model_toolkit_foam", text="Foam", icon="OUTLINER_DATA_POINTCLOUD")
        row.operator("mustardui.model_toolkit_remove_foam", text="", icon="X")

        row = layout.row(align=True)
        row.label(text="", icon="GEOMETRY_NODES")
        row.separator()
        row.operator("mustardui.model_toolkit_marks", text="Marks", icon="TPAINT_HLT")
        row.operator("mustardui.model_toolkit_remove_marks", text="", icon="X")

        layout.separator()

        row = layout.row(align=True)
        row.label(text="", icon="GEOMETRY_NODES")
        row.separator()
        row.operator("mustardui.model_toolkit_cloth_tear", text="Cloth Tear", icon="MOD_CLOTH")
        row.operator(
            "mustardui.model_toolkit_cloth_rip", text="Cloth Rip", icon="EMPTY_SINGLE_ARROW"
        )
        row.operator("mustardui.model_toolkit_remove_cloth_tear", text="", icon="X")

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

        row = layout.row(align=True)
        row.label(text="", icon="GEOMETRY_NODES")
        row.separator()
        row.operator("mustardui.model_toolkit_aura", text="Aura", icon="LIGHT_POINT")
        row.operator("mustardui.model_toolkit_remove_aura", text="", icon="X")

        layout.separator()

        row = layout.row(align=True)
        row.label(text="", icon="GEOMETRY_NODES")
        row.separator()
        row.operator("mustardui.model_toolkit_shatter", text="Shatter", icon="MOD_EXPLODE")
        row.operator("mustardui.model_toolkit_remove_shatter", text="", icon="X")

        row = layout.row(align=True)
        row.label(text="", icon="GEOMETRY_NODES")
        row.separator()
        row.operator("mustardui.model_toolkit_crush", text="Crush", icon="MOD_MESHDEFORM")
        row.operator("mustardui.model_toolkit_remove_crush", text="", icon="X")

        row = layout.row(align=True)
        row.label(text="", icon="GEOMETRY_NODES")
        row.separator()
        row.operator("mustardui.model_toolkit_imprints", text="Imprints", icon="MOD_DISPLACE")
        row.operator("mustardui.model_toolkit_remove_imprints", text="", icon="X")

        row = layout.row(align=True)
        row.label(text="", icon="GEOMETRY_NODES")
        row.separator()
        row.operator("mustardui.model_toolkit_dust_puff", text="Dust Puff", icon="FORCE_TURBULENCE")
        row.operator("mustardui.model_toolkit_remove_dust_puff", text="", icon="X")

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

        layout.separator()

        row = layout.row(align=True)
        row.label(text="", icon="GEOMETRY_NODES")
        row.separator()
        row.operator("mustardui.model_toolkit_dust_motes", text="Dust Motes", icon="PARTICLE_POINT")
        row.operator("mustardui.model_toolkit_remove_dust_motes", text="", icon="X")


def effect_draw_inputs(layout, modifier):
    """Inputs of the modifier, in the panels of its node group"""
    inputs, panels = modifier.properties.inputs, modifier.properties.panels
    # Layout of the open panels, the root one being 0
    bodies = {0: layout}
    for item in modifier.node_group.interface.items_tree:
        body = bodies.get(item.parent.persistent_uid)
        if body is None:
            continue
        if item.item_type == "PANEL":
            header, bodies[item.persistent_uid] = body.panel_prop(
                panels, f"open_{item.persistent_uid}"
            )
            toggle = next(
                (x for x in item.interface_items if getattr(x, "is_panel_toggle", False)), None
            )
            if toggle is None:
                header.label(text=item.name)
                continue
            toggle = getattr(inputs, toggle.identifier)
            header.prop(toggle, "value", text=item.name)
            if bodies[item.persistent_uid]:
                bodies[item.persistent_uid].active = toggle.value
        elif not (
            item.in_out == "OUTPUT"
            or item.socket_type == "NodeSocketGeometry"
            or item.hide_value
            or item.hide_in_modifier
            or item.is_panel_toggle
        ):
            socket = getattr(inputs, item.identifier)
            # Vectors in a column, not to squeeze their values
            vector = item.socket_type == "NodeSocketVector"
            row = body.column(align=True) if vector else body.row(align=True)
            if getattr(socket, "type", "") == "ATTRIBUTE":
                row.prop(socket, "attribute_name", text=item.name)
            else:
                row.prop(socket, "value", text=item.name)
            if item.socket_type == "NodeSocketObject" and socket.value:
                row.operator(
                    "mustardui.model_toolkit_select_object", text="", icon="RESTRICT_SELECT_OFF"
                ).name = socket.value.name


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

        layout.template_list(
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
        modifier = item.object.modifiers.get(item.modifier)
        if modifier is not None and modifier.node_group is not None:
            header, body = layout.panel("MustardUI_SceneEffects_GeometryNodes")
            header.label(text="Geometry Nodes", icon="GEOMETRY_NODES")
            if body:
                effect_draw_inputs(body, modifier)

        material_group = EFFECTS[item.effect][2]
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
    bpy.utils.register_class(PANEL_PT_MustardUI_ModelToolkit)
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
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ModelToolkit)
