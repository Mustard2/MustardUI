"""Simple materials for the export: the textures found in each material, on a Principled BSDF.

FBX only carries base color, normal, roughness and alpha textures, so node setups are reduced to
the images feeding those inputs, and the images are copied next to the FBX.
Unreal makes the materials opaque, so surfaces to see through without an alpha texture, as the
moisture over the eyes, are left out.
"""

import json
import os
import re
import shutil
from collections import Counter

import bmesh
import bpy

ROLES = ("color", "normal", "roughness", "alpha")

# Words in socket names, in order of precedence
SOCKET_WORDS = (
    ("normal", ("normal",)),
    ("roughness", ("rough",)),
    ("alpha", ("alpha", "opacity", "cutout", "transparen")),
    ("color", ("color", "diffuse", "albedo", "base")),
)

# Words in image names, used when the nodes do not tell
NAME_PATTERNS = (
    ("normal", r"normal|(^|[^a-z])(n|nm|nrm)([^a-z]|$)"),
    ("roughness", r"rough|(^|[^a-z])r([^a-z]|$)"),
    ("alpha", r"alpha|opacity|cutout|(^|[^a-z])(trans|tr)([^a-z]|$)"),
    ("color", r"color|colour|diffuse|albedo|base|(^|[^a-z])(c|d|col)([^a-z]|$)"),
)

# Nodes which pass a texture on, possibly changed, to the shader
PASS_THROUGH = {
    "NodeReroute",
    "ShaderNodeMix",
    "ShaderNodeMixRGB",
    "ShaderNodeMath",
    "ShaderNodeGamma",
    "ShaderNodeHueSaturation",
    "ShaderNodeInvert",
    "ShaderNodeBrightContrast",
    "ShaderNodeRGBCurve",
    "ShaderNodeValToRGB",
    "ShaderNodeSeparateColor",
    "ShaderNodeSeparateRGB",
    "ShaderNodeMapRange",
    "ShaderNodeClamp",
}


def socket_role(name):
    name = name.lower()
    for role, words in SOCKET_WORDS:
        if any(word in name for word in words):
            return role
    return None


def name_role(name):
    name = os.path.splitext(name.lower())[0]
    for role, pattern in NAME_PATTERNS:
        if re.search(pattern, name):
            return role
    return None


def downstream_role(socket, depth=0):
    """Role of the shader input an output socket ends in, following nodes passing it on."""
    if depth > 8:
        return None
    for link in socket.links:
        node, target = link.to_node, link.to_socket
        if node.bl_idname in {"ShaderNodeNormalMap", "ShaderNodeBump"}:
            return "normal"
        if node.bl_idname in PASS_THROUGH:
            for output in node.outputs:
                role = downstream_role(output, depth + 1)
                if role is not None:
                    return role
            continue
        role = socket_role(target.name)
        if role is not None:
            return role
    return None


def used_nodes(tree):
    """Nodes of the tree with a path to the active Material Output."""
    outputs = [n for n in tree.nodes if n.bl_idname == "ShaderNodeOutputMaterial"]
    active = [n for n in outputs if n.is_active_output] or outputs
    seen, stack = set(), active[:1]
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        for socket in node.inputs:
            stack.extend(link.from_node for link in socket.links)
    return seen


def material_textures(material):
    """{role: (image, output)} for the images feeding the material. The output is Alpha when
    the alpha channel of an image is used."""
    if material.node_tree is None:
        return {}
    candidates = {}
    for node in used_nodes(material.node_tree):
        if node.bl_idname != "ShaderNodeTexImage" or node.image is None:
            continue
        image = node.image
        found = [(downstream_role(o), o.name, True) for o in node.outputs if o.links]
        found = [entry for entry in found if entry[0] is not None]
        if not found:
            found = [(name_role(image.name), "Color", False)]
        for role, output, from_socket in found:
            if role is None:
                continue
            pixels = image.size[0] * image.size[1]
            score = (from_socket, name_role(image.name) == role, pixels)
            if role not in candidates or score > candidates[role][0]:
                candidates[role] = (score, image, output)
    return {role: (image, output) for role, (_, image, output) in candidates.items()}


