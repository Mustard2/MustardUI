import bpy
from ..model_selection.active_object import *
from .ops_remove import *

def cleanup_dangling_drivers(rig_settings):
    if rig_settings.model_body:
        if not rig_settings.model_body.data.shape_keys or not rig_settings.model_body.data.shape_keys.animation_data:
            return 0

        drivers = rig_settings.model_body.data.shape_keys.animation_data.drivers
        drivers_to_remove = set()

        for drv in drivers:
            if not drv.driver.is_valid:
                drivers_to_remove.add(drv)
                break

        for drv in drivers_to_remove:
            drivers.remove(drv)

        return len(drivers_to_remove)

    return 0

class MustardUI_DeleteOutfit(bpy.types.Operator):
    """Delete the selected Outfit from the Scene.\nThe collection and its objects are deleted"""
    bl_idname = "mustardui.delete_outfit"
    bl_label = "Delete Outfit"
    bl_options = {'UNDO'}

    is_config: bpy.props.BoolProperty(default=True)

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=-1)
        rig_settings = arm.MustardUI_RigSettings

        if self.is_config:
            uilist = rig_settings.outfits_collections
            index = context.scene.mustardui_outfits_uilist_index

            col = uilist[index].collection
        else:
            col = bpy.data.collections[rig_settings.outfits_list]

        bpy.ops.mustardui.remove_outfit(is_config=self.is_config)

        if not col:
            self.report({'WARNING'}, 'MustardUI - The Outfit collection to remove was not found.')
            return {'FINISHED'}

        outfit_name = col.name

        # Remove Objects
        items = {}
        for obj in col.all_objects if rig_settings.outfit_config_subcollections else col.objects:
            items[obj.name] = obj

        for _, obj in reversed(items.items()):
            data = obj.data
            obj_type = obj.type
            bpy.data.objects.remove(obj)
            if obj_type == "MESH":
                bpy.data.meshes.remove(data)
            elif obj_type == "ARMATURE":
                bpy.data.armatures.remove(data)

        bpy.data.collections.remove(col)

        # Revert Mask settings
        if rig_settings.model_body:
            for mod in rig_settings.model_body.modifiers:
                if mod.type == "MASK" and outfit_name in mod.name:
                    mod.show_viewport = False
                    mod.show_render = False

        self.report({'INFO'}, f"MustardUI - Outfit '{outfit_name}' deleted.")

        '''
        After the removal of drivers, some go in invalid state, we should handle those too after all drivers have
        been removed!
        '''
        cleanup_dangling_drivers(rig_settings)

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_DeleteOutfit)


def unregister():
    bpy.utils.unregister_class(MustardUI_DeleteOutfit)
