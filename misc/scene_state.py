import bpy


class SceneState:
    """Pose positions, frame, mode, active object and selection, to restore them after a
    tool changed them, also when it fails. Objects are stored by name, as the tool might
    remove some of them."""

    def __init__(self, context):
        self.pose_positions = {
            obj.name: obj.data.pose_position for obj in bpy.data.objects if obj.type == "ARMATURE"
        }
        self.frame = context.scene.frame_current
        active = context.view_layer.objects.active
        self.active = active.name if active else ""
        self.mode = active.mode if active else "OBJECT"
        self.selected = {obj.name for obj in context.selected_objects}

    def restore_poses_and_frame(self, context):
        for name, pose_position in self.pose_positions.items():
            obj = bpy.data.objects.get(name)
            if obj is not None and obj.data.pose_position != pose_position:
                obj.data.pose_position = pose_position
        if context.scene.frame_current != self.frame:
            context.scene.frame_set(self.frame)

    def restore_all(self, context):
        self.restore_poses_and_frame(context)
        if context.object and context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        for obj in context.view_layer.objects:
            obj.select_set(obj.name in self.selected)
        # If the active object was removed, the current one is kept
        active = context.view_layer.objects.get(self.active)
        if active is not None:
            context.view_layer.objects.active = active
        if active and self.mode != "OBJECT":
            bpy.ops.object.mode_set(mode=self.mode)


def execute_restoring_state(operator, context):
    """Run operator._execute, restoring pose positions and frame, and also the mode and
    selection if it fails."""
    state = SceneState(context)
    try:
        result = operator._execute(context)
    except Exception:
        state.restore_all(context)
        raise
    state.restore_poses_and_frame(context)
    return result
