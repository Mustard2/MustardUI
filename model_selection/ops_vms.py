import bpy
from bpy.props import StringProperty

from ..model_selection.active_object import mustardui_active_object


class MustardUI_ViewportModelSelection(bpy.types.Operator):
    """Turn on/off Viewport Model Selection.\nWhen active, the model associated to the selected Armature is shown in the UI.\nWhen disabled, the model can be selected from the Model Selection panel."""  # noqa: E501

    bl_idname = "mustardui.viewportmodelselection"
    bl_label = "Viewport Model Selection"
    bl_options = {"UNDO"}

    config: bpy.props.BoolProperty(default=0)

    def execute(self, context):
        settings = bpy.context.scene.MustardUI_Settings

        poll, settings.panel_model_selection_armature = mustardui_active_object(
            context, self.config
        )
        settings.viewport_model_selection = not settings.viewport_model_selection

        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_ViewportModelSelection)


def unregister():
    bpy.utils.unregister_class(MustardUI_ViewportModelSelection)
