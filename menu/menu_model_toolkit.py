import bpy

from .. import __package__ as base_package
from ..misc.geometry_nodes import draw_modifier_inputs
from ..model_selection.active_object import (
    ModelMode,
    active_object_operator_poll,
    mustardui_active_object,
)
from ..model_toolkit.cloth import solver
from ..model_toolkit.cloth.settings import STATE, active_cloth, cloth_objects
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
    # Experimental sections are hidden unless the Experimental Features preference is on
    experimental = False

    @classmethod
    def poll(cls, context):
        prefs = context.preferences.addons[base_package].preferences
        if not prefs.model_toolkit or (cls.experimental and not prefs.experimental):
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


class PANEL_PT_MustardUI_ModelToolkit_Unreal(ModelToolkitSection, bpy.types.Panel):
    header = ("Unreal Tools (Experimental)", "EXPORT")
    experimental = True

    def draw(self, context):
        col = self.layout.column(align=True)
        col.operator("mustardui.unreal_tools_export_character", icon="OUTLINER_OB_ARMATURE")
        col.operator("mustardui.unreal_tools_export_animation", icon="ACTION")


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
                if effect.experimental:
                    row.label(text="", icon="EXPERIMENTAL")
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


class PANEL_PT_MustardUI_ModelToolkit_Cloth(ModelToolkitSection, bpy.types.Panel):
    header = ("Cloth Physics (Experimental)", "MOD_CLOTH")
    experimental = True

    def draw(self, context):
        layout = self.layout
        if not solver.gpu_available():
            layout.label(text="Needs a GPU with compute shaders", icon="ERROR")
            return
        sc = context.scene.MustardUI_ClothScene
        row = layout.row()
        row.scale_y = 1.4
        row.prop(sc, "mode", expand=True)
        layout.row().prop(sc, "advanced", expand=True)

        # Cloths: the list first, then adding the selected outfit
        box = layout.box()
        cloths = cloth_objects(context)
        box.label(text=f"Cloths ({len(cloths)})", icon="MOD_CLOTH")
        col = box.column(align=True)
        for o in cloths:
            icon = "RADIOBUT_ON" if o == context.active_object else "RADIOBUT_OFF"
            col.operator(
                "mustardui.model_toolkit_cloth_select",
                text=o.name,
                icon=icon,
                emboss=o == context.active_object,
            ).name = o.name
        obj = context.active_object
        if obj and obj.type == "MESH" and not obj.MustardUI_Cloth.enabled:
            row = box.row()
            row.scale_y = 1.4
            row.operator(
                "mustardui.model_toolkit_cloth_enable", text=f"Add Cloth: {obj.name}", icon="ADD"
            )

        if sc.mode == "INTERACTIVE":
            col = layout.column(align=True)
            row = col.row(align=True)
            row.scale_y = 1.6
            if STATE["running"]:
                row.alert = True
                row.operator("mustardui.model_toolkit_cloth_stop", icon="CANCEL")
            else:
                row.operator(
                    "mustardui.model_toolkit_cloth_interactive",
                    text="Start Interactive Mode",
                    icon="PLAY",
                )
            row = col.row(align=True)
            row.operator(
                "mustardui.model_toolkit_cloth_reset", text="Reset All", icon="LOOP_BACK"
            ).all = True
            row.operator(
                "mustardui.model_toolkit_cloth_rebuild", text="Rebuild All", icon="FILE_REFRESH"
            )
            return

        scene = context.scene
        row = layout.row(align=True)
        row.prop(scene, "frame_start", text="Start")
        row.prop(scene, "frame_end", text="End")
        col = layout.column(align=True)
        row = col.row(align=True)
        row.scale_y = 1.6
        playing = context.screen.is_animation_playing
        row.operator(
            "mustardui.model_toolkit_cloth_play",
            text="Pause" if playing else "Play from Start",
            icon="PAUSE" if playing else "PLAY",
        )
        row = col.row(align=True)
        row.operator("mustardui.model_toolkit_cloth_bake", text="Bake", icon="REC")
        row.operator("mustardui.model_toolkit_cloth_free_cache", text="Free", icon="TRASH")
        row.operator("mustardui.model_toolkit_cloth_rebuild", text="", icon="FILE_REFRESH")
        world = solver.WORLD["world"]
        if world and world.cache:
            layout.label(text=f"Cached {min(world.cache)}-{max(world.cache)}", icon="TIME")


