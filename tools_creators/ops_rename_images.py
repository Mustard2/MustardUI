import os
import re

import bpy
from bpy.props import BoolProperty, PointerProperty, StringProperty

from ..model_selection.active_object import (
    active_object_operator_poll,
    mustardui_active_object,
)


def sanitize_name(name: str):
    name = name.replace(" ", "_")
    name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    name = re.sub(r"_+", "_", name)
    return name.strip("_")


def make_node_label(name: str):
    parts = name.split("_")
    return " ".join(p.upper() if p.upper() in {"AO", "UV"} else p.capitalize() for p in parts)


def detect_texture_type(name: str):
    name = re.sub(r"\.\d+$", "", name).lower()

    mapping = {
        "Diffuse": ["diffuse", "albedo", "basecolor", "color", "col"],
        "Normal": ["normal", "nrm"],
        "Roughness": ["roughness", "rough"],
        "Metallic": ["metallic", "metal"],
        "Specular": ["specular", "spec"],
        "Emission": ["emission", "emit"],
        "Opacity": ["opacity", "alpha"],
        "Height": ["height", "disp"],
        "AO": ["ao"],
    }

    for key, values in mapping.items():
        for v in values:
            if v in name:
                return key

    # Suffix detection (LegsN, BodyD, etc.)
    match = re.search(r"([a-z]+)([dnrmseoha])$", name)
    if match:
        return {
            "d": "Diffuse",
            "n": "Normal",
            "r": "Roughness",
            "m": "Metallic",
            "s": "Specular",
            "e": "Emission",
            "o": "Opacity",
            "h": "Height",
            "a": "AO",
        }.get(match.group(2), "Texture")

    return "Texture"


def detect_material_zone(material_name, image_name, node_name):
    mapping = [
        ("Genitals", ["genital"]),
        ("Fingernails", ["fingernail"]),
        ("Toenails", ["toenail"]),
        ("Eyes", ["eye", "iris", "sclera"]),
        ("Face", ["face", "head"]),
        ("Hair", ["hair"]),
        ("Teeth", ["teeth"]),
        ("Mouth", ["mouth", "tongue", "lips"]),
        ("Arms", ["arm", "hand"]),
        ("Legs", ["leg", "thigh", "calf", "foot"]),
        ("Body", ["body", "torso"]),
    ]

    sources = [image_name.lower(), node_name.lower(), material_name.lower()]

    # PASS 1: image name
    for zone, keys in mapping:
        for k in keys:
            if k in sources[0]:
                return zone

    # PASS 2: node name
    for zone, keys in mapping:
        for k in keys:
            if k in sources[1]:
                return zone

    # PASS 3: material name
    for zone, keys in mapping:
        for k in keys:
            if k in sources[2]:
                return zone

    return ""


def extract_base_name(image_name: str, tex_type: str, zone: str):
    # Remove .001 etc
    name = re.sub(r"\.\d+$", "", image_name).lower()

    # Remove ALL trailing type letters (sn, ns, rn, etc.)
    name = re.sub(r"[dnrmseoha]+$", "", name)

    # Remove texture keywords
    type_words = [
        "diffuse",
        "albedo",
        "basecolor",
        "color",
        "col",
        "normal",
        "nrm",
        "roughness",
        "rough",
        "metallic",
        "metal",
        "specular",
        "spec",
        "ao",
        "opacity",
        "alpha",
        "height",
        "disp",
        "emission",
        "emit",
    ]

    for w in type_words:
        name = name.replace(w, "")

    # Remove ALL anatomical words
    zone_words = [
        "genital",
        "fingernail",
        "toenail",
        "eye",
        "iris",
        "sclera",
        "face",
        "head",
        "hair",
        "teeth",
        "mouth",
        "tongue",
        "lips",
        "arm",
        "hand",
        "leg",
        "thigh",
        "calf",
        "foot",
        "body",
        "torso",
    ]

    for w in zone_words:
        name = name.replace(w, "")

    # Remove separators
    name = re.sub(r"[_\-.]+", "_", name)

    # Remove leftover single letters
    name = re.sub(r"\b[a-z]\b", "", name)

    return sanitize_name(name)


def make_node_color(tex_type: str):
    return {
        "Diffuse": (0.45, 0.45, 0.20),  # muted warm
        "Normal": (0.35, 0.40, 0.60),  # softer blue
        "Roughness": (0.25, 0.35, 0.50),  # cool muted
        "Metallic": (0.30, 0.30, 0.30),  # neutral gray
        "Specular": (0.40, 0.35, 0.45),  # subtle purple-gray
        "AO": (0.25, 0.45, 0.30),  # muted green
        "Emission": (0.60, 0.40, 0.20),  # toned orange
        "Opacity": (0.35, 0.35, 0.35),  # neutral
        "Height": (0.30, 0.30, 0.40),  # dark bluish
    }.get(tex_type, (0.35, 0.35, 0.35))  # fallback


def update_name(self, context):
    self.enabled = True


class MustardUI_RenameImageNodes_Item(bpy.types.PropertyGroup):
    enabled: BoolProperty(default=False)
    node_name: StringProperty()
    material: PointerProperty(type=bpy.types.Material)
    image: PointerProperty(type=bpy.types.Image)
    name: StringProperty(name="New Name", default="", update=update_name)


