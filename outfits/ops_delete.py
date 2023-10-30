import bpy
from ..model_selection.active_object import *
from .ops_remove import *


class MustardUI_DeleteOutfit(bpy.types.Operator):
    """Delete the selected Outfit from the Scene.\nThe collection and its objects are deleted"""
    bl_idname = "mustardui.delete_outfit"
    bl_label = "Delete Outfit"
    bl_options = {'UNDO'}

    col: bpy.props.StringProperty()

    def execute(self, context):

        settings = bpy.context.scene.MustardUI_Settings
        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings

        bpy.ops.mustardui.remove_outfit(col=self.col)
        col = bpy.data.collections[self.col]

        # Remove Objects
        items = col.all_objects if rig_settings.outfit_config_subcollections else col.objects
        for obj in items:
            data = obj.data
            obj_type = obj.type
            bpy.data.objects.remove(obj)
            if obj_type == "MESH":
                bpy.data.meshes.remove(data)
            elif obj_type == "ARMATURE":
                bpy.data.armatures.remove(data)

        bpy.data.collections.remove(col)

        self.report({'INFO'}, 'MustardUI - Outfit deleted.')

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_DeleteOutfit)


def unregister():
    bpy.utils.unregister_class(MustardUI_DeleteOutfit)