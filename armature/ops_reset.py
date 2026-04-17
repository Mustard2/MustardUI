import bpy

from ..model_selection.active_object import mustardui_active_object


class MustardUI_Armature_ResetCollections(bpy.types.Operator):
    """Reset the collections visibility to the default status"""

    bl_idname = "mustardui.armature_reset_bcoll"
    bl_label = "Armature Collections Reset"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):

        res, arm = mustardui_active_object(context, config=0)
        return res

    def execute(self, context):

        res, obj = mustardui_active_object(context, config=0)

        for coll in obj.collections_all:
            coll.is_visible = (
                coll.MustardUI_ArmatureBoneCollection.is_in_UI
                and coll.MustardUI_ArmatureBoneCollection.default
            )
            coll.is_solo = False

        # Outfits visibility sync, (Hair does not seem to be affected by the reset)
        arm = obj.MustardUI_ArmatureSettings

        arm.armature_visibility_outfits_update(context)

        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_Armature_ResetCollections)


def unregister():
    bpy.utils.unregister_class(MustardUI_Armature_ResetCollections)
