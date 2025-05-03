import bpy
from bpy.props import *
from ..model_selection.active_object import *
from.settings_item import mustardui_physics_item_type_dict


class MustardUI_PhysicsItem_Outfits_Remove(bpy.types.Operator):
    """Remove the selected Physics Item intersecting Outfit"""
    bl_idname = "mustardui.physics_intersecting_object_remove"
    bl_label = "Remove Physics Item Intersecing Outfit"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=1)
        physics_settings = arm.MustardUI_PhysicsSettings
        return res and arm.mustardui_physics_items_outfits_uilist_index > -1 and physics_settings.items[arm.mustardui_physics_items_uilist_index].object is not None

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=1)
        physics_settings = arm.MustardUI_PhysicsSettings

        uilist = physics_settings.items[arm.mustardui_physics_items_uilist_index].intersecting_objects
        index = arm.mustardui_physics_items_outfits_uilist_index

        if len(uilist) <= index:
            return {'FINISHED'}

        # Remove the collection from the Outfits Collections
        uilist.remove(index)

        index = min(max(0, index - 1), len(uilist) - 1)
        arm.mustardui_physics_items_outfits_uilist_index = index

        arm.update_tag()

        self.report({'INFO'}, 'MustardUI - Physics Item Intersecting Outfit removed.')

        return {'FINISHED'}


class MUSTARDUI_UL_PhysicsItems_Outfits_UIList(bpy.types.UIList):
    """UIList for Physics Items"""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if item.object:
            layout.prop(item.object, 'name', text="", emboss=False, translate=False)
        else:
            layout.label(text="Object not found!", icon="ERROR")


def register():
    bpy.utils.register_class(MUSTARDUI_UL_PhysicsItems_Outfits_UIList)
    bpy.utils.register_class(MustardUI_PhysicsItem_Outfits_Remove)

    bpy.types.Armature.mustardui_physics_items_outfits_uilist_index = IntProperty(name="", default=0)


def unregister():
    del bpy.types.Armature.mustardui_physics_items_outfits_uilist_index

    bpy.utils.unregister_class(MustardUI_PhysicsItem_Outfits_Remove)
    bpy.utils.unregister_class(MUSTARDUI_UL_PhysicsItems_Outfits_UIList)