def material_tile(meshes, material):
    """UDIM tile of most faces with the material."""
    tiles = Counter()
    for obj in meshes:
        indices = [i for i, slot in enumerate(obj.material_slots) if slot.material == material]
        uv = obj.data.uv_layers.active
        if not indices or uv is None:
            continue
        for polygon in obj.data.polygons:
            if polygon.material_index in indices:
                u, v = uv.data[polygon.loop_start].uv
                tiles[1001 + int(u // 1) + 10 * int(v // 1)] += 1
    return tiles.most_common(1)[0][0] if tiles else 1001


def image_path(image, paths):
    """Absolute path of the image file. The export works on a copy saved somewhere else, so
    paths come from the open file when it has them."""
    if image.name_full in paths:
        return paths[image.name_full]
    return os.path.normpath(bpy.path.abspath(image.filepath, library=image.library))


def image_file(image, tile, folder, written, paths):
    """Path of a copy of the image (of the tile, for UDIMs) in the folder, or None.
    written maps the copies made so far to their paths."""
    key = (image.name, tile if image.source == "TILED" else None)
    if key in written:
        return written[key]
    source = image_path(image, paths)
    if image.source == "TILED":
        u, v = (tile - 1001) % 10, (tile - 1001) // 10
        source = source.replace("<UDIM>", str(tile)).replace("<UVTILE>", f"u{u + 1}_v{v + 1}")
    name = os.path.basename(source) or bpy.path.clean_name(image.name) + ".png"
    # Unreal reads names ending in a number of 4 digits as tiles of a UDIM texture
    stem, extension = os.path.splitext(name)
    if re.search(r"[._]\d{4}$", stem):
        name = f"{stem[:-5]}_T{stem[-4:]}{extension}"
    # Different images with the same file name get a number
    if os.path.join(folder, name) in written.values():
        name = f"{len(written)}_{name}"
    target = os.path.join(folder, name)
    if image.packed_file is not None and image.source != "TILED":
        with open(target, "wb") as file:
            file.write(image.packed_file.data)
    elif os.path.isfile(source):
        shutil.copyfile(source, target)
    else:
        return None
    written[key] = target
    return target


def is_see_through(material):
    """Materials made to be seen through, as the moisture over the eyes."""
    tree = material.node_tree
    if tree is None:
        return False
    nodes = used_nodes(tree)
    for node in nodes:
        if node.bl_idname == "ShaderNodeBsdfTransparent":
            return True
        if node.bl_idname == "ShaderNodeBsdfPrincipled":
            alpha = node.inputs["Alpha"]
            if not alpha.links and alpha.default_value < 0.5:
                return True
            weight = node.inputs.get("Transmission Weight") or node.inputs.get("Transmission")
            if weight is not None and not weight.links and weight.default_value > 0.5:
                return True
    return False


def rebuild(material, files, see_through=False):
    """Replace the nodes of the material with a Principled BSDF using the files of the roles.
    Materials to see through without an alpha texture become fully transparent."""
    color = tuple(material.diffuse_color)
    material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    shader = tree.nodes.new("ShaderNodeBsdfPrincipled")
    tree.links.new(shader.outputs[0], output.inputs["Surface"])
    shader.inputs["Base Color"].default_value = color
    shader.inputs["Roughness"].default_value = material.roughness

    def texture(role, non_color=False):
        """The output of a new image node with the file of the role."""
        path, output = files[role]
        node = tree.nodes.new("ShaderNodeTexImage")
        node.image = bpy.data.images.load(path, check_existing=True)
        if non_color:
            node.image.colorspace_settings.name = "Non-Color"
        return node.outputs[output]

    if "color" in files:
        tree.links.new(texture("color"), shader.inputs["Base Color"])
    if "alpha" in files:
        tree.links.new(texture("alpha"), shader.inputs["Alpha"])
    elif see_through:
        shader.inputs["Alpha"].default_value = 0.0
    if "roughness" in files:
        tree.links.new(texture("roughness", non_color=True), shader.inputs["Roughness"])
    if "normal" in files:
        normal_map = tree.nodes.new("ShaderNodeNormalMap")
        tree.links.new(texture("normal", non_color=True), normal_map.inputs["Color"])
        tree.links.new(normal_map.outputs["Normal"], shader.inputs["Normal"])


def simplify(meshes, folder, paths):
    """Replace the materials of the meshes with simple ones using their textures, copied to
    the folder. Returns the numbers of materials with and without textures, and the materials
    to see through without an alpha texture."""
    os.makedirs(folder, exist_ok=True)
    materials = {s.material for obj in meshes for s in obj.material_slots if s.material}
    written, textured, plain, clear, manifest = {}, 0, 0, set(), {}
    for material in sorted(materials, key=lambda m: m.name):
        tile = material_tile(meshes, material)
        files = {}
        for role, (image, output) in material_textures(material).items():
            path = image_file(image, tile, folder, written, paths)
            if path is not None:
                files[role] = (path, output)
        see_through = is_see_through(material)
        if see_through and "alpha" not in files:
            clear.add(material)
        else:
            manifest[material.name] = material_entry(material, files)
        rebuild(material, files, see_through)
        if files:
            textured += 1
        else:
            plain += 1
    with open(os.path.join(folder, MANIFEST), "w") as file:
        json.dump({"version": 1, "materials": manifest}, file, indent=1)
    return {"textured materials": textured, "materials without textures": plain}, clear


# Texture list read by the Unreal script, in the folder of the textures
MANIFEST = "materials.json"


def uses_subsurface(tree, depth=0):
    """Whether a Principled BSDF of the nodes, also inside node groups, scatters light."""
    if tree is None or depth > 4:
        return False
    nodes = used_nodes(tree) if depth == 0 else tree.nodes
    for node in nodes:
        if node.bl_idname == "ShaderNodeGroup" and uses_subsurface(node.node_tree, depth + 1):
            return True
        if node.bl_idname == "ShaderNodeBsdfPrincipled":
            weight = node.inputs.get("Subsurface Weight") or node.inputs.get("Subsurface")
            if weight is not None and (weight.links or weight.default_value > 0.01):
                return True
    return False


def material_kind(material, files):
    """Kind of Unreal material: masked with an alpha texture, eye, skin, or opaque."""
    if "alpha" in files:
        return "masked"
    name = material.name.lower()
    if "eye" in name and not re.search("lash|brow|moist|tear|lid", name):
        return "eye"
    if uses_subsurface(material.node_tree):
        return "skin"
    return "opaque"


def material_entry(material, files):
    """What the Unreal script needs to build the material: files in the folder of the
    textures, the channel with the alpha, and the values used without textures."""
    entry = {
        role: os.path.basename(path)
        for role, (path, _) in files.items()
        if role in ("color", "normal", "roughness", "alpha")
    }
    if "alpha" in files:
        entry["alpha_channel"] = "A" if files["alpha"][1] == "Alpha" else "R"
    entry["kind"] = material_kind(material, files)
    entry["base_color"] = list(material.diffuse_color)[:3]
    entry["roughness_value"] = material.roughness
    return entry


def remove_faces(meshes, materials):
    """Delete the faces with the materials. Returns the meshes with faces left."""
    kept = []
    for obj in meshes:
        indices = {i for i, s in enumerate(obj.material_slots) if s.material in materials}
        if indices:
            mesh = bmesh.new()
            mesh.from_mesh(obj.data)
            faces = [f for f in mesh.faces if f.material_index in indices]
            bmesh.ops.delete(mesh, geom=faces, context="FACES")
            mesh.to_mesh(obj.data)
            mesh.free()
        if obj.data.polygons:
            kept.append(obj)
        else:
            bpy.data.objects.remove(obj, do_unlink=True)
    return kept