class ClothSubPanel(MainPanel):
    bl_category = "MustardUI Toolkit"
    bl_parent_id = "PANEL_PT_MustardUI_ModelToolkit_Cloth"

    @classmethod
    def poll(cls, context):
        return PANEL_PT_MustardUI_ModelToolkit_Cloth.poll(context) and solver.gpu_available()


class SelectedClothSubPanel(ClothSubPanel):
    """Sub-panel of the selected cloth"""

    @classmethod
    def poll(cls, context):
        return super().poll(context) and active_cloth(context) is not None


class PANEL_PT_MustardUI_ModelToolkit_Cloth_Brush(ClothSubPanel, bpy.types.Panel):
    bl_label = "Brush"

    @classmethod
    def poll(cls, context):
        return super().poll(context) and context.scene.MustardUI_ClothScene.mode == "INTERACTIVE"

    def draw(self, context):
        layout = self.layout
        sc = context.scene.MustardUI_ClothScene
        layout.active = STATE["running"]
        row = layout.row()
        row.scale_y = 1.3
        row.prop(sc, "brush", expand=True, icon_only=True)
        row = layout.row(align=True)
        row.prop(sc, "brush_radius", text="Radius")
        row.prop(sc, "brush_strength")


class PANEL_PT_MustardUI_ModelToolkit_Cloth_Selected(SelectedClothSubPanel, bpy.types.Panel):
    bl_label = "Selected Cloth"

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        st = obj.MustardUI_Cloth
        row = layout.row(align=True)
        row.operator("mustardui.model_toolkit_cloth_reset", icon="FILE_REFRESH").all = False
        row.operator(
            "mustardui.model_toolkit_cloth_save_shape_key",
            text="Save Shape Key",
            icon="SHAPEKEY_DATA",
        )
        row = layout.row(align=True)
        row.operator("mustardui.model_toolkit_cloth_disable", icon="HIDE_ON")
        row.operator("mustardui.model_toolkit_cloth_remove", icon="TRASH")
        layout.prop(st, "sim_mesh", text="Mesh")
        cloth = solver.SIMS.get(obj.name)
        if cloth and context.scene.MustardUI_ClothScene.debug:
            layout.label(
                text=f"{cloth.source_verts} source / {len(cloth.rest)} simulation vertices"
            )


class PANEL_PT_MustardUI_ModelToolkit_Cloth_Fabric(SelectedClothSubPanel, bpy.types.Panel):
    bl_label = "Fabric"

    def draw(self, context):
        layout = self.layout
        st = context.active_object.MustardUI_Cloth
        layout.prop(st, "material", text="Preset")
        if context.scene.MustardUI_ClothScene.advanced == "ADVANCED":
            col = layout.column(align=True)
            for name in ("stretch", "shear", "bend", "density", "friction", "damping"):
                col.prop(st, name)


class PANEL_PT_MustardUI_ModelToolkit_Cloth_Collision(SelectedClothSubPanel, bpy.types.Panel):
    bl_label = "Collision"

    def draw(self, context):
        layout = self.layout
        st = context.active_object.MustardUI_Cloth
        layout.prop(st, "collider")
        if context.scene.MustardUI_ClothScene.advanced == "ADVANCED":
            layout.prop(st, "thickness")
            layout.prop(st, "auto_fit")


class PANEL_PT_MustardUI_ModelToolkit_Cloth_SelfCollision(ClothSubPanel, bpy.types.Panel):
    bl_label = "Self Collision"

    def draw_header(self, context):
        self.layout.prop(context.scene.MustardUI_ClothScene, "self_collision", text="")

    def draw(self, context):
        layout = self.layout
        sc = context.scene.MustardUI_ClothScene
        layout.active = sc.self_collision
        if sc.advanced == "ADVANCED":
            layout.prop(sc, "self_radius", text="Distance")
            layout.prop(sc, "untangle")


class PANEL_PT_MustardUI_ModelToolkit_Cloth_Pinning(SelectedClothSubPanel, bpy.types.Panel):
    bl_label = "Pinning"

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        layout.prop_search(obj.MustardUI_Cloth, "pin_group", obj, "vertex_groups", text="Group")
        layout.prop(obj.MustardUI_Cloth, "pin_target", text="Follow")
        layout.prop(obj.MustardUI_Cloth, "follow", slider=True)


