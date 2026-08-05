from ..misc.set_bool import set_bool


def find_layer_collection(layer_coll, collection):
    """Recursively find the LayerCollection (view-layer wrapper that holds the
    'exclude' flag) for a given collection, starting from a root layer collection."""
    if layer_coll.collection == collection:
        return layer_coll
    for child in layer_coll.children:
        result = find_layer_collection(child, collection)
        if result:
            return result
    return None


def update_extras_visibility(context, rig_settings):
    """Recursively hide/exclude each Extras (sub-)collection only when all its
    objects are hidden.
    Returns True if the whole tree is hidden, None if no Extras collection."""
    extras = rig_settings.extras_collection
    if extras is None:
        return None

    def _update(coll):
        children_hidden = [_update(child) for child in coll.children]
        all_hidden = all(obj.hide_render for obj in coll.objects) and all(children_hidden)

        set_bool(coll, "hide_viewport", all_hidden)
        set_bool(coll, "hide_render", all_hidden)

        lc = find_layer_collection(context.view_layer.layer_collection, coll)
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
    """{piece name: visible} for every piece which can drive masks."""
    return {obj.name: not obj.hide_viewport for obj, _ in get_mask_pieces(rig_settings)}


def update_obj_masks(context, obj, visibility, mask=True):
    """Update the mask modifiers hosted by obj which are driven by the pieces in
    visibility ({piece name: visible})."""
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

        should_show = mask and any(visibility[x] for x in driving)
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
    from ..tools_creators.ops_optimize_mods import mask_vg_name

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


def outfits_update_armature_collections(
    rig_settings, arm, is_extras_hidden=None, outfits=False, hair=False
):
    """Update visibility of armature bone collections like the outfit operator"""

    for bcoll in arm.collections_all:
        bcoll_settings = bcoll.MustardUI_ArmatureBoneCollection
        if not bcoll_settings.outfit_switcher_enable:
            continue
        if not bcoll_settings.outfit_switcher_collection:
            continue

        switcher_collection = bcoll_settings.outfit_switcher_collection

        if (
            outfits
            and rig_settings.hair_collection is not None
            and switcher_collection == rig_settings.hair_collection
        ):
            continue
        if hair and switcher_collection not in {
            rig_settings.hair_collection,
            rig_settings.hair_extras_collection,
        }:
            continue

        use_subcollections = (
            rig_settings.extras_config_subcollections
            if switcher_collection == rig_settings.extras_collection
            else rig_settings.outfit_config_subcollections
        )

        items = (
            switcher_collection.all_objects if use_subcollections else switcher_collection.objects
        )

        visible = False
        for ob in items:
            if ob == bcoll_settings.outfit_switcher_object:
                # If it is an Extras item, we should test if the collection
                # is not hidden
                is_extras_item = False
                if rig_settings.extras_collection:
                    is_extras_item = any(
                        ob == extra for extra in rig_settings.extras_collection.all_objects
                    )

                if is_extras_item:
                    visible = (
                        not ob.hide_viewport
                        and not bcoll_settings.outfit_switcher_collection.hide_viewport
                        and not is_extras_hidden
                    )
                else:
                    visible = (
                        not ob.hide_viewport
                        and not bcoll_settings.outfit_switcher_collection.hide_viewport
                    )
                break

        if bcoll.is_visible != visible:
            bcoll.is_visible = visible
