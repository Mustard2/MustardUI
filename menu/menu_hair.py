import bpy

from .. import __package__ as base_package
from ..configuration.naming_convention import strip_naming_convention
from ..hair.helper_functions import hair_switcher_active
from ..misc.geometry_nodes import (
    draw_geometry_nodes_modifier_inputs,
    geometry_nodes_modifier_inputs,
)
from ..misc.ui_collapse import ui_collapse_prop
from ..model_selection.active_object import mustardui_active_object
from ..physics.definitions_nodes import HAIR_DYNAMICS_NODE_GROUP, HAIR_DYNAMICS_SOCKETS
from ..tools_creators.physics_presets import find_physics_modifier
from ..warnings.can_draw_ui import can_draw_ui
from . import MainPanel
from .misc import mustardui_custom_properties_print


# Function to format dynamic name
def format_dynamic_name(x):
    return (
        x.particle_system.name
        if "Dynamic" not in x.particle_system.name
        else x.particle_system.name.replace("Dynamic", "").lstrip().rstrip()
    )


def hair_extras_list_make(rig_settings):
    objects = rig_settings.hair_extras_collection.objects
    return [obj for obj in objects if obj.type in {"MESH", "CURVES"}]


def draw_hair_piece(layout, obj, arm, rig_settings, physics_settings, settings):
    if obj in [x.object for x in physics_settings.items]:
        return

    col = layout.column()
    row = col.row(align=True)

    op = row.operator(
        "mustardui.hair_visibility_extras",
        text=strip_naming_convention(
            obj.name,
            rig_settings.hair_extras_collection.name,
            rig_settings.model_MustardUI_naming_convention,
        ),
        icon="OUTLINER_OB_" + obj.type,
        depress=not obj.hide_viewport,
    )
    op.obj_name = obj.name

    # Physics
    pi = None
    for pii in [x for x in physics_settings.items]:
        if pii.outfit_object == obj:
            pi = pii
            break
    if pi is not None:
        col2 = row.column(align=True)
        col2.enabled = physics_settings.enable_physics
        col2.prop(
            obj.MustardUI_OutfitSettings,
            "enable_pi_physics",
            text="",
            icon="PHYSICS" if pi.type != "COLLISION" else "MOD_PHYSICS",
        )
        if pi.type != "COLLISION":
            col2 = row.column(align=True)
            col2.enabled = physics_settings.enable_physics
            col2.prop(
                obj.MustardUI_OutfitSettings,
                "enable_pi_collisions",
                text="",
                icon="MOD_PHYSICS",
            )
    elif rig_settings.hair_physics_support:
        m = find_physics_modifier(obj)
        if m is not None:
            row.prop(
                obj.MustardUI_OutfitSettings,
                "physics",
                text="",
                icon="PHYSICS" if m.type != "COLLISION" else "MOD_PHYSICS",
            )

    # Hair custom properties
    if rig_settings.outfit_custom_properties_name_order:
        custom_properties_obj = sorted(
            [x for x in arm.MustardUI_CustomPropertiesHair if x.hair == obj and not x.hidden],
            key=lambda x: x.name,
        )
    else:
        custom_properties_obj = [
            x for x in arm.MustardUI_CustomPropertiesHair if x.hair == obj and not x.hidden
        ]

    if len(custom_properties_obj) > 0:
        row.prop(
            obj.MustardUI_OutfitSettings,
            "additional_options_show",
            toggle=True,
            icon="PREFERENCES",
        )
        check_show = obj.MustardUI_OutfitSettings.additional_options_show
        if check_show:
            row2 = col.row()
            mustardui_custom_properties_print(
                arm,
                settings,
                custom_properties_obj,
                row2,
                rig_settings.outfit_custom_properties_icons,
            )

    return len(custom_properties_obj) > 0


