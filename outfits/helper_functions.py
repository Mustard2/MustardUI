from ..misc.set_bool import set_bool
from ..tools_creators.ops_optimize_mods import mask_vg_name


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


def update_outfit_body_masks(context, body, obj_name, visible):
    for mod in body.modifiers:
        if mod.type in ("MASK", "VERTEX_WEIGHT_MIX") and obj_name in mod.name.split("|"):
            # Shared modifier (names joined by "|"): keep it on if another
            # piece using it is still visible.
            should_show = visible
            if not should_show:
                for other_name in mod.name.split("|"):
                    if other_name == obj_name:
                        continue
                    other_obj = context.scene.objects.get(other_name)
                    if other_obj and not other_obj.hide_viewport:
                        should_show = True
                        break
            set_bool(mod, "show_viewport", should_show)
            set_bool(mod, "show_render", should_show)


def update_global_body_mask(body):
    activate = any(
        mod.type == "VERTEX_WEIGHT_MIX" and mod.vertex_group_a == mask_vg_name and mod.show_viewport
        for mod in body.modifiers
    )
    for mod in body.modifiers:
        if mod.type == "MASK" and mod.vertex_group == mask_vg_name:
            set_bool(mod, "show_viewport", activate)
            set_bool(mod, "show_render", activate)


def outfits_update_armature_collections(rig_settings, arm, is_extras_hidden=None):
    """Update visibility of armature bone collections like the outfit operator"""

    use_subcollections = rig_settings.outfit_config_subcollections

    for bcoll in arm.collections_all:
        bcoll_settings = bcoll.MustardUI_ArmatureBoneCollection
        if not bcoll_settings.outfit_switcher_enable:
            continue
        if not bcoll_settings.outfit_switcher_collection:
            continue

        items = (
            bcoll_settings.outfit_switcher_collection.all_objects
            if use_subcollections
            else bcoll_settings.outfit_switcher_collection.objects
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
