"""MustardUI - Materials for characters exported with Export Character.

Run inside the Unreal Editor, with the Python Editor Script Plugin enabled:
select the imported skeletal meshes in the Content Browser, then use
Tools > Execute Python Script and choose this file.

For each material slot of the meshes, the script imports the textures listed in the
materials.json file next to the textures exported from Blender, and assigns a material
instance of a MustardUI parent material: skin with subsurface scattering, opaque, or masked for
brows and lashes. The parent materials work with skeletal meshes and morph targets, and are
created once in /Game/MustardUI/Materials, where they can be changed for all the characters.
"""

import json
import os
import re
import struct
import zlib

import unreal

PARENT_FOLDER = "/Game/MustardUI/Materials"
WHITE = "/Engine/EngineResources/WhiteSquareTexture"
LINEAR_WHITE = f"{PARENT_FOLDER}/T_MustardUI_LinearWhite"
FLAT_NORMAL = "/Engine/EngineMaterials/FlatNormal"

assets = unreal.AssetToolsHelpers.get_asset_tools()
library = unreal.EditorAssetLibrary
materials = unreal.MaterialEditingLibrary


def log(message):
    unreal.log(f"MustardUI - {message}")


def unreal_name(name):
    """Names as Unreal gives them to imported assets and material slots."""
    return re.sub(r"[^A-Za-z0-9_\-]", "_", name)


def texture_parameter(material, name, default, x, y, sampler=None):
    node = materials.create_material_expression(
        material, unreal.MaterialExpressionTextureSampleParameter2D, x, y
    )
    node.set_editor_property("parameter_name", name)
    node.set_editor_property("texture", unreal.load_asset(default))
    if sampler is not None:
        node.set_editor_property("sampler_type", sampler)
    return node


def scalar_parameter(material, name, value, x, y):
    node = materials.create_material_expression(
        material, unreal.MaterialExpressionScalarParameter, x, y
    )
    node.set_editor_property("parameter_name", name)
    node.set_editor_property("default_value", value)
    return node


def linear_white():
    """White texture which is not sRGB, the default of the roughness and opacity textures:
    Unreal needs defaults with the same color space as the textures used later."""
    if library.does_asset_exist(LINEAR_WHITE):
        return

    # A 4x4 white PNG
    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    rows = b"".join(b"\x00" + b"\xff" * 12 for _ in range(4))
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 4, 4, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )
    path = os.path.join(unreal.Paths.project_saved_dir(), "T_MustardUI_LinearWhite.png")
    with open(path, "wb") as file:
        file.write(png)
    import_texture(path, PARENT_FOLDER, "data")


# Subsurface scattering of skin, as tuned for the MustardUI characters
SKIN_PROFILE = {
    "surface_albedo": (0.91, 0.42, 0.33),
    "mean_free_path_color": (1.0, 0.25, 0.16),
    "mean_free_path_distance": 1.0,
    "world_unit_scale": 0.1,
    "subsurface_color": (0.48, 0.41, 0.28),
    "falloff_color": (1.0, 0.37, 0.3),
    "ior": 1.55,
    "roughness0": 0.75,
    "roughness1": 1.3,
    "lobe_mix": 0.85,
    "scatter_radius": 1.2,
    "normal_scale": 0.08,
}
# Subsurface amount, and a tint balancing the red of the scattering
SKIN_AMOUNT = 0.15
SKIN_TINT = (0.86, 0.97, 1.0)
EYE_ROUGHNESS = 0.1


def skin_profile():
    """Subsurface profile of the skin parent material, created once."""
    path = f"{PARENT_FOLDER}/SSS_MustardUI_Skin"
    if library.does_asset_exist(path):
        return unreal.load_asset(path)
    factory_class = getattr(unreal, "SubsurfaceProfileFactory", None)
    factory = factory_class() if factory_class else None
    profile = assets.create_asset(
        "SSS_MustardUI_Skin", PARENT_FOLDER, unreal.SubsurfaceProfile, factory
    )
    settings = profile.get_editor_property("settings")
    for key, value in SKIN_PROFILE.items():
        setting = unreal.LinearColor(*value, 1.0) if isinstance(value, tuple) else value
        try:
            settings.set_editor_property(key, setting)
        except Exception as error:
            unreal.log_warning(f"MustardUI - Subsurface profile setting {key}: {error}")
    profile.set_editor_property("settings", settings)
    library.save_loaded_asset(profile)
    return profile