class PANEL_PT_MustardUI_Hair(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Hair"
    bl_label = "Hair"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):

        if can_draw_ui():
            return False

        res, arm = mustardui_active_object(context, config=0)

        if arm is None:
            return False

        rig_settings = arm.MustardUI_RigSettings

        hair_global_properties_avail = sum(
            1 for x in arm.MustardUI_CustomPropertiesHair if x.hair is None
        )

        hair_collection = rig_settings.hair_collection
        hair_extras_collection = rig_settings.hair_extras_collection
        model_body = rig_settings.model_body

        hair_avail = hair_collection is not None and any(
            obj.type in {"MESH", "CURVES"} for obj in hair_collection.objects
        )

        hair_extras_avail = hair_extras_collection is not None and any(
            obj.type in {"MESH", "CURVES"} for obj in hair_extras_collection.objects
        )

        curves_hair = hair_collection is not None and any(
            obj.type == "CURVES" for obj in hair_collection.objects
        )

        particle_avail = (
            model_body is not None
            and rig_settings.particle_systems_enable
            and any(mod.type == "PARTICLE_SYSTEM" for mod in model_body.modifiers)
        )

        return (
            res
            if (
                hair_avail
                or hair_extras_avail
                or particle_avail
                or curves_hair
                or hair_global_properties_avail
            )
            else False
        )

    def draw_header(self, context):

        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings

        layout = self.layout
        layout.prop(rig_settings, "hair_show", text="", toggle=False)

    def draw(self, context):
        settings = bpy.context.scene.MustardUI_Settings

        poll, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings
        physics_settings = arm.MustardUI_PhysicsSettings
        addon_prefs = context.preferences.addons[base_package].preferences

        layout = self.layout
        layout.enabled = rig_settings.hair_show

        if rig_settings.hair_collection is not None:
            hair_num = len(
                [x for x in rig_settings.hair_collection.objects if x.type in {"MESH", "CURVES"}]
            )

            # An Outfit piece brings its own Hair: the Hair selection is locked to avoid
            # showing a second Hair on top of it
            switcher_active = hair_switcher_active(rig_settings)

            if hair_num > 1:
                row = layout.row(align=True)
                sub = row.row(align=True)
                sub.enabled = not switcher_active
                sub.prop(rig_settings, "hair_list", text="")

                if switcher_active:
                    layout.label(text="Hair disabled by an Outfit piece.", icon="INFO")

            elif hair_num > 0 and rig_settings.hair_collection.objects[0] is not None:
                obj = rig_settings.hair_collection.objects[0]
                row = layout.row(align=True)
                row.label(
                    text=strip_naming_convention(
                        obj.name,
                        rig_settings.hair_collection.name,
                        rig_settings.model_MustardUI_naming_convention,
                    ),
                    icon="OUTLINER_OB_" + obj.type,
                )

            try:
                obj = context.scene.objects[rig_settings.hair_list]

                # Physics
                pi = None
                for pii in [x for x in physics_settings.items]:
                    if pii.outfit_object == obj:
                        pi = pii
                        break
                if pi is not None:
                    col2 = row.column(align=True)
                    col2.enabled = physics_settings.enable_physics
                    col2.prop(
                        obj.MustardUI_OutfitSettings,
                        "enable_pi_physics",
                        text="",
                        icon="PHYSICS" if pi.type != "COLLISION" else "MOD_PHYSICS",
                    )
                    if pi.type != "COLLISION":
                        col2 = row.column(align=True)
                        col2.enabled = physics_settings.enable_physics
                        col2.prop(
                            obj.MustardUI_OutfitSettings,
                            "enable_pi_collisions",
                            text="",
                            icon="MOD_PHYSICS",
                        )
                elif rig_settings.hair_physics_support:
                    m = find_physics_modifier(obj)
                    if m is not None:
                        row.prop(
                            obj.MustardUI_OutfitSettings,
                            "physics",
                            text="",
                            icon="PHYSICS" if m.type != "COLLISION" else "MOD_PHYSICS",
                        )

                if hair_num > 0:
                    if rig_settings.hair_custom_properties_name_order:
                        custom_properties_obj = sorted(
                            [x for x in arm.MustardUI_CustomPropertiesHair if x.hair == obj],
                            key=lambda x: x.name,
                        )
                    else:
                        custom_properties_obj = [
                            x for x in arm.MustardUI_CustomPropertiesHair if x.hair == obj
                        ]
                    if len(custom_properties_obj) > 0:
                        row.prop(
                            obj.MustardUI_OutfitSettings,
                            "additional_options_show",
                            toggle=True,
                            icon="PREFERENCES",
                        )
                        if obj.MustardUI_OutfitSettings.additional_options_show:
                            mustardui_custom_properties_print(
                                arm,
                                settings,
                                custom_properties_obj,
                                layout,
                                rig_settings.hair_custom_properties_icons,
                            )
            except Exception:
                box = layout.box()
                box.label(text="An error occurred.", icon="ERROR")
                box.label(text="The UI Hair data seems corrupted.", icon="BLANK1")
                if addon_prefs.developer:
                    box.label(text="Enter and exit Configuration mode to fix.", icon="BLANK1")
                    box.operator(
                        "mustardui.configuration",
                        text="Enter Configuration Mode",
                        icon="PREFERENCES",
                    )


