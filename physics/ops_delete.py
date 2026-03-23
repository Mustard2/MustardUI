import bpy
from ..model_selection.active_object import *


class MustardUI_PhysicsItem_Delete(bpy.types.Operator):
    """Delete the selected Physics Item, removing it from the UI and deleting all the Objects from the scene"""
    bl_idname = "mustardui.physics_item_delete"
    bl_label = "Delete Physics Item"
    bl_options = {'UNDO'}

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=1)
        physics_settings = arm.MustardUI_PhysicsSettings

        uilist = physics_settings.items
        index = arm.mustardui_physics_items_uilist_index

        if len(uilist) <= index:
            return {'FINISHED'}

        item = uilist[index]
        pi_obj = item.object
        obj_name = pi_obj.name

        # Remove the associated modifiers in the scene
        for obj in context.scene.objects:
            if obj.type != "MESH":
                continue
            for mod in list(obj.modifiers):
                if (mod.type == "SURFACE_DEFORM" and mod.target == pi_obj) or (
                        mod.type == "MESH_DEFORM" and mod.target == pi_obj) or (
                        mod.name == obj_name
                ):
                    obj.modifiers.remove(mod)

        # Delete the Objects
        try:
            data = pi_obj.data
            bpy.data.objects.remove(pi_obj)
            bpy.data.meshes.remove(data)
        except:
            self.report({'ERROR'}, 'MustardUI - An error occurred while deleting the Physics Item.')
            return {'FINISHED'}

        # Remove the Physics Items from the list
        bpy.ops.mustardui.physics_item_remove()

        self.report({'INFO'}, 'MustardUI - Physics Item deleted.')

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_PhysicsItem_Delete)


def unregister():
    bpy.utils.unregister_class(MustardUI_PhysicsItem_Delete)