def create_parent(name, kind):
    """Parent material: base color texture with a tint, normal and roughness textures.
    Masked materials add an opacity mask from the red or alpha channel of a texture, and skin
    materials scatter light under the surface."""
    path = f"{PARENT_FOLDER}/{name}"
    if library.does_asset_exist(path):
        return unreal.load_asset(path)
    linear_white()
    material = assets.create_asset(
        name, PARENT_FOLDER, unreal.Material, unreal.MaterialFactoryNew()
    )
    material.set_editor_property("used_with_skeletal_mesh", True)
    material.set_editor_property("used_with_morph_targets", True)

    color = texture_parameter(material, "BaseColorTexture", WHITE, -700, -300)
    tint = materials.create_material_expression(
        material, unreal.MaterialExpressionVectorParameter, -700, -80
    )
    tint.set_editor_property("parameter_name", "BaseColorTint")
    tint.set_editor_property("default_value", unreal.LinearColor(1, 1, 1, 1))
    multiply = materials.create_material_expression(
        material, unreal.MaterialExpressionMultiply, -350, -200
    )
    materials.connect_material_expressions(color, "RGB", multiply, "A")
    materials.connect_material_expressions(tint, "", multiply, "B")
    base_color = multiply
    if kind == "skin":
        skin_tint = materials.create_material_expression(
            material, unreal.MaterialExpressionVectorParameter, -350, -400
        )
        skin_tint.set_editor_property("parameter_name", "SkinTint")
        skin_tint.set_editor_property("default_value", unreal.LinearColor(*SKIN_TINT, 1.0))
        base_color = materials.create_material_expression(
            material, unreal.MaterialExpressionMultiply, -150, -250
        )
        materials.connect_material_expressions(multiply, "", base_color, "A")
        materials.connect_material_expressions(skin_tint, "", base_color, "B")
    materials.connect_material_property(base_color, "", unreal.MaterialProperty.MP_BASE_COLOR)

    normal = texture_parameter(
        material,
        "NormalTexture",
        FLAT_NORMAL,
        -700,
        100,
        unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL,
    )
    materials.connect_material_property(normal, "RGB", unreal.MaterialProperty.MP_NORMAL)

    rough = texture_parameter(
        material,
        "RoughnessTexture",
        LINEAR_WHITE,
        -700,
        350,
        unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR,
    )
    scale = scalar_parameter(material, "Roughness", 1.0, -700, 600)
    rough_multiply = materials.create_material_expression(
        material, unreal.MaterialExpressionMultiply, -350, 400
    )
    materials.connect_material_expressions(rough, "R", rough_multiply, "A")
    materials.connect_material_expressions(scale, "", rough_multiply, "B")
    materials.connect_material_property(rough_multiply, "", unreal.MaterialProperty.MP_ROUGHNESS)

    if kind == "skin":
        material.set_editor_property(
            "shading_model", unreal.MaterialShadingModel.MSM_SUBSURFACE_PROFILE
        )
        material.set_editor_property("subsurface_profile", skin_profile())
        amount = scalar_parameter(material, "SubsurfaceAmount", SKIN_AMOUNT, -350, 800)
        materials.connect_material_property(amount, "", unreal.MaterialProperty.MP_OPACITY)

    if kind == "masked":
        material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
        material.set_editor_property("two_sided", True)
        opacity = texture_parameter(
            material,
            "OpacityTexture",
            LINEAR_WHITE,
            -700,
            800,
            unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR,
        )
        use_alpha = scalar_parameter(material, "OpacityFromAlpha", 0.0, -700, 1050)
        choose = materials.create_material_expression(
            material, unreal.MaterialExpressionLinearInterpolate, -350, 850
        )
        materials.connect_material_expressions(opacity, "R", choose, "A")
        materials.connect_material_expressions(opacity, "A", choose, "B")
        materials.connect_material_expressions(use_alpha, "", choose, "Alpha")
        materials.connect_material_property(choose, "", unreal.MaterialProperty.MP_OPACITY_MASK)

    materials.recompile_material(material)
    library.save_loaded_asset(material)
    return material


def import_texture(file_path, folder, kind):
    """Texture of the file, imported once in the folder. kind is color, data or normal:
    data and normal textures are not sRGB, and normal maps use their own compression."""
    name = unreal_name(os.path.splitext(os.path.basename(file_path))[0])
    path = f"{folder}/{name}"
    if not library.does_asset_exist(path):
        task = unreal.AssetImportTask()
        task.filename = file_path
        task.destination_path = folder
        task.destination_name = name
        task.automated = True
        task.save = True
        task.replace_existing = True
        assets.import_asset_tasks([task])
    texture = unreal.load_asset(path)
    if texture is None:
        return None
    changed = False
    if kind != "color" and texture.get_editor_property("srgb"):
        texture.set_editor_property("srgb", False)
        changed = True
    normal_map = unreal.TextureCompressionSettings.TC_NORMALMAP
    if kind == "normal" and texture.get_editor_property("compression_settings") != normal_map:
        texture.set_editor_property("compression_settings", normal_map)
        changed = True
    if changed:
        library.save_loaded_asset(texture)
    return texture


