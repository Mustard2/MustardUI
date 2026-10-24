import bpy

from ..misc.geometry_nodes import blender_asset

# ----------------------------------------------------------------------------
# Cloth Dynamics (Experimental) node group (Blender 5.2)
# ----------------------------------------------------------------------------

# Blender assets file of the Cloth and Hair Dynamics node groups
DYNAMICS_ASSET = "geometry_nodes_dynamics_assets.blend"

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


def cloth_dynamics_available():
    return bpy.app.version >= (5, 2, 0) and bool(blender_asset(DYNAMICS_ASSET))


# ----------------------------------------------------------------------------
# Hair Dynamics node group
# ----------------------------------------------------------------------------

HAIR_DYNAMICS_NODE_GROUP = "Hair Dynamics"
HAIR_DYNAMICS_SOCKETS = {
    "substeps": "Socket_6",
    "constraint_steps": "Socket_10",
    "time_scale": "Socket_45",
    "mass": "Socket_36",
    "friction": "Socket_34",
    "stretchiness": "Socket_19",
    "bendiness": "Socket_20",
    "root_bendiness": "Socket_35",
    "linear_damping": "Socket_13",
    "angular_damping": "Socket_14",
    "effectors_collection": "Socket_27",
}
# Inputs added by MustardUI to its copy, by name as their identifiers follow the asset inputs
HAIR_DYNAMICS_MUSTARDUI_SOCKETS = {
    "simulation_space": "Simulation Space",
    "pin_stiffness": "Pin Stiffness",
}


def hair_dynamics_input(modifier, key):
    """Input of a Hair Dynamics modifier, None if its node group does not have it"""
    identifier = HAIR_DYNAMICS_SOCKETS.get(key)
    if identifier is None:
        identifier = next(
            (
                x.identifier
                for x in modifier.node_group.interface.items_tree
                if x.item_type == "SOCKET"
                and x.in_out == "INPUT"
                and x.name == HAIR_DYNAMICS_MUSTARDUI_SOCKETS[key]
            ),
            None,
        )
    return getattr(modifier.properties.inputs, identifier, None) if identifier else None


# Children of the particle hair converted to curves, and their on/off input
HAIR_CHILDREN_MODIFIER = "Hair Children"
HAIR_CHILDREN_SWITCH = "Children"

hair_dynamics_available = cloth_dynamics_available


def register():
    return


def unregister():
    return
