import bpy
from ..model_selection.active_object import *
from .ops_remove import *


class MustardUI_DeleteOutfit(bpy.types.Operator):
    """Delete the selected Outfit from the Scene.\nThe collection and its objects are deleted"""
    bl_idname = "mustardui.delete_outfit"
    bl_label = "Delete Outfit"
    bl_options = {'UNDO'}

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings

        uilist = rig_settings.outfits_collections
        index = context.scene.mustardui_outfits_uilist_index

        col = uilist[index].collection
        bpy.ops.mustardui.remove_outfit()

        # FIXME: check crash when using this on some outfits

        # Remove Objects
        items = {}
        for obj in col.all_objects if rig_settings.outfit_config_subcollections else col.objects:
            items[obj.name] = obj

        for _, obj in reversed(items.items()):
            data = obj.data
            obj_type = obj.type
            context.scene.objects.remove(obj)
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
