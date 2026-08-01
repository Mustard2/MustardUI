import bpy


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
                drawable.append((item.name, entry, "value"))
    else:
        # Before 5.2, every input is a flat custom property on the modifier
        for item in items:
            if item.identifier in modifier.keys():
                drawable.append((item.name, modifier, f'["{item.identifier}"]'))

    return drawable


def draw_geometry_nodes_modifier_inputs(layout, drawable):
    for label, target, prop_path in drawable:
        layout.prop(target, prop_path, text=label)
