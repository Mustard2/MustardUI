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


def modifier_input_keys(modifier):
    """Inputs of a Geometry Nodes modifier set by value, by their name numbered when repeated"""
    if modifier.node_group is None or not hasattr(modifier, "properties"):
        return
    count = {}
    for item in modifier.node_group.interface.items_tree:
        if item.item_type != "SOCKET" or item.in_out != "INPUT":
            continue
        n = count[item.name] = count.get(item.name, 0) + 1
        socket = getattr(modifier.properties.inputs, item.identifier, None)
        if socket is not None and "value" in socket.bl_rna.properties:
            yield item.name if n == 1 else f"{item.name} ({n})", socket


def modifier_values(modifier):
    """Values of the inputs of a Geometry Nodes modifier, without attributes and data-blocks"""
    values = {}
    for key, socket in modifier_input_keys(modifier):
        if getattr(socket, "type", "") == "ATTRIBUTE":
            continue
        if socket.bl_rna.properties["value"].type == "POINTER":
            continue
        value = socket.value
        values[key] = value if isinstance(value, (bool, int, float, str)) else list(value)
    return values


def set_modifier_values(modifier, values):
    """Set the inputs of a Geometry Nodes modifier from modifier_values, returning the failures"""
    sockets = dict(modifier_input_keys(modifier))
    errors = 0
    for key, value in values.items():
        socket = sockets.get(key)
        if socket is None:
            errors += 1
        elif getattr(socket, "type", "") != "ATTRIBUTE":
            try:
                socket.value = value
            except (TypeError, ValueError):
                errors += 1
    # Changing the inputs from Python does not tag the object
    modifier.id_data.update_tag()
    return errors


def simulation_bakes(obj):
    """Geometry Nodes modifiers of the object, with the bakes of their simulations"""
    for modifier in obj.modifiers:
        if modifier.type == "NODES" and hasattr(modifier, "bakes"):
            for bake in modifier.bakes:
                if bake.node is not None and bake.node.bl_idname == "GeometryNodeSimulationOutput":
                    yield modifier, bake


def draw_geometry_nodes_modifier_inputs(layout, drawable):
    for item, target, prop_path in drawable:
        layout.prop(target, prop_path, text=item.name)


def draw_modifier_inputs(layout, modifier, select_objects=False, collisions=None):
    """Inputs of a Geometry Nodes modifier, in the panels of its node group"""
    if not hasattr(modifier, "properties"):
        # Before 5.2 the inputs are custom properties, without panels
        draw_geometry_nodes_modifier_inputs(layout, geometry_nodes_modifier_inputs(modifier))
        return

    inputs, panels = modifier.properties.inputs, modifier.properties.panels
    # Layout of the open panels, the root one being 0
    bodies = {0: layout}
    for item in modifier.node_group.interface.items_tree:
        body = bodies.get(item.parent.persistent_uid)
        if body is None:
            continue
        if item.item_type == "PANEL":
            header, bodies[item.persistent_uid] = body.panel_prop(
                panels, f"open_{item.persistent_uid}"
            )
            toggle = next(
                (x for x in item.interface_items if getattr(x, "is_panel_toggle", False)), None
            )
            # The panel with the colliders Collection is toggled by collisions, (data, property)
            colliders = any(
                getattr(x, "socket_type", "") == "NodeSocketCollection"
                for x in item.interface_items
            )
            if collisions and colliders:
                header.prop(*collisions, text=item.name)
                if bodies[item.persistent_uid]:
                    bodies[item.persistent_uid].active = getattr(*collisions)
                continue
            if toggle is None:
                header.label(text=item.name)
                continue
            toggle = getattr(inputs, toggle.identifier)
            header.prop(toggle, "value", text=item.name)
            if bodies[item.persistent_uid]:
                bodies[item.persistent_uid].active = toggle.value
            continue
        if item.in_out == "OUTPUT" or item.hide_value or item.hide_in_modifier:
            continue
        # Geometry, matrices, bundles and the like can't be set on the modifier
        socket = getattr(inputs, item.identifier, None)
        if socket is None or "value" not in socket.bl_rna.properties or item.is_panel_toggle:
            continue
        # Vectors in a column, not to squeeze their values
        vector = item.socket_type == "NodeSocketVector"
        row = body.column(align=True) if vector else body.row(align=True)
        if getattr(socket, "type", "") == "ATTRIBUTE":
            row.prop(socket, "attribute_name", text=item.name)
        else:
            row.prop(socket, "value", text=item.name)
        if select_objects and item.socket_type == "NodeSocketObject" and socket.value:
            row.operator(
                "mustardui.model_toolkit_select_object", text="", icon="RESTRICT_SELECT_OFF"
            ).name = socket.value.name
