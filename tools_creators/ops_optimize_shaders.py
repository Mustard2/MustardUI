import hashlib

import bpy


class MustardUI_ToolsCreators_OptimizeShaders(bpy.types.Operator):
    """Replace duplicate shader node groups with identical ones across all materials"""

    bl_idname = "mustardui.tool_creators_optimize_shaders"
    bl_label = "Optimize Shaders"
    bl_options = {"REGISTER", "UNDO"}

    remove_unused: bpy.props.BoolProperty(
        name="Remove Unused Groups",
        default=True,
        description="Remove duplicate node groups left without users",
    )

    def socket_default(self, socket):
        try:
            if hasattr(socket, "default_value"):
                value = socket.default_value

                # Float / Int
                if isinstance(value, (float, int, bool)):
                    return value

                # Vector / Color
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

        # Generic RNA properties
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

        # Input defaults
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

        # Special handling for nested groups
        if node.type == "GROUP" and node.node_tree:
            data["group_name"] = node.node_tree.name

        return data

    def serialize_links(self, node_tree):
        links = []

        for link in node_tree.links:
            try:
                links.append(
                    (
                        link.from_node.name,
                        link.from_socket.name,
                        link.to_node.name,
                        link.to_socket.name,
                    )
                )
            except Exception:
                pass

        return sorted(links)

    def serialize_interface(self, node_tree):
        interface = []

        # Blender 4+
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
        """
        Generate a structural signature for the node tree.
        If two groups have the same signature,
        they are considered duplicates.
        """

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

    def execute(self, context):

        # Only shader node groups
        groups = [ng for ng in bpy.data.node_groups if ng.bl_idname == "ShaderNodeTree"]

        if not groups:
            self.report({"INFO"}, "No shader groups found")
            return {"CANCELLED"}

        signature_map = {}
        duplicate_map = {}

        # Detect duplicates
        for group in groups:
            try:
                signature = self.node_tree_signature(group)

            except Exception as e:
                self.report({"WARNING"}, f"Failed analyzing {group.name}: {e}")
                continue

            if signature not in signature_map:
                signature_map[signature] = group
            else:
                original = signature_map[signature]
                duplicate_map[group] = original

        if not duplicate_map:
            self.report({"INFO"}, "No duplicate shader groups found")
            return {"FINISHED"}

        # Replace references
        replaced = 0
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

                    node.node_tree = original
                    replaced += 1

        # Replace inside node groups too
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

                    node.node_tree = original
                    replaced += 1

        # Remove unused duplicates
        removed = 0
        if self.remove_unused:
            for duplicate in duplicate_map.keys():
                if duplicate.users == 0:
                    bpy.data.node_groups.remove(duplicate)
                    removed += 1

        self.report(
            {"INFO"},
            f"MustardUI - Shaders Optimized: replaced {replaced} shader groups",
        )

        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_ToolsCreators_OptimizeShaders)


def unregister():
    bpy.utils.unregister_class(MustardUI_ToolsCreators_OptimizeShaders)
