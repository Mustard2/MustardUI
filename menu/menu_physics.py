import bpy
from . import MainPanel
from ..model_selection.active_object import *
from ..warnings.ops_fix_old_UI import check_old_UI
from ..settings.rig import *
from ..misc.ui_collapse import ui_collapse_prop
from ..misc.mirror import check_mirror
from ..physics.settings_item import mustardui_physics_item_type_dict


def cloth_panel(layout, pi, mod):
    cloth = mod.settings
    col = layout.column(align=True)
    col.prop(cloth, 'quality')
    col.prop(cloth, 'time_scale')
    col.prop(cloth, "mass", text="Vertex Mass")
    col.prop(cloth, "air_damping", text="Air Viscosity")
    col.separator()
    col.prop(cloth, 'pin_stiffness')

    if ui_collapse_prop(layout, pi, 'collapse_cloth_stiffness', "Stiffness"):
        col = layout.column(align=True)
        if cloth.bending_model == 'ANGULAR':
            col.prop(cloth, "tension_stiffness", text="Tension")
            col.prop(cloth, "compression_stiffness", text="Compression")
        else:
            col.prop(cloth, "tension_stiffness", text="Structural")
        col.prop(cloth, "shear_stiffness", text="Shear")
        col.prop(cloth, "bending_stiffness", text="Bending")

    if ui_collapse_prop(layout, pi, 'collapse_cloth_damping', "Damping"):
        col = layout.column(align=True)
        if cloth.bending_model == 'ANGULAR':
            col.prop(cloth, "tension_damping", text="Tension")
            col.prop(cloth, "compression_damping", text="Compression")
        else:
            col.prop(cloth, "tension_damping", text="Structural")
        col.prop(cloth, "shear_damping", text="Shear")
        col.prop(cloth, "bending_damping", text="Bending")

    if ui_collapse_prop(layout, pi, 'collapse_cloth_internal_springs', "Internal Springs"):
        col = layout.column(align=True)
        col.prop(cloth, "internal_tension_stiffness", text="Tension")
        col.prop(cloth, "internal_compression_stiffness", text="Compression")
        col = layout.column(align=True)
        col.prop(cloth, "internal_tension_stiffness_max", text="Max Tension")
        col.prop(cloth, "internal_compression_stiffness_max", text="Max Compression")

    if ui_collapse_prop(layout, pi, 'collapse_cloth_pressure', "Pressure"):
        col = layout.column(align=True)
        col.prop(cloth, "uniform_pressure_force")
        col.prop(cloth, "pressure_factor")

    if ui_collapse_prop(layout, pi, 'collapse_cloth_cache', "Cache"):
        cache = mod.point_cache
        row = layout.row(align=True)
        row.prop(cache, "frame_start")
        row.prop(cache, "frame_end")
        row.prop(pi, 'unique_cache_frames', icon="TRACKING_REFINE_BACKWARDS", text="")

    row = layout.row(align=True)
    collisions = mod.collision_settings
    row.prop(pi, 'collapse_cloth_collisions',
             icon="DOWNARROW_HLT" if not pi.collapse_cloth_collisions else "RIGHTARROW", icon_only=True,
             emboss=False)
    row.prop(collisions, 'use_collision', text="")
    row.label(text="Collisions")

    if not pi.collapse_cloth_collisions:
        collisions = mod.collision_settings
        col = layout.column(align=True)
        col.prop(collisions, "distance_min", slider=True, text="Distance")
        col.prop(collisions, "impulse_clamp")
        col = layout.column(align=True)
        col.prop(collisions, "collection", text="Collection")

    row = layout.row(align=True)
    collisions = mod.collision_settings
    row.prop(pi, 'collapse_cloth_self_collisions',
             icon="DOWNARROW_HLT" if not pi.collapse_cloth_self_collisions else "RIGHTARROW", icon_only=True,
             emboss=False)
    row.prop(collisions, 'use_self_collision', text="")
    row.label(text="Self Collisions")

    if not pi.collapse_cloth_self_collisions:
        collisions = mod.collision_settings
        col = layout.column(align=True)
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

    if ui_collapse_prop(layout, pi, 'collapse_softbody_cache', "Cache"):
        cache = mod.point_cache
        row = layout.row(align=True)
        row.prop(cache, "frame_start")
        row.prop(cache, "frame_end")
        row.prop(pi, 'unique_cache_frames', icon="TRACKING_REFINE_BACKWARDS", text="")

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
        if check_old_UI():
            return False

        res, obj = mustardui_active_object(context, config=0)
        if obj:
            physics_settings = obj.MustardUI_PhysicsSettings
            if res:
                return res and physics_settings.enable_ui and len([x for x in physics_settings.items if x.object])

        return res

    def draw_header(self, context):

        poll, obj = mustardui_active_object(context, config=0)
        physics_settings = obj.MustardUI_PhysicsSettings

        self.layout.prop(physics_settings, "enable_physics", text="", toggle=False)

    def draw(self, context):

        poll, obj = mustardui_active_object(context, config=0)
        physics_settings = obj.MustardUI_PhysicsSettings

        layout = self.layout

        layout.enabled = physics_settings.enable_physics

        layout.template_list("MUSTARDUI_UL_PhysicsItems_UIList_Menu", "The_List", physics_settings,
                          "items", obj,
                          "mustardui_physics_items_uilist_index")

        pi = physics_settings.items[obj.mustardui_physics_items_uilist_index]

        if pi.type == "BONES_DRIVER":
            row = layout.row()
            row.enabled = pi.enable
            row.prop(pi, 'bone_influence')
        elif pi.type == "CAGE":
            row = layout.row()
            row.enabled = pi.enable
            row.prop(pi, 'cage_influence')

        layout.separator()
        layout.operator("mustardui.physics_rebind", text="Re-bind Cages", icon="FILE_REFRESH")


