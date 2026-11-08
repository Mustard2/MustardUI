"""Export run by a background Blender on a copy of the scene, so it can change the data freely.

blender -b file.blend --factory-startup --disable-autoexec --python worker.py -- settings.json
"""

import json
import os
import shutil
import sys
import traceback

import addon_utils
import bpy
import numpy as np
from mathutils import Matrix, Quaternion

sys.path.insert(0, os.path.dirname(__file__))
import hair_rigs  # noqa: E402
import materials  # noqa: E402
import mhx_skeleton  # noqa: E402
import morph_targets  # noqa: E402

settings = json.load(open(sys.argv[sys.argv.index("--") + 1]))
UNREAL_SCRIPT = "MustardUI_Unreal_Materials.py"


def report_failure(kind, error, trace):
    with open(settings["result"], "w") as file:
        json.dump({"error": str(error)}, file)
    traceback.print_exception(kind, error, trace)


sys.excepthook = report_failure
rig = bpy.data.objects[settings["rig"]]
filepath = settings["filepath"]
addon_utils.enable("io_scene_fbx", default_set=False)

bound = [
    o
    for o in bpy.data.objects
    if o.type == "MESH" and any(m.type == "ARMATURE" and m.object is rig for m in o.modifiers)
]
missing = mhx_skeleton.missing_bones(rig)
if missing:
    raise RuntimeError("Not a complete MHX rig, missing bones: " + ", ".join(missing[:8]))
# Meshes of the hair lists, which can follow the rig without being deformed by it
hair_meshes = set(settings.get("hair_meshes", ()))
hair_objects = [o for o in bpy.data.objects if o.name in hair_meshes and o.type == "MESH"]
# All the bound meshes and hair armatures define the skeleton, so characters and animations
# always match
weighted = mhx_skeleton.weighted_bones(bound)
taken = set(mhx_skeleton.PARENT) | {name.replace(".", "_") for name in weighted}
hair_bones, hair_bone_names = hair_rigs.skeleton_bones(hair_objects, rig, taken)
rest, parent, source = mhx_skeleton.build(rig, weighted, hair_bones)
bones = rig.data.bones


def export(object_types, path_mode="AUTO", animation=None):
    bpy.context.scene.unit_settings.scale_length = 0.01
    bpy.ops.export_scene.fbx(
        filepath=filepath,
        use_selection=True,
        object_types=object_types,
        add_leaf_bones=False,
        use_armature_deform_only=True,
        bake_anim=animation if animation is not None else "MESH" not in object_types,
        bake_anim_use_all_bones=True,
        bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=False,
        bake_anim_force_startend_keying=True,
        bake_anim_step=1.0,
        bake_anim_simplify_factor=0.0,
        mesh_smooth_type="FACE",
        use_mesh_modifiers=False,
        apply_scale_options="FBX_SCALE_ALL",
        axis_forward="-Z",
        axis_up="Y",
        primary_bone_axis="Y",
        secondary_bone_axis="X",
        use_tspace=True,
        path_mode=path_mode,
        embed_textures=False,
    )


def add_bones(armature):
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode="EDIT")
    edit_bones = armature.data.edit_bones
    for name, matrix in rest.items():
        bone = edit_bones.new(name)
        bone.head, bone.tail = (0, 0, 0), (0, 1, 0)
        bone.matrix = matrix
        bone.length = 3.0
        bone.use_deform = True
    for name, above in parent.items():
        if above:
            edit_bones[name].parent = edit_bones[above]
    bpy.ops.object.mode_set(mode="OBJECT")


