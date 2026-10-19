import os
import re
from contextlib import contextmanager

import bpy

from ...armature.helper_functions import outfits_update_armature_collections
from ...custom_properties.misc import mustardui_add_driver
from ...misc.prop_utils import evaluate_path, evaluate_rna
from ...model_selection.active_object import ModelMode, active_object_operator_poll
from ...text_storage import storage as text_storage
from ..helper_functions import outfits_get_collection_items
from ..ops_delete import delete_extras_pieces, delete_outfit_collection
from .ops_add_outfit import (
    AddOutfitSettings,
    add_outfit_fill_shape_keys,
    add_outfit_model,
    add_outfit_pieces,
    custom_property_refs,
    fit_property,
    outfit_default_name,
    parents,
    piece_default_names,
    rna_id,
    rna_with_id,
    update_custom_property_paths,
)


def data_ids():
    """All the datablocks of the file"""

    ids = set()
    for prop in bpy.data.bl_rna.properties:
        if prop.type == "COLLECTION":
            ids.update(x for x in getattr(bpy.data, prop.identifier) if isinstance(x, bpy.types.ID))
    return ids


def source_rigs(objects):
    """Armatures of the appended models, or all the appended ones if not from a model"""

    rigs = [o for o in objects if isinstance(o, bpy.types.Object) and o.type == "ARMATURE"]
    # The armatures of an Outfit from a model are kept (e.g. for wings)
    models = [o for o in rigs if o.data.MustardUI_RigSettings.model_body is not None]
    return models or rigs


def replace_models(objects, armature, body):
    """Use the model armature and body in place of the appended ones, returning these"""

    rigs = source_rigs(objects)
    replaced = {rig: armature for rig in rigs}
    for rig in rigs:
        source_body = rig.data.MustardUI_RigSettings.model_body
        if source_body in objects:
            replaced[source_body] = body
        # Drivers of the materials use the armature data
        if rig.data != armature.data:
            rig.data.user_remap(armature.data)

    body_keys = body.data.shape_keys
    for source, target in replaced.items():
        # Shape Keys linked to the source body follow the model one
        source_keys = source.data.shape_keys if source.type == "MESH" else None
        if source_keys is not None and body_keys is not None:
            for obj in objects:
                keys = obj.data.shape_keys if obj.type == "MESH" else None
                if keys is None or keys.animation_data is None:
                    continue
                for fcurve in keys.animation_data.drivers:
                    for var in fcurve.driver.variables:
                        for t in var.targets:
                            if t.id == source_keys:
                                t.id = body_keys
        # Without linking the model to the appended collections
        for coll in source.users_collection:
            coll.objects.unlink(source)
        source.user_remap(target)
    return list(replaced)


def remove_unused(scene, before, replaced, armature):
    """Remove the appended datablocks not used by the appended Objects in the scene or the model"""

    appended = data_ids() - before
    in_scene = set(scene.objects)
    kept = {o for o in appended if isinstance(o, bpy.types.Object) and o in in_scene}
    kept -= set(replaced)
    users = kept | {armature}
    for obj in kept:
        users.add(obj.data)
        if obj.type == "MESH" and obj.data.shape_keys is not None:
            users.add(obj.data.shape_keys)

    unlinked = [o for o in appended if isinstance(o, bpy.types.Object) and o not in kept]
    user_map = bpy.data.user_map(subset=unlinked)
    remove = [o for o in unlinked if o in replaced or not user_map[o] & users]
    scene_colls = set(scene.collection.children_recursive)
    remove += [c for c in appended if isinstance(c, bpy.types.Collection) and c not in scene_colls]
    # Scenes always have a user, so they are not removed as orphans
    for source_scene in [s for s in appended if isinstance(s, bpy.types.Scene)]:
        source_scene.user_remap(scene)
        remove.append(source_scene)
    remove += [lib for lib in appended if isinstance(lib, bpy.types.Library)]
    bpy.data.batch_remove(remove)

    # Data left without users, e.g. meshes of the removed Objects
    for _ in range(10):
        orphans = [i for i in data_ids() - before if i.users == 0]
        if not orphans:
            break
        bpy.data.batch_remove(orphans)


def resolves(id_data, path):
    try:
        id_data.path_resolve(path)
    except ValueError:
        return False
    return bool(path)


