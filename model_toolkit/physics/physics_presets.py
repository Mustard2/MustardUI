import bpy

from ...misc.geometry_nodes import blender_node_group, node_group_has_simulation
from ...misc.move_modifier import move_modifier
from ...physics.definitions_nodes import (
    CLOTH_DYNAMICS_NODE_GROUP,
    DYNAMICS_ASSET,
    JIGGLE_DYNAMICS_NODE_GROUP,
    cloth_dynamics_available,
    jiggle_dynamics_available,
    jiggle_dynamics_node_group,
    modifier_input,
)

# ----------------------------------------------------------------------------
# Presets
# ----------------------------------------------------------------------------

# Cloth modifier presets.
# 'settings' and 'collisions' are written as they are on the modifier, so the keys
# are the names of the Blender properties.
# 'fps_time_scale' re-scales the speed of the simulation on the frame rate of the
# scene, taking the value as the one meant for 24 fps
CLOTH_PRESETS = [
    (
        "CAGE",
        "Cage Physics",
        "The Jiggle Cage settings, with a faster simulation and a much stronger "
        "pressure.\nMeant for the cages generated from a vertex selection",
        {
            "quality": 7,
            "time_scale": 0.340,
            "mass": 0.3,
            "air_damping": 1,
            "bending_model": "ANGULAR",
            "tension_stiffness": 1,
            "compression_stiffness": 0.1,
            "shear_stiffness": 0.02,
            "bending_stiffness": 0.02,
            "tension_damping": 1,
            "compression_damping": 0.1,
            "shear_damping": 0.02,
            "bending_damping": 0.02,
            "use_internal_springs": True,
            "use_pressure": True,
            "internal_spring_max_length": 0,
            "internal_spring_max_diversion": 0.785398,
            "internal_spring_normal_check": True,
            "internal_tension_stiffness": 0.1,
            "internal_compression_stiffness": 0.1,
            "internal_tension_stiffness_max": 0.3,
            "internal_compression_stiffness_max": 0.3,
            "uniform_pressure_force": 0.06,
            "use_pressure_volume": False,
            "target_volume": 0,
            "pressure_factor": 10000,
            "fluid_density": 0,
            "pin_stiffness": 1,
            "use_sewing_springs": False,
            "sewing_force_max": 0,
            "shrink_min": 0,
            "use_dynamic_mesh": False,
            "tension_stiffness_max": 15,
            "compression_stiffness_max": 15,
            "shear_stiffness_max": 5,
            "bending_stiffness_max": 0.5,
            "shrink_max": 0,
        },
        {
            "collision_quality": 2,
            "use_collision": False,
            "distance_min": 0.001,
            "impulse_clamp": 0,
            "use_self_collision": False,
            "self_friction": 5,
            "self_distance_min": 0.001,
            "self_impulse_clamp": 0,
        },
        False,
    ),
    (
        "JIGGLE",
        "Jiggle Cage Physics",
        "Soft and bouncy, with internal springs and pressure holding the volume.\n"
        "Collisions are disabled: the cage is meant to be driven, not to collide",
        {
            "quality": 7,
            "time_scale": 0.240,
            "mass": 0.3,
            "air_damping": 1,
            "bending_model": "ANGULAR",
            "tension_stiffness": 1,
            "compression_stiffness": 0.1,
            "shear_stiffness": 0.02,
            "bending_stiffness": 0.02,
            "tension_damping": 1,
            "compression_damping": 0.1,
            "shear_damping": 0.02,
            "bending_damping": 0.02,
            "use_internal_springs": True,
            "use_pressure": True,
            "internal_spring_max_length": 0,
            "internal_spring_max_diversion": 0.785398,
            "internal_spring_normal_check": True,
            "internal_tension_stiffness": 0.1,
            "internal_compression_stiffness": 0.1,
            "internal_tension_stiffness_max": 0.3,
            "internal_compression_stiffness_max": 0.3,
            "uniform_pressure_force": 0.06,
            "use_pressure_volume": False,
            "target_volume": 0,
            "pressure_factor": 1,
            "fluid_density": 0,
            "pin_stiffness": 1,
            "use_sewing_springs": False,
            "sewing_force_max": 0,
            "shrink_min": 0,
            "use_dynamic_mesh": False,
            "tension_stiffness_max": 15,
            "compression_stiffness_max": 15,
            "shear_stiffness_max": 5,
            "bending_stiffness_max": 0.5,
            "shrink_max": 0,
        },
        {
            "collision_quality": 2,
            "use_collision": False,
            "distance_min": 0.015,
            "impulse_clamp": 0,
            "use_self_collision": False,
            "self_friction": 5,
            "self_distance_min": 0.015,
            "self_impulse_clamp": 0,
        },
        False,
    ),
    (
        "HAIR",
        "Hair Physics",
        "Heavier and stiffer in bending, with collisions enabled and a small "
        "collision distance.\nMeant for the hair cages",
        {
            "quality": 7,
            "time_scale": 1.0,
            "mass": 1.0,
            "shear_stiffness": 0.1,
            "bending_stiffness": 1,
        },
        {
            "collision_quality": 2,
            "use_collision": True,
            "distance_min": 0.001,
            "use_self_collision": False,
            "self_distance_min": 0.001,
        },
        True,
    ),
    (
        "ACCESSORY",
        "Accessory Physics",
        "Heavy and hardly stretching, with collisions and very stiff Rigid parts.\n"
        "Meant for the necklaces, chains and pendants",
        {
            "quality": 15,
            "time_scale": 1.0,
            "mass": 0.3,
            "air_damping": 2,
            "bending_model": "ANGULAR",
            "tension_stiffness": 80,
            "compression_stiffness": 80,
            "shear_stiffness": 20,
            "bending_stiffness": 0.2,
            "tension_damping": 10,
            "compression_damping": 10,
            "shear_damping": 5,
            "bending_damping": 0.5,
            "pin_stiffness": 1,
            "tension_stiffness_max": 200,
            "compression_stiffness_max": 200,
            "shear_stiffness_max": 200,
            "bending_stiffness_max": 200,
        },
        {
            "collision_quality": 4,
            "use_collision": True,
            "distance_min": 0.001,
            "impulse_clamp": 0.02,
            "use_self_collision": False,
        },
        True,
    ),
]


