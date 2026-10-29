import bpy

from ..misc.geometry_nodes import draw_modifier_inputs, node_group_has_simulation
from ..misc.mirror import check_mirror
from ..misc.ui_collapse import ui_collapse_panel
from ..model_selection.active_object import ModelMode, mustardui_active_object
from . import MainPanel


# Physics item selected in the list: None if the list index is out of range
def selected_physics_item(physics_settings, arm):
    index = arm.mustardui_physics_items_uilist_index
    if 0 <= index < len(physics_settings.items):
        return physics_settings.items[index]
    return None


def cloth_panel(layout, pi, mod):
    cloth = mod.settings
    col = layout.column(align=True)
    col.prop(cloth, "quality")
    col.prop(cloth, "time_scale")
    col.prop(cloth, "mass", text="Vertex Mass")
    col.prop(cloth, "air_damping", text="Air Viscosity")
    col.separator()
    col.prop(cloth, "pin_stiffness")

    uid = f"MustardUI_Physics_{pi.object.name}"

    body = ui_collapse_panel(layout, f"{uid}_Stiffness", "Stiffness")
    if body:
        col = body.column(align=True)
        if cloth.bending_model == "ANGULAR":
            col.prop(cloth, "tension_stiffness", text="Tension")
            col.prop(cloth, "compression_stiffness", text="Compression")
        else:
            col.prop(cloth, "tension_stiffness", text="Structural")
        col.prop(cloth, "shear_stiffness", text="Shear")
        col.prop(cloth, "bending_stiffness", text="Bending")

    body = ui_collapse_panel(layout, f"{uid}_Damping", "Damping")
    if body:
        col = body.column(align=True)
        if cloth.bending_model == "ANGULAR":
            col.prop(cloth, "tension_damping", text="Tension")
            col.prop(cloth, "compression_damping", text="Compression")
        else:
            col.prop(cloth, "tension_damping", text="Structural")
        col.prop(cloth, "shear_damping", text="Shear")
        col.prop(cloth, "bending_damping", text="Bending")

    body = ui_collapse_panel(layout, f"{uid}_InternalSprings", "Internal Springs")
    if body:
        col = body.column(align=True)
        col.prop(cloth, "internal_tension_stiffness", text="Tension")
        col.prop(cloth, "internal_compression_stiffness", text="Compression")
        col = body.column(align=True)
        col.prop(cloth, "internal_tension_stiffness_max", text="Max Tension")
        col.prop(cloth, "internal_compression_stiffness_max", text="Max Compression")

    body = ui_collapse_panel(layout, f"{uid}_Pressure", "Pressure")
    if body:
        col = body.column(align=True)
        col.prop(cloth, "uniform_pressure_force")
        col.prop(cloth, "pressure_factor")

    body = ui_collapse_panel(layout, f"{uid}_Cache", "Cache")
    if body:
        cache = mod.point_cache
        row = body.row(align=True)
        row.prop(cache, "frame_start")
        row.prop(cache, "frame_end")
        row.prop(pi, "unique_cache_frames", icon="TRACKING_REFINE_BACKWARDS", text="")

    collisions = mod.collision_settings
    header, body = layout.panel(f"{uid}_Collisions", default_closed=True)
    header.prop(collisions, "use_collision", text="Collisions")
    if body:
        col = body.column(align=True)
        col.prop(collisions, "distance_min", slider=True, text="Distance")
        col.prop(collisions, "impulse_clamp")
        col = body.column(align=True)
        col.prop(collisions, "collection", text="Collection")

    header, body = layout.panel(f"{uid}_SelfCollisions", default_closed=True)
    header.prop(collisions, "use_self_collision", text="Self Collisions")
    if body:
        col = body.column(align=True)
        col.prop(collisions, "self_friction", slider=True, text="Friction")
        col.prop(collisions, "self_distance_min", slider=True, text="Minimum Distance")
        col.prop(collisions, "self_impulse_clamp", slider=True, text="Impulse Clamping")

    # Add all settings inserted here also in the mirror operator