def driver_broken(id_data, fcurve):
    """Whether the driven property or a variable target is missing"""

    if not resolves(id_data, fcurve.data_path):
        return True
    for var in fcurve.driver.variables:
        if var.type == "CONTEXT_PROP":
            continue
        for t in var.targets:
            if t.id is None:
                return True
            if var.type == "SINGLE_PROP" and not resolves(t.id, t.data_path):
                return True
            if var.type != "SINGLE_PROP" and t.bone_target:
                is_armature = getattr(t.id, "type", None) == "ARMATURE"
                if not is_armature or t.bone_target not in t.id.data.bones:
                    return True
    return False


def id_drivers(ids):
    """Datablocks with drivers, with their owner for the material node trees"""

    for owner in ids:
        # Material node trees are not in bpy.data
        for id_data in (owner, getattr(owner, "node_tree", None)):
            anim = getattr(id_data, "animation_data", None)
            if anim is not None:
                yield owner, id_data, anim


def remove_broken_drivers(ids):
    """Remove the drivers with missing targets, returning their descriptions"""

    removed = []
    for owner, id_data, anim in list(id_drivers(ids)):
        # Shape Keys are named after their mesh
        name = (getattr(owner, "user", None) or owner).name
        for fcurve in [fc for fc in anim.drivers if driver_broken(id_data, fc)]:
            removed.append(f"{name}: {fcurve.data_path}")
            anim.drivers.remove(fcurve)
    return removed


# Custom property pointer to the datablock of its path, by pointer type
PTR_FIELDS = {
    "ARMATURE": "ptr_armature",
    "OBJECT": "ptr_object",
    "SHAPEKEY": "ptr_key",
    "MATERIAL": "ptr_material",
    "COLLECTION": "ptr_collection",
    "NODE_TREE": "ptr_node_tree",
}

# Armature property in a driver target path, e.g. ["Name"][0]
PROP_PATH = re.compile(r'\["((?:[^"\\]|\\.)*)"\]')


def appended_id(rna, appended, pointer=None):
    """Collection name, appended datablock and rest of a source custom property path"""

    parsed = rna_id(rna)
    coll = getattr(bpy.data, parsed[0], None) if parsed else None
    if not isinstance(coll, bpy.types.bpy_prop_collection):
        return None
    attr, name, rest = parsed

    id_data = pointer if pointer in appended else None
    if id_data is None:
        # Appended datablocks get a number suffix if the name is taken
        pattern = re.compile(re.escape(name) + r"(\.\d{3})?")
        found = [i for i in coll if i in appended and pattern.fullmatch(i.name)]
        found = [i for i in found if i.name == name] or found
        id_data = found[0] if len(found) == 1 else None
    if id_data is None or coll.get(id_data.name) != id_data:
        return None
    return attr, id_data, rest


def source_model_map(appended, arm, arm_obj, body):
    """Armatures and bodies of the appended models, with the model ones replacing them"""

    model = {o: arm_obj for o in source_rigs(appended)}
    for data in [a for a in appended if isinstance(a, bpy.types.Armature)]:
        source_body = data.MustardUI_RigSettings.model_body
        if source_body is None:
            continue
        model[data] = arm
        model[source_body] = body
        model[source_body.data] = body.data
        if source_body.data.shape_keys is not None:
            model[source_body.data.shape_keys] = body.data.shape_keys
    return model


def model_path(target, model):
    """Path of a source custom property, on the model if on the source model"""

    attr, id_data, rest = target
    if id_data not in model:
        return rna_with_id(*target), False
    mapped = model[id_data]
    return (rna_with_id(attr, mapped, rest) if mapped is not None else None), True


def model_path_problem(rna, path):
    """Why a property of the model can not be driven by an imported custom property"""

    if rna is None or evaluate_path(rna, path) is None:
        return "not on the model"
    owner = evaluate_rna(rna)
    anim = owner.id_data.animation_data
    try:
        full = owner.path_from_id(path)
    except ValueError:
        full = path
    # The model custom properties are not taken over
    if anim is not None and any(fc.data_path == full for fc in anim.drivers):
        return "already driven on the model"
    return None


# Nested settings copied with their owner: bone colors and their custom colors
NESTED = ("color", "custom")


def copy_settings(source, target, skip=()):
    """Copy the settings shared by two structs, with the nested colors, but the collections"""

    for prop in target.bl_rna.properties:
        pid = prop.identifier
        if pid in skip or pid == "rna_type" or prop.type == "COLLECTION":
            continue
        if not hasattr(source, pid):
            continue
        if prop.type == "POINTER" and pid in NESTED:
            copy_settings(getattr(source, pid), getattr(target, pid))
        elif not prop.is_readonly:
            try:
                setattr(target, pid, getattr(source, pid))
            except (AttributeError, TypeError, ValueError):
                pass


