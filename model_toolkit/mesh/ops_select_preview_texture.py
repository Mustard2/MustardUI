import bpy

from ...misc.get_ui_objects import get_ui_mesh_objects
from ...misc.materials import material_uses_nodes
from ...model_selection.active_object import (
    ModelMode,
    active_object_operator_poll,
    mustardui_active_object,
)


def find_base_color_image(socket, groups=(), base_color=False, visited=None):
    """First color image of the material tree feeding a Principled BSDF Base Color."""

    visited = set() if visited is None else visited

    for link in socket.links:
        node = link.from_node
        key = (groups, link.from_socket, base_color)
        if key in visited:
            continue
        visited.add(key)

        node_groups, node_base_color = groups, base_color
        if node.type == "GROUP":
            if not node.node_tree:
                continue
            nodes = node.node_tree.nodes
            output = next(
                (n for n in nodes if n.type == "GROUP_OUTPUT" and n.is_active_output), None
            )
            if not output:
                continue
            inputs = [output.inputs.get(link.from_socket.identifier)]
            node_groups = groups + (node,)
        elif node.type == "GROUP_INPUT":
            if not groups:
                continue
            inputs = [groups[-1].inputs.get(link.from_socket.identifier)]
            node_groups = groups[:-1]
        elif node.type == "BSDF_PRINCIPLED":
            inputs = [node.inputs["Base Color"]]
            node_base_color = True
        elif (
            base_color
            and not groups
            and node.type == "TEX_IMAGE"
            and node.image
            and not node.image.colorspace_settings.is_data
        ):
            return node
        else:
            inputs = node.inputs

        for input_socket in inputs:
            if input_socket and (
                image := find_base_color_image(input_socket, node_groups, node_base_color, visited)
            ):
                return image

    return None


class MustardUI_ModelToolkit_SelectPreviewTexture(bpy.types.Operator):
    bl_idname = "mustardui.model_toolkit_select_preview_texture"
    bl_label = "Select Solid Preview Texture"
    bl_options = {"REGISTER", "UNDO"}

    scene: bpy.props.BoolProperty(
        name="Whole Scene",
        description="Apply to the materials of every object in the scene",
        options={"SKIP_SAVE"},
    )

    @classmethod
    def description(cls, context, properties):
        if properties.scene:
            target = "every object in the scene"
        elif active_object_operator_poll(context, config=ModelMode.MODEL_TOOLKIT):
            target = "the model"
        else:
            target = "the selected objects"
        return f"Set Viewport Solid Mode preview texture for all materials of {target}"

    def execute(self, context):
        res, arm = mustardui_active_object(context, config=ModelMode.MODEL_TOOLKIT)
        if self.scene:
            objects = context.scene.objects
        elif res:
            objects = get_ui_mesh_objects(arm.MustardUI_RigSettings)
        else:
            objects = context.selected_objects

        # Materials shared by several objects are processed once
        materials = {slot.material for obj in objects for slot in obj.material_slots}

        processed = 0
        for material in materials:
            if not material_uses_nodes(material):
                continue

            nodes = material.node_tree.nodes
            output = next(
                (n for n in nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output), None
            )
            image = output and find_base_color_image(output.inputs["Surface"])
            if image:
                nodes.active = image
                processed += 1

        if not processed:
            self.report({"WARNING"}, "MustardUI - No preview textures found")
            return {"CANCELLED"}

        self.report({"INFO"}, f"MustardUI - Updated {processed} material previews")
        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_SelectPreviewTexture)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_SelectPreviewTexture)