class PANEL_PT_MustardUI_ModelToolkit_Cloth_Sewing(SelectedClothSubPanel, bpy.types.Panel):
    bl_label = "Sewing"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        self.layout.prop(context.active_object.MustardUI_Cloth, "sewing", text="")

    def draw(self, context):
        layout = self.layout
        layout.active = context.active_object.MustardUI_Cloth.sewing
        if context.scene.MustardUI_ClothScene.advanced == "ADVANCED":
            layout.prop(context.scene.MustardUI_ClothScene, "sew_force")


class PANEL_PT_MustardUI_ModelToolkit_Cloth_Simulation(ClothSubPanel, bpy.types.Panel):
    bl_label = "Simulation"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        sc = context.scene.MustardUI_ClothScene
        layout.prop(sc, "quality")
        layout.prop(sc, "smooth_display")
        if sc.advanced == "ADVANCED":
            row = layout.row(align=True)
            row.prop(sc, "substeps")
            row.prop(sc, "iterations")
            layout.prop(sc, "gravity")
            layout.prop(sc, "air")
        layout.prop(sc, "debug")
        world = solver.WORLD["world"]
        if world and sc.debug:
            layout.label(text=f"{world.solver.n} vertices, {len(world.solver.colors)} colors")


def draw_cloth_brush_bar(self, context):
    """Cloth Physics brushes as icons in the 3D View header while Interactive Mode runs"""
    sc = context.scene.MustardUI_ClothScene
    if not STATE["running"] or sc.mode != "INTERACTIVE":
        return
    layout = self.layout
    layout.separator()
    row = layout.row(align=True)
    row.prop(sc, "brush", expand=True, icon_only=True)
    row = layout.row(align=True)
    row.ui_units_x = 8
    row.prop(sc, "brush_radius", text="R")
    row.prop(sc, "brush_strength", text="S")
    layout.operator("mustardui.model_toolkit_cloth_stop", text="", icon="CANCEL")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_ModelToolkit_Model)
    bpy.utils.register_class(PANEL_PT_MustardUI_ModelToolkit_Rig)
    bpy.utils.register_class(PANEL_PT_MustardUI_ModelToolkit_Outfits)
    bpy.utils.register_class(PANEL_PT_MustardUI_ModelToolkit_Mesh)
    bpy.utils.register_class(PANEL_PT_MustardUI_ModelToolkit_Physics)
    bpy.utils.register_class(PANEL_PT_MustardUI_ModelToolkit_Cloth)
    bpy.utils.register_class(PANEL_PT_MustardUI_ModelToolkit_Cloth_Brush)
    bpy.utils.register_class(PANEL_PT_MustardUI_ModelToolkit_Cloth_Selected)
    bpy.utils.register_class(PANEL_PT_MustardUI_ModelToolkit_Cloth_Fabric)
    bpy.utils.register_class(PANEL_PT_MustardUI_ModelToolkit_Cloth_Collision)
    bpy.utils.register_class(PANEL_PT_MustardUI_ModelToolkit_Cloth_SelfCollision)
    bpy.utils.register_class(PANEL_PT_MustardUI_ModelToolkit_Cloth_Pinning)
    bpy.utils.register_class(PANEL_PT_MustardUI_ModelToolkit_Cloth_Sewing)
    bpy.utils.register_class(PANEL_PT_MustardUI_ModelToolkit_Cloth_Simulation)
    bpy.utils.register_class(PANEL_PT_MustardUI_ModelToolkit_Optimizations)
    bpy.utils.register_class(PANEL_PT_MustardUI_ModelToolkit_Unreal)
    bpy.utils.register_class(PANEL_PT_MustardUI_ModelToolkit_Effects)
    bpy.utils.register_class(PANEL_PT_MustardUI_ModelToolkit_SceneEffects)
    bpy.types.VIEW3D_HT_header.append(draw_cloth_brush_bar)


def unregister():
    bpy.types.VIEW3D_HT_header.remove(draw_cloth_brush_bar)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ModelToolkit_SceneEffects)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ModelToolkit_Effects)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ModelToolkit_Unreal)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ModelToolkit_Optimizations)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ModelToolkit_Cloth_Simulation)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ModelToolkit_Cloth_Sewing)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ModelToolkit_Cloth_Pinning)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ModelToolkit_Cloth_SelfCollision)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ModelToolkit_Cloth_Collision)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ModelToolkit_Cloth_Fabric)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ModelToolkit_Cloth_Selected)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ModelToolkit_Cloth_Brush)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ModelToolkit_Cloth)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ModelToolkit_Physics)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ModelToolkit_Mesh)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ModelToolkit_Outfits)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ModelToolkit_Rig)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ModelToolkit_Model)