def export_animation():
    action = bpy.data.actions[settings["action"]]
    animation = rig.animation_data or rig.animation_data_create()
    animation.action = action
    # Slotted actions, from Blender 4.4
    if hasattr(animation, "action_slot") and not animation.action_slot and action.slots:
        animation.action_slot = action.slots[0]
    first = settings["frame_start"] or int(action.frame_range[0])
    last = settings["frame_end"] or int(action.frame_range[1])
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = first, last
    for obj in bound:
        obj.hide_viewport = True

    sources = {name: bones[name].matrix_local.inverted() for name in set(source.values())}
    lift = Matrix.Translation((0, 0, settings["height_offset"]))
    curves = morph_curves(action, animation)
    samples = {}
    values = {name: [] for name in curves}
    for frame in range(first, last + 1):
        for name, fcurve in curves.items():
            values[name].append(fcurve.evaluate(frame))
        scene.frame_set(frame)
        pose = rig.evaluated_get(bpy.context.evaluated_depsgraph_get()).pose.bones
        motion = {name: pose[name].matrix @ inverse for name, inverse in sources.items()}
        sample = {}
        for name, matrix in rest.items():
            moved = motion[source[name]].copy()
            moved.translation *= 100.0
            placed = moved @ matrix
            if name != "root":
                placed = lift @ placed
            location, rotation, _ = placed.decompose()
            sample[name] = Matrix.Translation(location) @ rotation.to_matrix().to_4x4()
        samples[frame] = sample

    animation.action = None
    rig.name = "MustardUI_Source"
    rig.hide_viewport = True
    armature = bpy.data.objects.new("Armature", bpy.data.armatures.new("Armature"))
    scene.collection.objects.link(armature)
    add_bones(armature)
    previous = {}
    for frame, sample in samples.items():
        for name, matrix in rest.items():
            above = parent[name]
            relative = rest[above].inverted() @ matrix if above else matrix
            local = sample[above].inverted() @ sample[name] if above else sample[name]
            location, rotation, _ = (relative.inverted() @ local).decompose()
            # Stay on the same side as the previous key, or the interpolation spins
            if name in previous and rotation.dot(previous[name]) < 0:
                rotation = Quaternion(-rotation)
            previous[name] = rotation
            bone = armature.pose.bones[name]
            bone.rotation_mode = "QUATERNION"
            bone.location, bone.rotation_quaternion = location, rotation
            bone.keyframe_insert("location", frame=frame, group=name)
            bone.keyframe_insert("rotation_quaternion", frame=frame, group=name)
    carrier = curve_carrier(armature, values, first) if values else None
    for obj in bpy.data.objects:
        obj.select_set(obj in (armature, carrier))
    if carrier is None:
        export({"ARMATURE"})
    else:
        export({"ARMATURE", "MESH"}, animation=True)
    result = {"bones": len(rest), "frames": last - first + 1}
    if values:
        result["morph curves"] = len(values)
    return result


def action_fcurves(action, animation):
    """(F-curve, ID type it animates) of the action. Slotted actions, from Blender 4.4, can
    animate the armature and the shape keys of the meshes together."""
    if not hasattr(action, "layers"):
        return [(fcurve, "OBJECT") for fcurve in action.fcurves]
    result = []
    for layer in action.layers:
        for strip in layer.strips:
            for bag in getattr(strip, "channelbags", ()):
                slot = bag.slot
                if slot.target_id_type == "OBJECT" and slot != animation.action_slot:
                    continue
                result.extend((fcurve, slot.target_id_type) for fcurve in bag.fcurves)
    return result


def morph_curves(action, animation):
    """F-curves of the action which drive morph targets, by name of the morph target: the
    properties of the rig which are face controls or MustardUI morphs, and the shape keys."""
    names = settings.get("curves", {})
    result = {}
    if not settings.get("morph_curves", False):
        return result
    for fcurve, id_type in action_fcurves(action, animation):
        path = fcurve.data_path
        if id_type == "OBJECT" and path.startswith('["') and path.endswith('"]'):
            for name in names.get(path[2:-2], ()):
                result[name] = fcurve
        elif id_type == "KEY" and path.startswith('key_blocks["') and path.endswith('"].value'):
            result.setdefault(path[12:-8], fcurve)
    return result


