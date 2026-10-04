import os

import bpy

from ...model_selection.active_object import ModelMode, active_object_operator_poll
from .effect import effects_available, new_control

NODE_GROUP = "MustardUI Hex Dissolve"
CONTROL_TYPE = "EFFECT_HEX_DISSOLVE"
RESOURCE = os.path.join(os.path.dirname(__file__), "resources", "hex_dissolve.blend")


def materials(objects):
    return {
        s.material for x in objects for s in x.material_slots if s.material and s.material.node_tree
    }


def effect_nodes(material):
    return [
        n
        for n in material.node_tree.nodes
        if n.type == "GROUP" and n.node_tree and n.node_tree.name.startswith(NODE_GROUP)
    ]


def effect_control(node):
    links = node.inputs["Control"].links
    return links[0].from_node.object if links else None


class MustardUI_ModelToolkit_HexDissolve(bpy.types.Operator):
    """Dissolve the materials of the selected meshes in glowing hexagons inside the sphere of a Control Empty, growing over them.\nMaterials shared with other objects dissolve on them too"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_hex_dissolve"
    bl_label = "Add Hex Dissolve"
    bl_options = {"REGISTER", "UNDO"}

    duration: bpy.props.IntProperty(
        name="Duration",
        default=48,
        min=1,
        description="Frames for the Control to grow over the meshes, from the current frame",
    )
    show: bpy.props.BoolProperty(
        name="Show",
        description="Shrink the Control instead, to show the meshes",
    )

    @classmethod
    def poll(cls, context):
        if not effects_available():
            cls.poll_message_set("Needs Blender 5.2")
            return False
        return active_object_operator_poll(context, config=ModelMode.MODEL_TOOLKIT) and bool(
            materials(context.selected_objects)
        )

    def execute(self, context):
        objects = [x for x in context.selected_objects if materials([x])]

        if NODE_GROUP not in bpy.data.node_groups:
            with bpy.data.libraries.load(RESOURCE) as (_, target):
                target.node_groups = [NODE_GROUP]

        control, low, high = new_control(objects, "Hex Dissolve", CONTROL_TYPE)
        radius = (high - low).length / 2 * 1.25
        frame = context.scene.frame_current
        start, end = (radius, 0.001) if self.show else (0.001, radius)
        # The current frame last, to leave the Control at its value
        for f, scale in ((frame + self.duration, end), (frame, start)):
            control.scale = (scale, scale, scale)
            control.keyframe_insert("scale", frame=f)

        # Wrap the surface shader of every output
        for material in materials(objects):
            nodes, links = material.node_tree.nodes, material.node_tree.links
            for output in [n for n in nodes if n.type == "OUTPUT_MATERIAL"]:
                surface = output.inputs["Surface"]
                if not surface.is_linked:
                    continue
                group = nodes.new("ShaderNodeGroup")
                group.node_tree = bpy.data.node_groups[NODE_GROUP]
                group.location = output.location
                coordinates = nodes.new("ShaderNodeTexCoord")
                coordinates.object = control
                coordinates.location = (output.location.x - 200, output.location.y)
                output.location.x += 250
                links.new(surface.links[0].from_socket, group.inputs["Shader"])
                links.new(coordinates.outputs["Object"], group.inputs["Control"])
                links.new(group.outputs["Shader"], surface)
            # Hidden parts should not cast shadows
            material.use_transparent_shadow = True

        self.report({"INFO"}, f"MustardUI - Hex Dissolve added to {len(objects)} objects.")
        return {"FINISHED"}


class MustardUI_ModelToolkit_RemoveHexDissolve(bpy.types.Operator):
    """Remove the Hex Dissolve from the materials of the selected meshes, and the Controls not used anymore"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_remove_hex_dissolve"
    bl_label = "Remove Hex Dissolve"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        return active_object_operator_poll(context, config=ModelMode.MODEL_TOOLKIT) and any(
            effect_nodes(m) for m in materials(context.selected_objects)
        )

    def execute(self, context):
        controls = set()
        for material in materials(context.selected_objects):
            nodes, links = material.node_tree.nodes, material.node_tree.links
            for group in effect_nodes(material):
                controls.add(effect_control(group))
                shader = group.inputs["Shader"].links
                for socket in [x.to_socket for x in group.outputs["Shader"].links]:
                    if shader:
                        links.new(shader[0].from_socket, socket)
                    if socket.node.type == "OUTPUT_MATERIAL":
                        socket.node.location = group.location
                for link in group.inputs["Control"].links:
                    nodes.remove(link.from_node)
                nodes.remove(group)

        used = {
            effect_control(n) for m in bpy.data.materials if m.node_tree for n in effect_nodes(m)
        }
        for control in controls - used - {None}:
            if control.MustardUI_tools_creators_type == CONTROL_TYPE:
                bpy.data.objects.remove(control)

        self.report({"INFO"}, "MustardUI - Hex Dissolve removed.")
        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_HexDissolve)
    bpy.utils.register_class(MustardUI_ModelToolkit_RemoveHexDissolve)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_RemoveHexDissolve)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_HexDissolve)
