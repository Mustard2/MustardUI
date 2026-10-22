import os

import bpy
from mathutils import Matrix
from mathutils.bvhtree import BVHTree

from .effect import (
    RemoveEffect,
    effects_available,
    is_effect,
    modifier_input,
    new_control,
    parent_control,
)

NODE_GROUP = "MustardUI Sticky Strands"
MATERIAL = "MustardUI Sticky Strands"
CONTROL_TYPE = "EFFECT_STICKY_STRANDS"
RESOURCE = os.path.join(os.path.dirname(__file__), "resources", "sticky_strands.blend")


class MustardUI_ModelToolkit_StickyStrands(bpy.types.Operator):
    """Add simulated strands of saliva or goo from the selected meshes to the active one, starting inside the sphere of a Control Empty where the selected meshes are closest to the active one.\nWith only one mesh, the strands connect it to itself, from the Start to the End Vertex Group, with the Control at the 3D cursor\nBlender 5.2 or above is required"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_sticky_strands"
    bl_label = "Add Sticky Strands"
    bl_options = {"REGISTER", "UNDO"}

    radius: bpy.props.FloatProperty(
        name="Radius",
        default=0.05,
        min=0.001,
        subtype="DISTANCE",
        description="Radius of the Control sphere",
    )

    @classmethod
    def poll(cls, context):
        return (
            effects_available()
            and context.active_object is not None
            and context.active_object.type == "MESH"
        )

    def execute(self, context):
        target = context.active_object
        objects = [x for x in context.selected_objects if x.type == "MESH" and x != target]
        objects = objects or [target]

        # On the active mesh if the selected one is a collider, as physics colliding with it
        # (e.g. cloth deforming the active mesh) would make a dependency cycle with the strands
        colliders = [any(m.type == "COLLISION" for m in x.modifiers) for x in (*objects, target)]
        if colliders == [True, False]:
            objects, target = [target], objects[0]

        with bpy.data.libraries.load(RESOURCE) as (_, data):
            if NODE_GROUP not in bpy.data.node_groups:
                data.node_groups = [NODE_GROUP]
            if MATERIAL not in bpy.data.materials:
                data.materials = [MATERIAL]

        # The strand ends follow the deformed meshes from their rest position
        for obj in {target, *objects}:
            obj.add_rest_position_attribute = True
        depsgraph = context.evaluated_depsgraph_get()

        # The Control on the vertex of the selected meshes closest to the active one, or to the
        # 3D cursor with one mesh
        if target in objects:
            source = target
            cursor = source.matrix_world.inverted() @ context.scene.cursor.location
            vertices = source.evaluated_get(depsgraph).data.vertices
            vertex = min(vertices, key=lambda x: (x.co - cursor).length_squared)
        else:
            tree = BVHTree.FromObject(target, depsgraph)
            closest = None
            for obj in objects:
                matrix = target.matrix_world.inverted() @ obj.matrix_world
                for x in obj.evaluated_get(depsgraph).data.vertices:
                    distance = tree.find_nearest(matrix @ x.co)[3]
                    if closest is None or distance < closest[0]:
                        closest = (distance, obj, x)
            _, source, vertex = closest
        location = source.matrix_world @ vertex.co

        # Not parented to the vertex, which would make a dependency cycle with the strands
        control, _, _ = new_control(objects, "Sticky Strands", CONTROL_TYPE)
        parent_control(control, source, vertex, depsgraph)
        control.matrix_basis = Matrix.LocRotScale(location, None, (self.radius,) * 3)

        for obj in objects:
            # Last, for the strands not to be subdivided
            modifier = obj.modifiers.new("Sticky Strands", "NODES")
            modifier.node_group = bpy.data.node_groups[NODE_GROUP]
            modifier_input(modifier, "Control").value = control
            modifier_input(modifier, "Material").value = bpy.data.materials[MATERIAL]
            modifier_input(modifier, "Start Frame").value = context.scene.frame_start
            if obj != target:
                modifier_input(modifier, "Target").value = target

        self.report({"INFO"}, f"MustardUI - Sticky Strands added to {len(objects)} objects.")
        return {"FINISHED"}


class MustardUI_ModelToolkit_RemoveStickyStrands(RemoveEffect, bpy.types.Operator):
    """Remove the Sticky Strands from the selected meshes, and the Controls not used anymore"""

    bl_idname = "mustardui.model_toolkit_remove_sticky_strands"
    bl_label = "Remove Sticky Strands"

    effect = "Sticky Strands"
    node_group = NODE_GROUP
    creators_type = CONTROL_TYPE


class MustardUI_ModelToolkit_ConvertStickyStrands(RemoveEffect, bpy.types.Operator):
    """Convert the Sticky Strands of the selected meshes at the current frame to new meshes parented to them, removing the modifiers and the Controls not used anymore"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_convert_sticky_strands"
    bl_label = "Convert Sticky Strands to Mesh"

    effect = "Sticky Strands"
    node_group = NODE_GROUP
    creators_type = CONTROL_TYPE
    done = "converted to meshes"

    def execute(self, context):
        # The strands are an instance, which applying the modifier would discard
        depsgraph = context.evaluated_depsgraph_get()
        for obj in context.selected_objects:
            if not any(is_effect(m, NODE_GROUP) for m in obj.modifiers):
                continue
            geometry = obj.evaluated_get(depsgraph).evaluated_geometry()
            for reference in geometry.instance_references():
                if reference.mesh and "sticky_factor" in reference.mesh.attributes:
                    mesh = reference.mesh.copy()
                    mesh.name = f"{obj.name} Sticky Strands"
                    strands = bpy.data.objects.new(mesh.name, mesh)
                    obj.users_collection[0].objects.link(strands)
                    strands.parent = obj
        return super().execute(context)


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_StickyStrands)
    bpy.utils.register_class(MustardUI_ModelToolkit_RemoveStickyStrands)
    bpy.utils.register_class(MustardUI_ModelToolkit_ConvertStickyStrands)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_ConvertStickyStrands)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_RemoveStickyStrands)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_StickyStrands)
