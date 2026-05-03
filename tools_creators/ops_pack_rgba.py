import bpy


class MustardUI_ToolsCreators_PackRGBA(bpy.types.Operator):
    bl_idname = "mustardui.tools_creators_pack_rgba"
    bl_label = "Pack Grayscale to RGBA"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        node_tree = context.space_data.node_tree
        nodes = node_tree.nodes
        links = node_tree.links

        selected = [n for n in nodes if n.select and n.type == "TEX_IMAGE"]

        if not selected:
            self.report({"ERROR"}, "Select up to 4 image nodes")
            return {"CANCELLED"}

        if len(selected) > 4:
            self.report({"ERROR"}, "Max 4 images")
            return {"CANCELLED"}

        # Sort top → bottom
        selected.sort(key=lambda n: -n.location.y)

        images = [n.image for n in selected]

        # Validate images
        w, h = images[0].size
        for img in images:
            if img.size[0] != w or img.size[1] != h:
                self.report({"ERROR"}, "All images must have same resolution")
                return {"CANCELLED"}

        # Create new image
        packed = bpy.data.images.new("Packed_RGBA", width=w, height=h, alpha=True)
        packed.colorspace_settings.name = "Non-Color"

        # Load pixel data
        channels = []
        for img in images:
            img.colorspace_settings.name = "Non-Color"

            pixels = list(img.pixels[:])

            gray = []

            for i in range(0, len(pixels), 4):
                r = pixels[i]
                a = pixels[i + 3]

                if a < 1.0:
                    gray.append(a)
                else:
                    gray.append(r)

            channels.append(gray)

        # Fill missing channels
        while len(channels) < 4:
            channels.append([1.0] * (w * h))

        # Combine into RGBA
        result_pixels = []

        for i in range(w * h):
            result_pixels.extend(
                [
                    channels[0][i],  # R
                    channels[1][i],  # G
                    channels[2][i],  # B
                    channels[3][i],  # A
                ]
            )

        packed.pixels = result_pixels
        packed.update()

        # Create Image node
        img_node = nodes.new("ShaderNodeTexImage")
        img_node.image = packed
        img_node.location = (
            sum(n.location.x for n in selected) / len(selected),
            sum(n.location.y for n in selected) / len(selected),
        )

        # Create Separate Color node (NEW correct node)
        separate = nodes.new("ShaderNodeSeparateColor")
        separate.location = (img_node.location.x + 200, img_node.location.y)

        links.new(img_node.outputs["Color"], separate.inputs["Color"])

        # Store links BEFORE deleting nodes
        original_links = []
        for i, node in enumerate(selected):
            for link in node.outputs["Color"].links:
                original_links.append((i, link.to_socket))

        # Reconnect channels
        for i, to_socket in original_links:
            if i == 0:
                links.new(separate.outputs["Red"], to_socket)
            elif i == 1:
                links.new(separate.outputs["Green"], to_socket)
            elif i == 2:
                links.new(separate.outputs["Blue"], to_socket)
            elif i == 3:
                # Alpha directly from image node
                links.new(img_node.outputs["Alpha"], to_socket)

        # Remove old nodes
        for node in selected:
            nodes.remove(node)

        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_ToolsCreators_PackRGBA)


def unregister():
    bpy.utils.unregister_class(MustardUI_ToolsCreators_PackRGBA)
