import bpy
from ..model_selection.active_object import *


# Operator to switch visibility of an object
class MustardUI_OutfitVisibility(bpy.types.Operator):
    """Chenge the visibility of the selected object"""
    bl_idname = "mustardui.object_visibility"
    bl_label = "Object Visibility"
    bl_options = {'UNDO'}

    obj: bpy.props.StringProperty()

    def execute(self, context):

        poll, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings
        #armature_settings = arm.MustardUI_ArmatureSettings
        outfit_cp = arm.MustardUI_CustomPropertiesOutfit

        bpy.data.objects[self.obj].hide_viewport = not bpy.data.objects[self.obj].hide_viewport
        bpy.data.objects[self.obj].hide_render = bpy.data.objects[self.obj].hide_viewport
        bpy.data.objects[self.obj].MustardUI_outfit_visibility = bpy.data.objects[self.obj].hide_viewport

        # Enable armature modifier
        for modifier in bpy.data.objects[self.obj].modifiers:
            if modifier.type == "ARMATURE":
                modifier.show_viewport = not bpy.data.objects[self.obj].MustardUI_outfit_visibility

        # Update values of custom properties
        outfit_cp = [x for x in outfit_cp if bpy.data.objects[self.obj] == x.outfit_piece and (
                x.outfit_enable_on_switch or x.outfit_disable_on_switch)]

        for cp in outfit_cp:

            ui_data = arm.id_properties_ui(cp.prop_name)
            ui_data_dict = ui_data.as_dict()

            if not cp.outfit_piece.hide_viewport and cp.outfit_enable_on_switch:
                arm[cp.prop_name] = ui_data_dict['max']
            elif cp.outfit_piece.hide_viewport and cp.outfit_disable_on_switch:
                arm[cp.prop_name] = ui_data_dict['default']

        arm.update_tag()

        # Disable Extras collection if none is active to increase performance
        if rig_settings.extras_collection is not None:
            items = rig_settings.extras_collection.all_objects if rig_settings.outfit_config_subcollections else rig_settings.extras_collection.objects
            rig_settings.extras_collection.hide_viewport = len([x for x in items if not x.hide_render]) == 0
            rig_settings.extras_collection.hide_render = rig_settings.extras_collection.hide_viewport

        # Enable/disable masks on the body
        if rig_settings.model_body:
            for modifier in rig_settings.model_body.modifiers:
                if modifier.type == "MASK" and self.obj in modifier.name and rig_settings.outfits_global_mask:
                    modifier.show_viewport = not bpy.data.objects[self.obj].hide_viewport
                    modifier.show_render = not bpy.data.objects[self.obj].hide_viewport
        else:
            self.report({'WARNING'}, 'MustardUI - Outfit Body has not been specified.')

        # Enable/disable armature layers
        # if len(armature_settings.layers) > 0 and armature_settings.outfits:
        #     outfit_armature_layers = [x for x in range(0, 32) if armature_settings.layers[x].outfit_switcher_enable and armature_settings.layers[x].outfit_switcher_collection != None]
        #
        #     for i in outfit_armature_layers:
        #         items = armature_settings.layers[
        #             i].outfit_switcher_collection.all_objects if rig_settings.outfit_config_subcollections else \
        #             armature_settings.layers[i].outfit_switcher_collection.objects
        #         for ob in [x for x in items]:
        #             if ob == armature_settings.layers[i].outfit_switcher_object:
        #                 armature_settings.layers[i].show = not bpy.data.objects[ob.name].hide_viewport and not \
        #                     armature_settings.layers[i].outfit_switcher_collection.hide_viewport

        if rig_settings.outfits_update_tag_on_switch:
            for obju in bpy.data.objects:
                obju.update_tag()

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_OutfitVisibility)


def unregister():
    bpy.utils.unregister_class(MustardUI_OutfitVisibility)