def copy_id_property(source, name, target, new_name):
    value = source[name]
    target[new_name] = value.to_list() if hasattr(value, "to_list") else value
    try:
        target.id_properties_ui(new_name).update(**source.id_properties_ui(name).as_dict())
    except TypeError:
        pass
    target.property_overridable_library_set(f'["{bpy.utils.escape_identifier(new_name)}"]', True)


def rename_driver_targets(ids, renamed):
    """Drivers reading the renamed properties of the source armatures read the new ones"""

    for _, _, anim in id_drivers(ids):
        for fcurve in anim.drivers:
            for var in fcurve.driver.variables:
                for t in var.targets:
                    match = PROP_PATH.match(t.data_path)
                    if match is None:
                        continue
                    new_name = renamed.get((t.id, re.sub(r"\\(.)", r"\1", match[1])))
                    if new_name is not None:
                        escaped = bpy.utils.escape_identifier(new_name)
                        t.data_path = f'["{escaped}"]' + t.data_path[match.end() :]


def import_custom_properties(arm, arm_obj, body, scene, appended):
    """Import the Outfit custom properties of the appended pieces"""

    pieces = set(scene.objects) & appended
    colls = set(scene.collection.children_recursive) & appended
    model = source_model_map(appended, arm, arm_obj, body)
    cps = arm.MustardUI_CustomPropertiesOutfit
    renamed = {}
    skipped = []

    for source in [a for a in appended if isinstance(a, bpy.types.Armature)]:
        for scp in source.MustardUI_CustomPropertiesOutfit:
            piece = scp.outfit_piece
            if not (piece in pieces if piece is not None else scp.outfit in colls):
                continue

            pointer = getattr(scp, PTR_FIELDS[scp.ptr_type]) if scp.ptr_type in PTR_FIELDS else None
            target = appended_id(scp.rna, appended, pointer)
            if target is None:
                skipped.append(f"{scp.name} (not found)")
                continue
            # Properties of the source body or armature are driven on the model ones
            rna, on_model = model_path(target, model)
            problem = model_path_problem(rna, scp.path) if on_model else None
            if problem is not None:
                skipped.append(f"{scp.name} ({problem})")
                continue

            cp = cps.add()
            copy_settings(scp, cp)
            cp.rna = rna
            to_drive = [(rna, scp.path)] if on_model else []
            for slp in scp.linked_properties:
                linked = appended_id(slp.rna, appended)
                lrna, lon_model = model_path(linked, model) if linked else (None, False)
                problem = model_path_problem(lrna, slp.path) if lon_model else None
                if lrna is None or problem is not None:
                    skipped.append(f"{scp.name} (linked {slp.path}, {problem or 'not found'})")
                    continue
                lp = cp.linked_properties.add()
                lp.rna, lp.path = lrna, slp.path
                if lon_model:
                    to_drive.append((lrna, slp.path))

            if scp.prop_name in source.keys():
                # Numbered like the new custom properties, if the name is taken
                name = scp.prop_name
                number = 1
                while name in arm.keys():
                    number += 1
                    name = f"{scp.prop_name} {number}"
                copy_id_property(source, scp.prop_name, arm, name)
                cp.prop_name = name
                if name != scp.prop_name:
                    renamed[(source, scp.prop_name)] = name
                for driven_rna, driven_path in to_drive:
                    mustardui_add_driver(arm, driven_rna, driven_path, name)

    if renamed:
        rename_driver_targets(appended, renamed)
    # The drivers read the evaluated armature, which needs the new properties
    arm.update_tag()
    return skipped


def remove_invalid_custom_properties(arm, start):
    """Remove the imported custom properties whose datablock was not kept, returning them"""

    cps = arm.MustardUI_CustomPropertiesOutfit
    removed = []
    for i in reversed(range(start, len(cps))):
        cp = cps[i]
        if evaluate_path(cp.rna, cp.path) is None:
            removed.append(cp.name)
            if cp.prop_name in arm.keys():
                del arm[cp.prop_name]
            cps.remove(i)
            continue
        for j in reversed(range(len(cp.linked_properties))):
            lp = cp.linked_properties[j]
            if evaluate_path(lp.rna, lp.path) is None:
                removed.append(f"{cp.name} (linked {lp.path})")
                cp.linked_properties.remove(j)
    return removed