def apply_texture(instance, entry, role, parameter, kind, files):
    """Set a texture parameter of the instance to the texture of the role, if the material
    has one. files is (folder of the exported textures, folder of the Unreal textures)."""
    if role not in entry:
        return False
    texture = import_texture(os.path.join(files[0], entry[role]), files[1], kind)
    if texture is None:
        return False
    materials.set_material_instance_texture_parameter_value(instance, parameter, texture)
    return True


def source_file(mesh):
    """FBX file the mesh was imported from."""
    data = mesh.get_editor_property("asset_import_data")
    files = data.extract_filenames() if data is not None else []
    return files[0] if files else ""


def setup(mesh):
    fbx = source_file(mesh)
    textures_dir = os.path.splitext(fbx)[0] + "_Textures"
    manifest_path = os.path.join(textures_dir, "materials.json")
    if not os.path.isfile(manifest_path):
        unreal.log_error(
            f"MustardUI - {mesh.get_name()}: no {manifest_path}. Export the character with "
            "Materials ticked, and keep the textures folder next to the FBX"
        )
        return 0
    entries = json.load(open(manifest_path))["materials"]
    by_slot = {unreal_name(name): entry for name, entry in entries.items()}

    mesh_folder = mesh.get_path_name().rsplit("/", 1)[0]
    texture_folder = f"{mesh_folder}/Textures"
    instance_folder = f"{mesh_folder}/Materials"
    parents = {
        kind: create_parent(f"M_MustardUI_{kind.title()}", kind)
        for kind in ("opaque", "masked", "skin")
    }

    # The list holds copies of the slots, so changed slots are put back before assigning it
    slots = list(mesh.get_editor_property("materials"))
    done = 0
    for index, slot in enumerate(slots):
        name = str(slot.get_editor_property("material_slot_name"))
        entry = by_slot.get(unreal_name(name))
        if entry is None:
            continue
        masked = "alpha" in entry
        # Eyes use the opaque material, shinier as the moisture over them is not exported
        kind = entry.get("kind", "masked" if masked else "opaque")
        parent = parents["opaque" if kind == "eye" else kind]
        instance_name = f"MI_{unreal_name(name)}"
        instance_path = f"{instance_folder}/{instance_name}"
        if library.does_asset_exist(instance_path):
            instance = unreal.load_asset(instance_path)
        else:
            instance = assets.create_asset(
                instance_name,
                instance_folder,
                unreal.MaterialInstanceConstant,
                unreal.MaterialInstanceConstantFactoryNew(),
            )
        materials.set_material_instance_parent(instance, parent)

        files = (textures_dir, texture_folder)
        if apply_texture(instance, entry, "color", "BaseColorTexture", "color", files):
            tint = unreal.LinearColor(1, 1, 1, 1)
        else:
            tint = unreal.LinearColor(*entry["base_color"], 1)
        materials.set_material_instance_vector_parameter_value(instance, "BaseColorTint", tint)
        apply_texture(instance, entry, "normal", "NormalTexture", "normal", files)
        if not apply_texture(instance, entry, "roughness", "RoughnessTexture", "data", files):
            roughness = EYE_ROUGHNESS if kind == "eye" else entry["roughness_value"]
            materials.set_material_instance_scalar_parameter_value(instance, "Roughness", roughness)
        if masked:
            apply_texture(instance, entry, "alpha", "OpacityTexture", "data", files)
            materials.set_material_instance_scalar_parameter_value(
                instance, "OpacityFromAlpha", 1.0 if entry.get("alpha_channel") == "A" else 0.0
            )
        materials.update_material_instance(instance)
        library.save_loaded_asset(instance)
        slot.set_editor_property("material_interface", instance)
        slots[index] = slot
        done += 1
    mesh.modify()
    mesh.set_editor_property("materials", slots)
    library.save_loaded_asset(mesh)
    log(f"{mesh.get_name()}: {done} materials from {manifest_path}")
    return done


def run():
    meshes = [
        a
        for a in unreal.EditorUtilityLibrary.get_selected_assets()
        if isinstance(a, unreal.SkeletalMesh)
    ]
    if not meshes:
        unreal.log_error("MustardUI - Select the skeletal meshes in the Content Browser first")
        return
    for mesh in meshes:
        setup(mesh)


run()
