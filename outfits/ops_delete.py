import bpy

from ..misc.remove_objects import remove_objects
from ..model_selection.active_object import (
    active_object_operator_poll,
    mustardui_active_object,
)
from .helper_functions import get_mask_visibility, update_masks


class MustardUI_DeleteOutfit(bpy.types.Operator):
    """Delete the selected Outfit from the Scene.\nThe collection and its objects are deleted"""  # noqa: E501

    bl_idname = "mustardui.delete_outfit"
    bl_label = "Delete Outfit"
    bl_options = {"UNDO"}

    is_config: bpy.props.BoolProperty(default=True)
    delete_cp: bpy.props.BoolProperty(default=True)

    @classmethod
    def poll(cls, context):
        return active_object_operator_poll(context, config=-1)

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=-1)
        rig_settings = arm.MustardUI_RigSettings
        physics_settings = arm.MustardUI_PhysicsSettings

        if self.is_config:
            uilist = rig_settings.outfits_collections
            index = context.scene.mustardui_outfits_uilist_index

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

        # Remove linked Physics Items
        items_to_remove = [
            pi_id
            for pi_id, item in enumerate(physics_settings.items)
            if item.outfit_enable and item.outfit_collection == col
        ]
        for pi_id in reversed(items_to_remove):
            arm.mustardui_physics_items_uilist_index = pi_id
            if physics_settings.items[pi_id].object is not None:
                bpy.ops.mustardui.physics_item_delete()
            else:
                bpy.ops.mustardui.physics_item_remove()

        # Remove Objects
        pieces = list(col.all_objects if rig_settings.outfit_config_subcollections else col.objects)
        deleted_names = [x.name for x in pieces]
        remove_objects(pieces)

        bpy.data.collections.remove(col)

        # Turn off the masks of the deleted pieces, matched by name as on outfit switch
        visibility = get_mask_visibility(rig_settings)
        visibility.update(dict.fromkeys(deleted_names, False))
        update_masks(context, rig_settings, visibility)

        self.report({"INFO"}, f"MustardUI - Outfit '{outfit_name}' deleted.")

        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_DeleteOutfit)


def unregister():
    bpy.utils.unregister_class(MustardUI_DeleteOutfit)