def outfit_bone_collections(arm, colls, pieces):
    """Outfit Switcher Bone Collections of the Outfits or pieces"""

    found = []
    for bc in arm.collections_all:
        settings = bc.MustardUI_ArmatureBoneCollection
        piece = settings.outfit_switcher_object
        if settings.outfit_switcher_enable and (
            piece in pieces if piece is not None else settings.outfit_switcher_collection in colls
        ):
            found.append(bc)
    return found


# Constraint armatures with their bone
CONSTRAINT_TARGETS = (
    ("target", "subtarget"),
    ("pole_target", "pole_subtarget"),
    ("space_object", "space_subtarget"),
)


def retarget(con, source, target, renamed):
    """Use the target armature in place of the source one, with the renamed bones"""

    for attr, sub in CONSTRAINT_TARGETS:
        if getattr(con, attr, None) == source:
            setattr(con, attr, target)
            setattr(con, sub, renamed.get(getattr(con, sub), getattr(con, sub)))


# Bone settings set apart: the rest place, the parent and the selection
BONE_SKIP = {
    "name",
    "parent",
    "use_connect",
    "head",
    "tail",
    "matrix",
    "length",
    "roll",
    "select",
    "select_head",
    "select_tail",
}

# Pose bones at rest, without the custom shape transform bone of the source armature
POSE_SKIP = {
    "name",
    "location",
    "rotation_quaternion",
    "rotation_euler",
    "rotation_axis_angle",
    "scale",
    "custom_shape_transform",
}


@contextmanager
def armature_edit_mode(context, target):
    """Edit Mode on the armature, restoring its visibility and the selection after"""

    view_layer = context.view_layer
    # Edit Mode needs the armature in the View Layer, visible, active and the only one selected
    linked = target.name not in view_layer.objects
    if linked:
        context.scene.collection.objects.link(target)
        view_layer.update()
    hidden = target.hide_viewport
    target.hide_viewport = False
    # X-Axis Mirror would move the bones of the other side to mirror the new ones
    mirror = target.data.use_mirror_x
    target.data.use_mirror_x = False
    selected, active = context.selected_objects, view_layer.objects.active
    for obj in selected:
        obj.select_set(False)
    view_layer.objects.active = target
    try:
        bpy.ops.object.mode_set(mode="EDIT")
        yield target.data.edit_bones
    finally:
        if target.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        target.hide_viewport = hidden
        target.data.use_mirror_x = mirror
        if linked:
            context.scene.collection.objects.unlink(target)
        else:
            target.select_set(False)
        for obj in selected:
            obj.select_set(True)
        view_layer.objects.active = active


def copy_bones(context, source, target, names, bone_collections):
    """Copy the bones with their constraints and Bone Collections, relative to the armature"""

    bones = [b for b in source.data.bones if b.name in names]
    existing = {b.name for b in target.data.bones}
    with armature_edit_mode(context, target) as edit_bones:
        renamed = {}
        for bone in bones:
            eb = edit_bones.new(bone.name)
            # Taken names get a number suffix
            renamed[bone.name] = eb.name
            eb.head, eb.tail = (0, 0, 0), (0, bone.length, 0)
            eb.matrix = bone.matrix_local
            copy_settings(bone, eb, BONE_SKIP)
        orphans = []
        for bone in [b for b in bones if b.parent is not None]:
            eb = edit_bones[renamed[bone.name]]
            parent = bone.parent.name
            if parent in renamed:
                eb.parent = edit_bones[renamed[parent]]
            elif parent in existing:
                eb.parent = edit_bones[parent]
            else:
                orphans.append(f"{eb.name} (parent {parent})")
                continue
            eb.use_connect = bone.use_connect

    # Only the switched bones are posed, the others are only parents
    switching = set(bone_collections)
    switched = [b for b in bones if not switching.isdisjoint(b.collections)]
    for bone in switched:
        source_pose = source.pose.bones[bone.name]
        pose = target.pose.bones[renamed[bone.name]]
        copy_settings(source_pose, pose, POSE_SKIP)
        for con in source_pose.constraints:
            new = pose.constraints.new(con.type)
            copy_settings(con, new)
            retarget(new, source, target, renamed)

    new_collections = {}
    for bc in bone_collections:
        new = target.data.collections.new(bc.name, parent=new_collections.get(bc.parent))
        copy_settings(bc, new, {"name", "parent", "child_number"})
        copy_settings(bc.MustardUI_ArmatureBoneCollection, new.MustardUI_ArmatureBoneCollection)
        new_collections[bc] = new
    for bone in switched:
        for bc in bone.collections:
            if bc in new_collections:
                new_collections[bc].assign(target.data.bones[renamed[bone.name]])
    return renamed, list(new_collections.values()), orphans