def hair_dynamics_panel(layout, rig_settings, mod):
    # Generic nodes
    if not (mod.node_group and mod.node_group.name.startswith(HAIR_DYNAMICS_NODE_GROUP)):
        col = layout.column(align=True)
        draw_geometry_nodes_modifier_inputs(col, geometry_nodes_modifier_inputs(mod))
        return

    # Blender default Hair Dynamics nodes
    HAIR_DYNAMICS_UI_FIELDS = [
        ("mass", "Mass"),
        ("time_scale", "Time Scale"),
        ("separator", ""),
        ("stretchiness", "Stretchiness"),
        ("bendiness", "Bendiness"),
        ("root_bendiness", "Root Bendiness"),
        ("friction", "Friction"),
        ("separator", ""),
        ("linear_damping", "Linear Damping"),
        ("angular_damping", "Angular Damping"),
        ("separator", ""),
        ("effectors_collection", "Collider Collection"),
    ]
    HAIR_DYNAMICS_UI_ADVANCED_FIELDS = [
        ("substeps", "Substeps"),
        ("constraint_steps", "Constraint Steps"),
    ]

    inputs = mod.properties.inputs

    col = layout.column(align=True)
    for key, label in HAIR_DYNAMICS_UI_FIELDS:
        if key == "separator":
            col.separator()
            continue
        socket = HAIR_DYNAMICS_SOCKETS.get(key)
        entry = getattr(inputs, socket, None) if socket else None
        if entry is None:
            continue
        col.prop(entry, "value", text=label)

    if ui_collapse_prop(layout, rig_settings, "collapse_hair_dynamics_advanced", "Advanced"):
        col = layout.column(align=True)
        for key, label in HAIR_DYNAMICS_UI_ADVANCED_FIELDS:
            socket = HAIR_DYNAMICS_SOCKETS.get(key)
            entry = getattr(inputs, socket, None) if socket else None
            if entry is None:
                continue
            col.prop(entry, "value", text=label)


class PANEL_PT_MustardUI_Hair_Dynamics(MainPanel, bpy.types.Panel):
    bl_label = ""
    bl_parent_id = "PANEL_PT_MustardUI_Hair"
    bl_options = {"DEFAULT_CLOSED", "HEADER_LAYOUT_EXPAND"}

    @classmethod
    def poll(cls, context):
        if can_draw_ui():
            return False

        res, arm = mustardui_active_object(context, config=0)
        if not res or arm is None:
            return False

        rig_settings = arm.MustardUI_RigSettings
        if not rig_settings.hair_physics_support:
            return False

        obj = context.scene.objects.get(rig_settings.hair_list)
        if obj is None or obj.type != "CURVES":
            return False

        modifier = find_physics_modifier(obj)
        return modifier is not None and modifier.type == "NODES"

    def draw_header(self, context):
        res, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings
        obj = context.scene.objects[rig_settings.hair_list]
        modifier = find_physics_modifier(obj)

        layout = self.layout

        if modifier.node_group and modifier.node_group.name.startswith(HAIR_DYNAMICS_NODE_GROUP):
            layout.label(text="Hair Dynamics Settings")
        elif modifier.node_group:
            layout.label(text=f"{modifier.node_group.name} Settings")
        else:
            layout.label(text="Physics Settings")

    def draw(self, context):
        res, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings
        obj = context.scene.objects[rig_settings.hair_list]
        modifier = find_physics_modifier(obj)

        layout = self.layout

        if modifier is None:
            return

        hair_dynamics_panel(layout, rig_settings, modifier)


