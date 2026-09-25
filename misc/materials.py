import bpy


def material_uses_nodes(material):
    """Check whether the material is rendered through its node tree."""

    if material is None or material.node_tree is None:
        return False

    return True if bpy.app.version >= (5, 0, 0) else material.use_nodes