def soft_body_panel(layout, pi, mod):
    softbody = mod.settings

    col = layout.column(align=True)

    col.prop(softbody, "friction")
    col.prop(softbody, "mass")
    col.prop(softbody, "speed")

    body = ui_collapse_panel(layout, f"MustardUI_Physics_{pi.object.name}_Cache", "Cache")
    if body:
        cache = mod.point_cache
        row = body.row(align=True)
        row.prop(cache, "frame_start")
        row.prop(cache, "frame_end")
        row.prop(pi, "unique_cache_frames", icon="TRACKING_REFINE_BACKWARDS", text="")

    # Add all settings inserted here also in the mirror operator


def collision_panel(layout, pi):
    settings = pi.object.collision

    col = layout.column(align=True)

    col.prop(settings, "damping", text="Damping", slider=True)
    col.prop(settings, "thickness_outer", text="Thickness Outer", slider=True)
    col.prop(settings, "thickness_inner", text="Inner", slider=True)
    col.prop(settings, "cloth_friction")


class PANEL_PT_MustardUI_Physics(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Physics"
    bl_label = "Physics"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        res, obj = mustardui_active_object(context, config=ModelMode.USER)
        if obj:
            physics_settings = obj.MustardUI_PhysicsSettings
            if res:
                return (
                    res
                    and physics_settings.enable_ui
                    and len([x for x in physics_settings.items if x.object])
                )

        return res

    def draw_header(self, context):

        poll, obj = mustardui_active_object(context, config=ModelMode.USER)
        physics_settings = obj.MustardUI_PhysicsSettings

        self.layout.prop(physics_settings, "enable_physics", text="", toggle=False)

    def draw(self, context):

        poll, obj = mustardui_active_object(context, config=ModelMode.USER)
        physics_settings = obj.MustardUI_PhysicsSettings

        layout = self.layout

        layout.active = physics_settings.enable_physics

        layout.template_list(
            "MUSTARDUI_UL_PhysicsItems_UIList_Menu",
            "The_List",
            physics_settings,
            "items",
            obj,
            "mustardui_physics_items_uilist_index",
        )

        pi = selected_physics_item(physics_settings, obj)

        if pi is not None and pi.type == "BONES_DRIVER":
            row = layout.row()
            row.enabled = pi.enable
            row.prop(pi, "bone_influence")
        elif pi is not None and pi.type == "CAGE":
            row = layout.row()
            row.enabled = pi.enable
            row.prop(pi, "cage_influence")

        layout.separator()
        layout.operator("mustardui.physics_rebind", text="Re-bind All Cages", icon="FILE_REFRESH")


def draw_header_buttons(layout, physics_settings, pi):
    """Mirror and Presets buttons of the settings panels of a Physics Item"""
    # Check if Mirror should be drawn
    if pi.type in ["CAGE", "SINGLE_ITEM"]:
        items = [x for x in physics_settings.items if x.object]
        for on in [x.object.name for x in items if x.object != pi.object]:
            if check_mirror(pi.object.name, on, left=True) or check_mirror(
                pi.object.name, on, left=False
            ):
                layout.active = layout.active and pi.enable
        layout.operator(
            "mustardui.physics_mirror", text="", icon="MOD_MIRROR"
        ).obj_name = pi.object.name

    op = layout.operator("mustardui.presets_ui", text="", icon="PRESET")
    op.preset_type = "PHYSICS"


class PANEL_PT_MustardUI_Physics_ClothSettings(MainPanel, bpy.types.Panel):
    bl_label = ""
    bl_parent_id = "PANEL_PT_MustardUI_Physics"
    bl_options = {"DEFAULT_CLOSED", "HEADER_LAYOUT_EXPAND"}

    @classmethod
    def poll(cls, context):
        res, obj = mustardui_active_object(context, config=ModelMode.USER)

        if obj is None:
            return False

        physics_settings = obj.MustardUI_PhysicsSettings
        pi = selected_physics_item(physics_settings, obj)
        if pi is None:
            return False

        if pi.object and pi.type in ["CAGE", "SINGLE_ITEM", "BONES_DRIVER"]:
            cloth = next((m for m in pi.object.modifiers if m.type == "CLOTH"), None)
            return res and cloth

        return False

    def draw_header(self, context):
        poll, obj = mustardui_active_object(context, config=ModelMode.USER)
        physics_settings = obj.MustardUI_PhysicsSettings

        layout = self.layout

        pi = selected_physics_item(physics_settings, obj)
        if pi is None:
            return

        layout.label(text="Cloth Settings")
        layout.active = physics_settings.enable_physics

        draw_header_buttons(layout, physics_settings, pi)

    def draw(self, context):

        poll, obj = mustardui_active_object(context, config=ModelMode.USER)
        physics_settings = obj.MustardUI_PhysicsSettings

        layout = self.layout

        pi = selected_physics_item(physics_settings, obj)
        if pi is None:
            return
        cloth = next((m for m in pi.object.modifiers if m.type == "CLOTH"), None)

        layout.active = physics_settings.enable_physics and pi.enable

        if cloth is None:
            return

        cloth_panel(layout, pi, cloth)


def find_geometry_nodes_physics_modifier(obj):
    """The Geometry Nodes modifier with a simulation, or else the first one"""
    modifiers = [m for m in obj.modifiers if m.type == "NODES" and m.node_group]
    return next(
        (m for m in modifiers if node_group_has_simulation(m.node_group)),
        modifiers[0] if modifiers else None,
    )


class PANEL_PT_MustardUI_Physics_ClothDynamicsSettings(MainPanel, bpy.types.Panel):
    bl_label = ""
    bl_parent_id = "PANEL_PT_MustardUI_Physics"
    bl_options = {"DEFAULT_CLOSED", "HEADER_LAYOUT_EXPAND"}

    @classmethod
    def poll(cls, context):
        res, obj = mustardui_active_object(context, config=ModelMode.USER)

        if obj is None:
            return False

        physics_settings = obj.MustardUI_PhysicsSettings
        pi = selected_physics_item(physics_settings, obj)
        if pi is None:
            return False

        if pi.object and pi.type in ["CAGE", "SINGLE_ITEM", "BONES_DRIVER"]:
            return res and find_geometry_nodes_physics_modifier(pi.object) is not None

        return False

    def draw_header(self, context):
        poll, obj = mustardui_active_object(context, config=ModelMode.USER)
        physics_settings = obj.MustardUI_PhysicsSettings

        layout = self.layout

        pi = selected_physics_item(physics_settings, obj)
        if pi is None:
            return
        dynamics = find_geometry_nodes_physics_modifier(pi.object)
        if dynamics is not None:
            name = dynamics.node_group.name.removeprefix("MustardUI ")
            layout.label(text=f"{name} Settings")
        layout.active = physics_settings.enable_physics

        draw_header_buttons(layout, physics_settings, pi)

    def draw(self, context):

        poll, obj = mustardui_active_object(context, config=ModelMode.USER)
        physics_settings = obj.MustardUI_PhysicsSettings

        layout = self.layout

        pi = selected_physics_item(physics_settings, obj)
        if pi is None:
            return
        dynamics = find_geometry_nodes_physics_modifier(pi.object)

        layout.active = physics_settings.enable_physics and pi.enable

        if dynamics is not None:
            draw_modifier_inputs(layout, dynamics, collisions=(pi, "collisions"))


class PANEL_PT_MustardUI_Physics_SoftBodySettings(MainPanel, bpy.types.Panel):
    bl_label = ""
    bl_parent_id = "PANEL_PT_MustardUI_Physics"
    bl_options = {"DEFAULT_CLOSED", "HEADER_LAYOUT_EXPAND"}

    @classmethod
    def poll(cls, context):
        res, obj = mustardui_active_object(context, config=ModelMode.USER)

        if obj is None:
            return False

        physics_settings = obj.MustardUI_PhysicsSettings
        pi = selected_physics_item(physics_settings, obj)
        if pi is None:
            return False

        if pi.object and pi.type in ["CAGE", "SINGLE_ITEM", "BONES_DRIVER"]:
            soft_body = next((m for m in pi.object.modifiers if m.type == "SOFT_BODY"), None)
            return res and soft_body

        return False

    def draw_header(self, context):
        poll, obj = mustardui_active_object(context, config=ModelMode.USER)
        physics_settings = obj.MustardUI_PhysicsSettings

        layout = self.layout

        pi = selected_physics_item(physics_settings, obj)
        if pi is None:
            return

        layout.label(text="Soft Body Settings")
        layout.active = physics_settings.enable_physics

        draw_header_buttons(layout, physics_settings, pi)

    def draw(self, context):

        poll, obj = mustardui_active_object(context, config=ModelMode.USER)
        physics_settings = obj.MustardUI_PhysicsSettings

        layout = self.layout

        pi = selected_physics_item(physics_settings, obj)
        if pi is None:
            return
        soft_body = next((m for m in pi.object.modifiers if m.type == "SOFT_BODY"), None)

        layout.active = physics_settings.enable_physics and pi.enable

        if soft_body is None:
            return

        soft_body_panel(layout, pi, soft_body)


class PANEL_PT_MustardUI_Physics_CollisionSettings(MainPanel, bpy.types.Panel):
    bl_label = ""
    bl_parent_id = "PANEL_PT_MustardUI_Physics"
    bl_options = {"DEFAULT_CLOSED", "HEADER_LAYOUT_EXPAND"}

    @classmethod
    def poll(cls, context):
        res, obj = mustardui_active_object(context, config=ModelMode.USER)

        if obj is None:
            return False

        physics_settings = obj.MustardUI_PhysicsSettings
        pi = selected_physics_item(physics_settings, obj)
        if pi is None:
            return False

        if pi.object and pi.type in ["COLLISION"]:
            cloth = next((m for m in pi.object.modifiers if m.type == "COLLISION"), None)
            return res and cloth

        return False

    def draw_header(self, context):
        poll, obj = mustardui_active_object(context, config=ModelMode.USER)
        physics_settings = obj.MustardUI_PhysicsSettings

        layout = self.layout
        layout.active = physics_settings.enable_physics

        layout.label(text="Collision Settings")
        op = layout.operator("mustardui.presets_ui", text="", icon="PRESET")
        op.preset_type = "PHYSICS"

    def draw(self, context):

        poll, obj = mustardui_active_object(context, config=ModelMode.USER)
        physics_settings = obj.MustardUI_PhysicsSettings

        layout = self.layout

        pi = selected_physics_item(physics_settings, obj)
        if pi is None:
            return
        collision = next((m for m in pi.object.modifiers if m.type == "COLLISION"), None)

        layout.active = physics_settings.enable_physics and pi.enable

        if collision is None or not pi.object.collision:
            return

        collision_panel(layout, pi)


class PANEL_PT_MustardUI_Physics_Cache(MainPanel, bpy.types.Panel):
    bl_label = "Global Cache"
    bl_parent_id = "PANEL_PT_MustardUI_Physics"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        res, obj = mustardui_active_object(context, config=ModelMode.USER)
        if obj:
            physics_settings = obj.MustardUI_PhysicsSettings
            if res:
                return res and len([x for x in physics_settings.items if x.object])
        return res

    def draw(self, context):

        poll, obj = mustardui_active_object(context, config=ModelMode.USER)
        physics_settings = obj.MustardUI_PhysicsSettings

        layout = self.layout

        layout.active = physics_settings.enable_physics

        row = layout.row(align=True)
        row.prop(physics_settings, "frame_start")
        row.prop(physics_settings, "frame_end")
        row.operator("mustardui.physics_bake_syncframes", text="", icon="UV_SYNC_SELECT")
        row = layout.row(align=True)
        row.operator("mustardui.physics_bake_all", text="Bake All").bake = True
        row.operator("mustardui.physics_bake_delete_all", text="Delete All Bake")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_Physics)
    bpy.utils.register_class(PANEL_PT_MustardUI_Physics_ClothSettings)
    bpy.utils.register_class(PANEL_PT_MustardUI_Physics_ClothDynamicsSettings)
    bpy.utils.register_class(PANEL_PT_MustardUI_Physics_SoftBodySettings)
    bpy.utils.register_class(PANEL_PT_MustardUI_Physics_CollisionSettings)
    bpy.utils.register_class(PANEL_PT_MustardUI_Physics_Cache)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Physics_Cache)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Physics_CollisionSettings)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Physics_SoftBodySettings)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Physics_ClothDynamicsSettings)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Physics_ClothSettings)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Physics)
