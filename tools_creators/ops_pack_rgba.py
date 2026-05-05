import bpy

# Try NumPy
try:
    import numpy as np

    USE_NUMPY = True
except ImportError:
    USE_NUMPY = False


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
            self.report({"ERROR"}, "MustardUI - Select up to 4 image nodes")
            return {"CANCELLED"}

        if len(selected) > 4:
            self.report({"ERROR"}, "MustardUI - Select max 4 images")
            return {"CANCELLED"}

        # Sort top → bottom
        selected.sort(key=lambda n: -n.location.y)

        images = [n.image for n in selected]

        # Validate images
        w, h = images[0].size
        for img in images:
            if img.size[0] != w or img.size[1] != h:
                self.report(
                    {"ERROR"}, "MustardUI - All images must have same resolution"
                )
                return {"CANCELLED"}

        num_pixels = w * h

        # Create new image
        packed = bpy.data.images.new("Packed_RGBA", width=w, height=h, alpha=True)
        packed.colorspace_settings.name = "Non-Color"

        channels = []

        # -------------------------
        # NUMPY FAST PATH
        # -------------------------
        if USE_NUMPY:
            for img in images:
                img.colorspace_settings.name = "Non-Color"

                pixels = np.empty(num_pixels * 4, dtype=np.float32)
                img.pixels.foreach_get(pixels)
                pixels = pixels.reshape(-1, 4)

                r = pixels[:, 0]
                a = pixels[:, 3]

                gray = np.where(a < 1.0, a, r)
                channels.append(gray)

            while len(channels) < 4:
                channels.append(np.ones(num_pixels, dtype=np.float32))

            result_pixels = np.stack(channels[:4], axis=1).ravel()

            packed.pixels.foreach_set(result_pixels)

        # -------------------------
        # PYTHON FALLBACK
        # -------------------------
        else:
            for img in images:
                img.colorspace_settings.name = "Non-Color"

                pixels = list(img.pixels[:])
                gray = []

                for i in range(0, len(pixels), 4):
                    r = pixels[i]
                    a = pixels[i + 3]

                    gray.append(a if a < 1.0 else r)

                channels.append(gray)

            while len(channels) < 4:
                channels.append([1.0] * num_pixels)

            result_pixels = []

            for i in range(num_pixels):
                result_pixels.extend(
                    [
                        channels[0][i],
                        channels[1][i],
                        channels[2][i],
                        channels[3][i],
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

        # Create Separate Color node
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
                links.new(img_node.outputs["Alpha"], to_socket)

        # Remove old nodes
        for node in selected:
            nodes.remove(node)

        self.report({"INFO"}, "MustardUI - Images packed into RGBA channels")

        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_ToolsCreators_PackRGBA)


def unregister():
    bpy.utils.unregister_class(MustardUI_ToolsCreators_PackRGBA)