class PANEL_PT_MustardUI_Hair_ParticleSettings(MainPanel, bpy.types.Panel):
    bl_label = ""
    bl_parent_id = "PANEL_PT_MustardUI_Hair"
    bl_options = {"HEADER_LAYOUT_EXPAND"}

    @classmethod
    def poll(cls, context):

        if can_draw_ui():
            return False

        res, arm = mustardui_active_object(context, config=0)

        if arm is None:
            return False

        rig_settings = arm.MustardUI_RigSettings

        if rig_settings.hair_list == "":
            return False

        obj = context.scene.objects[rig_settings.hair_list]
        mod_particle_system = sorted(
            [x for x in obj.modifiers if x.type == "PARTICLE_SYSTEM"],
            key=format_dynamic_name,
        )

        return res if obj is not None and len(mod_particle_system) > 0 else False

    def draw_header(self, context):
        res, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings

        layout = self.layout

        layout.label(text="Particles Settings")

        obj = context.scene.objects[rig_settings.hair_list]

        mod_particle_system = sorted(
            [x for x in obj.modifiers if x.type == "PARTICLE_SYSTEM"],
            key=format_dynamic_name,
        )

        row = layout.row(align=True)
        row.enabled = rig_settings.hair_show
        if any("Dynamic" in x.particle_system.name for x in mod_particle_system):
            status = any(x.particle_system.use_hair_dynamics for x in mod_particle_system)
            op = row.operator(
                "mustardui.physics_particlehair_switch",
                text="",
                icon="PHYSICS",
                depress=status,
            )
            op.enable = not status
            op.obj = obj.name

        row = layout.row(align=True)
        row.enabled = rig_settings.hair_show
        row.prop(
            rig_settings,
            "hair_particle_hide_viewport",
            icon="RESTRICT_VIEW_ON"
            if not rig_settings.hair_particle_hide_viewport
            else "RESTRICT_VIEW_OFF",
            text="",
            emboss=True,
        )
        row.prop(
            rig_settings,
            "hair_particle_hide_render",
            icon="RESTRICT_RENDER_ON"
            if not rig_settings.hair_particle_hide_render
            else "RESTRICT_RENDER_OFF",
            text="",
            emboss=True,
        )

    def draw(self, context):
        res, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings

        layout = self.layout
        layout.enabled = rig_settings.hair_show

        obj = context.scene.objects[rig_settings.hair_list]

        mod_particle_system = sorted(
            [x for x in obj.modifiers if x.type == "PARTICLE_SYSTEM"],
            key=format_dynamic_name,
        )

        row = layout.row(align=True)
        row.prop(
            rig_settings,
            "hair_particle_children_viewport_factor",
            text="Density (Viewport)",
        )

        col = layout.column()
        for mod in mod_particle_system:
            row = col.row(align=True)
            row.label(text=format_dynamic_name(mod), icon="PARTICLES")
            row2 = row.row(align=True)
            if "Dynamic" in mod.particle_system.name:
                row2.prop(mod.particle_system, "use_hair_dynamics", text="", icon="PHYSICS")
            row2.prop(mod, "show_viewport", text="")
            row2.prop(mod, "show_render", text="")


class PANEL_PT_MustardUI_Hair_Extras(MainPanel, bpy.types.Panel):
    bl_label = "Extras"
    bl_parent_id = "PANEL_PT_MustardUI_Hair"
    bl_options = {"HEADER_LAYOUT_EXPAND"}

    @classmethod
    def poll(cls, context):

        if can_draw_ui():
            return False

        res, arm = mustardui_active_object(context, config=0)

        if arm is None:
            return False

        rig_settings = arm.MustardUI_RigSettings

        hair_extras_collection = rig_settings.hair_extras_collection
        model_body = rig_settings.model_body

        hair_extras_avail = hair_extras_collection is not None and any(
            obj.type in {"MESH", "CURVES"} for obj in hair_extras_collection.objects
        )
        particle_avail = (
            model_body is not None
            and rig_settings.particle_systems_enable
            and any(mod.type == "PARTICLE_SYSTEM" for mod in model_body.modifiers)
        )

        return res if (hair_extras_avail or particle_avail) else False

    def draw(self, context):
        res, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings
        physics_settings = arm.MustardUI_PhysicsSettings

        hair_extras_collection = rig_settings.hair_extras_collection

        layout = self.layout
        layout.enabled = rig_settings.hair_show

        settings = bpy.context.scene.MustardUI_Settings

        box_already_allocated = False
        col = None
        if hair_extras_collection is not None:
            eitems = hair_extras_list_make(rig_settings)
            if len(eitems) > 0:
                col = layout.column()
                box_already_allocated = True

            for obj in eitems:
                row = col.row(align=True)
                if not draw_hair_piece(row, obj, arm, rig_settings, physics_settings, settings):
                    row.label(text="", icon="BLANK1")

        # Particle systems
        if rig_settings.particle_systems_enable:
            mod_particle_system = sorted(
                [x for x in rig_settings.model_body.modifiers if x.type == "PARTICLE_SYSTEM"],
                key=lambda x: x.particle_system.name,
            )
            if len(mod_particle_system) > 0 and not box_already_allocated:
                col = layout.column()

            for mod in mod_particle_system:
                row = col.row()
                op = row.operator(
                    "mustardui.hair_visibility_extras_particle_system",
                    text=mod.particle_system.name,
                    icon="PARTICLES",
                    depress=mod.show_viewport,
                )
                op.obj_name = rig_settings.model_body.name
                op.mod_name = mod.name


