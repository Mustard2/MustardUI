import bpy

from ..model_selection.active_object import active_object_operator_poll, mustardui_active_object
from ..physics.update_enable import enable_physics_update
from .helper_functions import (
    outfits_update_armature_collections,
    update_extras_visibility,
)


class MustardUI_ExtrasCollectionVisibility(bpy.types.Operator):
    """Change the visibility of all the objects in the selected Extras sub-collection"""

    bl_idname = "mustardui.extras_collection_visibility"
    bl_label = "Extras Collection Visibility"
    bl_options = {"UNDO"}

    collection: bpy.props.StringProperty()

    @classmethod
    def poll(cls, context):
        return active_object_operator_poll(context, config=0)

    def execute(self, context):
        collection = bpy.data.collections.get(self.collection)

        if collection is None:
            self.report({"WARNING"}, f'MustardUI - Collection "{self.collection}" not found.')
            return {"CANCELLED"}

        poll, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings
        armature_settings = arm.MustardUI_ArmatureSettings
        physics_settings = arm.MustardUI_PhysicsSettings

        # Master show/hide for the sub-collection
        show = not collection.MustardUI_extras_show
        collection.MustardUI_extras_show = show
        for obj in collection.all_objects:
            obj.hide_viewport = not show
            obj.hide_render = not show

        # Recompute hide/exclude flags on the whole Extras tree
        is_extras_hidden = update_extras_visibility(context, rig_settings)

        # Physics update
        if physics_settings.enable_ui:
            enable_physics_update(physics_settings, context)

        # Armature collections
        if armature_settings.outfits:
            outfits_update_armature_collections(
                rig_settings, arm, is_extras_hidden=is_extras_hidden
            )

        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_ExtrasCollectionVisibility)


def unregister():
    bpy.utils.unregister_class(MustardUI_ExtrasCollectionVisibility)