def curve_carrier(armature, values, first):
    """A small mesh with a shape key per curve, animated with the values. FBX keeps the
    animation of morph targets only on meshes, and Unreal reads it as curves."""
    mesh = bpy.data.meshes.new("MorphCurves")
    mesh.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
    obj = bpy.data.objects.new("MorphCurves", mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = armature
    obj.vertex_groups.new(name="root").add([0, 1, 2], 1.0, "REPLACE")
    obj.modifiers.new("Armature", "ARMATURE").object = armature
    obj.shape_key_add(name="Basis", from_mix=False)
    for name, frames in values.items():
        key = obj.shape_key_add(name=name, from_mix=False)
        # Shape keys without offsets are not exported
        key.data[0].co.z += 0.01
        key.slider_min, key.slider_max = -10.0, 10.0
        for frame, value in enumerate(frames, start=first):
            key.value = value
            key.keyframe_insert("value", frame=frame)
    return obj


def smooth_split(t):
    t = max(0.0, min(1.0, (t - 0.25) / 0.5))
    return t * t * (3 - 2 * t)


def mustardui_morphs():
    """MustardUI morphs chosen for the export, as (morph name, owner, property)."""
    controls = []
    for morph in settings.get("morphs", []):
        owner = getattr(bpy.data, morph["collection"]).get(morph["owner"])
        if owner is None:
            continue
        if "shape_key" in morph:
            block = owner.key_blocks.get(morph["shape_key"])
            if block is not None:
                controls.append((morph["name"], block, None))
        elif morph["property"] in owner.keys():
            controls.append((morph["name"], owner, morph["property"]))
    return controls


def converted_morphs(meshes, controls):
    """Shape key offsets of controls which can move bones or several shape keys, measured on
    the evaluated meshes. A control is (morph name, owner, property), and None as property
    means the value of a shape key."""
    for bone in rig.pose.bones:
        bone.location, bone.rotation_quaternion, bone.rotation_euler = (
            (0, 0, 0),
            (1, 0, 0, 0),
            (0, 0, 0),
        )
        bone.scale = (1, 1, 1)
    for obj in meshes:
        for modifier in obj.modifiers:
            if modifier.type != "ARMATURE":
                modifier.show_viewport = False

    def get(owner, prop):
        return owner.value if prop is None else owner[prop]

    def set_value(owner, prop, value):
        if prop is None:
            owner.value = value
        else:
            owner[prop] = type(owner[prop])(value)
        owner.id_data.update_tag()

    def positions():
        for data in [rig, rig.data] + [o.data for o in meshes]:
            data.update_tag()
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        result = {}
        for obj in meshes:
            evaluated = obj.evaluated_get(depsgraph)
            mesh = evaluated.to_mesh()
            co = np.empty(len(mesh.vertices) * 3, dtype=np.float64)
            mesh.vertices.foreach_get("co", co)
            evaluated.to_mesh_clear()
            result[obj.name] = co.reshape(-1, 3)
        return result

    if "facs_ctrl_EyeLookAuto" in rig.keys():
        rig["facs_ctrl_EyeLookAuto"] = 0.0
    neutral = positions()
    offsets = {}
    for name, owner, prop in controls:
        value = get(owner, prop)
        # Morphs already in use are measured from zero, as they are part of the character
        if value:
            set_value(owner, prop, 0.0)
        start = positions() if value else neutral
        set_value(owner, prop, 1.0)
        moved = positions()
        set_value(owner, prop, value)
        offsets[name] = {
            k: moved[k] - start[k]
            for k in moved
            if np.linalg.norm(moved[k] - start[k], axis=1).max() > 1e-4
        }
    # Drivers write their values back to the shape keys: evaluate the restored controls again,
    # or the shape keys driven by the last control would look active and be baked
    if controls:
        positions()
    return offsets


def key_co(key, count):
    co = np.empty(count * 3, dtype=np.float32)
    key.data.foreach_get("co", co)
    return co.reshape(-1, 3)


def final(obj, co):
    """Shape key positions in world space, in cm."""
    if not obj.matrix_world.is_identity:
        world = np.array(obj.matrix_world, dtype=np.float64)
        co = co @ world[:3, :3].T + world[:3, 3]
    return (co * 100.0).astype(np.float32)


def hair_color(material):
    """Color of the strands: the Principled Hair BSDF of the material, its viewport color if
    changed, or None. Inputs driven by nodes are left out."""
    tree = material.node_tree if material.use_nodes else None
    output = tree and (tree.get_output_node("ALL") or tree.get_output_node("CYCLES"))
    links = output.inputs["Surface"].links if output else ()
    bsdf = links[0].from_node if links else None
    if bsdf is not None and bsdf.bl_idname == "ShaderNodeBsdfHairPrincipled":
        if bsdf.parametrization == "COLOR":
            return list(bsdf.inputs["Color"].default_value[:3])
        if bsdf.parametrization == "MELANIN":
            # Absorption of the melanin as in Cycles, and the color giving it back
            amount = -np.log(max(1.0 - bsdf.inputs["Melanin"].default_value, 1e-4))
            redness = bsdf.inputs["Melanin Redness"].default_value
            sigma = amount * (
                (1 - redness) * np.array((0.506, 0.841, 1.653))
                + redness * np.array((0.343, 0.733, 1.924))
            )
            roughness = bsdf.inputs.get("Radial Roughness", bsdf.inputs["Roughness"])
            b = roughness.default_value
            scale = 5.969 - 0.215 * b + 2.532 * b**2 - 10.73 * b**3 + 5.574 * b**4 + 0.245 * b**5
            return list(np.exp(-np.sqrt(sigma) * scale))
    color = list(material.diffuse_color[:3])
    return None if np.allclose(color, 0.8) else color


def export_grooms(names):
    """Particle hair as Alembic files for the hair strands of Unreal, in a folder next to the
    FBX, with the rig in rest pose and in cm like the meshes. hair.json gives the Unreal script
    the width, tip scale and color of the strands of each particle system."""
    folder = os.path.splitext(filepath)[0] + "_Hair"
    os.makedirs(folder, exist_ok=True)
    rig.data.pose_position = "REST"
    entries = []
    for name in names:
        obj = bpy.data.objects[name]
        hair_rigs.show(obj)
        obj.hide_render = obj.hide_select = False
        materials = [slot.material for slot in obj.material_slots]
        groups = []
        for modifier in obj.modifiers:
            system = getattr(modifier, "particle_system", None)
            if system is None or system.settings.type != "HAIR":
                continue
            modifier.show_viewport = modifier.show_render = True
            # The combed shape, not a simulated one
            system.use_hair_dynamics = False
            hair = system.settings
            # Particle settings number the material slots from 1
            material = materials[hair.material - 1] if hair.material <= len(materials) else None
            groups.append(
                {
                    "width": hair.root_radius * hair.radius_scale * 100.0,
                    "tip_scale": hair.tip_radius / hair.root_radius if hair.root_radius else 1.0,
                    "color": hair_color(material) if material else None,
                }
            )
        for other in bpy.context.view_layer.objects:
            other.select_set(other is obj)
        file = bpy.path.clean_name(name) + ".abc"
        frame = bpy.context.scene.frame_current
        bpy.ops.wm.alembic_export(
            filepath=os.path.join(folder, file),
            selected=True,
            flatten=True,
            start=frame,
            end=frame,
            export_hair=True,
            export_particles=False,
            normals=False,
            global_scale=100.0,
            evaluation_mode="RENDER",
            as_background_job=False,
        )
        entries.append({"name": name, "file": file, "groups": groups})
    rig.data.pose_position = "POSE"
    with open(os.path.join(folder, "hair.json"), "w") as file:
        json.dump({"hair": entries}, file, indent=1)
    return len(entries)


def export_character():
    particle_hair = set(settings.get("particle_hair", ()))
    pieces = set(settings.get("outfit_pieces", ())) | hair_meshes | particle_hair
    chosen = set(settings.get("outfits", ())) | set(settings.get("hair", ()))
    # Particle hair is not in the FBX: it is exported first, before the scene is changed
    grooms = export_grooms(sorted(chosen & particle_hair)) if chosen & particle_hair else 0
    # Outfit pieces and hair chosen in the export, and the other visible meshes of the model
    meshes = [o for o in bound if (o.name in chosen if o.name in pieces else o.visible_get())]
    # Hair not deformed by the rig follows it rigidly, or with its own hair armature
    rigid, prepared = {}, set()
    for obj in hair_objects:
        if obj.name in chosen and obj not in bound:
            bone = hair_rigs.prepare(obj, rig, prepared)
            if bone is not None:
                rigid[obj.name] = bone
            meshes.append(obj)
    if not meshes:
        raise RuntimeError("No visible mesh bound to the armature")
    # Hidden outfit pieces are shown, so they are evaluated like the others
    for obj in meshes:
        if obj.name not in bpy.context.view_layer.objects:
            bpy.context.scene.collection.objects.link(obj)
        obj.hide_set(False)
        obj.hide_viewport = False
    for obj in meshes:
        if obj.data.shape_keys is None:
            obj.shape_key_add(name="Basis", from_mix=False)
    # Kinds of morph targets in the export, without the items not chosen in its lists
    export_keys = settings.get("shape_keys", True)
    skip_keys = set(settings.get("skip_shape_keys", ()))
    export_controls = settings.get("face_controls", True)
    skip_controls = set(settings.get("skip_face_controls", ()))
    controls = mustardui_morphs()
    morph_names = {name for name, _, _ in controls}
    # A face control which is also a MustardUI morph is exported once, as the morph
    morph_properties = {prop for _, owner, prop in controls if owner == rig}
    controls = [
        (name, rig, name)
        for name in morph_targets.face_controls(rig)
        if export_controls
        and name not in morph_names | morph_properties
        and name not in skip_controls
    ] + controls
    offsets = converted_morphs(meshes, controls)
    # Morphs which change nothing in the exported meshes are left out
    unused = [name for name, offset in offsets.items() if not offset]

    morphs = set()
    for obj in meshes:
        mesh = obj.data
        keys = mesh.shape_keys.key_blocks
        count = len(mesh.vertices)

        values = {k.name: k.value for k in keys}
        # Active morphs that are not animation controls are part of the character's shape
        baked = [k.name for k in keys if morph_targets.is_baked(k)]
        basis = key_co(keys["Basis"], count).astype(np.float64)
        shape = np.zeros_like(basis)
        for name in baked:
            shape += values[name] * (key_co(keys[name], count) - basis)
        names = {g.index: g.name for g in obj.vertex_groups}
        weights = {}
        armature = hair_rigs.armature_of(obj, rig)
        hair_groups = hair_bone_names.get(armature.name, {}) if armature is not None else {}
        for vertex in mesh.vertices:
            position = obj.matrix_world @ vertex.co
            for group in vertex.groups:
                name = names.get(group.group)
                if group.weight > 0 and name in hair_groups:
                    weights.setdefault(hair_groups[name], []).append((vertex.index, group.weight))
                    continue
                if group.weight <= 0 or name not in bones:
                    continue
                if name in mhx_skeleton.SPLIT:
                    bone = bones[name]
                    along = bone.tail_local - bone.head_local
                    t = smooth_split((position - bone.head_local).dot(along) / along.dot(along))
                    first, second = mhx_skeleton.SPLIT[name]
                    if t < 1:
                        weights.setdefault(first, []).append((vertex.index, group.weight * (1 - t)))
                    if t > 0:
                        weights.setdefault(second, []).append((vertex.index, group.weight * t))
                else:
                    target = mhx_skeleton.PLAIN.get(name, name.replace(".", "_"))
                    weights.setdefault(target, []).append((vertex.index, group.weight))
        if obj.name in rigid:
            weights = {rigid[obj.name]: [(v.index, 1.0) for v in mesh.vertices]}

        result = {
            k.name: final(obj, key_co(k, count) + shape)
            for k in keys
            if k.name not in baked
            and (k.name == "Basis" or (export_keys and k.name not in skip_keys))
        }
        for control, offset in offsets.items():
            if obj.name in offset:
                result[control] = final(obj, basis + shape + offset[obj.name])

        if mesh.shape_keys.animation_data:
            mesh.shape_keys.animation_data_clear()
        if mesh.animation_data:
            mesh.animation_data_clear()
        obj.animation_data_clear()
        obj.active_shape_key_index = 0
        obj.show_only_shape_key = False
        for name in [k.name for k in keys if k.name not in result]:
            obj.shape_key_remove(keys[name])
        for name in result:
            if name not in keys:
                obj.shape_key_add(name=name, from_mix=False)
        for key in keys:
            key.data.foreach_set("co", result[key.name].ravel())
            key.value = 0.0
            key.mute = False
        mesh.vertices.foreach_set("co", result["Basis"].ravel())
        mesh.update()
        morphs.update(n for n in result if n != "Basis")

        obj.parent_type = "OBJECT"
        if not obj.matrix_world.is_identity:
            obj.matrix_parent_inverse = Matrix.Identity(4)
            obj.location, obj.rotation_mode, obj.rotation_euler = (0, 0, 0), "XYZ", (0, 0, 0)
            obj.scale = (1, 1, 1)
        for modifier in list(obj.modifiers):
            if modifier.type != "ARMATURE":
                obj.modifiers.remove(modifier)
        # One Armature modifier with the exported skeleton, also for hair
        deform = [m for m in obj.modifiers if m.type == "ARMATURE"]
        for modifier in deform[1:]:
            obj.modifiers.remove(modifier)
        modifier = deform[0] if deform else obj.modifiers.new("Armature", "ARMATURE")
        modifier.object = rig
        obj.vertex_groups.clear()
        for name, entries in weights.items():
            group = obj.vertex_groups.new(name=name)
            for index, weight in entries:
                group.add([index], weight, "ADD")

    for obj in list(bpy.data.objects):
        if obj is not rig and obj not in meshes:
            bpy.data.objects.remove(obj, do_unlink=True)
    if rig.animation_data:
        rig.animation_data_clear()
    if rig.data.animation_data:
        rig.data.animation_data_clear()
    rig.name = "Armature"
    rig.data.pose_position = "REST"
    rig.data.use_mirror_x = False
    for obj in [rig, *meshes]:
        if obj.name not in bpy.context.view_layer.objects:
            bpy.context.scene.collection.objects.link(obj)
        obj.hide_set(False)
        obj.hide_viewport = False
        # The FBX export takes the selected objects, and pieces can be unselectable
        obj.hide_select = False
        obj.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    for bone in list(rig.data.edit_bones):
        rig.data.edit_bones.remove(bone)
    bpy.ops.object.mode_set(mode="OBJECT")
    add_bones(rig)
    result = {"bones": len(rest), "meshes": len(meshes), "morphs": len(morphs)}
    if grooms:
        result["grooms"] = grooms
    if settings.get("materials"):
        # Textures go to a folder next to the FBX, which refers to them with relative paths
        folder = os.path.splitext(filepath)[0] + "_Textures"
        info, clear = materials.simplify(meshes, folder, settings.get("images", {}))
        result.update(info)
        if clear:
            meshes = materials.remove_faces(meshes, clear)
            result["meshes"] = len(meshes)
            result["see-through materials left out"] = len(clear)
        export({"ARMATURE", "MESH"}, path_mode="RELATIVE")
    else:
        export({"ARMATURE", "MESH"})
    if settings.get("materials") or grooms:
        # The script building the materials and the grooms in Unreal, next to the FBX
        shutil.copyfile(
            os.path.join(os.path.dirname(__file__), "resources", UNREAL_SCRIPT),
            os.path.join(os.path.dirname(filepath), UNREAL_SCRIPT),
        )
    if unused:
        result["morphs without effect"] = len(unused)
    return result


result = export_animation() if settings["mode"] == "ANIMATION" else export_character()
json.dump(result, open(settings["result"], "w"))
sys.stdout.flush()
os._exit(0)
