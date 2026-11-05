import bpy

from .settings import EFFECTS


class MustardUI_ModelToolkit_RemoveSceneEffect(bpy.types.Operator):
    """Remove the effect from the object, as its remove button in the Effects section"""

    bl_idname = "mustardui.model_toolkit_remove_scene_effect"
    bl_label = "Remove Effect"
    bl_options = {"UNDO"}

    effect: bpy.props.StringProperty(options={"HIDDEN"})
    name: bpy.props.StringProperty(options={"HIDDEN"})

    def execute(self, context):
        obj = context.scene.objects.get(self.name)
        if obj is None or self.effect not in EFFECTS:
            self.report({"WARNING"}, f"MustardUI - {self.effect} of {self.name} not found.")
            return {"CANCELLED"}
        # The remove operators act on the selected objects
        with context.temp_override(selected_objects=[obj], active_object=obj, object=obj):
            return getattr(bpy.ops.mustardui, f"model_toolkit_{EFFECTS[self.effect][3]}")()


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_RemoveSceneEffect)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_RemoveSceneEffect)
