import math
import os

import bpy

from ...model_selection.active_object import ModelMode, active_object_operator_poll
from .effect import RemoveEffect, add_effect_modifier, effects_available, new_control

NODE_GROUP = "MustardUI Ripple"
CONTROL_TYPE = "EFFECT_RIPPLE"
RESOURCE = os.path.join(os.path.dirname(__file__), "resources", "ripple.blend")


class MustardUI_ModelToolkit_Ripple(bpy.types.Operator):
    """Ripple the selected meshes where the flattened sphere of a Control Empty cuts them, moving it to move the ripple"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_ripple"
    bl_label = "Add Ripple"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        if not effects_available():
            cls.poll_message_set("Needs Blender 5.2")
            return False
        return active_object_operator_poll(context, config=ModelMode.MODEL_TOOLKIT) and any(
            x.type == "MESH" for x in context.selected_objects
        )

    def execute(self, context):
        objects = [x for x in context.selected_objects if x.type == "MESH"]

        if NODE_GROUP not in bpy.data.node_groups:
            with bpy.data.libraries.load(RESOURCE) as (_, target):
                target.node_groups = [NODE_GROUP]

        # Vertical disc facing the back, as thick as the ripple
        control, low, high = new_control(objects, "Ripple", CONTROL_TYPE)
        radius = max(high - low) / 8
        control.scale = (radius, radius, radius / 8)
        control.rotation_euler = (math.pi / 2, 0, 0)

        for obj in objects:
            add_effect_modifier(obj, "Ripple", NODE_GROUP, control)

        self.report({"INFO"}, f"MustardUI - Ripple added to {len(objects)} objects.")
        return {"FINISHED"}


class MustardUI_ModelToolkit_RemoveRipple(RemoveEffect, bpy.types.Operator):
    """Remove the Ripple from the selected meshes, and the Controls not used anymore"""

    bl_idname = "mustardui.model_toolkit_remove_ripple"
    bl_label = "Remove Ripple"

    effect = "Ripple"
    node_group = NODE_GROUP
    creators_type = CONTROL_TYPE


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_Ripple)
    bpy.utils.register_class(MustardUI_ModelToolkit_RemoveRipple)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_RemoveRipple)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_Ripple)
