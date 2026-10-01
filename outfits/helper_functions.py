from array import array

from ..misc.set_bool import set_bool

# Largest image side copied into a full resolution preview
FULL_PREVIEW_MAX_SIZE = 1024


def set_full_resolution_preview(image):
    """Use the full resolution image as preview, to keep it sharp"""

    if image is None:
        return

    width, height = image.size
    if width == 0 or height == 0 or max(width, height) > FULL_PREVIEW_MAX_SIZE:
        return

    pixels = array("f", [0.0]) * (width * height * 4)
    image.pixels.foreach_get(pixels)

    preview = image.preview_ensure()
    preview.image_size = (width, height)
    preview.image_pixels_float.foreach_set(pixels)


def find_layer_collection(layer_coll, collection):
    """LayerCollection of the collection, searched from the root one"""
    if layer_coll.collection == collection:
        return layer_coll
    for child in layer_coll.children:
        result = find_layer_collection(child, collection)
        if result:
            return result
    return None


def find_layer_collections(layer_coll, collections):
    """find_layer_collection for several collections in one walk, stopping when all are found."""
    wanted = set(collections)
    result = {}

    def _walk(lc):
        coll = lc.collection
        if coll in wanted and coll not in result:
            result[coll] = lc
            if len(result) == len(wanted):
                return True
        return any(_walk(child) for child in lc.children)

    if wanted:
        _walk(layer_coll)
    return result


def update_extras_visibility(context, rig_settings):
    """Hide the Extras collections with all their objects hidden"""
    extras = rig_settings.extras_collection
    if extras is None:
        return None

    layer_colls = find_layer_collections(
        context.view_layer.layer_collection, [extras, *extras.children_recursive]
    )

    def _update(coll):
        children_hidden = [_update(child) for child in coll.children]
        all_hidden = all(obj.hide_render for obj in coll.objects) and all(children_hidden)

        set_bool(coll, "hide_viewport", all_hidden)
        set_bool(coll, "hide_render", all_hidden)

        lc = layer_colls.get(coll)
        if lc is not None:
            set_bool(lc, "exclude", all_hidden)

        return all_hidden

    return _update(extras)


def outfits_get_collections(rig_settings):
    """All the collections handled by the Outfits UI (Outfits + Extras)."""
    collections = [
        x.collection for x in rig_settings.outfits_collections if x.collection is not None
    ]
    if rig_settings.extras_collection is not None:
        collections.append(rig_settings.extras_collection)
    return collections


def outfits_get_collection_items(rig_settings, collection):
    """Objects of an Outfits/Extras collection, honouring the sub-collections setting."""
    use_sub = (
        rig_settings.extras_config_subcollections
        if collection == rig_settings.extras_collection
        else rig_settings.outfit_config_subcollections
    )
    return collection.all_objects if use_sub else collection.objects


def get_mask_pieces(rig_settings):
    """(piece, mask switch) for every piece which can drive or host masks."""
    outfits_mask = rig_settings.outfits_global_mask
    hair_mask = (
        rig_settings.hair_global_mask if rig_settings.hair_enable_global_mask else outfits_mask
    )

    for collection in outfits_get_collections(rig_settings):
        for obj in outfits_get_collection_items(rig_settings, collection):
            yield obj, outfits_mask

    for collection in (rig_settings.hair_collection, rig_settings.hair_extras_collection):
        if collection is not None:
            for obj in collection.all_objects:
                yield obj, hair_mask


def get_mask_objects(rig_settings):
    """[(mesh, mask switch)] for every Object which can host masks."""
    objects = []
    seen = set()

    body = rig_settings.model_body
    if body is not None:
        objects.append((body, rig_settings.outfits_global_mask))
        seen.add(body)

    for obj, mask in get_mask_pieces(rig_settings):
        if obj is None or obj.type != "MESH" or obj in seen:
            continue
        objects.append((obj, mask))
        seen.add(obj)

    return objects


def get_mask_visibility(rig_settings):
    """{piece name: mask visibility} for every piece which can drive masks."""
    return {obj.name: not obj.hide_viewport and mask for obj, mask in get_mask_pieces(rig_settings)}


def update_obj_masks(context, obj, visibility, mask=True):
    """Update the mask modifiers of obj driven by the pieces"""
    for mod in obj.modifiers:
        if mod.type not in ("MASK", "VERTEX_WEIGHT_MIX"):
            continue

        names = [x for x in mod.name.split("|") if x != obj.name]

        # Mask modifiers not associated to Outfits/Hair
        driving = [x for x in names if x in visibility]
        if not driving:
            if not mask and mod.type == "MASK":
                set_bool(mod, "show_viewport", False)
                set_bool(mod, "show_render", False)
            continue

        should_show = any(visibility[x] for x in driving)
        if mask and not should_show:
            # Shared modifier (names joined by "|"): keep it on if another
            # piece using it is still visible.
            for other_name in names:
                if other_name in visibility:
                    continue
                other_obj = context.scene.objects.get(other_name)
                if other_obj and not other_obj.hide_viewport:
                    should_show = True
                    break

        set_bool(mod, "show_viewport", should_show)
        set_bool(mod, "show_render", should_show)


def update_global_obj_mask(obj):
    from ..model_toolkit.optimization.ops_optimize_mods import mask_vg_name

    activate = any(
        mod.type == "VERTEX_WEIGHT_MIX" and mod.vertex_group_a == mask_vg_name and mod.show_viewport
        for mod in obj.modifiers
    )
    for mod in obj.modifiers:
        if mod.type == "MASK" and mod.vertex_group == mask_vg_name:
            set_bool(mod, "show_viewport", activate)
            set_bool(mod, "show_render", activate)


def update_masks(context, rig_settings, visibility=None):
    """Update every mask of the model."""
    mask_objects = get_mask_objects(rig_settings)
    if not mask_objects:
        return

    if visibility is None:
        visibility = get_mask_visibility(rig_settings)

    for obj, mask in mask_objects:
        update_obj_masks(context, obj, visibility, mask)
        update_global_obj_mask(obj)


def rename_model_ids(arm, names, addon_prefs):
    """Rename IDs of the model, updating masks and custom property paths"""
    from ..custom_properties.misc import assign_pointers
    from ..custom_properties.ops_rebuild import fix_custom_property_path

    custom_properties_lists = [
        arm.MustardUI_CustomProperties,
        arm.MustardUI_CustomPropertiesOutfit,
        arm.MustardUI_CustomPropertiesHair,
    ]
    # Store pointers to the IDs while the paths still resolve
    for custom_properties in custom_properties_lists:
        assign_pointers(custom_properties, addon_prefs)

    renamed = {}
    for id_block, name in names.items():
        old_name = id_block.name
        id_block.name = name
        if id_block.name != old_name and id_block.id_type == "OBJECT":
            renamed[old_name] = id_block.name

    # Masks are linked to the pieces by name ("|" separated)
    if renamed:
        for obj, _ in get_mask_objects(arm.MustardUI_RigSettings):
            for mod in obj.modifiers:
                if mod.type not in ("MASK", "VERTEX_WEIGHT_MIX"):
                    continue
                parts = mod.name.split("|")
                if any(x in renamed for x in parts):
                    mod.name = "|".join(renamed.get(x, x) for x in parts)

    fixed = 0
    for custom_properties in custom_properties_lists:
        for custom_prop in custom_properties:
            res = fix_custom_property_path(arm, custom_properties, custom_prop, addon_prefs)
            fixed += res == "FIXED"
    return fixed