class PANEL_PT_MustardUI_Physics_ClothSettings(MainPanel, bpy.types.Panel):
    bl_label = ""
    bl_parent_id = "PANEL_PT_MustardUI_Physics"
    bl_options = {"DEFAULT_CLOSED", "HEADER_LAYOUT_EXPAND"}

    @classmethod
    def poll(cls, context):
        if check_old_UI():
            return False

        res, obj = mustardui_active_object(context, config=0)

        if obj is None:
            return False

        physics_settings = obj.MustardUI_PhysicsSettings
        pi = physics_settings.items[obj.mustardui_physics_items_uilist_index]

        if pi.object and pi.type in ["CAGE", "SINGLE_ITEM", "BONES_DRIVER"]:
            cloth = next((m for m in pi.object.modifiers if m.type == 'CLOTH'), None)
            return res and cloth

        return False

    def draw_header(self, context):
        poll, obj = mustardui_active_object(context, config=0)
        physics_settings = obj.MustardUI_PhysicsSettings

        layout = self.layout

        pi = physics_settings.items[obj.mustardui_physics_items_uilist_index]

        layout.label(text="Cloth Settings")

        # Check if Mirror should be drawn
        if pi.type in ["CAGE", "SINGLE_ITEM"]:
            items = [x for x in physics_settings.items if x.object]
            for on in [x.object.name for x in items if x.object != pi.object]:
                if check_mirror(pi.object.name, on, left=True) or check_mirror(pi.object.name, on, left=False):
                    layout.enabled = pi.enable
            layout.operator("mustardui.physics_mirror", text="", icon="MOD_MIRROR").obj_name = pi.object.name

        layout.operator("mustardui.physics_presets_ui", text="", icon="PRESET")

    def draw(self, context):

        poll, obj = mustardui_active_object(context, config=0)
        physics_settings = obj.MustardUI_PhysicsSettings

        layout = self.layout

        pi = physics_settings.items[obj.mustardui_physics_items_uilist_index]
        cloth = next((m for m in pi.object.modifiers if m.type == 'CLOTH'), None)

        layout.enabled = physics_settings.enable_physics and pi.enable

        if cloth is None:
            return

        cloth_panel(layout, pi, cloth)