# Geometry Nodes presets, each with the node group it runs and the values of its inputs by name.
# The Jiggle Dynamics values are fitted at 24 fps on the motion of the Cloth presets of the
# same name, gravity included, on Hinata's cages (hops, walk and run). The low Speed is the slow
# motion of the Cloth presets as Time Scale, keeping the sag small next to the swing
NODES_PRESETS = [
    (
        "CAGE",
        "Cage Physics",
        "Soft flesh that swings with the motion and settles under its weight.\n"
        "Matched on the motion of the Cloth Cage preset, for the cages generated from a "
        "vertex selection",
        JIGGLE_DYNAMICS_NODE_GROUP,
        {
            "Softness": 0.16,
            "Mass": 2.45,
            "Time Scale": 0.24,
            "Damping": 0.717,
            "Wobble": 0.744,
            "Sway": 0.505,
            "Stretching": 0.0478,
            "Bending": 0.133,
            "Preserve Volume": 0.903,
            "Gravity": True,
            "Collisions": False,
        },
    ),
    (
        "JIGGLE",
        "Jiggle Cage Physics",
        "Soft flesh that swings with the motion and settles under its weight.\n"
        "Matched on the motion of the Cloth Jiggle Cage preset",
        JIGGLE_DYNAMICS_NODE_GROUP,
        {
            "Softness": 0.274,
            "Mass": 1.53,
            "Time Scale": 0.141,
            "Damping": 0.0088,
            "Wobble": 0.536,
            "Sway": 0.0,
            "Stretching": 0.0981,
            "Bending": 0.145,
            "Preserve Volume": 0.0218,
            "Gravity": True,
            "Collisions": False,
        },
    ),
    (
        "HAIR",
        "Hair Physics",
        "Heavier, with a small collision radius and more bending resistance",
        CLOTH_DYNAMICS_NODE_GROUP,
        {
            "Mass": 1.0,
            "Substeps": 5,
            "Constraint Steps": 15,
            "Bendiness": 0.2,
            "Collision Radius": 0.004,
            "Linear Damping": 1.0,
        },
    ),
]


NODES_ENGINE_NAMES = {
    JIGGLE_DYNAMICS_NODE_GROUP: "Jiggle Dynamics",
    CLOTH_DYNAMICS_NODE_GROUP: "Cloth Dynamics",
}


def _items(presets):
    return [(identifier, name, description) for identifier, name, description, *_ in presets]


CLOTH_PRESET_ITEMS = _items(CLOTH_PRESETS)
NODES_PRESET_ITEMS = _items(NODES_PRESETS)

