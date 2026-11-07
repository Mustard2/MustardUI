"""Skeleton with the bones of the Unreal mannequin built from an MHX rig.

Imported also by worker.py in a background Blender, so it must not import the add-on.
"""

import json
import math
import os

from mathutils import Matrix, Vector

with open(os.path.join(os.path.dirname(__file__), "resources/manny_rest.json")) as file:
    MANNY = json.load(file)

FINGERS = ("index", "middle", "ring", "pinky")

# MHX bone: Unreal bone receiving its weights
PLAIN = {
    "pelvis.twk": "pelvis",
    "spine.twk": "spine_01",
    "spine-1.twk": "spine_02",
    "chest-1.twk": "spine_05",
    "neck.twk": "neck_01",
    "neck-1.twk": "neck_02",
    "head": "head",
}
# MHX bone: the two Unreal bones its weights are split between, along the length of the bone
SPLIT = {"chest.twk": ("spine_03", "spine_04")}
# Unreal bone: MHX bone at the same joint
JOINT = {}
# Unreal bone: parent
PARENT = {
    "root": None,
    "pelvis": "root",
    "spine_01": "pelvis",
    "spine_02": "spine_01",
    "spine_03": "spine_02",
    "spine_04": "spine_03",
    "spine_05": "spine_04",
    "neck_01": "spine_05",
    "neck_02": "neck_01",
    "head": "neck_02",
}
# Non deforming MHX bone: the Unreal bone its deforming children are parented to
ANCESTOR = {
    "master": "root",
    "hip": "pelvis",
    "pelvis": "pelvis",
    "DEF-spine": "spine_01",
    "DEF-spine-1": "spine_02",
    "DEF-chest": "spine_04",
    "DEF-chest-1": "spine_05",
    "neckParent": "spine_05",
    "neck": "neck_01",
    "neck-1": "neck_02",
}

for S, s in (("L", "l"), ("R", "r")):
    PLAIN |= {
        f"clavicle.{S}": f"clavicle_{s}",
        f"upper_arm.twist.twk.{S}": f"upperarm_twist_02_{s}",
        f"forearm.twist.twk.{S}": f"lowerarm_twist_01_{s}",
        f"thigh.twist.twk.{S}": f"thigh_twist_02_{s}",
        f"shin.twist.twk.{S}": f"calf_twist_01_{s}",
        f"foot.twk.{S}": f"foot_{s}",
        f"tarsal.{S}": f"foot_{s}",
        f"toe.{S}": f"ball_{s}",
        f"hand.twk.{S}": f"hand_{s}",
    }
    SPLIT |= {
        f"upper_arm.bend.twk.{S}": (f"upperarm_{s}", f"upperarm_twist_01_{s}"),
        f"forearm.bend.twk.{S}": (f"lowerarm_{s}", f"lowerarm_twist_02_{s}"),
        f"thigh.bend.twk.{S}": (f"thigh_{s}", f"thigh_twist_01_{s}"),
        f"shin.bend.twk.{S}": (f"calf_{s}", f"calf_twist_02_{s}"),
    }
    JOINT |= {
        f"clavicle_{s}": f"clavicle.{S}",
        f"upperarm_{s}": f"upper_arm.{S}",
        f"lowerarm_{s}": f"forearm.{S}",
        f"hand_{s}": f"hand.{S}",
        f"thigh_{s}": f"thigh.{S}",
        f"calf_{s}": f"shin.{S}",
        f"foot_{s}": f"foot.{S}",
        f"ball_{s}": f"toe.{S}",
    }
    PARENT |= {
        f"clavicle_{s}": "spine_05",
        f"upperarm_{s}": f"clavicle_{s}",
        f"upperarm_twist_01_{s}": f"upperarm_{s}",
        f"upperarm_twist_02_{s}": f"upperarm_{s}",
        f"lowerarm_{s}": f"upperarm_{s}",
        f"lowerarm_twist_01_{s}": f"lowerarm_{s}",
        f"lowerarm_twist_02_{s}": f"lowerarm_{s}",
        f"hand_{s}": f"lowerarm_{s}",
        f"thigh_{s}": "pelvis",
        f"thigh_twist_01_{s}": f"thigh_{s}",
        f"thigh_twist_02_{s}": f"thigh_{s}",
        f"calf_{s}": f"thigh_{s}",
        f"calf_twist_01_{s}": f"calf_{s}",
        f"calf_twist_02_{s}": f"calf_{s}",
        f"foot_{s}": f"calf_{s}",
        f"ball_{s}": f"foot_{s}",
        f"thumb_01_{s}": f"hand_{s}",
    }
    for i in (1, 2, 3):
        PLAIN[f"thumb.0{i}.{S}"] = f"thumb_0{i}_{s}"
        JOINT[f"thumb_0{i}_{s}"] = f"thumb.0{i}.{S}"
        if i > 1:
            PARENT[f"thumb_0{i}_{s}"] = f"thumb_0{i - 1}_{s}"
    for finger in FINGERS:
        PLAIN[f"palm_{finger}.{S}"] = f"{finger}_metacarpal_{s}"
        JOINT[f"{finger}_metacarpal_{s}"] = f"palm_{finger}.{S}"
        PARENT[f"{finger}_metacarpal_{s}"] = f"hand_{s}"
        for i in (1, 2, 3):
            PLAIN[f"f_{finger}.0{i}.{S}"] = f"{finger}_0{i}_{s}"
            JOINT[f"{finger}_0{i}_{s}"] = f"f_{finger}.0{i}.{S}"
            PARENT[f"{finger}_0{i}_{s}"] = (
                f"{finger}_0{i - 1}_{s}" if i > 1 else f"{finger}_metacarpal_{s}"
            )

