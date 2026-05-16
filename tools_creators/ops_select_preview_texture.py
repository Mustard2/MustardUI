import bpy


class MustardUI_ToolsCreators_SelectPreviewTexture(bpy.types.Operator):
    """Set Viewport Solid Mode preview texture for all materials of the Active Object"""

    bl_idname = "mustardui.tools_creators_select_preview_texture"
    bl_label = "Select Solid Preview Texture"
    bl_options = {"REGISTER", "UNDO"}

    PREVIEW_NODE_NAME = "__MUSTARDUI_PREVIEW__"

    @staticmethod
    def is_rgb_image_node(node):

        if node.type != "TEX_IMAGE":
            return False

        if not node.image:
            return False

        colorspace = node.image.colorspace_settings.name.lower().strip()

        # Explicitly allowed color spaces only
        allowed = {
            "srgb",
            "linear",
            "linear rec.709",
            "utility - linear - srgb",
        }

        return colorspace in allowed

    @staticmethod
    def find_principled_recursive(node_tree, parent_group=None):

        # Direct Principled
        for node in node_tree.nodes:
            if node.type == "BSDF_PRINCIPLED":
                return node, node_tree, parent_group

        # Search inside groups
        for node in node_tree.nodes:
            if node.type != "GROUP":
                continue

            if not node.node_tree:
                continue

            result = (
                MustardUI_ToolsCreators_SelectPreviewTexture.find_principled_recursive(
                    node.node_tree, node
                )
            )

            if result:
                return result

        return None

    @staticmethod
    def find_image_from_socket(socket, current_tree, parent_group=None, visited=None):

        if visited is None:
            visited = set()

        if not socket:
            return None

        if not socket.is_linked:
            return None

        for link in socket.links:
            from_node = link.from_node

            key = (current_tree, from_node.name)

            if key in visited:
                continue

            visited.add(key)

            # RGB image found
            if MustardUI_ToolsCreators_SelectPreviewTexture.is_rgb_image_node(
                from_node
            ):
                return from_node.image

            # Traverse normally inside same tree
            for input_socket in from_node.inputs:
                result = (
                    MustardUI_ToolsCreators_SelectPreviewTexture.find_image_from_socket(
                        input_socket, current_tree, parent_group, visited
                    )
                )

                if result:
                    return result

            # IMPORTANT:
            # If we hit GROUP_INPUT,
            # jump OUTSIDE the group
            if from_node.type == "GROUP_INPUT" and parent_group:
                for output_index, output_socket in enumerate(from_node.outputs):
                    if output_socket != link.from_socket:
                        continue

                    if output_index >= len(parent_group.inputs):
                        continue

                    outer_socket = parent_group.inputs[output_index]

                    result = MustardUI_ToolsCreators_SelectPreviewTexture.find_image_from_socket(  # noqa: E501
                        outer_socket, parent_group.id_data, None, visited
                    )

                    if result:
                        return result

        return None

    @classmethod
    def poll(cls, context):
        return context.active_object.type == "MESH"

    def execute(self, context):

        obj = context.object

        if not obj:
            self.report({"WARNING"}, "No active object")
            return {"CANCELLED"}

        processed = 0

        for slot in obj.material_slots:
            mat = slot.material

            if not mat:
                continue

            if not mat.use_nodes:
                continue

            if not mat.node_tree:
                continue

            node_tree = mat.node_tree

            principled_data = self.find_principled_recursive(node_tree)

            if not principled_data:
                continue

            principled, principled_tree, parent_group = principled_data

            socket = principled.inputs.get("Base Color")

            if not socket:
                continue

            image = self.find_image_from_socket(socket, principled_tree, parent_group)

            if not image:
                continue

            # Remove old preview node
            old_node = node_tree.nodes.get(self.PREVIEW_NODE_NAME)

            if old_node:
                node_tree.nodes.remove(old_node)

            # Create preview node
            preview_node = node_tree.nodes.new("ShaderNodeTexImage")

            preview_node.name = self.PREVIEW_NODE_NAME
            preview_node.label = self.PREVIEW_NODE_NAME

            preview_node.image = image

            preview_node.location = (-10000, -10000)
            preview_node.hide = True

            # Deselect all
            for node in node_tree.nodes:
                node.select = False

            # Set active node
            preview_node.select = True
            node_tree.nodes.active = preview_node

            processed += 1

        if processed == 0:
            self.report({"WARNING"}, "No RGB preview textures found")
            return {"CANCELLED"}

        self.report({"INFO"}, f"Updated {processed} material previews")

        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_ToolsCreators_SelectPreviewTexture)


def unregister():
    bpy.utils.unregister_class(MustardUI_ToolsCreators_SelectPreviewTexture)