class PANEL_PT_MustardUI_Hair_GlobalProperties(MainPanel, bpy.types.Panel):
    bl_label = "Global Properties"
    bl_parent_id = "PANEL_PT_MustardUI_Hair"
    bl_options = {"HEADER_LAYOUT_EXPAND"}

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)

        if arm is None:
            return False

        rig_settings = arm.MustardUI_RigSettings

        hair_global_properties_avail = sum(
            1 for x in arm.MustardUI_CustomPropertiesHair if x.hair is None
        )
        if rig_settings.hair_collection is not None:
            return res if hair_global_properties_avail else False

        return False

    def draw(self, context):
        settings = bpy.context.scene.MustardUI_Settings

        res, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings

        layout = self.layout
        layout.enabled = rig_settings.hair_show

        hair_global_properties = [x for x in arm.MustardUI_CustomPropertiesHair if x.hair is None]
        mustardui_custom_properties_print(
            arm,
            settings,
            hair_global_properties,
            layout,
            rig_settings.hair_custom_properties_icons,
            boxed=False,
        )


class PANEL_PT_MustardUI_Hair_Optimize(MainPanel, bpy.types.Panel):
    bl_label = ""
    bl_parent_id = "PANEL_PT_MustardUI_Hair"
    bl_options = {"HEADER_LAYOUT_EXPAND"}

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)

        if arm is None:
            return False

        rig_settings = arm.MustardUI_RigSettings

        global_settings_avail = (
            rig_settings.hair_enable_global_subsurface
            or rig_settings.hair_enable_global_smoothcorrection
            or rig_settings.hair_enable_global_solidify
            or rig_settings.hair_enable_global_particles
        )
        if rig_settings.hair_collection is not None:
            hair_num = len(
                [x for x in rig_settings.hair_collection.objects if x.type in {"MESH", "CURVES"}]
            )
            return res if (global_settings_avail and hair_num) else False

        return False

    def draw_header(self, context):
        poll, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings

        layout = self.layout

        row = layout.row(align=True)
        row.label(text="Optimize")

        row2 = row.row(align=True)
        row2.enabled = rig_settings.hair_show
        row2.operator(
            "mustardui.hair_switchglobal", text="", icon="RESTRICT_VIEW_OFF"
        ).enable = True
        row2.operator(
            "mustardui.hair_switchglobal", text="", icon="RESTRICT_VIEW_ON"
        ).enable = False

    def draw(self, context):
        res, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings

        layout = self.layout
        layout.enabled = rig_settings.hair_show

        col = layout.column(align=True)
        if rig_settings.hair_enable_global_subsurface:
            col.prop(rig_settings, "hair_global_subsurface")
        if rig_settings.hair_enable_global_smoothcorrection:
            col.prop(rig_settings, "hair_global_smoothcorrection")
        if rig_settings.hair_enable_global_solidify:
            col.prop(rig_settings, "hair_global_solidify")
        if rig_settings.hair_enable_global_particles:
            col.prop(rig_settings, "hair_global_particles")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_Hair)
    bpy.utils.register_class(PANEL_PT_MustardUI_Hair_Dynamics)
    bpy.utils.register_class(PANEL_PT_MustardUI_Hair_ParticleSettings)
    bpy.utils.register_class(PANEL_PT_MustardUI_Hair_GlobalProperties)
    bpy.utils.register_class(PANEL_PT_MustardUI_Hair_Extras)
    bpy.utils.register_class(PANEL_PT_MustardUI_Hair_Optimize)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Hair_Optimize)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Hair_Extras)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Hair_GlobalProperties)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Hair_ParticleSettings)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Hair_Dynamics)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Hair)