# Bones placed without a joint in JOINT
SPINE_JOINTS = {
    "spine_01": "DEF-spine",
    "spine_02": "DEF-spine-1",
    "spine_03": "DEF-chest",
    "spine_05": "DEF-chest-1",
    "neck_01": "neck",
    "neck_02": "neck-1",
    "head": "head",
}
# Bone: the bone it points to, to align the mannequin axes to the limbs of the character
AIM = {
    "pelvis": "spine_01",
    "spine_01": "spine_02",
    "spine_02": "spine_03",
    "spine_03": "spine_04",
    "spine_04": "spine_05",
    "spine_05": "neck_01",
    "neck_01": "neck_02",
    "neck_02": "head",
}
for s in "lr":
    AIM |= {
        f"clavicle_{s}": f"upperarm_{s}",
        f"upperarm_{s}": f"lowerarm_{s}",
        f"lowerarm_{s}": f"hand_{s}",
        f"hand_{s}": f"middle_01_{s}",
        f"thigh_{s}": f"calf_{s}",
        f"calf_{s}": f"foot_{s}",
        f"foot_{s}": f"ball_{s}",
        f"thumb_01_{s}": f"thumb_02_{s}",
        f"thumb_02_{s}": f"thumb_03_{s}",
    }
    for finger in FINGERS:
        AIM |= {
            f"{finger}_metacarpal_{s}": f"{finger}_01_{s}",
            f"{finger}_01_{s}": f"{finger}_02_{s}",
            f"{finger}_02_{s}": f"{finger}_03_{s}",
        }
# Limb bone, its child, and the twist bones at 1/3 and 2/3 of it
TWISTS = (
    ("upperarm", "lowerarm", "01", "02"),
    ("thigh", "calf", "01", "02"),
    ("lowerarm", "hand", "02", "01"),
    ("calf", "foot", "02", "01"),
)


def manny_rotation(name):
    """Rest rotation of a mannequin bone in Blender space, where Unreal has Y flipped."""
    rotation = MANNY[name]["rotation"]
    p, y, r = (math.radians(rotation[k]) for k in ("pitch", "yaw", "roll"))
    sp, cp, sy, cy, sr, cr = (
        math.sin(p),
        math.cos(p),
        math.sin(y),
        math.cos(y),
        math.sin(r),
        math.cos(r),
    )
    matrix = Matrix(
        (
            (cp * cy, sr * sp * cy - cr * sy, -(cr * sp * cy + sr * sy)),
            (cp * sy, sr * sp * sy + cr * cy, cy * sr - cr * sp * sy),
            (sp, -sr * cp, cr * cp),
        )
    )
    flip = Matrix.Diagonal((1, -1, 1))
    return flip @ matrix @ flip


