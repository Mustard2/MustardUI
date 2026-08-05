from ..misc.set_bool import set_bool
from ..outfits.helper_functions import (
    get_mask_objects,
    update_global_masks,
    update_outfit_masks,
)


def set_object_visibility(obj, visible, rig_settings):
    """Set object and relevant modifiers visibility"""
    set_bool(obj, "hide_viewport", not visible)
    set_bool(obj, "hide_render", not visible)

    for mod in [x for x in obj.modifiers if x.type in ["PARTICLE_SYSTEM", "ARMATURE", "NODES"]]:
        if mod.type in ["PARTICLE_SYSTEM", "NODES"]:
            set_bool(mod, "show_viewport", visible)
            set_bool(mod, "show_render", visible)
        else:  # ARMATURE
            set_bool(
                mod,
                "show_viewport",
                visible if rig_settings.hair_switch_armature_disable else True,
            )


def apply_hair_visibility(rig_settings, force_hidden=False):
    """Show the Hair Object selected in the Hair list, hiding all the others."""
    hair_collection = rig_settings.hair_collection
    if hair_collection is None:
        return

    hair_collection_objs = [x for x in hair_collection.objects]
    for obj in [x for x in hair_collection_objs if x.type in {"MESH", "CURVES"}]:
        visible = obj.name == rig_settings.hair_list and not force_hidden

        set_object_visibility(obj, visible, rig_settings)

        parent_armature = obj.find_armature()
        if parent_armature is not None and parent_armature in hair_collection_objs:
            set_object_visibility(parent_armature, visible, rig_settings)


def get_hair_mask_visibility(rig_settings, mask=True):
    """{Hair piece name: mask visibility} for the Hair and Hair Extras collections."""
    visibility = {}
    for collection in (rig_settings.hair_collection, rig_settings.hair_extras_collection):
        if collection is None:
            continue
        for obj in collection.all_objects:
            visibility[obj.name] = not obj.hide_viewport and mask
    return visibility


def update_hair_masks(context, rig_settings):
    """Refresh the masks driven by the Hair pieces on every object hosting them."""
    mask_objects = get_mask_objects(rig_settings)
    if not mask_objects:
        return
    visibility = get_hair_mask_visibility(rig_settings, rig_settings.hair_global_mask)
    update_outfit_masks(context, mask_objects, visibility)
    update_global_masks(mask_objects)


def hair_switcher_active(rig_settings):
    """Return True if an Object of the Hair Switch collection is currently visible."""
    hair_switch_collection = rig_settings.hair_switch_collection
    if rig_settings.hair_collection is None or hair_switch_collection is None:
        return False

    return any(
        obj.type in {"MESH", "ARMATURE"} and not obj.hide_viewport
        for obj in hair_switch_collection.all_objects
    )


def store_current_hair(rig_settings):
    """Return the name of the currently visible hair object, or '' if none found."""
    if rig_settings.hair_collection is None:
        return ""
    for obj in rig_settings.hair_collection.objects:
        if (
            obj is not None
            and not obj.hide_viewport
            and not obj.hide_render
            and obj.type in ["MESH", "CURVES"]
        ):
            return obj.name
    return ""


def set_selected_hair(context, rig_settings, object_active):
    """Set hair_list to object_active, falling back to the first element if needed."""
    hlist = rig_settings.hair_list_make(context)
    if not hlist:
        return
    if object_active:
        try:
            rig_settings.hair_list = object_active
        except Exception:
            rig_settings.hair_list = hlist[0][0]
    else:
        rig_settings.hair_list = hlist[0][0]
