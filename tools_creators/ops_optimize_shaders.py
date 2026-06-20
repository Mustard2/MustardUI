import hashlib
import os

import bpy

from .. import __package__ as base_package


class MustardUI_ToolsCreators_OptimizeShaders(bpy.types.Operator):
    """Replace duplicate shader node groups and duplicate images.
    Node group matching includes canvas position and width, so groups that are
    structurally identical but placed at different locations will not be merged."""

    bl_idname = "mustardui.tools_creators_optimize_shaders"
    bl_label = "Optimize Shaders"
    bl_options = {"REGISTER", "UNDO"}

    remove_duplicate_groups: bpy.props.BoolProperty(
        name="Remove Duplicate Groups",
        default=True,
        description="Remove duplicate Groups",
    )

    remove_duplicate_images: bpy.props.BoolProperty(
        name="Remove Duplicate Images",
        default=True,
        description="Remove duplicate Images",
    )

    remove_unused: bpy.props.BoolProperty(
        name="Remove Unused",
        default=True,
        description="Remove duplicate datablocks left without users",
    )

    # Image hashing — reads only the first and last 8 KB of each file for
    # performance. Two images with identical metadata and boundary chunks but
    # different middle content would be incorrectly treated as duplicates.
    def image_signature(self, image):

        if image.source != "FILE":
            return None

        filepath = bpy.path.abspath(image.filepath)

        if not filepath:
            return None

        try:
            if not os.path.exists(filepath):
                return None

            stat = os.stat(filepath)

            meta = (
                image.size[0],
                image.size[1],
                image.channels,
                stat.st_size,
            )

            CHUNK_SIZE = 8192

            hasher = hashlib.sha256()

            with open(filepath, "rb") as f:
                start = f.read(CHUNK_SIZE)

                f.seek(max(0, stat.st_size - CHUNK_SIZE))

                end = f.read(CHUNK_SIZE)

            hasher.update(repr(meta).encode("utf-8"))
            hasher.update(start)
            hasher.update(end)

            return hasher.hexdigest()

        except Exception:
            return None

    # Group hashing
    def socket_default(self, socket):
        try:
            if hasattr(socket, "default_value"):
                value = socket.default_value

                if isinstance(value, (float, int, bool)):
                    return value

                try:
                    return tuple(value)
                except Exception:
                    return str(value)

        except Exception:
            pass

        return None

    def serialize_node(self, node):
        data = {
            "type": node.bl_idname,
            "name": node.name,
            "label": node.label,
            "location": (
                round(node.location.x, 3),
                round(node.location.y, 3),
            ),
            "width": round(node.width, 3),
            "mute": node.mute,
            "hide": node.hide,
            "properties": {},
        }

        ignored = {
            "name",
            "label",
            "location",
            "width",
            "height",
            "select",
            "show_options",
            "show_preview",
            "show_texture",
            "parent",
            "rna_type",
            "type",
        }

        for prop in node.bl_rna.properties:
            identifier = prop.identifier

            if identifier in ignored:
                continue

            if prop.is_readonly:
                continue

            try:
                value = getattr(node, identifier)

                if isinstance(value, (float, int, bool, str)):
                    data["properties"][identifier] = value

                else:
                    try:
                        data["properties"][identifier] = tuple(value)
                    except Exception:
                        pass

            except Exception:
                pass

        inputs = []

        for socket in node.inputs:
            inputs.append(
                {
                    "name": socket.name,
                    "type": socket.bl_idname,
                    "default": self.socket_default(socket),
                }
            )

        data["inputs"] = inputs

        # Nested groups
        if node.type == "GROUP" and node.node_tree:
            data["group_name"] = node.node_tree.name

        # Image texture nodes
        if node.type == "TEX_IMAGE" and node.image:
            data["image_name"] = node.image.name

        return data

    def serialize_links(self, node_tree):
        links = []

        for link in node_tree.links:
            try:
                links.append(
                    (
                        link.from_node.name,
                        link.from_socket.identifier,
                        link.to_node.name,
                        link.to_socket.identifier,
                    )
                )

            except Exception:
                pass

        return sorted(links)

    def serialize_interface(self, node_tree):
        interface = []

        if hasattr(node_tree, "interface"):
            try:
                for item in node_tree.interface.items_tree:
                    if item.item_type != "SOCKET":
                        continue

                    interface.append(
                        (
                            item.in_out,
                            item.socket_type,
                            item.name,
                        )
                    )

            except Exception:
                pass

        return interface

    def node_tree_signature(self, node_tree):
        data = {
            "type": node_tree.bl_idname,
            "nodes": [],
            "links": self.serialize_links(node_tree),
            "interface": self.serialize_interface(node_tree),
        }

        nodes = sorted(node_tree.nodes, key=lambda n: n.name)

        for node in nodes:
            data["nodes"].append(self.serialize_node(node))

        raw = repr(data).encode("utf-8")

        return hashlib.sha256(raw).hexdigest()

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH"

    def execute(self, context):

        if not self.remove_duplicate_groups and not self.remove_duplicate_images:
            self.report(
                {"WARNING"},
                "MustardUI - No Option Selected.",
            )
            return {"CANCELLED"}

        addon_prefs = context.preferences.addons[base_package].preferences

        total_group_replaced = 0
        total_group_removed = 0

        total_image_replaced = 0
        total_image_removed = 0

        if addon_prefs.debug:
            print("------------------------------------------------------")
            print("Shader Optimization")

        # Remove duplicate shader groups
        if self.remove_duplicate_groups:
            groups = [ng for ng in bpy.data.node_groups if ng.bl_idname == "ShaderNodeTree"]

            signature_map = {}
            duplicate_map = {}

            for group in groups:
                try:
                    signature = self.node_tree_signature(group)

                except Exception as e:
                    self.report(
                        {"WARNING"},
                        f"Failed analyzing {group.name}: {e}",
                    )
                    continue

                if signature not in signature_map:
                    signature_map[signature] = group
                else:
                    original = signature_map[signature]
                    duplicate_map[group] = original
                    if addon_prefs.debug:
                        print(f"Group duplicate found: {group.name}")

            # Replace in materials
            for material in bpy.data.materials:
                if not material.use_nodes or not material.node_tree:
                    continue

                for node in material.node_tree.nodes:
                    if node.type != "GROUP":
                        continue

                    if not node.node_tree:
                        continue

                    if node.node_tree in duplicate_map:
                        original = duplicate_map[node.node_tree]

                        if addon_prefs.debug:
                            print(
                                f"Material {material.name} - "
                                f"Group {node.node_tree.name} substituted with "
                                f"{original.name}."
                            )

                        node.node_tree = original
                        total_group_replaced += 1

            # Replace inside groups too
            for group in bpy.data.node_groups:
                if not hasattr(group, "nodes"):
                    continue

                for node in group.nodes:
                    if node.type != "GROUP":
                        continue

                    if not node.node_tree:
                        continue

                    if node.node_tree in duplicate_map:
                        original = duplicate_map[node.node_tree]

                        if addon_prefs.debug:
                            print(
                                f"Group {group.name} - "
                                f"Group {node.node_tree.name} substituted with "
                                f"{original.name}."
                            )

                        node.node_tree = original
                        total_group_replaced += 1

            # Remove unused duplicate groups
            if self.remove_unused:
                for duplicate in duplicate_map.keys():
                    if duplicate.users == 0:
                        bpy.data.node_groups.remove(duplicate)
                        total_group_removed += 1

        # Remove duplicate images
        if self.remove_duplicate_images:
            image_map = {}
            duplicate_images = {}

            for image in bpy.data.images:
                signature = self.image_signature(image)

                if signature is None:
                    continue

                if signature not in image_map:
                    image_map[signature] = image
                else:
                    original = image_map[signature]
                    duplicate_images[image] = original

                    if addon_prefs.debug:
                        print(f"Image duplicate found: {image.name}")

            # Replace image texture nodes in materials
            for material in bpy.data.materials:
                if not material.use_nodes or not material.node_tree:
                    continue

                for node in material.node_tree.nodes:
                    if node.type != "TEX_IMAGE":
                        continue

                    if not node.image:
                        continue

                    if node.image in duplicate_images:
                        original = duplicate_images[node.image]

                        if addon_prefs.debug:
                            print(
                                f"Material {material.name} - "
                                f"Image {node.image.name} substituted with "
                                f"{original.name}."
                            )

                        node.image = original
                        total_image_replaced += 1

            # Replace image texture nodes in groups
            for group in bpy.data.node_groups:
                if not hasattr(group, "nodes"):
                    continue

                for node in group.nodes:
                    if node.type != "TEX_IMAGE":
                        continue

                    if not node.image:
                        continue

                    if node.image in duplicate_images:
                        original = duplicate_images[node.image]

                        if addon_prefs.debug:
                            print(
                                f"Group {group.name} - "
                                f"Image {node.image.name} substituted with "
                                f"{original.name}."
                            )

                        node.image = original
                        total_image_replaced += 1

            # Remove unused duplicate images
            if self.remove_unused:
                for duplicate in duplicate_images.keys():
                    if duplicate.users == 0:
                        bpy.data.images.remove(duplicate)
                        total_image_removed += 1

        if addon_prefs.debug:
            print("------------------------------------------------------")
            print("Shader Optimization Recap")

            print(f"Duplicate Group Nodes Replaced: {total_group_replaced}")
            print(f"Duplicate Image Nodes Replaced: {total_image_replaced}")

            if self.remove_unused:
                print(f"Duplicate Group Data Removed : {total_group_removed}")
                print(f"Duplicate Images Data Removed: {total_image_removed}")

        total = (
            total_group_replaced + total_group_removed + total_image_replaced + total_image_removed
        )

        if total == 0:
            self.report({"WARNING"}, "MustardUI - Nothing to optimize.")
            return {"FINISHED"}

        parts = []
        if self.remove_duplicate_groups:
            group_msg = f"Groups: {total_group_replaced} replaced"
            if self.remove_unused:
                group_msg += f", {total_group_removed} removed"
            parts.append(group_msg)
        if self.remove_duplicate_images:
            image_msg = f"Images: {total_image_replaced} replaced"
            if self.remove_unused:
                image_msg += f", {total_image_removed} removed"
            parts.append(image_msg)

        self.report(
            {"INFO"},
            "MustardUI - Shaders Optimized. " + " | ".join(parts),
        )

        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=250)

    def draw(self, context):

        layout = self.layout

        col = layout.column(align=True)

        col.prop(self, "remove_duplicate_images")
        col.prop(self, "remove_duplicate_groups")

        col.separator()

        col.prop(self, "remove_unused")


def register():
    bpy.utils.register_class(MustardUI_ToolsCreators_OptimizeShaders)


def unregister():
    bpy.utils.unregister_class(MustardUI_ToolsCreators_OptimizeShaders)
