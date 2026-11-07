"""Export run by a background Blender on a copy of the scene, so it can change the data freely.

blender -b file.blend --factory-startup --disable-autoexec --python worker.py -- settings.json
"""

import json
import os
import re
import sys
import traceback

import addon_utils
import bpy
import numpy as np
from mathutils import Matrix, Quaternion

sys.path.insert(0, os.path.dirname(__file__))
import mhx_skeleton  # noqa: E402

settings = json.load(open(sys.argv[sys.argv.index("--") + 1]))


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
# All the bound meshes define the skeleton, so characters and animations always match
weighted = mhx_skeleton.weighted_bones(bound)
rest, parent, source = mhx_skeleton.build(rig, weighted)
bones = rig.data.bones


def export(object_types):
    bpy.context.scene.unit_settings.scale_length = 0.01
    bpy.ops.export_scene.fbx(
        filepath=filepath,
        use_selection=True,
        object_types=object_types,
        add_leaf_bones=False,
        use_armature_deform_only=True,
        bake_anim="ARMATURE" in object_types and "MESH" not in object_types,
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
        path_mode="AUTO",
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
    samples = {}
    for frame in range(first, last + 1):
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
    for obj in bpy.data.objects:
        obj.select_set(obj is armature)
    export({"ARMATURE"})
    return {"bones": len(rest), "frames": last - first + 1}


def smooth_split(t):
    t = max(0.0, min(1.0, (t - 0.25) / 0.5))
    return t * t * (3 - 2 * t)


def bone_driven_morphs(meshes):
    """Shape key offsets of the facial controls which only move bones in the rig."""
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
    controls = set()
    for driver in rig.animation_data.drivers if rig.animation_data else ():
        if re.match(
            r'pose\.bones\["[^"]+"\]\.(location|rotation_euler|rotation_quaternion|scale)',
            driver.data_path,
        ):
            for variable in driver.driver.variables:
                path = variable.targets[0].data_path
                if variable.type == "SINGLE_PROP" and path.startswith('["'):
                    controls.add(path[2:-2].replace("(fin)", ""))
    controls = sorted(
        n
        for n in controls
        if n.startswith("facs_")
        and n in rig.keys()
        and not re.search("EyeLook|EyeCrossed|EyeResting", n)
    )

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
    for control in controls:
        value = rig[control]
        rig[control] = 1.0
        moved = positions()
        offsets[control] = {
            k: moved[k] - neutral[k]
            for k in moved
            if np.linalg.norm(moved[k] - neutral[k], axis=1).max() > 1e-4
        }
        rig[control] = value
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


def export_character():
    meshes = [o for o in bound if o.visible_get()]
    if not meshes:
        raise RuntimeError("No visible mesh bound to the armature")
    for obj in meshes:
        if obj.data.shape_keys is None:
            obj.shape_key_add(name="Basis", from_mix=False)
    offsets = bone_driven_morphs(meshes)

    morphs = set()
    for obj in meshes:
        mesh = obj.data
        keys = mesh.shape_keys.key_blocks
        count = len(mesh.vertices)

        values = {k.name: k.value for k in keys}
        # Active morphs that are not animation controls are part of the character's shape
        baked = [
            k.name
            for k in keys
            if k.name != "Basis"
            and abs(k.value) > 1e-3
            and not k.name.startswith(("facs_", "body_cbs"))
        ]
        basis = key_co(keys["Basis"], count).astype(np.float64)
        shape = np.zeros_like(basis)
        for name in baked:
            shape += values[name] * (key_co(keys[name], count) - basis)
        names = {g.index: g.name for g in obj.vertex_groups}
        weights = {}
        for vertex in mesh.vertices:
            position = obj.matrix_world @ vertex.co
            for group in vertex.groups:
                name = names.get(group.group)
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

        result = {k.name: final(obj, key_co(k, count) + shape) for k in keys if k.name not in baked}
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
        obj.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    for bone in list(rig.data.edit_bones):
        rig.data.edit_bones.remove(bone)
    bpy.ops.object.mode_set(mode="OBJECT")
    add_bones(rig)
    export({"ARMATURE", "MESH"})
    return {"bones": len(rest), "meshes": len(meshes), "morphs": len(morphs)}


result = export_animation() if settings["mode"] == "ANIMATION" else export_character()
json.dump(result, open(settings["result"], "w"))
sys.stdout.flush()
os._exit(0)