def constraint_bones(owner, arm_obj):
    """Bones of the armature targeted by the constraints"""

    return {
        getattr(con, sub)
        for con in owner.constraints
        for attr, sub in CONSTRAINT_TARGETS
        if getattr(con, attr, None) == arm_obj
    }


def delete_switched_bones(context, arm_obj, colls, pieces):
    """Delete the Bone Collections switched with the Outfits or pieces, with their bones not used
    by the other objects or bones"""

    arm = arm_obj.data
    bone_collections = outfit_bone_collections(arm, colls, pieces)
    names = {b.name for bc in bone_collections for b in bc.bones}
    if not names:
        return

    # Bones used by the objects not deleted, through parents, weights and constraints
    deleted = set(pieces) | {o for c in colls for o in c.all_objects}
    used = set()
    for obj in [o for o in bpy.data.objects if o not in deleted]:
        if obj.parent == arm_obj and obj.parent_type == "BONE":
            used.add(obj.parent_bone)
        if any(m.type == "ARMATURE" and m.object == arm_obj for m in obj.modifiers):
            used |= {vg.name for vg in obj.vertex_groups}
        used |= constraint_bones(obj, arm_obj)
        if obj.pose is not None:
            for pose in obj.pose.bones:
                if obj != arm_obj or pose.name not in names:
                    used |= constraint_bones(pose, arm_obj)

    # Parents and constraint targets of the bones kept are kept
    removed = names - used
    while True:
        kept = [b for b in arm.bones if b.name not in removed]
        keep = {p.name for b in kept for p in b.parent_recursive}
        for bone in [b for b in kept if b.name in names]:
            keep |= constraint_bones(arm_obj.pose.bones[bone.name], arm_obj)
        if removed.isdisjoint(keep):
            break
        removed -= keep
    empty = [bc.name for bc in bone_collections if {b.name for b in bc.bones} <= removed]

    with armature_edit_mode(context, arm_obj) as edit_bones:
        for name in removed:
            edit_bones.remove(edit_bones[name])
    for name in empty:
        arm.collections.remove(arm.collections_all[name])


def import_bones(context, arm_obj, appended):
    """Add the switched bones of the appended models to the model, renaming the taken names"""

    scene = context.scene
    pieces = set(scene.objects) & appended
    colls = set(scene.collection.children_recursive) & appended
    rigs = [r for r in source_rigs(appended) if r.data.MustardUI_RigSettings.model_body is not None]
    names, renamed, orphans = [], [], []
    for rig in rigs:
        bone_collections = outfit_bone_collections(rig.data, colls, pieces)
        bones = {b.name for bc in bone_collections for b in bc.bones}
        if not bones:
            continue
        new_names, new_collections, rig_orphans = copy_bones(
            context, rig, arm_obj, bones, bone_collections
        )
        names += [bc.name for bc in new_collections]
        orphans += rig_orphans
        changed = {k: v for k, v in new_names.items() if k != v}
        renamed += [f"{k} > {v}" for k, v in changed.items()]
        if not changed:
            continue

        for obj in [o for o in appended if isinstance(o, bpy.types.Object)]:
            for owner in (obj, *(obj.pose.bones if obj.pose is not None else ())):
                for con in owner.constraints:
                    retarget(con, rig, rig, changed)
            if not any(m.type == "ARMATURE" and m.object == rig for m in obj.modifiers):
                continue
            groups = [(vg, changed[vg.name]) for vg in obj.vertex_groups if vg.name in changed]
            # Through temporary names, as a new name can be the one of another renamed group
            for i, (vg, _) in enumerate(groups):
                vg.name = f"MustardUI Bone {i}"
            for vg, name in groups:
                vg.name = name
    return names, renamed, orphans


