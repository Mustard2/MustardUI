"""Mesh hair for the background worker: how each hair mesh follows the rig, and the bones of
hair armatures added to the exported skeleton.

A hair mesh can be deformed by the rig, by a hair armature of its own, or follow a bone of
the rig rigidly (parented to it, with a Child Of constraint, or not attached at all, then the
head).
"""

import bpy
import mhx_skeleton
from mathutils import Matrix


def armature_of(obj, rig):
    """Armature deforming the object other than the rig, or None."""
    for modifier in obj.modifiers:
        target = modifier.object if modifier.type == "ARMATURE" else None
        if target is not None and target is not rig and target.type == "ARMATURE":
            return target
    return None


def is_bound(obj, rig):
    return any(m.type == "ARMATURE" and m.object is rig for m in obj.modifiers)


def follow_bone(obj, rig):
    """Bone of the rig the object follows: its parent bone or Child Of target, else head."""
    bones = rig.data.bones
    if obj.parent is rig and obj.parent_type == "BONE" and obj.parent_bone in bones:
        return obj.parent_bone
    for constraint in obj.constraints:
        target = getattr(constraint, "target", None)
        subtarget = getattr(constraint, "subtarget", "")
        if constraint.type == "CHILD_OF" and target is rig and subtarget in bones:
            return subtarget
    return "head"


def unreal_bone(name):
    """Bone of the exported skeleton for a bone of the rig, or head."""
    if name in mhx_skeleton.PLAIN:
        return mhx_skeleton.PLAIN[name]
    if name in mhx_skeleton.SPLIT:
        return mhx_skeleton.SPLIT[name][1]
    return mhx_skeleton.ANCESTOR.get(name, "head")


def rest_matrix(obj, rig):
    """World matrix of the object with the rig in rest pose, keeping it on its bone."""
    bone = follow_bone(obj, rig)
    posed = rig.matrix_world @ rig.pose.bones[bone].matrix
    rested = rig.matrix_world @ rig.data.bones[bone].matrix_local
    return rested @ posed.inverted() @ obj.matrix_world


def skeleton_bones(hair_objects, rig, taken):
    """Bones of the hair armatures used by the hair meshes, for the exported skeleton.
    Returns (bones as (name, rest matrix in cm, parent, rig bone it follows), and the names of
    the bones by armature and bone). Names already taken by the skeleton get a hair_ prefix."""
    armatures = {}
    for obj in hair_objects:
        armature = armature_of(obj, rig)
        if armature is not None:
            armatures[armature.name] = armature
    extra, names = [], {}
    to_rig = rig.matrix_world.inverted()
    for armature in armatures.values():
        follow = follow_bone(armature, rig)
        world = rest_matrix(armature, rig)
        deform = [b for b in armature.data.bones if b.use_deform]
        renamed = {}
        for bone in deform:
            name = bone.name.replace(".", "_")
            while name in taken:
                name = "hair_" + name
            taken.add(name)
            renamed[bone.name] = name
        for bone in deform:
            location, rotation, _ = (to_rig @ world @ bone.matrix_local).decompose()
            matrix = Matrix.Translation(location * 100.0) @ rotation.to_matrix().to_4x4()
            above = bone.parent
            while above is not None and above.name not in renamed:
                above = above.parent
            parent = renamed[above.name] if above is not None else unreal_bone(follow)
            extra.append((renamed[bone.name], matrix, parent, follow))
        names[armature.name] = renamed
    return extra, names


def prepare(obj, rig, done):
    """Place a hair mesh not deformed by the rig where it is with the rig in rest pose, free
    from parents and constraints, and its hair armature with it, once for all its meshes in
    done. Returns the bone of the exported skeleton the mesh follows rigidly, or None if a
    hair armature deforms it."""
    armature = armature_of(obj, rig)
    targets = [obj] if armature is None or armature in done else [obj, armature]
    worlds = [rest_matrix(o, rig) for o in targets]
    for target, world in zip(targets, worlds, strict=True):
        show(target)
        target.parent = None
        target.constraints.clear()
        target.matrix_world = world
    if armature is None:
        return unreal_bone(follow_bone(obj, rig))
    done.add(armature)
    for bone in armature.pose.bones:
        bone.location, bone.rotation_quaternion, bone.rotation_euler = (
            (0, 0, 0),
            (1, 0, 0, 0),
            (0, 0, 0),
        )
        bone.scale = (1, 1, 1)
    return None


def show(obj):
    """Hidden objects are not evaluated, so they are linked to the scene and shown."""
    if obj.name not in bpy.context.view_layer.objects:
        bpy.context.scene.collection.objects.link(obj)
    obj.hide_set(False)
    obj.hide_viewport = False
