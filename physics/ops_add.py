import bpy
from ..model_selection.active_object import *


class MustardUI_PhysicsAddItem(bpy.types.Operator):
    """Add the item as a Physics item.\nThis can be done only in Configuration mode"""
    bl_idname = "mustardui.physics_add_item"
    bl_label = "Add Physics Item"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):

        res, arm = mustardui_active_object(context, config=1)
        return res

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings
        physics_settings = arm.MustardUI_PhysicsSettings

        # Check if the item is already used as Extras, Hair or Outfit
        if rig_settings.extras_collection is not None:
            if context.object in [x for x in rig_settings.extras_collection.objects]:
                self.report({'ERROR'}, 'MustardUI - Object already added in Extras.')
                return {'FINISHED'}
        if rig_settings.hair_collection is not None:
            if context.object in [x for x in rig_settings.hair_collection.objects]:
                self.report({'ERROR'}, 'MustardUI - Object already added in Hair.')
                return {'FINISHED'}
        for coll in [x.collection for x in rig_settings.outfits_collections]:
            if context.object in [x for x in coll.objects]:
                self.report({'ERROR'}, 'MustardUI - Object already added in Outfits.')
                return {'FINISHED'}

        # Add the item
        add_item = physics_settings.items.add()
        add_item.object = bpy.context.object
        self.report({'INFO'}, 'MustardUI - Physics Items added.')

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_PhysicsAddItem)


def unregister():
    bpy.utils.unregister_class(MustardUI_PhysicsAddItem)
