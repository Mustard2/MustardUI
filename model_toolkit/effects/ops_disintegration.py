import os

import bpy

from ...model_selection.active_object import ModelMode, active_object_operator_poll
from .effect import (
    RemoveEffect,
    add_effect_modifier,
    effects_available,
    modifier_input,
    new_control,
)

NODE_GROUP = "MustardUI Disintegration"
MATERIAL = "MustardUI Disintegration Particles"
CONTROL_TYPE = "EFFECT_DISINTEGRATION"
RESOURCE = os.path.join(os.path.dirname(__file__), "resources", "disintegration.blend")


class MustardUI_ModelToolkit_Disintegration(bpy.types.Operator):
    """Disintegrate the selected meshes into particles inside the sphere of a Control Empty, growing over them"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_disintegration"
    bl_label = "Add Disintegration"
    bl_options = {"REGISTER", "UNDO"}

    duration: bpy.props.IntProperty(
        name="Duration",
        default=48,
        min=1,
        description="Frames for the Control to grow over the meshes, from the current frame",
    )

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

        with bpy.data.libraries.load(RESOURCE) as (_, target):
            if NODE_GROUP not in bpy.data.node_groups:
                target.node_groups = [NODE_GROUP]
            if MATERIAL not in bpy.data.materials:
                target.materials = [MATERIAL]

        # Control growing until it covers the meshes
        control, low, high = new_control(objects, "Disintegration", CONTROL_TYPE)
        radius = (high - low).length / 2 * 1.25
        frame = context.scene.frame_current
        for f, scale in ((frame, 0.001), (frame + self.duration, radius)):
            control.scale = (scale, scale, scale)
            control.keyframe_insert("scale", frame=f)

        for obj in objects:
            modifier = add_effect_modifier(obj, "Disintegration", NODE_GROUP, control)
            modifier_input(modifier, "Material").value = bpy.data.materials[MATERIAL]

        self.report({"INFO"}, f"MustardUI - Disintegration added to {len(objects)} objects.")
        return {"FINISHED"}


class MustardUI_ModelToolkit_RemoveDisintegration(RemoveEffect, bpy.types.Operator):
    """Remove the Disintegration from the selected meshes, and the Controls not used anymore"""

    bl_idname = "mustardui.model_toolkit_remove_disintegration"
    bl_label = "Remove Disintegration"

    effect = "Disintegration"
    node_group = NODE_GROUP
    creators_type = CONTROL_TYPE


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_Disintegration)
    bpy.utils.register_class(MustardUI_ModelToolkit_RemoveDisintegration)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_RemoveDisintegration)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_Disintegration)
