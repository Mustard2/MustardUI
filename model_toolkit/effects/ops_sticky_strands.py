import os

import bpy
from mathutils import Matrix
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

from ...model_selection.active_object import ModelMode, active_object_operator_poll
from .effect import RemoveEffect, effects_available, modifier_input, new_control

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
        return effects_available() and (
            active_object_operator_poll(context, config=ModelMode.MODEL_TOOLKIT)
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

        # Parented to the bone deforming the vertex the most, found from its rest position, or
        # to the mesh, for the Control to follow it. Not to the vertex, which would make a
        # dependency cycle with the strands
        rest = source.evaluated_get(depsgraph).data.attributes["rest_position"]
        rest = rest.data[vertex.index].vector
        kd = KDTree(len(source.data.vertices))
        for x in source.data.vertices:
            kd.insert(x.co, x.index)
        kd.balance()
        armature = next(
            (m.object for m in source.modifiers if m.type == "ARMATURE" and m.object), None
        )
        bones = armature.pose.bones if armature else {}
        group = max(
            (
                x
                for x in source.data.vertices[kd.find(rest)[1]].groups
                if source.vertex_groups[x.group].name in bones
            ),
            key=lambda x: x.weight,
            default=None,
        )
        control, _, _ = new_control(objects, "Sticky Strands", CONTROL_TYPE)
        if group:
            bone = bones[source.vertex_groups[group.group].name]
            control.parent = armature
            control.parent_type = "BONE"
            control.parent_bone = bone.name
            # The bone parent matrix is at its tail
            parent = armature.matrix_world @ bone.matrix
            parent.translation = armature.matrix_world @ bone.tail
        else:
            control.parent = source
            parent = source.matrix_world
        control.matrix_parent_inverse = parent.inverted()
        control.matrix_basis = Matrix.LocRotScale(location, None, (self.radius,) * 3)

        for obj in objects:
            # Last, for the strands not to be subdivided
            modifier = obj.modifiers.new("Sticky Strands", "NODES")
            modifier.node_group = bpy.data.node_groups[NODE_GROUP]
            modifier_input(modifier, "Control").value = control
            modifier_input(modifier, "Material").value = bpy.data.materials[MATERIAL]
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


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_StickyStrands)
    bpy.utils.register_class(MustardUI_ModelToolkit_RemoveStickyStrands)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_RemoveStickyStrands)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_StickyStrands)
