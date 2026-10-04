import math
import os

import bpy

from ...model_selection.active_object import ModelMode, active_object_operator_poll
from .effect import effects_available, is_effect, modifier_input

RESOURCE = os.path.join(os.path.dirname(__file__), "resources", "wrap.blend")


class AddWrap:
    """Base of the operators wrapping the selected curves, or a new loop, around the active mesh"""

    bl_options = {"REGISTER", "UNDO"}

    effect = ""
    node_group = ""
    creators_type = ""

    radius: bpy.props.FloatProperty(
        name="Radius",
        default=0.1,
        min=0.001,
        subtype="DISTANCE",
        description="Radius of the new loop, on the plane of the 3D cursor",
    )
    vertex_group: bpy.props.StringProperty(
        name="Vertex Group",
        description="Vertex Group of the active mesh to wrap around, set as the Mask. "
        "Empty to wrap around the whole mesh",
    )

    @classmethod
    def poll(cls, context):
        return (
            effects_available()
            and active_object_operator_poll(context, config=ModelMode.MODEL_TOOLKIT)
            and context.active_object is not None
            and context.active_object.type == "MESH"
        )

    def draw(self, context):
        self.layout.prop(self, "radius")
        self.layout.prop_search(self, "vertex_group", context.active_object, "vertex_groups")

    def execute(self, context):
        target = context.active_object

        # The node group and its material share the name
        with bpy.data.libraries.load(RESOURCE) as (_, data):
            if self.node_group not in bpy.data.node_groups:
                data.node_groups = [self.node_group]
            if self.node_group not in bpy.data.materials:
                data.materials = [self.node_group]

        curves = [x for x in context.selected_objects if x.type == "CURVE"]
        if not curves:
            curve = bpy.data.curves.new(self.effect, "CURVE")
            curve.dimensions = "3D"
            spline = curve.splines.new("BEZIER")
            spline.bezier_points.add(7)
            spline.use_cyclic_u = True
            for i, point in enumerate(spline.bezier_points):
                angle = i * math.pi / 4
                point.co = (self.radius * math.cos(angle), self.radius * math.sin(angle), 0.0)
                point.handle_left_type = point.handle_right_type = "AUTO"

            # Parented to the target, to move with the model
            loop = bpy.data.objects.new(f"{target.name} {self.effect}", curve)
            target.users_collection[0].objects.link(loop)
            loop.parent = target
            loop.matrix_parent_inverse = target.matrix_world.inverted()
            loop.matrix_basis = context.scene.cursor.matrix
            loop.MustardUI_tools_creators_is_created = True
            loop.MustardUI_tools_creators_type = self.creators_type
            curves = [loop]

        for curve in curves:
            modifier = curve.modifiers.new(self.effect, "NODES")
            modifier.node_group = bpy.data.node_groups[self.node_group]
            modifier_input(modifier, "Target").value = target
            modifier_input(modifier, "Material").value = bpy.data.materials[self.node_group]
            if self.vertex_group:
                mask = modifier_input(modifier, "Mask")
                mask.type = "ATTRIBUTE"
                mask.attribute_name = self.vertex_group

        self.report({"INFO"}, f"MustardUI - {self.effect} added to {len(curves)} curves.")
        return {"FINISHED"}


class RemoveWrap:
    """Base of the operators removing a wrap from the selected curves, and the curves it added"""

    bl_options = {"UNDO"}

    effect = ""
    node_group = ""
    creators_type = ""

    @classmethod
    def poll(cls, context):
        return active_object_operator_poll(context, config=ModelMode.MODEL_TOOLKIT) and any(
            is_effect(m, cls.node_group) for x in context.selected_objects for m in x.modifiers
        )

    def execute(self, context):
        for obj in context.selected_objects:
            for modifier in [m for m in obj.modifiers if is_effect(m, self.node_group)]:
                obj.modifiers.remove(modifier)
            if obj.MustardUI_tools_creators_type == self.creators_type:
                bpy.data.objects.remove(obj)

        self.report({"INFO"}, f"MustardUI - {self.effect} removed.")
        return {"FINISHED"}


class Rope:
    effect = "Rope"
    node_group = "MustardUI Rope"
    creators_type = "EFFECT_ROPE"


class Tape:
    effect = "Tape"
    node_group = "MustardUI Tape"
    creators_type = "EFFECT_TAPE"


class MustardUI_ModelToolkit_Rope(Rope, AddWrap, bpy.types.Operator):
    """Wrap the selected curves around the active mesh as tight ropes, or a new loop around the 3D cursor if no curve is selected\nBlender 5.2 or above is required"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_rope"
    bl_label = "Add Rope"


class MustardUI_ModelToolkit_RemoveRope(Rope, RemoveWrap, bpy.types.Operator):
    """Remove the Rope from the selected curves, and the curves it added"""

    bl_idname = "mustardui.model_toolkit_remove_rope"
    bl_label = "Remove Rope"


class MustardUI_ModelToolkit_Tape(Tape, AddWrap, bpy.types.Operator):
    """Wrap the selected curves around the active mesh as tight tapes, or a new loop around the 3D cursor if no curve is selected\nBlender 5.2 or above is required"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_tape"
    bl_label = "Add Tape"


class MustardUI_ModelToolkit_RemoveTape(Tape, RemoveWrap, bpy.types.Operator):
    """Remove the Tape from the selected curves, and the curves it added"""

    bl_idname = "mustardui.model_toolkit_remove_tape"
    bl_label = "Remove Tape"


classes = (
    MustardUI_ModelToolkit_Rope,
    MustardUI_ModelToolkit_RemoveRope,
    MustardUI_ModelToolkit_Tape,
    MustardUI_ModelToolkit_RemoveTape,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
