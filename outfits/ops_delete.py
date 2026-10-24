import bpy

from .. import __package__ as base_package
from ..custom_properties.misc import mustardui_clean_prop, mustardui_reassign_default
from ..misc.remove_objects import remove_objects
from ..model_selection.active_object import (
    ModelMode,
    active_object_operator_poll,
    mustardui_active_object,
)
from .helper_functions import get_mask_visibility, outfits_get_collection_items, update_masks


def delete_collection_physics_items(arm, collection):
    """Delete the Physics Items linked to a collection, with their Objects"""

    physics_settings = arm.MustardUI_PhysicsSettings
    items_to_remove = [
        pi_id
        for pi_id, item in enumerate(physics_settings.items)
        if item.outfit_enable and item.outfit_collection == collection
    ]
    for pi_id in reversed(items_to_remove):
        arm.mustardui_physics_items_uilist_index = pi_id
        if physics_settings.items[pi_id].object is not None:
            bpy.ops.mustardui.physics_item_delete()
        else:
            bpy.ops.mustardui.physics_item_remove()


def delete_extras_pieces(
    context, arm, objs, physics=True, custom_properties=True, remove_empty=True
):
    """Delete the Extras pieces, their Physics Items and custom properties, returning the count"""

    rig_settings = arm.MustardUI_RigSettings
    physics_settings = arm.MustardUI_PhysicsSettings
    addon_prefs = context.preferences.addons[base_package].preferences
    extras = rig_settings.extras_collection
    objs = list(objs)

    if physics:
        items_to_remove = [
            pi_id
            for pi_id, item in enumerate(physics_settings.items)
            if item.outfit_enable
            and item.outfit_collection == extras
            and item.outfit_object in objs
            and item.object is not None
        ]
        # The Physics Items Objects are deleted with the items
        pi_objects = {physics_settings.items[i].object for i in items_to_remove}
        objs = [x for x in objs if x not in pi_objects]
        for pi_id in reversed(items_to_remove):
            arm.mustardui_physics_items_uilist_index = pi_id
            bpy.ops.mustardui.physics_item_delete()

    # Custom properties set to their default value first, then deleted
    outfit_cp = arm.MustardUI_CustomPropertiesOutfit
    to_remove = [
        i for i, cp in enumerate(outfit_cp) if cp.outfit == extras and cp.outfit_piece in objs
    ]
    for i in to_remove:
        mustardui_reassign_default(arm, outfit_cp, i, addon_prefs)
    if rig_settings.model_armature_object:
        rig_settings.model_armature_object.update_tag()
    context.view_layer.update()
    if custom_properties:
        for i in to_remove:
            mustardui_clean_prop(arm, outfit_cp, i, addon_prefs)
        for i in reversed(to_remove):
            outfit_cp.remove(i)

    deleted_names = [x.name for x in objs]
    remove_objects(objs)
    if remove_empty and not len(outfits_get_collection_items(rig_settings, extras)):
        bpy.data.collections.remove(extras)

    # Turn off the masks of the deleted pieces, matched by name as on outfit switch
    visibility = get_mask_visibility(rig_settings)
    visibility.update(dict.fromkeys(deleted_names, False))
    update_masks(context, rig_settings, visibility)
    return len(deleted_names)


def delete_outfit_collection(context, arm, col):
    """Delete the collection of an Outfit removed from the UI, with its pieces and Physics Items"""

    rig_settings = arm.MustardUI_RigSettings
    delete_collection_physics_items(arm, col)
    pieces = list(col.all_objects if rig_settings.outfit_config_subcollections else col.objects)
    deleted_names = [x.name for x in pieces]
    remove_objects(pieces)
    bpy.data.collections.remove(col)

    # Turn off the masks of the deleted pieces, matched by name as on outfit switch
    visibility = get_mask_visibility(rig_settings)
    visibility.update(dict.fromkeys(deleted_names, False))
    update_masks(context, rig_settings, visibility)


class MustardUI_DeleteOutfit(bpy.types.Operator):
    """Delete the selected Outfit from the Scene.\nThe collection and its objects are deleted"""  # noqa: E501

    bl_idname = "mustardui.delete_outfit"
    bl_label = "Delete Outfit"
    bl_options = {"UNDO"}

    is_config: bpy.props.BoolProperty(default=True)
    delete_cp: bpy.props.BoolProperty(default=True)

    @classmethod
    def poll(cls, context):
        return active_object_operator_poll(context, config=ModelMode.ANY)

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=ModelMode.ANY)
        rig_settings = arm.MustardUI_RigSettings

        if self.is_config:
            uilist = rig_settings.outfits_collections
            index = context.scene.mustardui_outfits_uilist_index
            if not 0 <= index < len(uilist):
                return {"FINISHED"}

            col = uilist[index].collection
        else:
            col = bpy.data.collections[rig_settings.outfits_list]

        bpy.ops.mustardui.remove_outfit(is_config=self.is_config, delete_cp=self.delete_cp)

        if not col:
            self.report(
                {"WARNING"},
                "MustardUI - The Outfit collection to remove was not found.",
            )
            return {"FINISHED"}

        outfit_name = col.name
        delete_outfit_collection(context, arm, col)
        bpy.data.orphans_purge(do_recursive=True)

        self.report({"INFO"}, f"MustardUI - Outfit '{outfit_name}' deleted.")

        return {"FINISHED"}


class MustardUI_DeleteExtras(bpy.types.Operator):
    """Delete the Extras from the Scene.\nThe collection and its objects are deleted"""

    bl_idname = "mustardui.delete_extras"
    bl_label = "Delete Extras"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=ModelMode.ANY)
        return arm is not None and arm.MustardUI_RigSettings.extras_collection is not None

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=ModelMode.ANY)
        rig_settings = arm.MustardUI_RigSettings
        extras = rig_settings.extras_collection

        delete_collection_physics_items(arm, extras)
        delete_extras_pieces(
            context, arm, outfits_get_collection_items(rig_settings, extras), physics=False
        )
        bpy.data.orphans_purge(do_recursive=True)

        self.report({"INFO"}, "MustardUI - Extras deleted.")

        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_DeleteOutfit)
    bpy.utils.register_class(MustardUI_DeleteExtras)


def unregister():
    bpy.utils.unregister_class(MustardUI_DeleteExtras)
    bpy.utils.unregister_class(MustardUI_DeleteOutfit)