def manny_location(name):
    location = MANNY[name]["location"]
    return Vector((location["x"], -location["y"], location["z"]))


def missing_bones(rig):
    needed = (
        set(PLAIN) | set(SPLIT) | set(JOINT.values()) | set(ANCESTOR) | set(SPINE_JOINTS.values())
    )
    return sorted(name for name in needed if name not in rig.data.bones)


def weighted_bones(meshes):
    """Names of the vertex groups of the meshes with at least one weight."""
    names = set()
    for obj in meshes:
        index = {g.index: g.name for g in obj.vertex_groups}
        for vertex in obj.data.vertices:
            names.update(index[g.group] for g in vertex.groups if g.weight > 0 and g.group in index)
    return names


def build(rig, weighted):
    """Return rest matrices in cm, parents and MHX source bones, ordered with parents first."""
    bones = rig.data.bones
    head = lambda name: bones[name].head_local * 100.0  # noqa: E731
    source = {"root": "master"}
    for name, target in PLAIN.items():
        source[target] = name
    for name, targets in SPLIT.items():
        source.update(dict.fromkeys(targets, name))

    pos = {"root": Vector((0, 0, 0))}
    pos |= {target: head(name) for target, name in SPINE_JOINTS.items()}
    pos |= {target: head(name) for target, name in JOINT.items()}
    pos["spine_04"] = (head("DEF-chest") + head("DEF-chest-1")) / 2
    pos["pelvis"] = ((pos["thigh_l"] + pos["thigh_r"]) / 2).lerp(pos["spine_01"], 0.4)
    for s in "lr":
        for part, child, first, second in TWISTS:
            pos[f"{part}_twist_{first}_{s}"] = pos[f"{part}_{s}"].lerp(pos[f"{child}_{s}"], 1 / 3)
            pos[f"{part}_twist_{second}_{s}"] = pos[f"{part}_{s}"].lerp(pos[f"{child}_{s}"], 2 / 3)

    # Rotation that aims each mannequin bone along the same limb of the character
    aim = {}
    for name, target in AIM.items():
        manny = manny_location(target) - manny_location(name)
        character = pos[target] - pos[name]
        aim[name] = (
            manny.rotation_difference(character).to_matrix()
            if manny.length > 1e-3 and character.length > 1e-3
            else Matrix.Identity(3)
        )
    # Bones with nothing to aim at follow the closest aimed bone
    for s in "lr":
        aim[f"ball_{s}"] = aim[f"foot_{s}"]
        aim[f"thumb_03_{s}"] = aim[f"thumb_02_{s}"]
        for finger in FINGERS:
            aim[f"{finger}_03_{s}"] = aim[f"{finger}_02_{s}"]
        for part in ("upperarm", "lowerarm", "thigh", "calf"):
            for twist in ("01", "02"):
                aim[f"{part}_twist_{twist}_{s}"] = aim[f"{part}_{s}"]

    rest, parent = {}, {}
    for target, position in pos.items():
        matrix = (aim.get(target, Matrix.Identity(3)) @ manny_rotation(target)).to_4x4()
        matrix.translation = position
        rest[target], parent[target] = matrix, PARENT[target]

    # Other weighted bones are not in the mannequin: keep their axes, with _ in place of .
    for bone in bones:
        if bone.name not in weighted or bone.name in PLAIN or bone.name in SPLIT:
            continue
        target = bone.name.replace(".", "_")
        ancestor, above = bone.parent, "head"
        while ancestor:
            if ancestor.name in PLAIN:
                above = PLAIN[ancestor.name]
                break
            if ancestor.name in SPLIT:
                above = SPLIT[ancestor.name][1]
                break
            if ancestor.name in weighted:
                above = ancestor.name.replace(".", "_")
                break
            if ancestor.name in ANCESTOR:
                above = ANCESTOR[ancestor.name]
                break
            ancestor = ancestor.parent
        matrix = bone.matrix_local.to_3x3().to_4x4()
        matrix.translation = bone.head_local * 100.0
        rest[target], parent[target], source[target] = matrix, above, bone.name

    order, seen = [], set()

    def visit(name):
        if name in seen:
            return
        seen.add(name)
        if parent[name]:
            visit(parent[name])
        order.append(name)

    for name in rest:
        visit(name)
    return {name: rest[name] for name in order}, parent, source
