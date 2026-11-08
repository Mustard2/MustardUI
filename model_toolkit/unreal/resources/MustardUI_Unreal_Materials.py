"""MustardUI - Materials and hair for characters exported with Export Character.

Run inside the Unreal Editor, with the Python Editor Script Plugin enabled:
select the imported skeletal meshes in the Content Browser, then use
Tools > Execute Python Script and choose this file.

For each material slot of the meshes, the script imports the textures listed in the
materials.json file next to the textures exported from Blender, and assigns a material
instance of a MustardUI parent material: skin with subsurface scattering, opaque, or masked for
brows and lashes. The parent materials work with skeletal meshes and morph targets, and are
created once in /Game/MustardUI/Materials, where they can be changed for all the characters.

Particle hair, exported as Alembic files in the _Hair folder next to the FBX, is imported as
simulated grooms bound to the mesh, with the strand sizes of Blender and a material instance of
the MustardUI hair material, and added to the Blueprints showing the mesh, colliding with its
physics asset. Grooms need the Groom and Alembic Groom Importer plugins, and Unreal must be
restarted before the new grooms are used.
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
# Hair color when the Blender material has none, and the axes of the Alembic files of Blender
HAIR_COLOR = (0.05, 0.035, 0.025)
HAIR_ROTATION = (90, 0, 0)
HAIR_SCALE = (1, -1, 1)
# Hair simulation: the strands keep their combed shape at rest, stiff at the roots and free
# at the tips (the bend scale goes from the root to the tip), damped so they do not overshoot
HAIR_PHYSICS = {"GravityPreloading": 1.0, "BendStiffness": 0.12, "BendDamping": 0.1}
HAIR_BEND_SCALE = ((0.0, 1.0), (0.3, 0.6), (0.65, 0.25), (1.0, 0.15))


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


def hair_parent():
    """Parent material of the grooms: soft hair, scattering the light through the strands,
    with roots darker than the tips."""
    path = f"{PARENT_FOLDER}/M_MustardUI_Hair"
    if library.does_asset_exist(path):
        return unreal.load_asset(path)
    material = assets.create_asset(
        "M_MustardUI_Hair", PARENT_FOLDER, unreal.Material, unreal.MaterialFactoryNew()
    )
    material.set_editor_property("used_with_hair_strands", True)
    material.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_HAIR)
    color = materials.create_material_expression(
        material, unreal.MaterialExpressionVectorParameter, -700, -300
    )
    color.set_editor_property("parameter_name", "HairColor")
    color.set_editor_property("default_value", unreal.LinearColor(*HAIR_COLOR, 1))
    root = materials.create_material_expression(
        material, unreal.MaterialExpressionMultiply, -450, -200
    )
    materials.connect_material_expressions(color, "", root, "A")
    brightness = scalar_parameter(material, "RootBrightness", 0.5, -700, -100)
    materials.connect_material_expressions(brightness, "", root, "B")
    strand = materials.create_material_expression(
        material, unreal.MaterialExpressionHairAttributes, -700, 150
    )
    # Along the strand, from the root to the tip
    fade = materials.create_material_expression(
        material, unreal.MaterialExpressionLinearInterpolate, -250, -250
    )
    materials.connect_material_expressions(root, "", fade, "A")
    materials.connect_material_expressions(color, "", fade, "B")
    materials.connect_material_expressions(strand, "U", fade, "Alpha")
    materials.connect_material_property(fade, "", unreal.MaterialProperty.MP_BASE_COLOR)
    # The hair shading model reads Scatter from Metallic and the strand tangent from Normal
    for name, value, prop, y in (
        ("Scatter", 0.9, unreal.MaterialProperty.MP_METALLIC, 350),
        ("Specular", 0.25, unreal.MaterialProperty.MP_SPECULAR, 500),
        ("Roughness", 0.55, unreal.MaterialProperty.MP_ROUGHNESS, 650),
    ):
        materials.connect_material_property(
            scalar_parameter(material, name, value, -450, y), "", prop
        )
    materials.connect_material_property(strand, "Tangent", unreal.MaterialProperty.MP_NORMAL)
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


def setup(mesh, textures_dir):
    manifest_path = os.path.join(textures_dir, "materials.json")
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


def import_groom(file_path, folder, name):
    """Groom of an Alembic file of Blender, or None if Unreal can not import it."""
    options = unreal.GroomImportOptions()
    conversion = unreal.GroomConversionSettings()
    conversion.rotation, conversion.scale = (
        unreal.Vector(*HAIR_ROTATION),
        unreal.Vector(*HAIR_SCALE),
    )
    options.set_editor_property("conversion_settings", conversion)
    task = unreal.AssetImportTask()
    task.filename = file_path
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.save = True
    task.options = options
    assets.import_asset_tasks([task])
    return unreal.load_asset(f"{folder}/{name}")


def setup_groom(groom, entry, instance):
    """Strand sizes of the particle systems and the material of a new groom. Its groups follow
    the particle systems, and the last system sizes the groups left."""
    groups = []
    for index, group in enumerate(groom.get_editor_property("hair_groups_rendering")):
        size = entry["groups"][min(index, len(entry["groups"]) - 1)]
        # The settings of a group are not exposed to Python, so they are changed as text
        text = re.sub(r'MaterialSlotName="[^"]*"', 'MaterialSlotName="Hair"', group.export_text())
        text = re.sub(r"HairWidth=[^,)]+", f"HairWidth={size['width']:.6f}", text)
        text = re.sub(r"HairTipScale=[^,)]+", f"HairTipScale={size['tip_scale']:.6f}", text)
        group.import_text(text.replace("HairWidth_Override=False", "HairWidth_Override=True"))
        groups.append(group)
    groom.set_editor_property("hair_groups_rendering", groups)
    slot = unreal.HairGroupsMaterial()
    slot.set_editor_property("slot_name", "Hair")
    slot.set_editor_property("material", instance)
    groom.set_editor_property("hair_groups_materials", [slot])
    library.save_loaded_asset(groom)


def enable_simulation(groom):
    """Turn on the simulation of a new groom. Unreal crashes when Python changes the
    simulation of a loaded groom, as it rebuilds the groom without the data the simulation
    needs: the change is saved without rebuilding, and the groom builds that data when Unreal
    loads it again."""
    keys = ",".join(f"(InterpMode=RCIM_Cubic,Time={t},Value={v})" for t, v in HAIR_BEND_SCALE)
    groups = []
    for group in groom.get_editor_property("hair_groups_physics"):
        text = group.export_text().replace("EnableSimulation=False", "EnableSimulation=True")
        for key, value in HAIR_PHYSICS.items():
            text = re.sub(rf"\b{key}=[^,)]+", f"{key}={value}", text)
        text = re.sub(
            r"(BendScale=\(EditorCurveData=\(Keys=\().*?\)(\),Default)", rf"\g<1>{keys}\2", text
        )
        group.import_text(text)
        groups.append(group)
    groom.modify()
    groom.set_editor_property(
        "hair_groups_physics", groups, unreal.PropertyAccessChangeNotifyMode.NEVER
    )
    library.save_loaded_asset(groom, False)


def setup_hair(mesh, hair_dir):
    if getattr(unreal, "GroomImportOptions", None) is None:
        unreal.log_error(
            "MustardUI - Enable the Groom and Alembic Groom Importer plugins to import the hair"
        )
        return 0
    mesh_folder = mesh.get_path_name().rsplit("/", 1)[0]
    folder = f"{mesh_folder}/Hair"
    parent = hair_parent()
    # (groom, binding, imported now)
    grooms = []
    for entry in json.load(open(os.path.join(hair_dir, "hair.json")))["hair"]:
        name = unreal_name(entry["name"])
        groom_path = f"{folder}/GR_{name}"
        # A groom is imported once: changing a simulated groom from Python can crash Unreal
        existed = library.does_asset_exist(groom_path)
        if existed:
            groom = unreal.load_asset(groom_path)
            log(f"{name}: kept the groom already imported, delete it to import it again")
        else:
            groom = import_groom(os.path.join(hair_dir, entry["file"]), folder, f"GR_{name}")
            if groom is None:
                unreal.log_error(
                    f"MustardUI - Could not import {entry['file']}: is the Alembic Groom "
                    "Importer plugin enabled?"
                )
                continue
            instance = assets.create_asset(
                f"MI_Hair_{name}",
                f"{mesh_folder}/Materials",
                unreal.MaterialInstanceConstant,
                unreal.MaterialInstanceConstantFactoryNew(),
            )
            materials.set_material_instance_parent(instance, parent)
            color = entry["groups"][0]["color"]
            if color is not None:
                materials.set_material_instance_vector_parameter_value(
                    instance, "HairColor", unreal.LinearColor(*color, 1)
                )
            library.save_loaded_asset(instance)
            setup_groom(groom, entry, instance)
        binding_path = f"{folder}/GB_{name}"
        if library.does_asset_exist(binding_path):
            binding = unreal.load_asset(binding_path)
        else:
            binding = unreal.GroomLibrary.create_new_groom_binding_asset_with_path(
                binding_path, groom, mesh
            )
            library.save_loaded_asset(binding)
        grooms.append((groom, binding, not existed))
    blueprints = add_to_blueprints(mesh, grooms)
    log(f"{mesh.get_name()}: {len(grooms)} grooms in {folder}")
    if blueprints:
        log(f"Grooms added under the {mesh.get_name()} mesh of {', '.join(blueprints)}")
    else:
        log(
            f"No Blueprint shows {mesh.get_name()}: add a Groom component under the skeletal "
            "mesh of the character, with the groom, its binding, and the physics asset of the "
            "mesh, for the hair to collide with the body"
        )
    # Last, as the grooms must not be rebuilt before Unreal loads them again
    simulated = [groom for groom, _, new in grooms if new]
    for groom in simulated:
        enable_simulation(groom)
    if simulated:
        names = ", ".join(groom.get_name() for groom in simulated)
        unreal.log_warning(
            f"MustardUI - Restart Unreal before using {names}: their hair "
            "simulation is built when they are loaded again, and Unreal can crash before"
        )
    return len(grooms)


def add_to_blueprints(mesh, grooms):
    """Add the grooms to the Blueprints with a component showing the mesh, under it, colliding
    with the physics asset of the mesh. Returns the names of the Blueprints."""
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    data = unreal.SubobjectDataBlueprintFunctionLibrary
    physics = mesh.get_editor_property("physics_asset")
    names = []
    referencers = registry.get_referencers(
        mesh.get_outermost().get_name(), unreal.AssetRegistryDependencyOptions()
    )
    for package in referencers or []:
        blueprint = unreal.load_asset(str(package))
        if not isinstance(blueprint, unreal.Blueprint):
            continue
        handles = subobjects.k2_gather_subobject_data_for_blueprint(blueprint)
        components = [(h, data.get_object(data.get_data(h))) for h in handles]
        parent = next(
            (
                h
                for h, c in components
                if isinstance(c, unreal.SkeletalMeshComponent) and c.get_skinned_asset() == mesh
            ),
            None,
        )
        if parent is None:
            continue
        present = {
            c.get_editor_property("groom_asset")
            for _, c in components
            if isinstance(c, unreal.GroomComponent)
        }
        for groom, binding, _ in grooms:
            if groom in present:
                continue
            handle, _ = subobjects.add_new_subobject(
                unreal.AddNewSubobjectParams(
                    parent_handle=parent,
                    new_class=unreal.GroomComponent,
                    blueprint_context=blueprint,
                )
            )
            subobjects.rename_subobject(handle, unreal.Text(groom.get_name().removeprefix("GR_")))
            component = data.get_object(data.get_data(handle))
            component.set_editor_property("groom_asset", groom)
            component.set_editor_property("binding_asset", binding)
            if physics is not None:
                component.set_editor_property("physics_asset", physics)
        unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
        library.save_loaded_asset(blueprint)
        names.append(blueprint.get_name())
    return names


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
        base = os.path.splitext(source_file(mesh))[0]
        textures_dir, hair_dir = base + "_Textures", base + "_Hair"
        has_materials = os.path.isfile(os.path.join(textures_dir, "materials.json"))
        has_hair = os.path.isfile(os.path.join(hair_dir, "hair.json"))
        if not has_materials and not has_hair:
            unreal.log_error(
                f"MustardUI - {mesh.get_name()}: nothing to set up next to {base}.fbx. Export "
                "the character with Materials ticked or with particle hair, and keep the folders "
                "next to the FBX"
            )
        if has_materials:
            setup(mesh, textures_dir)
        if has_hair:
            setup_hair(mesh, hair_dir)


run()
