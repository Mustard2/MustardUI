import os
import re

import bpy

from ...custom_properties.misc import mustardui_add_driver
from ...misc.prop_utils import evaluate_path, evaluate_rna
from ...model_selection.active_object import ModelMode, active_object_operator_poll
from .ops_add_outfit import (
    AddOutfitSettings,
    add_outfit_fill_shape_keys,
    add_outfit_groups,
    add_outfit_model,
    add_outfit_pieces,
    custom_property_refs,
    fit_property,
    outfit_default_name,
    rna_id,
    rna_with_id,
    update_custom_property_paths,
)

# Blend file folders that can be appended, with their bpy.data collection
ID_TYPES = {"Collection": "collections", "Object": "objects"}


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
        for child in source.children:
            matrix = child.matrix_world.copy()
            child.parent = None
            child.matrix_world = matrix
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


def remove_unused(scene, before, replaced):
    """Remove the appended datablocks not used by the appended Objects in the scene"""

    appended = data_ids() - before
    in_scene = set(scene.objects)
    kept = {o for o in appended if isinstance(o, bpy.types.Object) and o in in_scene}
    kept -= set(replaced)
    users = set(kept)
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


def copy_settings(source, target):
    """Copy the settings of a custom property, but its collections"""

    for prop in source.bl_rna.properties:
        if prop.identifier == "rna_type" or prop.is_readonly or prop.type == "COLLECTION":
            continue
        try:
            setattr(target, prop.identifier, getattr(source, prop.identifier))
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
    """Add the Outfit custom properties of the appended models for the appended pieces,
    returning the skipped ones"""

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


class MustardUI_ModelToolkit_AddOutfitFromFile(AddOutfitSettings, bpy.types.Operator):
    """Append Collections or Objects from another blend file, and add them to the model as
    Outfits"""

    bl_idname = "mustardui.model_toolkit_add_outfit_from_file"
    bl_label = "Add Outfit from File"
    bl_options = {"UNDO"}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH", options={"HIDDEN", "SKIP_SAVE"})
    directory: bpy.props.StringProperty(subtype="DIR_PATH", options={"HIDDEN", "SKIP_SAVE"})
    files: bpy.props.CollectionProperty(
        type=bpy.types.OperatorFileListElement, options={"HIDDEN", "SKIP_SAVE"}
    )
    filter_blender: bpy.props.BoolProperty(default=True, options={"HIDDEN"})
    filter_blenlib: bpy.props.BoolProperty(default=True, options={"HIDDEN"})
    filter_folder: bpy.props.BoolProperty(default=True, options={"HIDDEN"})
    # Browse inside the blend files
    filemode: bpy.props.IntProperty(default=1, options={"HIDDEN"})

    fit: fit_property("NONE")

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

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT" and active_object_operator_poll(
            context, config=ModelMode.MODEL_TOOLKIT
        )

    def draw(self, context):
        self.layout.prop(self, "import_custom_properties")
        self.layout.prop(self, "remove_drivers")
        self.draw_settings(context)

    def invoke(self, context, event):
        add_outfit_fill_shape_keys(context)
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        arm, arm_obj, body = add_outfit_model(context)
        if arm_obj is None or body is None:
            self.report({"ERROR"}, "MustardUI - The model has no Armature or Body")
            return {"CANCELLED"}

        filepath, id_type = os.path.split(os.path.normpath(bpy.path.abspath(self.directory)))
        names = [f.name for f in self.files if f.name]
        if id_type not in ID_TYPES or not os.path.isfile(filepath) or not names:
            self.report({"ERROR"}, "MustardUI - Select Collections or Objects inside a blend file")
            return {"CANCELLED"}
        if bpy.data.filepath and os.path.samefile(filepath, bpy.data.filepath):
            self.report({"ERROR"}, "MustardUI - Select another blend file")
            return {"CANCELLED"}

        before = data_ids()
        attr = ID_TYPES[id_type]
        try:
            with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
                available = set(getattr(data_from, attr))
                setattr(data_to, attr, [n for n in names if n in available])
        except OSError as error:
            self.report({"ERROR"}, f"MustardUI - {error}")
            return {"CANCELLED"}
        items = [x for x in getattr(data_to, attr) if x is not None]
        if not items:
            self.report({"ERROR"}, "MustardUI - Nothing to append")
            return {"CANCELLED"}

        scene_coll = context.scene.collection
        if id_type == "Collection":
            # Children of other appended collections are already linked
            nested = {c for coll in items for c in coll.children_recursive}
            for coll in items:
                if coll not in nested:
                    scene_coll.children.link(coll)
            colls = [c for coll in items for c in (coll, *coll.children_recursive)]
        else:
            coll = bpy.data.collections.new(os.path.splitext(os.path.basename(filepath))[0])
            scene_coll.children.link(coll)
            for obj in items:
                coll.objects.link(obj)
            colls = [coll]

        # Before the source models are replaced, as the custom properties are on them
        start = len(arm.MustardUI_CustomPropertiesOutfit)
        if self.import_custom_properties:
            skipped = import_custom_properties(
                arm, arm_obj, body, context.scene, data_ids() - before
            )

        # Collections without the name of the model they come from
        sources = {
            a.MustardUI_RigSettings.model_name
            for a in data_ids() - before
            if isinstance(a, bpy.types.Armature)
        }
        refs = custom_property_refs(arm)
        for coll in colls:
            for source_name in sources - {""}:
                if coll.name.startswith(f"{source_name} "):
                    coll.name = coll.name[len(source_name) + 1 :]
        update_custom_property_paths(refs)

        appended = [o for o in bpy.data.objects if o not in before]
        replaced = replace_models(appended, arm_obj, body)
        remove_unused(context.scene, before, replaced)

        if self.import_custom_properties:
            skipped += remove_invalid_custom_properties(arm, start)
            imported = len(arm.MustardUI_CustomPropertiesOutfit) - start
            if skipped:
                print("MustardUI - Custom properties not imported:\n  " + "\n  ".join(skipped))
                self.report(
                    {"WARNING"},
                    f"MustardUI - {imported} custom properties imported, {len(skipped)} "
                    "skipped (listed in the console)",
                )
            elif imported:
                self.report({"INFO"}, f"MustardUI - {imported} custom properties imported")

        if self.remove_drivers:
            removed = remove_broken_drivers(data_ids() - before)
            if removed:
                print("MustardUI - Broken drivers removed:\n  " + "\n  ".join(removed))
                self.report(
                    {"WARNING"},
                    f"MustardUI - {len(removed)} broken drivers removed (listed in the console)",
                )

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
        # Outfit named after the appended collection by default
        groups = add_outfit_groups(pieces)
        if not self.outfit_name.strip() and len(groups) == 1:
            model_name = arm.MustardUI_RigSettings.model_name
            settings["outfit_name"] = outfit_default_name(next(iter(groups)).name, model_name)

        # Default piece names, as the appended pieces are not listed
        context.window_manager.MustardUI_ModelToolkit_AddOutfit_Items.clear()
        try:
            bpy.ops.mustardui.model_toolkit_add_outfit(**settings)
        except RuntimeError as error:
            # The appended pieces are kept selected, to add them with Add Outfit
            self.report({"ERROR"}, str(error).removeprefix("Error: ").strip())
        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_AddOutfitFromFile)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_AddOutfitFromFile)
