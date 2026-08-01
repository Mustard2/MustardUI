import os

import bpy

# ----------------------------------------------------------------------------
# Cloth Dynamics (Experimental) node group (Blender 5.2)
# ----------------------------------------------------------------------------

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
    return os.path.join(
        bpy.utils.resource_path("LOCAL"),
        "datafiles",
        "assets",
        "nodes",
        "geometry_nodes_dynamics_assets.blend",
    )


def cloth_dynamics_available():
    return bpy.app.version >= (5, 2, 0) and os.path.isfile(cloth_dynamics_asset())


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

hair_dynamics_available = cloth_dynamics_available


def register():
    return


def unregister():
    return
