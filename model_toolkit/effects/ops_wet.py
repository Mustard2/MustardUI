import os

import bpy

from .effect import (
    RemoveEffect,
    add_effect_modifier,
    effects_available,
    is_effect,
    materials,
    modifier_input,
    new_control,
    parent_control,
    shader_nodes,
    unwrap_shader,
    wrap_shader,
)

NODE_GROUP = "MustardUI Wet"
FILM = "MustardUI Wet Film"
MATERIAL = "MustardUI Wet Drops"
CONTROL_TYPE = "EFFECT_WET"
RESOURCE = os.path.join(os.path.dirname(__file__), "resources", "wet.blend")
# Tag of the Normal Map nodes added for the film
NORMAL_TAG = "MustardUI Wet Normal"


def normal_users(socket):
    """Sockets using the output socket for a normal, through reroutes"""
    for link in socket.links:
        if link.to_node.type == "REROUTE":
            yield from normal_users(link.to_node.outputs[0])
        elif link.to_node.type == "NORMAL_MAP" or "normal" in link.to_socket.name.lower():
            yield link.to_socket


def normal_maps(tree):
    """Normal Map nodes of the node tree and of its node groups"""
    for node in tree.nodes:
        if node.type == "NORMAL_MAP" and not node.get(NORMAL_TAG):
            yield node
        elif node.type == "GROUP" and node.node_tree:
            yield from normal_maps(node.node_tree)


def film_normal(material):
    """Normal of the material for the film, from its normal image outside the node groups"""
    nodes = material.node_tree.nodes
    for image in [n for n in nodes if n.type == "TEX_IMAGE"]:
        users = list(normal_users(image.outputs["Color"]))
        if not users:
            continue
        found = next((x.node for x in users if x.node.type == "NORMAL_MAP"), None)
        if found:
            return found.outputs["Normal"]
        # A Normal Map on the image, on its UV map, as strong as the ones in the node groups
        normal_map = nodes.new("ShaderNodeNormalMap")
        normal_map[NORMAL_TAG] = True
        uv = image.inputs["Vector"].links
        if uv and uv[0].from_node.type == "UVMAP":
            normal_map.uv_map = uv[0].from_node.uv_map
        inner = next(normal_maps(material.node_tree), None)
        if inner:
            normal_map.inputs["Strength"].default_value = inner.inputs["Strength"].default_value
        normal_map.location = (image.location.x + 300, image.location.y)
        material.node_tree.links.new(image.outputs["Color"], normal_map.inputs["Color"])
        return normal_map.outputs["Normal"]
    return None


class MustardUI_ModelToolkit_Wet(bpy.types.Operator):
    """Wet the selected meshes inside the sphere of a Control Empty covering them, with water drops and a glossy film on their materials, scale the Control to wet a part only.\nThe film shows only on the meshes with the effect\nBlender 5.2 or above is required"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_wet"
    bl_label = "Add Wet"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        return effects_available() and any(x.type == "MESH" for x in context.selected_objects)

    def execute(self, context):
        objects = [x for x in context.selected_objects if x.type == "MESH"]

        with bpy.data.libraries.load(RESOURCE) as (_, data):
            data.node_groups = [x for x in (NODE_GROUP, FILM) if x not in bpy.data.node_groups]
            if MATERIAL not in bpy.data.materials:
                data.materials = [MATERIAL]

        # The drops placed on the rest mesh, not to move on the deformed one
        for obj in objects:
            obj.add_rest_position_attribute = True
        depsgraph = context.evaluated_depsgraph_get()

        # Covering the meshes, following the vertex closest to its center
        control, low, high = new_control(objects, "Wet", CONTROL_TYPE)
        radius = (high - low).length
        control.scale = (radius, radius, radius)
        source, vertex = min(
            ((x, v) for x in objects for v in x.evaluated_get(depsgraph).data.vertices),
            key=lambda p: (p[0].matrix_world @ p[1].co - control.location).length_squared,
        )
        parent_control(control, source, vertex, depsgraph)
        # In the scene collection, not to be listed only under its bone parent in the Outliner
        control.users_collection[0].objects.unlink(control)
        context.scene.collection.objects.link(control)

        for obj in objects:
            modifier = add_effect_modifier(obj, "Wet", NODE_GROUP, control)
            modifier_input(modifier, "Material").value = bpy.data.materials[MATERIAL]
            modifier_input(modifier, "Start Frame").value = context.scene.frame_current
            # Changing the modifier inputs from Python does not tag the object
            obj.update_tag()
        for material in materials(objects):
            if not shader_nodes(material, FILM):
                groups = wrap_shader(material, FILM)
                normal = film_normal(material)
                for group in groups if normal else ():
                    material.node_tree.links.new(normal, group.inputs["Normal"])

        self.report({"INFO"}, f"MustardUI - Wet added to {len(objects)} objects.")
        return {"FINISHED"}


class MustardUI_ModelToolkit_RemoveWet(RemoveEffect, bpy.types.Operator):
    """Remove the Wet from the selected meshes, the film from their materials not used by other wet meshes, and the Controls not used anymore"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_remove_wet"
    bl_label = "Remove Wet"

    effect = "Wet"
    node_group = NODE_GROUP
    creators_type = CONTROL_TYPE

    def execute(self, context):
        result = super().execute(context)
        wet = materials(
            x for x in bpy.data.objects if any(is_effect(m, NODE_GROUP) for m in x.modifiers)
        )
        for material in materials(context.selected_objects) - wet:
            for group in shader_nodes(material, FILM):
                unwrap_shader(material, group)
            for node in [n for n in material.node_tree.nodes if n.get(NORMAL_TAG)]:
                material.node_tree.nodes.remove(node)
        return result


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_Wet)
    bpy.utils.register_class(MustardUI_ModelToolkit_RemoveWet)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_RemoveWet)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_Wet)
