import bpy

from ..model_selection.active_object import (
    active_object_operator_poll,
    mustardui_active_object,
)


class MustardUI_Outfits_SelectInConfiguration(bpy.types.Operator):
    """Show the Outfit"""

    bl_idname = "mustardui.outfits_select_in_configuration"
    bl_label = "Outfits Property Switch"

    @classmethod
    def poll(cls, context):
        return active_object_operator_poll(context, config=1)

    def execute(self, context):

        scene = context.scene

        poll, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings

        if (
            scene.mustardui_outfits_uilist_index >= len(rig_settings.outfits_collections)
            or scene.mustardui_outfits_uilist_index < 0
        ):
            return {"CANCELLED"}

        collection = rig_settings.outfits_collections[
            scene.mustardui_outfits_uilist_index
        ].collection
        if collection is None:
            return {"CANCELLED"}

        rig_settings.outfits_list = collection.name

        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_Outfits_SelectInConfiguration)


def unregister():
    bpy.utils.unregister_class(MustardUI_Outfits_SelectInConfiguration)