def append_outfits(filepath):
    """Append the Outfits and Extras of a blend file, returning them with the Extras ones"""

    with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
        data_to.collections = data_from.collections
        data_to.armatures = data_from.armatures
        data_to.objects = data_from.objects
    # The appended models can store their settings in the other storage
    text_storage.apply()

    colls = [c for c in data_to.collections if c is not None]
    arms = [a for a in data_to.armatures if a is not None]
    settings = [a.MustardUI_RigSettings for a in arms]
    extras = {s.extras_collection for s in settings} - {None}

    # MustardUI models: their Outfits and Extras
    models = [a.MustardUI_RigSettings for a in arms if a.MustardUI_created]
    if models:
        roots = [x.collection for s in models for x in s.outfits_collections]
        return [c for c in roots if c is not None] + list(extras), extras

    nested = {c for coll in colls for c in coll.children}
    roots = [c for c in colls if c not in nested]
    # Exported Outfits, with the Extras named after the model one if exported before it was stored
    if any(s.model_body is not None for s in settings):
        if not extras:
            extras = {c for c in roots if re.sub(r"\.\d{3}$", "", c.name).endswith(" Extras")}
        return roots, extras

    # Other files: the collections are Outfits, the meshes in no collection Extras
    meshes = [
        o for o in data_to.objects if o is not None and o.type == "MESH" and not o.users_collection
    ]
    if not meshes:
        return roots, set()
    coll = bpy.data.collections.new(os.path.splitext(os.path.basename(filepath))[0])
    for obj in {*meshes, *(p for m in meshes for p in parents(m) if not p.users_collection)}:
        coll.objects.link(obj)
    return [*roots, coll], {coll}