class PANEL_PT_MustardUI_Physics_SoftBodySettings(MainPanel, bpy.types.Panel):
    bl_label = ""
    bl_parent_id = "PANEL_PT_MustardUI_Physics"
    bl_options = {"DEFAULT_CLOSED", "HEADER_LAYOUT_EXPAND"}

    @classmethod
    def poll(cls, context):
        if check_old_UI():
            return False

        res, obj = mustardui_active_object(context, config=0)

        if obj is None:
            return False

        physics_settings = obj.MustardUI_PhysicsSettings
        pi = physics_settings.items[obj.mustardui_physics_items_uilist_index]

        if pi.object and pi.type in ["CAGE", "SINGLE_ITEM", "BONES_DRIVER"]:
            soft_body = next((m for m in pi.object.modifiers if m.type == 'SOFT_BODY'), None)
            return res and soft_body

        return False

    def draw_header(self, context):
        poll, obj = mustardui_active_object(context, config=0)
        physics_settings = obj.MustardUI_PhysicsSettings

        layout = self.layout

        pi = physics_settings.items[obj.mustardui_physics_items_uilist_index]

        layout.label(text="Soft Body Settings")

        # Check if Mirror should be drawn
        if pi.type in ["CAGE", "SINGLE_ITEM"]:
            items = [x for x in physics_settings.items if x.object]
            for on in [x.object.name for x in items if x.object != pi.object]:
                if check_mirror(pi.object.name, on, left=True) or check_mirror(pi.object.name, on, left=False):
                    layout.enabled = pi.enable
            layout.operator("mustardui.physics_mirror", text="", icon="MOD_MIRROR").obj_name = pi.object.name

        layout.operator("mustardui.physics_presets_ui", text="", icon="PRESET")

    def draw(self, context):

        poll, obj = mustardui_active_object(context, config=0)
        physics_settings = obj.MustardUI_PhysicsSettings

        layout = self.layout

        pi = physics_settings.items[obj.mustardui_physics_items_uilist_index]
        soft_body = next((m for m in pi.object.modifiers if m.type == 'SOFT_BODY'), None)

        layout.enabled = physics_settings.enable_physics and pi.enable

        if soft_body is None:
            return

        soft_body_panel(layout, pi, soft_body)


class PANEL_PT_MustardUI_Physics_CollisionSettings(MainPanel, bpy.types.Panel):
    bl_label = ""
    bl_parent_id = "PANEL_PT_MustardUI_Physics"
    bl_options = {"DEFAULT_CLOSED", "HEADER_LAYOUT_EXPAND"}

    @classmethod
    def poll(cls, context):
        if check_old_UI():
            return False

        res, obj = mustardui_active_object(context, config=0)

        if obj is None:
            return False

        physics_settings = obj.MustardUI_PhysicsSettings
        pi = physics_settings.items[obj.mustardui_physics_items_uilist_index]

        if pi.object and pi.type in ["COLLISION"]:
            cloth = next((m for m in pi.object.modifiers if m.type == 'COLLISION'), None)
            return res and cloth

        return False

    def draw_header(self, context):
        layout = self.layout
        layout.label(text="Collision Settings")
        layout.operator("mustardui.physics_presets_ui", text="", icon="PRESET")

    def draw(self, context):

        poll, obj = mustardui_active_object(context, config=0)
        physics_settings = obj.MustardUI_PhysicsSettings

        layout = self.layout

        pi = physics_settings.items[obj.mustardui_physics_items_uilist_index]
        collision = next((m for m in pi.object.modifiers if m.type == 'COLLISION'), None)

        layout.enabled = physics_settings.enable_physics and pi.enable

        if collision is None or not pi.object.collision:
            return

        collision_panel(layout, pi)


class PANEL_PT_MustardUI_Physics_Cache(MainPanel, bpy.types.Panel):
    bl_label = "Global Cache"
    bl_parent_id = "PANEL_PT_MustardUI_Physics"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        if check_old_UI():
            return False

        res, obj = mustardui_active_object(context, config=0)
        if obj:
            physics_settings = obj.MustardUI_PhysicsSettings
            if res:
                return res and len([x for x in physics_settings.items if x.object])
        return res

    def draw(self, context):

        poll, obj = mustardui_active_object(context, config=0)
        physics_settings = obj.MustardUI_PhysicsSettings

        layout = self.layout

        layout.enabled = physics_settings.enable_physics

        row = layout.row(align=True)
        row.prop(physics_settings, 'frame_start')
        row.prop(physics_settings, 'frame_end')
        row.operator("mustardui.physics_bake_syncframes", text="", icon="UV_SYNC_SELECT")
        row = layout.row(align=True)
        row.operator("mustardui.physics_bake_all", text="Bake All").bake = True
        row.operator('ptcache.free_bake_all', text="Delete All Bake")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_Physics)
    bpy.utils.register_class(PANEL_PT_MustardUI_Physics_ClothSettings)
    bpy.utils.register_class(PANEL_PT_MustardUI_Physics_SoftBodySettings)
    bpy.utils.register_class(PANEL_PT_MustardUI_Physics_CollisionSettings)
    bpy.utils.register_class(PANEL_PT_MustardUI_Physics_Cache)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Physics_Cache)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Physics_CollisionSettings)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Physics_SoftBodySettings)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Physics_ClothSettings)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Physics)
