import bpy

from ..model_toolkit.cloth import solver
from ..model_toolkit.cloth.settings import STATE, active_cloth, cloth_objects
from . import MainPanel
from .menu_model_toolkit import ModelToolkitSection


class PANEL_PT_MustardUI_ModelToolkit_Cloth(ModelToolkitSection, bpy.types.Panel):
    header = ("Cloth Physics (Experimental)", "MOD_CLOTH")
    experimental = True

    def draw(self, context):
        layout = self.layout
        if not solver.gpu_available():
            layout.label(text="Needs a GPU with compute shaders", icon="ERROR")
            return
        sc = context.scene.MustardUI_ClothScene
        cloths = cloth_objects(context)
        obj = context.active_object
        if not cloths:
            row = layout.row()
            row.scale_y = 1.4
            name = obj.name if obj and obj.type == "MESH" else ""
            row.operator(
                "mustardui.model_toolkit_cloth_enable",
                text=f"Add Cloth: {name}" if name else "Add Cloth",
                icon="ADD",
            )
            return

        row = layout.row()
        row.scale_y = 1.4
        row.prop(sc, "mode", expand=True)

        col = layout.column(align=True)
        for o in cloths:
            icon = "RADIOBUT_ON" if o == context.active_object else "RADIOBUT_OFF"
            row = col.row(align=True)
            row.operator(
                "mustardui.model_toolkit_cloth_select",
                text=o.name,
                icon=icon,
                emboss=o == context.active_object,
            ).name = o.name
            row.operator("mustardui.model_toolkit_cloth_remove", text="", icon="X").name = o.name
        if obj and obj.type == "MESH" and not obj.MustardUI_Cloth.enabled:
            row = layout.row()
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
        return (
            PANEL_PT_MustardUI_ModelToolkit_Cloth.poll(context)
            and solver.gpu_available()
            and bool(cloth_objects(context))
        )


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
        row.prop(sc, "brush", expand=True)
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
        col = layout.column(align=True)
        for name in ("stretch", "shear", "bend", "density", "friction", "damping"):
            col.prop(st, name)


class PANEL_PT_MustardUI_ModelToolkit_Cloth_Collision(SelectedClothSubPanel, bpy.types.Panel):
    bl_label = "Collision"

    def draw_header(self, context):
        self.layout.prop(context.active_object.MustardUI_Cloth, "collision", text="")

    def draw(self, context):
        layout = self.layout
        st = context.active_object.MustardUI_Cloth
        layout.active = st.collision
        layout.prop(st, "collider")
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
        layout.prop(sc, "self_radius", text="Distance")
        layout.prop(sc, "untangle")


class PANEL_PT_MustardUI_ModelToolkit_Cloth_Floor(ClothSubPanel, bpy.types.Panel):
    bl_label = "Floor"

    def draw_header(self, context):
        self.layout.prop(context.scene.MustardUI_ClothScene, "floor", text="")

    def draw(self, context):
        layout = self.layout
        sc = context.scene.MustardUI_ClothScene
        layout.active = sc.floor
        layout.prop(sc, "floor_height")


class PANEL_PT_MustardUI_ModelToolkit_Cloth_Pinning(SelectedClothSubPanel, bpy.types.Panel):
    bl_label = "Pinning"

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        layout.prop_search(obj.MustardUI_Cloth, "pin_group", obj, "vertex_groups", text="Group")
        layout.prop(obj.MustardUI_Cloth, "pin_target", text="Follow")
        layout.prop(obj.MustardUI_Cloth, "follow", slider=True)
        st = obj.MustardUI_Cloth
        layout.label(text="Pin Empties")
        row = layout.row()
        row.template_list(
            "MUSTARDUI_UL_ClothPinEmpties_UIList",
            "",
            st,
            "pin_empties",
            st,
            "pin_empties_index",
            rows=3,
        )
        col = row.column(align=True)
        col.operator("mustardui.model_toolkit_cloth_add_pin_empty", text="", icon="ADD")
        col.operator("mustardui.model_toolkit_cloth_remove_pin_empty", text="", icon="REMOVE")


class PANEL_PT_MustardUI_ModelToolkit_Cloth_Sewing(SelectedClothSubPanel, bpy.types.Panel):
    bl_label = "Sewing"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        self.layout.prop(context.active_object.MustardUI_Cloth, "sewing", text="")

    def draw(self, context):
        layout = self.layout
        layout.active = context.active_object.MustardUI_Cloth.sewing
        layout.prop(context.scene.MustardUI_ClothScene, "sew_force")


class PANEL_PT_MustardUI_ModelToolkit_Cloth_Simulation(ClothSubPanel, bpy.types.Panel):
    bl_label = "Simulation"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        sc = context.scene.MustardUI_ClothScene
        layout.prop(sc, "quality")
        layout.prop(sc, "smooth_display")
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


classes = (
    PANEL_PT_MustardUI_ModelToolkit_Cloth,
    PANEL_PT_MustardUI_ModelToolkit_Cloth_Brush,
    PANEL_PT_MustardUI_ModelToolkit_Cloth_Selected,
    PANEL_PT_MustardUI_ModelToolkit_Cloth_Fabric,
    PANEL_PT_MustardUI_ModelToolkit_Cloth_Collision,
    PANEL_PT_MustardUI_ModelToolkit_Cloth_SelfCollision,
    PANEL_PT_MustardUI_ModelToolkit_Cloth_Floor,
    PANEL_PT_MustardUI_ModelToolkit_Cloth_Pinning,
    PANEL_PT_MustardUI_ModelToolkit_Cloth_Sewing,
    PANEL_PT_MustardUI_ModelToolkit_Cloth_Simulation,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_HT_header.append(draw_cloth_brush_bar)


def unregister():
    bpy.types.VIEW3D_HT_header.remove(draw_cloth_brush_bar)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
