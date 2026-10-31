import os

import bpy
from mathutils import Matrix, Vector

from .effect import (
    RemoveEffect,
    add_effect_modifier,
    effects_available,
    is_effect,
    materials,
    modifier_input,
    new_control,
    parent_control,
    shader_nodes,
    tint,
    untint,
)

NODE_GROUP = "MustardUI Marks"
TINT = "MustardUI Marks Tint"
CONTROL_TYPE = "EFFECT_MARKS"
RESOURCE = os.path.join(os.path.dirname(__file__), "resources", "marks.blend")
# Radius and modifier inputs of each kind of mark
PRESETS = {
    "BLUSH": (
        0.04,
        {"Color": (1.0, 0.45, 0.45, 1.0), "Strength": 0.6, "Falloff": 1.0, "Blotches": 0.3},
    ),
    "HAND": (
        0.1,
        {"Hand": True, "Color": (1.0, 0.35, 0.33, 1.0), "Strength": 0.8, "Blotches": 0.3},
    ),
    "BRUISE": (
        0.025,
        {"Color": (0.55, 0.3, 0.45, 1.0), "Strength": 0.8, "Falloff": 0.7, "Blotches": 0.5},
    ),
    "DIRT": (
        0.08,
        {
            "Color": (0.35, 0.27, 0.2, 1.0),
            "Strength": 1.0,
            "Falloff": 0.6,
            "Blotches": 0.6,
            "Blotch Scale": 40.0,
        },
    ),
}


class MustardUI_ModelToolkit_Marks(bpy.types.Operator):
    """Mark the selected meshes inside the sphere of a Control Empty, on their vertex closest to the 3D cursor, tinting the base color of their materials.\nThe marks show only on the meshes with the effect\nBlender 5.2 or above is required"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_marks"
    bl_label = "Add Marks"
    bl_options = {"REGISTER", "UNDO"}

    def update_kind(self, context):
        self.radius = PRESETS[self.kind][0]

    kind: bpy.props.EnumProperty(
        name="Kind",
        items=(
            ("BLUSH", "Blush", "Soft redness, as on the cheeks"),
            ("HAND", "Hand Print", "Red print of a hand, fingers up"),
            ("BRUISE", "Bruise", "Small purple blotchy mark"),
            ("DIRT", "Dirt", "Brown blotchy smudge"),
        ),
        update=update_kind,
    )
    radius: bpy.props.FloatProperty(
        name="Radius",
        default=PRESETS["BLUSH"][0],
        min=0.001,
        subtype="DISTANCE",
        description="Radius of the Control sphere",
    )
    left: bpy.props.BoolProperty(
        name="Left Hand",
        description="Print a left hand, mirroring the Control along its X axis",
    )

    @classmethod
    def poll(cls, context):
        return effects_available() and any(x.type == "MESH" for x in context.selected_objects)

    def draw(self, context):
        self.layout.prop(self, "kind")
        self.layout.prop(self, "radius")
        if self.kind == "HAND":
            self.layout.prop(self, "left")

    def execute(self, context):
        objects = [x for x in context.selected_objects if x.type == "MESH"]

        with bpy.data.libraries.load(RESOURCE) as (_, data):
            data.node_groups = [x for x in (NODE_GROUP, TINT) if x not in bpy.data.node_groups]

        # The blotches placed on the rest mesh, not to move on the deformed one
        for obj in objects:
            obj.add_rest_position_attribute = True
        depsgraph = context.evaluated_depsgraph_get()

        # On the vertex closest to the 3D cursor, facing out of the mesh, Y up along it
        cursor = context.scene.cursor.location
        source, vertex = min(
            ((x, v) for x in objects for v in x.evaluated_get(depsgraph).data.vertices),
            key=lambda p: (p[0].matrix_world @ p[1].co - cursor).length_squared,
        )
        normal = (source.matrix_world.to_3x3() @ vertex.normal).normalized()
        up = Vector((0.0, 0.0, 1.0))
        if abs(normal.dot(up)) > 0.99:
            up = Vector((0.0, 1.0, 0.0))
        y = (up - normal * normal.dot(up)).normalized()
        rotation = Matrix((y.cross(normal), y, normal)).transposed().to_4x4()
        mirror = -1.0 if self.left and self.kind == "HAND" else 1.0
        control, _, _ = new_control(objects, "Marks", CONTROL_TYPE)
        parent_control(control, source, vertex, depsgraph)
        control.matrix_basis = (
            Matrix.Translation(source.matrix_world @ vertex.co)
            @ rotation
            @ Matrix.Diagonal((self.radius * mirror, self.radius, self.radius, 1.0))
        )
        # In the scene collection, not to be listed only under its bone parent in the Outliner
        control.users_collection[0].objects.unlink(control)
        context.scene.collection.objects.link(control)

        for obj in objects:
            modifier = add_effect_modifier(obj, "Marks", NODE_GROUP, control)
            for name, value in PRESETS[self.kind][1].items():
                modifier_input(modifier, name).value = value
            modifier_input(modifier, "Start Frame").value = context.scene.frame_current
            # Changing the modifier inputs from Python does not tag the object
            obj.update_tag()
        for material in materials(objects):
            if not shader_nodes(material, TINT):
                tint(material, TINT)

        # The Control selected, to be moved or scaled right away
        for obj in objects:
            obj.select_set(False)
        control.select_set(True)
        context.view_layer.objects.active = control

        self.report({"INFO"}, f"MustardUI - Marks added to {len(objects)} objects.")
        return {"FINISHED"}


class MustardUI_ModelToolkit_RemoveMarks(RemoveEffect, bpy.types.Operator):
    """Remove the Marks from the selected meshes, the tint from their materials not used by other marked meshes, and the Controls not used anymore"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_remove_marks"
    bl_label = "Remove Marks"

    effect = "Marks"
    node_group = NODE_GROUP
    creators_type = CONTROL_TYPE

    def execute(self, context):
        result = super().execute(context)
        marked = materials(
            x for x in bpy.data.objects if any(is_effect(m, NODE_GROUP) for m in x.modifiers)
        )
        for material in materials(context.selected_objects) - marked:
            for group in shader_nodes(material, TINT):
                untint(material, group)
        return result


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_Marks)
    bpy.utils.register_class(MustardUI_ModelToolkit_RemoveMarks)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_RemoveMarks)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_Marks)
