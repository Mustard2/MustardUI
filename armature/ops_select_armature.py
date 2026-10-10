import bpy

from ..model_selection.active_object import (
    ModelMode,
    active_object_operator_poll,
    mustardui_active_object,
)


class MustardUI_Armature_Select(bpy.types.Operator):
    """Select the Armature"""

    bl_idname = "mustardui.armature_select"
    bl_label = "Armature Select"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        return active_object_operator_poll(context, config=ModelMode.USER)

    def execute(self, context):

        res, obj = mustardui_active_object(context, config=ModelMode.USER)
        rig_settings = obj.MustardUI_RigSettings

        rig = rig_settings.model_armature_object

        if rig is not None:
            for o in context.view_layer.objects:
                o.select_set(False)
            rig.select_set(True)
            context.view_layer.objects.active = rig

        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_Armature_Select)


def unregister():
    bpy.utils.unregister_class(MustardUI_Armature_Select)