class MustardUI_RenameImageNodes_Update(bpy.types.Operator):
    bl_idname = "mustardui.rename_image_nodes_update"
    bl_label = "Smart Rename"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        return active_object_operator_poll(context, config=1)

    def execute(self, context):
        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings

        collection = context.scene.mustardui_rename_images
        if context.object == rig_settings.model_body:
            model_name = rig_settings.model_name if rig_settings.model_name else None
        else:
            model_name = sanitize_name(context.object.name) if context.object else ""

        for item in [x for x in collection if x.enabled]:
            if item.image.filepath:
                filename = bpy.path.basename(item.image.filepath)
                original = os.path.splitext(filename)[0]
            else:
                original = os.path.splitext(item.image.name)[0]

            tex_type = detect_texture_type(original)
            zone = detect_material_zone(
                item.material.name if item.material else "", original, item.node_name
            )

            base = extract_base_name(original, tex_type, zone)

            parts = []

            if model_name:
                parts.append(model_name)

            if zone:
                parts.append(zone)

            if base:
                parts.append(base)

            if tex_type != "Texture":
                parts.append(tex_type)

            parts.append("Texture")

            item.name = sanitize_name("_".join(parts))

        return {"FINISHED"}


class MustardUI_RenameImageNodes_SelectAll(bpy.types.Operator):
    bl_idname = "mustardui.rename_image_nodes_select_all"
    bl_label = "Select All"

    value: BoolProperty(default=True)

    @classmethod
    def poll(cls, context):
        return active_object_operator_poll(context, config=1)

    def execute(self, context):
        for item in context.scene.mustardui_rename_images:
            item.enabled = self.value
        return {"FINISHED"}


class MustardUI_RenameImageNodes(bpy.types.Operator):
    bl_idname = "mustardui.rename_image_nodes"
    bl_label = "Rename Image Nodes"
    bl_options = {"UNDO"}

    rename_datablock: BoolProperty(default=True)
    rename_file: BoolProperty(default=False)
    color_nodes: BoolProperty(name="Color Nodes", default=True)

    @classmethod
    def poll(cls, context):
        return active_object_operator_poll(context, config=1)

    def invoke(self, context, event):
        mat = context.object.active_material
        collection = context.scene.mustardui_rename_images
        collection.clear()

        for node in mat.node_tree.nodes:
            if node.type == "TEX_IMAGE" and node.image:
                item = collection.add()
                item.node_name = node.name
                item.material = mat
                item.image = node.image
                item.name = node.image.name

        return context.window_manager.invoke_props_dialog(self, width=600)

    def execute(self, context):
        for item in context.scene.mustardui_rename_images:
            if not item.enabled:
                continue

            node = item.material.node_tree.nodes.get(item.node_name)
            image = item.image
            new_name = item.name

            if not node or not image:
                continue

            node.name = new_name
            node.label = make_node_label(new_name)

            if self.color_nodes:
                tex_type = detect_texture_type(new_name)
                node.use_custom_color = True
                node.color = make_node_color(tex_type)
            else:
                node.use_custom_color = False

            if self.rename_datablock:
                image.name = new_name

            if self.rename_file:
                if image.packed_file or image.source == "TILED" or "<UDIM>" in image.filepath:
                    continue

                try:
                    abs_path = bpy.path.abspath(image.filepath)
                    if os.path.exists(abs_path):
                        directory = os.path.dirname(abs_path)
                        ext = os.path.splitext(abs_path)[1]
                        new_path = os.path.join(directory, new_name + ext)

                        if abs_path != new_path:
                            os.rename(abs_path, new_path)
                            image.filepath = bpy.path.relpath(new_path)
                except Exception:
                    pass

        context.scene.mustardui_rename_images.clear()
        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        col = context.scene.mustardui_rename_images

        box = layout.box()
        row = box.row()
        row.operator("mustardui.rename_image_nodes_update", icon="LOOP_FORWARDS")

        row = box.row(align=True)
        row.operator("mustardui.rename_image_nodes_select_all", text="Select All").value = True
        row.operator("mustardui.rename_image_nodes_select_all", text="None").value = False

        box = layout.box()
        for item in col:
            row = box.row(align=True)
            row.prop(item, "enabled", text="")

            sub = row.row()
            sub.enabled = item.enabled

            sub.label(text=item.node_name, icon="IMAGE_DATA")
            sub.prop(item, "name", text="")

        box = layout.box()
        row = box.row(align=True)
        row.prop(self, "rename_datablock", text="Rename Image Nodes")
        row.prop(self, "rename_file", text="Rename File on Disk")
        row.prop(self, "color_nodes", text="Color Nodes with Texture Type")


# -------------------------
# REGISTER
# -------------------------


def register():
    bpy.utils.register_class(MustardUI_RenameImageNodes_Item)
    bpy.utils.register_class(MustardUI_RenameImageNodes_Update)
    bpy.utils.register_class(MustardUI_RenameImageNodes_SelectAll)
    bpy.utils.register_class(MustardUI_RenameImageNodes)

    bpy.types.Scene.mustardui_rename_images = bpy.props.CollectionProperty(
        type=MustardUI_RenameImageNodes_Item
    )


def unregister():
    del bpy.types.Scene.mustardui_rename_images

    bpy.utils.unregister_class(MustardUI_RenameImageNodes)
    bpy.utils.unregister_class(MustardUI_RenameImageNodes_SelectAll)
    bpy.utils.unregister_class(MustardUI_RenameImageNodes_Update)
    bpy.utils.unregister_class(MustardUI_RenameImageNodes_Item)
