import bpy
from bpy.props import *
from ..model_selection.active_object import *


class MustardUI_ViewportModelSelection(bpy.types.Operator):
    """Turn on/off Viewport Model Selection"""
    bl_idname = "mustardui.viewportmodelselection"
    bl_label = "Viewport Model Selection"
    bl_options = {'UNDO'}

    config: bpy.props.BoolProperty(default=0)

    def execute(self, context):
        settings = bpy.context.scene.MustardUI_Settings

        poll, settings.panel_model_selection_armature = mustardui_active_object(context, self.config)
        settings.viewport_model_selection = not settings.viewport_model_selection

        return {'FINISHED'}


class MustardUI_SwitchModel(bpy.types.Operator):
    """Switch to the selected model"""
    bl_idname = "mustardui.switchmodel"
    bl_label = "Switch Model"
    bl_options = {'UNDO'}

    model_to_switch: StringProperty()

    @classmethod
    def poll(cls, context):

        settings = bpy.context.scene.MustardUI_Settings

        return not settings.viewport_model_selection

    def execute(self, context):

        settings = bpy.context.scene.MustardUI_Settings

        # Check if you are trying to switch to the same model already in use
        if bpy.data.armatures[self.model_to_switch] == settings.panel_model_selection_armature:
            self.report({'WARNING'}, 'MustardUI - Already using ' + bpy.data.armatures[
                self.model_to_switch].MustardUI_RigSettings.model_name + ' model.')
            return {'FINISHED'}

        # Change the model if it is not None
        if bpy.data.armatures[self.model_to_switch] is not None:
            settings.panel_model_selection_armature = bpy.data.armatures[self.model_to_switch]
            self.report({'INFO'}, 'MustardUI - Switched to ' + bpy.data.armatures[
                self.model_to_switch].MustardUI_RigSettings.model_name + '.')
        else:
            self.report({'ERROR'}, 'MustardUI - Error occurred while switching the model.')

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_ViewportModelSelection)
    bpy.utils.register_class(MustardUI_SwitchModel)


def unregister():
    bpy.utils.unregister_class(MustardUI_SwitchModel)
    bpy.utils.unregister_class(MustardUI_ViewportModelSelection)
