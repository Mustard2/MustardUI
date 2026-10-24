import os

import bpy


def blender_asset(file):
    """Path of a node assets file bundled with Blender, empty if missing"""
    # Blender 4.x stores the assets in 'geometry_nodes', 5.x in 'nodes'
    for folder in ("nodes", "geometry_nodes"):
        # Blender's lookup of the local, system and environment datafiles, only resolving folders
        directory = bpy.utils.system_resource("DATAFILES", path=f"assets/{folder}")
        path = os.path.join(directory, file)
        if directory and os.path.isfile(path):
            return path
    return ""


def blender_node_group(file, name):
    """Node group of the Blender bundled assets, appended if not in the file"""
    if name in bpy.data.node_groups:
        return bpy.data.node_groups[name]
    path = blender_asset(file)
    if not path:
        return None
    with bpy.data.libraries.load(path) as (source, target):
        target.node_groups = [x for x in source.node_groups if x == name]
    return target.node_groups[0] if target.node_groups else None


def geometry_nodes_modifier_inputs(modifier):
    if modifier.node_group is None:
        return []

    interface = modifier.node_group.interface.items_tree

    items = [
        item
        for key, item in interface.items()
        if isinstance(getattr(interface[key], "identifier", None), str)
        and not item.hide_in_modifier
        and not item.socket_type == "NodeSocketMenu"
    ]

    drawable = []

    if tuple(bpy.app.version) >= (5, 2, 0):
        # Every input of the modifier is its own struct holding 'value'
        modifier_inputs = modifier.properties.inputs
        for item in items:
            entry = getattr(modifier_inputs, item.identifier, None)
            if (
                entry is not None
                and hasattr(entry, "bl_rna")
                and "value" in entry.bl_rna.properties
            ):
                drawable.append((item, entry, "value"))
    else:
        # Before 5.2, every input is a flat custom property on the modifier
        for item in items:
            if item.identifier in modifier.keys():
                drawable.append((item, modifier, f'["{item.identifier}"]'))

    return drawable


def node_group_has_simulation(node_group, visited=None):
    if node_group is None:
        return False

    if visited is None:
        visited = set()
    if node_group.name in visited:
        return False
    visited.add(node_group.name)

    for node in node_group.nodes:
        if node.bl_idname == "GeometryNodeSimulationInput":
            return True
        if node.type == "GROUP" and node_group_has_simulation(node.node_tree, visited):
            return True

    return False


def draw_geometry_nodes_modifier_inputs(layout, drawable):
    for item, target, prop_path in drawable:
        layout.prop(target, prop_path, text=item.name)
