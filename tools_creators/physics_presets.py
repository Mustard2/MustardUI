import os

import bpy

# ----------------------------------------------------------------------------
# Cloth Dynamics (Experimental) node group
# ----------------------------------------------------------------------------

# Node group bundled with the Essentials assets of Blender 5.2. The socket
# identifiers are the ones of the group interface, and are stable: the names shown
# in the UI are not
CLOTH_DYNAMICS_NODE_GROUP = "Cloth Dynamics (Experimental)"

CLOTH_DYNAMICS_SOCKETS = {
    "pin_group": "Socket_2",
    "invert_pin_group": "Socket_23",
    "stretchiness": "Socket_6",
    "bendiness": "Socket_30",
    "substeps": "Socket_14",
    "constraint_steps": "Socket_15",
    "mass": "Socket_31",
    "friction": "Socket_28",
    "collision_radius": "Socket_24",
    "linear_damping": "Socket_8",
    "gravity": "Socket_5",
    "effectors_collection": "Socket_7",
}


def cloth_dynamics_asset():
    """Path of the Blender asset holding the Cloth Dynamics node group."""
    return os.path.join(
        bpy.utils.resource_path("LOCAL"),
        "datafiles",
        "assets",
        "nodes",
        "geometry_nodes_dynamics_assets.blend",
    )


def cloth_dynamics_available():
    """Whether this Blender ships the Cloth Dynamics node group.

    The node group is bundled with the Essentials assets of Blender 5.2, together
    with the solver it is built on: on any earlier version the Geometry Nodes
    physics cannot be used at all.
    """
    return bpy.app.version >= (5, 2, 0) and os.path.isfile(cloth_dynamics_asset())


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
]

# Cloth Dynamics presets. The keys are the ones of CLOTH_DYNAMICS_SOCKETS, and the
# values are written on the inputs of the Geometry Nodes modifier
NODES_PRESETS = [
    (
        "JIGGLE",
        "Jiggle Cage Physics",
        "Soft and light, so that the cage swings freely",
        {
            "mass": 0.3,
            "substeps": 5,
            "constraint_steps": 15,
            "bendiness": 0.0,
            "linear_damping": 1.0,
        },
    ),
    (
        "CAGE",
        "Cage Physics",
        "Like the Jiggle Cage one, with more constraint steps to hold the shape of "
        "a cage generated from a vertex selection",
        {
            "mass": 0.3,
            "substeps": 5,
            "constraint_steps": 25,
            "bendiness": 0.0,
            "linear_damping": 1.0,
        },
    ),
    (
        "HAIR",
        "Hair Physics",
        "Heavier, with a small collision radius and more bending resistance",
        {
            "mass": 1.0,
            "substeps": 5,
            "constraint_steps": 15,
            "bendiness": 0.2,
            "collision_radius": 0.004,
            "linear_damping": 1.0,
        },
    ),
]


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
        "Cloth Dynamics",
        "Use the Cloth Dynamics (Experimental) Geometry Nodes, built on the solver "
        "added in Blender 5.2.\nNot available on Blender 5.1 and earlier",
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
        description="Settings applied to the Cloth Dynamics Geometry Nodes",
        items=NODES_PRESET_ITEMS,
        default=default,
    )


def draw_physics_presets(layout, operator):
    """Draw the engine and the preset of the engine currently selected.

    Two separate properties are used, and not a single list filtered on the engine,
    so that each tool keeps its own default on both of them and the enums stay
    static.
    """
    available = cloth_dynamics_available()

    row = layout.row()
    row.enabled = available
    row.prop(operator, "physics_engine", expand=True)
    if not available:
        layout.label(text="Cloth Dynamics needs Blender 5.2", icon="INFO")

    if operator.physics_engine == "NODES" and available:
        layout.prop(operator, "nodes_preset")
    else:
        layout.prop(operator, "cloth_preset")


def selected_preset(operator):
    """Engine and preset identifier a tool is going to use."""
    if operator.physics_engine == "NODES" and cloth_dynamics_available():
        return "NODES", operator.nodes_preset
    return "CLOTH", operator.cloth_preset


# ----------------------------------------------------------------------------
# Applying
# ----------------------------------------------------------------------------


def remove_physics(obj):
    """Remove the simulation of both engines from an object.

    Both are removed whichever engine is being applied: the two are alternatives,
    and leaving the other one behind would stack two simulations on the same mesh.
    """
    for modifier in [
        x
        for x in obj.modifiers
        if x.type == "CLOTH"
        or (
            x.type == "NODES"
            and x.node_group
            and x.node_group.name.startswith(CLOTH_DYNAMICS_NODE_GROUP)
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


def _cloth_dynamics_node_group():
    """Append the Cloth Dynamics node group, or reuse the one already in the file."""
    node_group = bpy.data.node_groups.get(CLOTH_DYNAMICS_NODE_GROUP)
    if node_group is not None:
        return node_group

    with bpy.data.libraries.load(cloth_dynamics_asset(), link=False) as (source, target):
        target.node_groups = [n for n in source.node_groups if n == CLOTH_DYNAMICS_NODE_GROUP]

    return target.node_groups[0] if target.node_groups else None


def _apply_nodes(obj, preset, pin_group_name):
    identifier, name, description, inputs = preset

    bpy.context.scene.sync_mode = "NONE"

    remove_physics(obj)

    node_group = _cloth_dynamics_node_group()
    if node_group is None:
        return None

    dynamics = obj.modifiers.new(name="Cloth Dynamics", type="NODES")
    dynamics.node_group = node_group

    # Every input of the modifier is its own struct holding 'value', and the name
    # of the attribute when the input is driven by one instead ('type' switches
    # between the two)
    modifier_inputs = dynamics.properties.inputs
    for key, value in inputs.items():
        socket = CLOTH_DYNAMICS_SOCKETS.get(key)
        if socket is not None:
            getattr(modifier_inputs, socket).value = value

    if pin_group_name:
        pin_input = getattr(modifier_inputs, CLOTH_DYNAMICS_SOCKETS["pin_group"])
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
        bpy.ops.object.modifier_move_to_index(modifier=modifier.name, index=min(corrective))


def apply_physics(
    obj,
    engine="CLOTH",
    preset="JIGGLE",
    pin_group_name="",
    structural_group_name="",
):
    """Add the physics of a preset to an object, replacing the one it may have.

    Returns the modifier which was added, or None if the Geometry Nodes physics was
    asked for and this Blender cannot provide it. The caller is expected to report
    that to the user and, if it makes sense, to fall back on the Cloth modifier.
    """
    if obj is None or obj.type != "MESH":
        return None

    if engine == "NODES":
        if not cloth_dynamics_available():
            return None
        definition = NODES_PRESETS_BY_ID.get(preset)
        if definition is None:
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


def preset_name(engine, preset):
    """Name of a preset, as it is shown in the UI."""
    presets = NODES_PRESETS_BY_ID if engine == "NODES" else CLOTH_PRESETS_BY_ID
    definition = presets.get(preset)
    return definition[1] if definition else preset


def register():
    return


def unregister():
    return
