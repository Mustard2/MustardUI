import bpy

from .get_ui_objects import get_ui_mesh_objects


def material_uses_nodes(material):
    """Check whether the material is rendered through its node tree."""

    if material is None or material.node_tree is None:
        return False

    return True if bpy.app.version >= (5, 0, 0) else material.use_nodes


def model_node_trees(rig_settings):
    """Node trees of the model materials, including the nested node groups."""

    trees = set()
    stack = [
        slot.material.node_tree
        for obj in get_ui_mesh_objects(rig_settings)
        for slot in obj.material_slots
        if material_uses_nodes(slot.material)
    ]

    while stack:
        tree = stack.pop()
        if tree is None or tree in trees:
            continue
        trees.add(tree)
        stack.extend(n.node_tree for n in tree.nodes if n.type == "GROUP")

    return trees
