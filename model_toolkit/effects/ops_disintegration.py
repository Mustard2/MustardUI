import os

import bpy
from mathutils import Vector

from ...model_selection.active_object import ModelMode, active_object_operator_poll

NODE_GROUP = "MustardUI Disintegration"
MATERIAL = "MustardUI Disintegration Particles"
RESOURCE = os.path.join(os.path.dirname(__file__), "resources", "disintegration.blend")


def disintegration_available():
    return bpy.app.version >= (5, 2, 0)


def is_disintegration(modifier):
    return (
        modifier.type == "NODES"
        and modifier.node_group is not None
        and modifier.node_group.name.startswith(NODE_GROUP)
    )


def modifier_input(modifier, name):
    identifier = next(
        x.identifier
        for x in modifier.node_group.interface.items_tree
        if x.item_type == "SOCKET" and x.in_out == "INPUT" and x.name == name
    )
    return getattr(modifier.properties.inputs, identifier)


class MustardUI_ModelToolkit_Disintegration(bpy.types.Operator):
    """Disintegrate the selected meshes into particles inside the sphere of a Control Empty, growing over them.\nThe edge of the cut is stored in the disintegration_edge attribute, to make it glow in the material"""  # noqa: E501

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
        if not disintegration_available():
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

        # Control at the center of the meshes, growing until it covers them
        corners = [obj.matrix_world @ Vector(c) for obj in objects for c in obj.bound_box]
        low = Vector([min(c[i] for c in corners) for i in range(3)])
        high = Vector([max(c[i] for c in corners) for i in range(3)])

        control = bpy.data.objects.new("Disintegration Control", None)
        objects[0].users_collection[0].objects.link(control)
        control.empty_display_type = "SPHERE"
        control.location = (low + high) / 2
        control.MustardUI_tools_creators_is_created = True
        control.MustardUI_tools_creators_type = "EFFECT_DISINTEGRATION"
        # Margin for the irregular edge, which goes inside the sphere
        radius = (high - low).length / 2 * 1.25
        frame = context.scene.frame_current
        for f, scale in ((frame, 0.001), (frame + self.duration, radius)):
            control.scale = (scale, scale, scale)
            control.keyframe_insert("scale", frame=f)

        for obj in objects:
            modifier = obj.modifiers.new("Disintegration", "NODES")
            modifier.node_group = bpy.data.node_groups[NODE_GROUP]
            modifier_input(modifier, "Control").value = control
            modifier_input(modifier, "Material").value = bpy.data.materials[MATERIAL]

            # Before the subdivision, to cut the low poly mesh
            subdivision = next(
                (i for i, m in enumerate(obj.modifiers) if m.type in {"SUBSURF", "MULTIRES"}), None
            )
            if subdivision is not None:
                obj.modifiers.move(len(obj.modifiers) - 1, subdivision)

        self.report({"INFO"}, f"MustardUI - Disintegration added to {len(objects)} objects.")
        return {"FINISHED"}


class MustardUI_ModelToolkit_RemoveDisintegration(bpy.types.Operator):
    """Remove the Disintegration from the selected meshes, and the Controls not used anymore"""

    bl_idname = "mustardui.model_toolkit_remove_disintegration"
    bl_label = "Remove Disintegration"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        return active_object_operator_poll(context, config=ModelMode.MODEL_TOOLKIT) and any(
            is_disintegration(m) for x in context.selected_objects for m in x.modifiers
        )

    def execute(self, context):
        controls = set()
        for obj in context.selected_objects:
            for modifier in [m for m in obj.modifiers if is_disintegration(m)]:
                controls.add(modifier_input(modifier, "Control").value)
                obj.modifiers.remove(modifier)

        used = {
            modifier_input(m, "Control").value
            for x in bpy.data.objects
            for m in x.modifiers
            if is_disintegration(m)
        }
        for control in controls - used - {None}:
            if control.MustardUI_tools_creators_type == "EFFECT_DISINTEGRATION":
                bpy.data.objects.remove(control)

        self.report({"INFO"}, "MustardUI - Disintegration removed.")
        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_Disintegration)
    bpy.utils.register_class(MustardUI_ModelToolkit_RemoveDisintegration)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_RemoveDisintegration)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_Disintegration)