class MustardUI_ModelToolkit_AddOutfitFromFile(AddOutfitSettings, bpy.types.Operator):
    """Append the Outfits and Extras of other blend files, and add them to the model.
    In files not from MustardUI, the collections are Outfits and the meshes in no collection
    Extras"""

    bl_idname = "mustardui.model_toolkit_add_outfit_from_file"
    bl_label = "Add Outfit from File"
    bl_options = {"UNDO", "PRESET"}

    directory: bpy.props.StringProperty(subtype="DIR_PATH", options={"HIDDEN", "SKIP_SAVE"})
    files: bpy.props.CollectionProperty(
        type=bpy.types.OperatorFileListElement, options={"HIDDEN", "SKIP_SAVE"}
    )
    filter_glob: bpy.props.StringProperty(default="*.blend", options={"HIDDEN"})

    # Outfits named after their collections
    choose_name = False

    destination: bpy.props.EnumProperty(
        name="Add to",
        description="Where the pieces are added.\nThe pieces of the Extras of the files always "
        "go to the Extras of the model",
        items=(
            ("NEW", "New Outfits", "Add a new Outfit for each collection, named after it"),
            ("OUTFIT", "Outfit", "Add the pieces to an existing Outfit"),
            ("EXTRAS", "Extras", "Add all the pieces to the Extras"),
        ),
        default="NEW",
    )

    fit: fit_property("NONE")

    transfer_shape_keys: bpy.props.BoolProperty(
        name="Transfer Shape Keys",
        default=False,
        description="Transfer the Shape Keys from the body",
    )

    import_custom_properties: bpy.props.BoolProperty(
        name="Import Custom Properties",
        default=True,
        description="Add the Outfit custom properties of the pieces, if appended from a "
        "MustardUI model.\nThe properties driving the model body are skipped, and listed in "
        "the console",
    )

    remove_drivers: bpy.props.BoolProperty(
        name="Remove Broken Drivers",
        default=True,
        description="Remove the drivers of the appended data using something missing in this "
        "file (e.g. a Shape Key or a property not on the model).\nThey are listed in the console",
    )

    overwrite: bpy.props.BoolProperty(
        name="Overwrite",
        default=False,
        description="Delete the Outfits of the model with the name of a new one, and the Extras "
        "pieces with the name of a new one, before adding them",
    )

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT" and active_object_operator_poll(
            context, config=ModelMode.ANY
        )

    def draw(self, context):
        self.draw_settings(context)

    def draw_extra(self, layout):
        header, body = layout.panel("MustardUI_AddOutfitFromFile_Import")
        header.label(text="Import", icon="APPEND_BLEND")
        if body is not None:
            col = body.column(heading="Custom Properties")
            col.prop(self, "import_custom_properties", text="Import")
            col = body.column(heading="Drivers")
            col.prop(self, "remove_drivers", text="Remove Broken")
            body.column(heading="Existing").prop(self, "overwrite")

    def invoke(self, context, event):
        add_outfit_fill_shape_keys(context)
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def delete_existing(self, context, arm, colls, to_extras, sources):
        """Delete the Outfits and Extras pieces of the model with the names of the new ones"""

        rig_settings = arm.MustardUI_RigSettings
        meshes = {o for c in colls for o in c.all_objects if o.type == "MESH"}
        pieces = [o for o in meshes if meshes.isdisjoint(parents(o))]
        if self.destination == "EXTRAS":
            to_extras = set(pieces)

        # Outfit names as given by Add Outfit, without the name of the source models
        old_outfits = []
        if self.destination == "NEW":
            names = set()
            for piece in [p for p in pieces if p not in to_extras]:
                name = piece.users_collection[0].name
                for source in sources:
                    name = outfit_default_name(name, source)
                names.add(outfit_default_name(name, rig_settings.model_name))
            if rig_settings.model_MustardUI_naming_convention:
                names = {f"{rig_settings.model_name} {n}" for n in names}
            old_outfits = [
                x.collection
                for x in rig_settings.outfits_collections
                if x.collection is not None and x.collection.name in names
            ]

        # Extras pieces matched by name without the collection prefix, with their children
        extras = rig_settings.extras_collection
        keys = {piece_default_names([p.name])[0] for p in pieces if p in to_extras}
        old_extras = set()
        if extras is not None and keys:
            items = outfits_get_collection_items(rig_settings, extras)
            old_extras = {o for o in items if piece_default_names([o.name])[0] in keys}
            old_extras |= {o for o in items if not old_extras.isdisjoint(parents(o))}

        # Before the pieces, as their weights tell the bones still used
        old_pieces = old_extras | {o for c in old_outfits for o in c.all_objects}
        delete_switched_bones(
            context, rig_settings.model_armature_object, set(old_outfits), old_pieces
        )
        for coll in old_outfits:
            outfits = [x.collection for x in rig_settings.outfits_collections]
            context.scene.mustardui_outfits_uilist_index = outfits.index(coll)
            bpy.ops.mustardui.remove_outfit(is_config=True)
            delete_outfit_collection(context, arm, coll)
        if old_extras:
            delete_extras_pieces(context, arm, old_extras, remove_empty=False)

    def execute(self, context):
        arm, arm_obj, body = add_outfit_model(context)
        if arm_obj is None or body is None:
            self.report({"ERROR"}, "MustardUI - The model has no Armature or Body")
            return {"CANCELLED"}

        directory = bpy.path.abspath(self.directory)
        paths = [os.path.join(directory, f.name) for f in self.files if f.name]
        if not paths or not all(os.path.isfile(p) and p.endswith(".blend") for p in paths):
            self.report({"ERROR"}, "MustardUI - Select blend files")
            return {"CANCELLED"}
        if bpy.data.filepath and any(os.path.samefile(p, bpy.data.filepath) for p in paths):
            self.report({"ERROR"}, "MustardUI - Select other blend files than this one")
            return {"CANCELLED"}

        before = data_ids()
        roots, extras = [], set()
        for path in paths:
            try:
                file_roots, file_extras = append_outfits(path)
            except OSError as error:
                bpy.data.batch_remove(data_ids() - before)
                self.report({"ERROR"}, f"MustardUI - {error}")
                return {"CANCELLED"}
            roots += file_roots
            extras |= file_extras

        # Children of other appended collections are already linked
        nested = {c for coll in roots for c in coll.children_recursive}
        for coll in roots:
            if coll not in nested:
                context.scene.collection.children.link(coll)
        colls = [c for coll in roots for c in (coll, *coll.children_recursive)]

        # Pieces going to the Extras, if the model has them
        rig_settings = arm.MustardUI_RigSettings
        to_extras = set()
        if rig_settings.extras_collection is not None:
            to_extras = {o for c in extras for o in c.all_objects}

        sources = {
            a.MustardUI_RigSettings.model_name
            for a in data_ids() - before
            if isinstance(a, bpy.types.Armature)
        } - {""}

        # Before the custom properties and bones are added, to keep their names
        if self.overwrite:
            appended = data_ids() - before
            self.delete_existing(context, arm, colls, to_extras, sources)
            # Without the deleted datablocks, as new ones can take their memory
            before = data_ids() - appended

        # Before the source models are replaced, as the custom properties are on them
        start = len(arm.MustardUI_CustomPropertiesOutfit)
        if self.import_custom_properties:
            skipped = import_custom_properties(
                arm, arm_obj, body, context.scene, data_ids() - before
            )

        # Collections without the name of the model they come from
        refs = custom_property_refs(arm)
        for coll in colls:
            for source_name in sources:
                if coll.name.startswith(f"{source_name} "):
                    coll.name = coll.name[len(source_name) + 1 :]
        update_custom_property_paths(refs)

        # Before the source models are replaced, as the bones are on them
        bone_collections, renamed, orphans = import_bones(context, arm_obj, data_ids() - before)

        appended = [o for o in bpy.data.objects if o not in before]
        replaced = replace_models(appended, arm_obj, body)
        remove_unused(context.scene, before, replaced, arm_obj)

        # Reported with the added Outfit
        issues = []
        if self.import_custom_properties:
            skipped += remove_invalid_custom_properties(arm, start)
            imported = len(arm.MustardUI_CustomPropertiesOutfit) - start
            print(f"MustardUI - Add Outfit from File: {imported} custom properties imported")
            if skipped:
                print("MustardUI - Custom properties not imported:\n  " + "\n  ".join(skipped))
                issues.append(f"{len(skipped)} custom properties skipped")

        if renamed:
            print("MustardUI - Bones renamed, as taken on the model:\n  " + "\n  ".join(renamed))
        if orphans:
            print(
                "MustardUI - Bones without parent, missing on the model:\n  " + "\n  ".join(orphans)
            )
            issues.append(f"{len(orphans)} bones without parent")

        if self.remove_drivers:
            removed = remove_broken_drivers(data_ids() - before)
            if removed:
                print("MustardUI - Broken drivers removed:\n  " + "\n  ".join(removed))
                issues.append(f"{len(removed)} broken drivers removed")

        # Outfit pieces might have been hidden in the other file
        for coll in colls:
            coll.hide_viewport = coll.hide_render = coll.hide_select = False
        meshes = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
        for obj in meshes:
            obj.hide_viewport = obj.hide_render = obj.hide_select = False

        context.view_layer.update()
        meshes = [o for o in meshes if o.name in context.view_layer.objects]
        for obj in meshes:
            obj.hide_set(False)
        for obj in context.view_layer.objects:
            obj.select_set(obj in meshes)
        context.view_layer.objects.active = meshes[-1] if meshes else None

        pieces = add_outfit_pieces(context)
        if not pieces:
            self.report({"WARNING"}, "MustardUI - No meshes to add as Outfit were appended")
            return {"FINISHED"}

        settings = {n: getattr(self, n) for n in [*AddOutfitSettings.__annotations__, "fit"]}
        if self.destination != "OUTFIT":
            del settings["outfit"]
        # Outfits named after the appended collections
        del settings["outfit_name"]
        settings["split"] = True

        # Pieces switched by the imported Bone Collections, to switch them in their Outfit
        switchers = []
        for name in bone_collections:
            switcher = arm.collections_all[name].MustardUI_ArmatureBoneCollection
            piece = switcher.outfit_switcher_object
            coll = switcher.outfit_switcher_collection
            switchers.append((name, {piece} if piece is not None else set(coll.all_objects)))

        groups = (
            ([p for p in pieces if p not in to_extras], settings),
            ([p for p in pieces if p in to_extras], {**settings, "destination": "EXTRAS"}),
        )

        # Default piece names, as the appended pieces are not listed
        context.window_manager.MustardUI_ModelToolkit_AddOutfit_Items.clear()
        for group, group_settings in groups:
            if not group:
                continue
            for obj in context.view_layer.objects:
                obj.select_set(obj in group)
            context.view_layer.objects.active = group[-1]
            try:
                bpy.ops.mustardui.model_toolkit_add_outfit(**group_settings)
            except RuntimeError as error:
                # The appended pieces are kept selected, to add them with Add Outfit
                self.report({"ERROR"}, str(error).removeprefix("Error: ").strip())
                return {"FINISHED"}

        if switchers:
            outfits = [x.collection for x in rig_settings.outfits_collections]
            outfits = [c for c in (*outfits, rig_settings.extras_collection) if c is not None]
            for name, switched in switchers:
                switcher = arm.collections_all[name].MustardUI_ArmatureBoneCollection
                switcher.outfit_switcher_collection = next(
                    (c for c in outfits if not switched.isdisjoint(c.all_objects)), None
                )
            outfits_update_armature_collections(rig_settings, arm)

        source = f"'{os.path.basename(paths[0])}'" if len(paths) == 1 else f"{len(paths)} files"
        message = f"MustardUI - {len(pieces)} pieces added from {source}"
        if issues:
            message += f", {' and '.join(issues)} (details in the console)"
        self.report({"WARNING"} if issues else {"INFO"}, message)
        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_AddOutfitFromFile)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_AddOutfitFromFile)