CLOTH_PRESETS_BY_ID = {p[0]: p for p in CLOTH_PRESETS}
NODES_PRESETS_BY_ID = {p[0]: p for p in NODES_PRESETS}

PHYSICS_ENGINE_ITEMS = [
    (
        "CLOTH",
        "Cloth",
        "Use the Cloth modifier.\nAvailable on every supported version of Blender",
        "MOD_CLOTH",
        0,
    ),
    (
        "NODES",
        "Dynamics",
        "Use the Geometry Nodes physics built on the solver added in Blender 5.2: Jiggle "
        "Dynamics for the jiggle presets, Cloth Dynamics for the hair one.\nNot available "
        "on Blender 5.1 and earlier",
        "GEOMETRY_NODES",
        1,
    ),
]


# ----------------------------------------------------------------------------
# Properties and drawing, so every tool offers the same choice
# ----------------------------------------------------------------------------


def physics_engine_property():
    return bpy.props.EnumProperty(
        name="Physics",
        description="Simulation added to the mesh",
        items=PHYSICS_ENGINE_ITEMS,
        default="CLOTH",
    )


def cloth_preset_property(default="JIGGLE"):
    return bpy.props.EnumProperty(
        name="Preset",
        description="Settings applied to the Cloth modifier",
        items=CLOTH_PRESET_ITEMS,
        default=default,
    )


def nodes_preset_property(default="JIGGLE"):
    return bpy.props.EnumProperty(
        name="Preset",
        description="Settings applied to the Geometry Nodes physics",
        items=NODES_PRESET_ITEMS,
        default=default,
    )


def nodes_available(preset):
    """Whether this Blender runs the node group of a Geometry Nodes preset"""
    if NODES_PRESETS_BY_ID[preset][3] == JIGGLE_DYNAMICS_NODE_GROUP:
        return jiggle_dynamics_available()
    return cloth_dynamics_available()


def draw_physics_presets(layout, operator):
    """Draw the engine and its preset"""
    available = nodes_available(operator.nodes_preset)
    engine = NODES_ENGINE_NAMES[NODES_PRESETS_BY_ID[operator.nodes_preset][3]]

    row = layout.row(align=True)
    row.enabled = available
    row.prop_enum(operator, "physics_engine", "CLOTH")
    row.prop_enum(operator, "physics_engine", "NODES", text=engine)
    if not available:
        layout.label(text=f"{engine} needs Blender 5.2", icon="INFO")
    layout.separator()

    if operator.physics_engine == "NODES" and available:
        layout.prop(operator, "nodes_preset")
    else:
        layout.prop(operator, "cloth_preset")


def selected_preset(operator):
    """Engine and preset identifier a tool is going to use."""
    if operator.physics_engine == "NODES" and nodes_available(operator.nodes_preset):
        return "NODES", operator.nodes_preset
    return "CLOTH", operator.cloth_preset


# ----------------------------------------------------------------------------
# Applying
# ----------------------------------------------------------------------------


def remove_physics(obj):
    """Remove the simulation of both engines from the object"""
    for modifier in [
        x
        for x in obj.modifiers
        if x.type == "CLOTH"
        or (
            x.type == "NODES"
            and x.node_group
            and x.node_group.name.startswith(
                (CLOTH_DYNAMICS_NODE_GROUP, JIGGLE_DYNAMICS_NODE_GROUP)
            )
        )
    ]:
        obj.modifiers.remove(modifier)


def _apply_cloth(obj, preset, pin_group_name, structural_group_name):
    identifier, name, description, settings, collisions, fps_time_scale = preset

    # Play every frame: the simulation is not evaluated correctly on skipped frames
    bpy.context.scene.sync_mode = "NONE"

    remove_physics(obj)

    cloth = obj.modifiers.new(name="Cloth", type="CLOTH")

    for key, value in settings.items():
        setattr(cloth.settings, key, value)
    for key, value in collisions.items():
        setattr(cloth.collision_settings, key, value)

    # The presets are written for 24 fps: the ones asking for it are re-scaled, so
    # that the simulation runs at the same speed whatever the frame rate
    if fps_time_scale:
        fps = bpy.context.scene.render.fps
        if fps > 0:
            cloth.settings.time_scale = settings.get("time_scale", 1.0) * 24.0 / fps

    if pin_group_name:
        cloth.settings.vertex_group_mass = pin_group_name

    # Assigning a structural group is what brings 'tension_stiffness_max' and
    # 'compression_stiffness_max' into play: without one the mesh only ever uses
    # the base values, and it is free to stretch
    if structural_group_name:
        cloth.settings.vertex_group_structural_stiffness = structural_group_name

    cloth.point_cache.frame_start = bpy.context.scene.frame_start
    cloth.point_cache.frame_end = bpy.context.scene.frame_end

    return cloth


