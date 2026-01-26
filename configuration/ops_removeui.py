import bpy
from bpy.props import *
from ..custom_properties.misc import mustardui_delete_all_custom_properties
from ..model_selection.active_object import *
from .. import __package__ as base_package


class MustardUI_RemoveUI(bpy.types.Operator):
    """Remove and clean the model and the UI"""
    bl_idname = "mustardui.remove"
    bl_label = "Remove UI and Model"
    bl_options = {'UNDO'}

    delete_settings: BoolProperty(default=False,
                                  name="Delete Settings",
                                  description="All Settings of the UI will be removed.\nA clean Configuration is "
                                              "necessary after using this option")
    delete_objects: BoolProperty(default=False,
                                 name="Delete Objects",
                                 description="All Objects are deleted from the file, including the main Armature")
    delete_bones_custom_shapes: BoolProperty(default=True,
                                             name="Delete Bones Custom Shapes",
                                             description="Bones Custom Shapes are deleted with the Armature. Disable "
                                                         "this if some shapes are shared between different Armatures")

    def remove_data_col(self, context, col, remove_subcoll=False):

        items = col.all_objects if remove_subcoll else col.objects
        for obj in items:
            data = obj.data
            obj_type = obj.type
            bpy.data.objects.remove(obj)
            if obj_type == "MESH":
                bpy.data.meshes.remove(data)
            elif obj_type == "ARMATURE":
                bpy.data.armatures.remove(data)

        bpy.data.collections.remove(col)

        return

    def remove_data_list(self, context, ll):

        for obj in ll:
            data = obj.data
            obj_type = obj.type
            bpy.data.objects.remove(obj)
            if obj_type == "MESH":
                bpy.data.meshes.remove(data)
            elif obj_type == "ARMATURE":
                bpy.data.armatures.remove(data)

        return

    def remove_property(self, obj, name):

        try:
            del obj[name]
        except:
            pass

    @classmethod
    def poll(cls, context):

        settings = bpy.context.scene.MustardUI_Settings
        res, arm = mustardui_active_object(context, config=0)

        if arm is not None:
            return res
        return False

    def execute(self, context):

        settings = bpy.context.scene.MustardUI_Settings
        res, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings
        arm_obj = rig_settings.model_armature_object
        addon_prefs = context.preferences.addons[base_package].preferences

        # Remove or delete outfits
        for i in reversed(range(len(rig_settings.outfits_collections))):
            context.scene.mustardui_outfits_uilist_index = i
            if self.delete_objects:
                bpy.ops.mustardui.delete_outfit(is_config=True)
            elif self.delete_settings:
                bpy.ops.mustardui.remove_outfit(is_config=True)

        if self.delete_objects:
            if rig_settings.hair_collection is not None:
                self.remove_data_col(context, rig_settings.hair_collection)
            if rig_settings.extras_collection is not None:
                self.remove_data_col(context, rig_settings.extras_collection, rig_settings.outfit_config_subcollections)

        # Remove settings
        if self.delete_settings or self.delete_objects:
            # Remove custom properties
            mustardui_delete_all_custom_properties(arm, arm.MustardUI_CustomProperties, addon_prefs, rig_settings)
            mustardui_delete_all_custom_properties(arm, arm.MustardUI_CustomPropertiesOutfit, addon_prefs, rig_settings)
            mustardui_delete_all_custom_properties(arm, arm.MustardUI_CustomPropertiesHair, addon_prefs, rig_settings)

            # Clear all settings
            self.remove_property(arm, 'MustardUI_ToolsSettings')
            self.remove_property(arm, 'MustardUI_MorphsSettings')
            self.remove_property(arm, 'MustardUI_PhysicsSettings')
            self.remove_property(arm, 'MustardUI_ArmatureSettings')
            self.remove_property(arm, 'MustardUI_CustomProperties')
            self.remove_property(arm, 'MustardUI_CustomPropertiesHair')
            self.remove_property(arm, 'MustardUI_CustomPropertiesOutfit')
            self.remove_property(arm, 'MustardUI_RigSettings')

        # Remove Armature and its children objects
        if self.delete_objects:

            # Remove Armature Children
            self.remove_data_list(context, arm_obj.children)

            # Remove bones custom properties
            if self.delete_bones_custom_shapes:
                csb = []
                for bone in arm_obj.pose.bones:
                    if bone.custom_shape is not None:
                        if bone.custom_shape not in csb:
                            csb.append(bone.custom_shape)
                self.remove_data_list(context, csb)

            # Remove Armature
            self.remove_data_list(context, [arm_obj])

        else:

            arm.MustardUI_enable = not arm.MustardUI_enable
            arm.MustardUI_created = False

        settings.viewport_model_selection = True

        self.report({'INFO'}, 'MustardUI - MustardUI deletion complete. Switched to Viewport Model Selection')

        return {'FINISHED'}

    def invoke(self, context, event):

        addon_prefs = context.preferences.addons[base_package].preferences

        return context.window_manager.invoke_props_dialog(self, width=550 if addon_prefs.debug else 450)

    def draw(self, context):

        layout = self.layout

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Notes:")
        col.label(text="Read the descriptions of all buttons (keep the mouse on the buttons).", icon="DOT")
        col.label(text="This is a highly destructive operation! Use it at your own risk!", icon="ERROR")

        box = layout.box()
        col = box.column(align=True)
        col.prop(self, "delete_settings")
        col.prop(self, "delete_objects")
        row = col.row()
        row.enabled = self.delete_objects
        row.prop(self, "delete_bones_custom_shapes")


def register():
    bpy.utils.register_class(MustardUI_RemoveUI)


def unregister():
    bpy.utils.unregister_class(MustardUI_RemoveUI)
