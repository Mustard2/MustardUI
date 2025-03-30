import bpy
from ..model_selection.active_object import *


class MustardUI_PhysicsItem_Remove(bpy.types.Operator):
    """Remove the selected Cage Item from the UI"""
    bl_idname = "mustardui.physics_item_remove"
    bl_label = "Remove Physics Item"
    bl_options = {'UNDO'}

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=1)
        physics_settings = arm.MustardUI_PhysicsSettings

        uilist = physics_settings.items
        index = arm.mustardui_physics_items_uilist_index

        if len(uilist) <= index:
            return {'FINISHED'}

        # Remove the collection from the Outfits Collections
        uilist.remove(index)

        index = min(max(0, index - 1), len(uilist) - 1)
        arm.mustardui_physics_items_uilist_index = index

        arm.update_tag()

        self.report({'INFO'}, 'MustardUI - Physics item removed.')

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_PhysicsItem_Remove)


def unregister():
    bpy.utils.unregister_class(MustardUI_PhysicsItem_Remove)
