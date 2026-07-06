import bpy

from ..model_selection.active_object import (
    active_object_operator_poll,
    mustardui_active_object,
)


class MustardUI_AddOutfit(bpy.types.Operator):
    """Add the collection as an outfit.\nThis can be done only in Configuration mode"""

    bl_idname = "mustardui.add_collection"
    bl_label = "Add Outfit"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        return active_object_operator_poll(context, config=1)

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings

        extras = rig_settings.extras_collection
        if extras is not None:
            extras_colls = [extras]
            if rig_settings.extras_config_subcollections:
                extras_colls.extend(extras.children_recursive)
            if bpy.context.collection in extras_colls:
                self.report({"ERROR"}, "MustardUI - Collection already added as Extras.")
                return {"FINISHED"}
        if bpy.context.collection == rig_settings.hair_collection:
            self.report({"ERROR"}, "MustardUI - Collection already added as Hair.")
            return {"FINISHED"}

        if bpy.context.collection not in [x.collection for x in rig_settings.outfits_collections]:
            add_item = rig_settings.outfits_collections.add()
            add_item.collection = bpy.context.collection
            self.report({"INFO"}, "MustardUI - Outfit added.")
        else:
            self.report({"ERROR"}, "MustardUI - Outfit was already added.")

        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_AddOutfit)


def unregister():
    bpy.utils.unregister_class(MustardUI_AddOutfit)