def _apply_nodes(obj, preset, pin_group_name):
    identifier, name, description, group_name, inputs = preset
    jiggle = group_name == JIGGLE_DYNAMICS_NODE_GROUP

    bpy.context.scene.sync_mode = "NONE"

    remove_physics(obj)

    if jiggle:
        node_group = jiggle_dynamics_node_group()
    else:
        node_group = blender_node_group(DYNAMICS_ASSET, CLOTH_DYNAMICS_NODE_GROUP)
        if node_group is None:
            return None

    dynamics = obj.modifiers.new(name=NODES_ENGINE_NAMES[group_name], type="NODES")
    dynamics.node_group = node_group

    # Every input of the modifier is its own struct holding 'value', and the name
    # of the attribute when the input is driven by one instead ('type' switches
    # between the two)
    for key, value in inputs.items():
        modifier_input(dynamics, key).value = value

    if jiggle:
        # The Zone is what moves: the inverted Pin group, or the whole mesh without one
        zone = modifier_input(dynamics, "Zone")
        if pin_group_name:
            zone.type = "ATTRIBUTE"
            zone.attribute_name = pin_group_name
            modifier_input(dynamics, "Invert Zone").value = True
        else:
            zone.value = 1.0
    elif pin_group_name:
        pin_input = modifier_input(dynamics, "Pin Group")
        pin_input.type = "ATTRIBUTE"
        pin_input.attribute_name = pin_group_name

    return dynamics


def move_before_corrective_smooth(obj, modifier):
    """The simulation has to be evaluated before the Corrective Smooth."""
    corrective = [
        obj.modifiers.find(x.name) for x in obj.modifiers if x.type == "CORRECTIVE_SMOOTH"
    ]
    if corrective:
        bpy.context.view_layer.objects.active = obj
        move_modifier(obj, modifier, min(corrective))


def apply_physics(
    obj,
    engine="CLOTH",
    preset="JIGGLE",
    pin_group_name="",
    structural_group_name="",
):
    """Add the physics of a preset, returning the modifier or None"""
    if obj is None or obj.type != "MESH":
        return None

    if engine == "NODES":
        definition = NODES_PRESETS_BY_ID.get(preset)
        if definition is None or not nodes_available(preset):
            return None
        modifier = _apply_nodes(obj, definition, pin_group_name)
    else:
        definition = CLOTH_PRESETS_BY_ID.get(preset)
        if definition is None:
            return None
        modifier = _apply_cloth(obj, definition, pin_group_name, structural_group_name)

    if modifier is not None:
        move_before_corrective_smooth(obj, modifier)

    return modifier


def find_physics_modifier(obj):
    return next(
        (
            m
            for m in obj.modifiers
            if m.type in ("CLOTH", "SOFT_BODY", "COLLISION")
            or (m.type == "NODES" and node_group_has_simulation(m.node_group))
        ),
        None,
    )


def physics_pin_group(obj):
    """Pin group of the physics the object already has, empty if none"""
    for modifier in obj.modifiers:
        if modifier.type == "CLOTH":
            return modifier.settings.vertex_group_mass
        if modifier.type != "NODES" or modifier.node_group is None:
            continue
        if modifier.node_group.name.startswith(JIGGLE_DYNAMICS_NODE_GROUP):
            pin = modifier_input(modifier, "Zone")
            if not modifier_input(modifier, "Invert Zone").value:
                continue
        elif modifier.node_group.name.startswith(CLOTH_DYNAMICS_NODE_GROUP):
            pin = modifier_input(modifier, "Pin Group")
        else:
            continue
        if pin.type == "ATTRIBUTE":
            return pin.attribute_name
    return ""


def preset_name(engine, preset):
    """Name of a preset, as it is shown in the UI."""
    presets = NODES_PRESETS_BY_ID if engine == "NODES" else CLOTH_PRESETS_BY_ID
    definition = presets.get(preset)
    return definition[1] if definition else preset


def register():
    return


def unregister():
    return
