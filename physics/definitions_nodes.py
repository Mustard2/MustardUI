import os

import bpy

from ..misc.geometry_nodes import blender_asset, blender_node_group


def modifier_input(modifier, name):
    """Input of a Geometry Nodes modifier by its name, None if its node group does not have it"""
    identifier = next(
        (
            x.identifier
            for x in modifier.node_group.interface.items_tree
            if x.item_type == "SOCKET" and x.in_out == "INPUT" and x.name == name
        ),
        None,
    )
    return getattr(modifier.properties.inputs, identifier, None) if identifier else None


def collection_inputs(modifier):
    """Inputs of a Geometry Nodes modifier taking a Collection, the colliders of its physics"""
    if modifier.node_group is None or not hasattr(modifier, "properties"):
        return []
    return [
        getattr(modifier.properties.inputs, x.identifier)
        for x in modifier.node_group.interface.items_tree
        if x.item_type == "SOCKET"
        and x.in_out == "INPUT"
        and x.socket_type == "NodeSocketCollection"
    ]


# ----------------------------------------------------------------------------
# Cloth Dynamics (Experimental) node group (Blender 5.2)
# ----------------------------------------------------------------------------

# Blender assets file of the Cloth and Hair Dynamics node groups
DYNAMICS_ASSET = "geometry_nodes_dynamics_assets.blend"

CLOTH_DYNAMICS_NODE_GROUP = "Cloth Dynamics (Experimental)"


def add_collider(obj, name="Collider"):
    """Deforming Collider for the Geometry Nodes physics, enabled with the collision cage"""
    if any(
        m.type == "NODES" and m.node_group and m.node_group.name.startswith("Collider")
        for m in obj.modifiers
    ):
        return
    group = blender_node_group(DYNAMICS_ASSET, "Collider")
    if group is None:
        return
    mod = obj.modifiers.new(name, "NODES")
    mod.node_group = group
    modifier_input(mod, "Deforming").value = True
    mod.show_viewport = mod.show_render = any(
        m.type == "COLLISION" and m.show_viewport for m in obj.modifiers
    )


def cloth_dynamics_available():
    return bpy.app.version >= (5, 2, 0) and bool(blender_asset(DYNAMICS_ASSET))


# ----------------------------------------------------------------------------
# Jiggle Dynamics node group (Blender 5.2), bundled with MustardUI
# ----------------------------------------------------------------------------

JIGGLE_DYNAMICS_NODE_GROUP = "MustardUI Jiggle Dynamics"
# Version of the bundled node group, the VERSION of its build script
JIGGLE_DYNAMICS_VERSION = 3
JIGGLE_DYNAMICS_RESOURCE = os.path.join(
    os.path.dirname(__file__), "resources", "jiggle_dynamics.blend"
)


def jiggle_dynamics_available():
    return bpy.app.version >= (5, 2, 0)


def jiggle_dynamics_node_group():
    """Jiggle Dynamics node group, appended if not in the file or older than the bundled one"""
    old = bpy.data.node_groups.get(JIGGLE_DYNAMICS_NODE_GROUP)
    if old is not None and old.get("MustardUI Version", 1) >= JIGGLE_DYNAMICS_VERSION:
        return old
    with bpy.data.libraries.load(JIGGLE_DYNAMICS_RESOURCE) as (_, target):
        target.node_groups = [JIGGLE_DYNAMICS_NODE_GROUP]
    new = target.node_groups[0]
    if old is not None:
        # The modifiers move to the new one, keeping their values
        old.user_remap(new)
        bpy.data.node_groups.remove(old)
        new.name = JIGGLE_DYNAMICS_NODE_GROUP
    return new


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
        return modifier_input(modifier, HAIR_DYNAMICS_MUSTARDUI_SOCKETS[key])
    return getattr(modifier.properties.inputs, identifier, None)


# Children of the particle hair converted to curves, and their on/off input
HAIR_CHILDREN_MODIFIER = "Hair Children"
HAIR_CHILDREN_SWITCH = "Children"

hair_dynamics_available = cloth_dynamics_available


def register():
    return


def unregister():
    return
