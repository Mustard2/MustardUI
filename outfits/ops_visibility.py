import bpy
from ..model_selection.active_object import *
from ..physics.update_enable import enable_physics_update


# Operator to switch visibility of an object
class MustardUI_OutfitVisibility(bpy.types.Operator):
    """Chenge the visibility of the selected object"""
    bl_idname = "mustardui.object_visibility"
    bl_label = "Object Visibility"
    bl_options = {'UNDO'}

    obj: bpy.props.StringProperty()
    shift: bpy.props.BoolProperty()

    def invoke(self, context, event):
        if not self.shift:
            self.shift = event.shift
        return self.execute(context)

    def execute(self, context):

        poll, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings
        armature_settings = arm.MustardUI_ArmatureSettings
        physics_settings = arm.MustardUI_PhysicsSettings
        outfit_cp = arm.MustardUI_CustomPropertiesOutfit

        object = context.scene.objects[self.obj]

        object.hide_viewport = not context.scene.objects[self.obj].hide_viewport
        object.hide_render = context.scene.objects[self.obj].hide_viewport
        object.MustardUI_outfit_visibility = context.scene.objects[self.obj].hide_viewport

        # Enable armature modifier
        for modifier in object.modifiers:
            if modifier.type == "ARMATURE":
                modifier.show_viewport = not object.MustardUI_outfit_visibility

        # Update values of custom properties
        outfit_cp = [x for x in outfit_cp if object == x.outfit_piece and (
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
                    modifier.show_viewport = not object.hide_viewport
                    modifier.show_render = not object.hide_viewport
        else:
            self.report({'WARNING'}, 'MustardUI - Outfit Body has not been specified.')

        # Enable/disable armature layers
        if armature_settings.outfits:
            collections = arm.collections_all
            outfit_armature_layers = [x for x in collections if x.MustardUI_ArmatureBoneCollection.outfit_switcher_enable and x.MustardUI_ArmatureBoneCollection.outfit_switcher_collection is not None]
            for bcoll in outfit_armature_layers:
                bcoll_settings = bcoll.MustardUI_ArmatureBoneCollection
                items = bcoll_settings.outfit_switcher_collection.all_objects if rig_settings.outfit_config_subcollections else bcoll_settings.outfit_switcher_collection.objects
                for ob in [x for x in items]:
                    if ob == bcoll_settings.outfit_switcher_object:
                        bcoll.is_visible = not context.scene.objects[ob.name].hide_viewport and not bcoll_settings.outfit_switcher_collection.hide_viewport

        if rig_settings.outfits_update_tag_on_switch:
            for obju in context.scene.objects:
                obju.update_tag()

        if self.shift:
            for c in object.children:
                bpy.ops.mustardui.object_visibility(obj=c.name, shift=True)

        # Force Physics recheck
        if physics_settings.enable_ui:
            enable_physics_update(physics_settings, context)

        self.shift = False

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_OutfitVisibility)


def unregister():
    bpy.utils.unregister_class(MustardUI_OutfitVisibility)
