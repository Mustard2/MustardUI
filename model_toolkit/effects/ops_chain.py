import os
import re

import bmesh
import bpy
from mathutils import Matrix, Vector

from ...model_selection.active_object import ModelMode, mustardui_active_object
from .effect import (
    effects_available,
    is_effect,
    load_node_group,
    modifier_input,
    parent_control,
    parent_to_bone,
)

NODE_GROUP = "MustardUI Chain"
# Version of the bundled node group, the VERSION of its build script
VERSION = 4
ANCHOR_TYPE = "EFFECT_CHAIN_ANCHOR"
RESOURCE = os.path.join(os.path.dirname(__file__), "resources", "chain.blend")
# Length of a chain from one Anchor, in m
HANGING = 0.5


class MustardUI_ModelToolkit_Chain(bpy.types.Operator):
    """Add a chain hanging with the gravity and attached to Anchor Empties, keeping its length.\nAttached to the selected vertices in Edit Mode, the selected bones in Pose Mode, or the selected Empties. Without them it hangs from the 3D cursor, following the selected mesh if any, its tip moved by a Tip Control Empty.\nThe chain goes through the Anchors in the order of their names: duplicate one to add another right after it, and parent them to what they follow\nBlender 5.2 or above is required"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_chain"
    bl_label = "Add Chain"
    bl_options = {"REGISTER", "UNDO"}

    slack: bpy.props.FloatProperty(
        name="Slack",
        default=0.2,
        min=0.0,
        soft_max=2.0,
        subtype="FACTOR",
        description="How much longer than the way through the Anchors the chain is",
    )
    free_length: bpy.props.FloatProperty(
        name="Free Length",
        default=0.0,
        min=0.0,
        soft_max=5.0,
        subtype="DISTANCE",
        description="Length of the chain after the last Anchor, moved by a Tip Control Empty",
    )
    hold_tip: bpy.props.BoolProperty(
        name="Hold Tip",
        default=True,
        description="Keep the tip of the Free Length at the Tip Control, moving it with the "
        "Empty, otherwise it hangs loose. It can be changed and keyframed with the Hold input",
    )
    collide: bpy.props.BoolProperty(
        name="Collide",
        default=True,
        description="Collide with the selected meshes, or the model body. More objects can be "
        "added to the Colliders collection of the effect",
    )

    @classmethod
    def poll(cls, context):
        return effects_available()

    def execute(self, context):
        scene = context.scene
        vertices, bones, empties = {}, [], []
        if context.mode == "EDIT_MESH":
            for obj in context.objects_in_mode:
                selected = [x.index for x in bmesh.from_edit_mesh(obj.data).verts if x.select]
                if selected:
                    vertices[obj] = selected
        elif context.mode == "POSE":
            bones = list(context.selected_pose_bones or ())
        else:
            empties = [x for x in context.selected_objects if x.type == "EMPTY"]
        meshes = [x for x in context.selected_objects if x.type == "MESH"]
        armature = context.active_object if bones else None
        res, arm = mustardui_active_object(context, config=ModelMode.MODEL_TOOLKIT)
        if context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        load_node_group(RESOURCE, NODE_GROUP, VERSION)
        if NODE_GROUP not in bpy.data.materials:
            with bpy.data.libraries.load(RESOURCE) as (_, data):
                data.materials = [NODE_GROUP]

        chain = bpy.data.objects.new("Chain", bpy.data.meshes.new("Chain"))
        # In the scene collection, out of the outfit collections not to be part of an outfit
        collection = bpy.data.collections.new(chain.name)
        scene.collection.children.link(collection)
        collection.objects.link(chain)
        anchors = bpy.data.collections.new(f"{chain.name} Anchors")
        colliders = bpy.data.collections.new(f"{chain.name} Colliders")
        collection.children.link(anchors)
        collection.children.link(colliders)
        # In the space of the object, which has to stay at the origin for the gravity to point down
        chain.lock_location = chain.lock_rotation = chain.lock_scale = (True, True, True)

        def new_anchor():
            anchor = bpy.data.objects.new("Chain Anchor", None)
            anchors.objects.link(anchor)
            anchor.empty_display_type = "SPHERE"
            anchor.empty_display_size = 0.02
            anchor.MustardUI_tools_creators_is_created = True
            anchor.MustardUI_tools_creators_type = ANCHOR_TYPE
            return anchor

        created = []
        for obj, selected in vertices.items():
            for index in selected:
                anchor = new_anchor()
                anchor.parent = obj
                anchor.parent_type = "VERTEX"
                anchor.parent_vertices = (index, 0, 0)
                created.append(anchor)
        for bone in bones:
            anchor = new_anchor()
            parent_to_bone(anchor, armature, bone)
            anchor.matrix_basis = Matrix.Translation(armature.matrix_world @ bone.head)
            created.append(anchor)
        if not (created or empties):
            anchor = new_anchor()
            cursor = scene.cursor.location
            if meshes:
                # Following the closest mesh, at the closest vertex
                meshes[0].add_rest_position_attribute = True
                depsgraph = context.evaluated_depsgraph_get()
                local = meshes[0].matrix_world.inverted() @ cursor
                vertex = min(
                    meshes[0].evaluated_get(depsgraph).data.vertices,
                    key=lambda x: (x.co - local).length_squared,
                    default=None,
                )
                if vertex is not None:
                    parent_control(anchor, meshes[0], vertex, depsgraph)
            anchor.matrix_basis = Matrix.Translation(cursor)
            created.append(anchor)

        # The created Anchors named along the shortest way through them, from an end
        context.view_layer.update()
        points = {x: x.matrix_world.translation.copy() for x in created}
        if points:
            middle = sum(points.values(), Vector()) / len(points)
            current = max(points, key=lambda x: (points[x] - middle).length_squared)
            for i in range(len(points)):
                current.name = f"{chain.name} Anchor {i + 1}"
                position = points.pop(current)
                created[i] = current
                if points:
                    current = min(points, key=lambda x: (points[x] - position).length_squared)

        # As the Collection Info node sorts them, with the numbers by their values
        for empty in empties:
            anchors.objects.link(empty)
        ordered = sorted(
            created + empties,
            key=lambda x: [
                int(p) if p.isdigit() else p for p in re.split(r"(\d+)", x.name.lower())
            ],
        )
        path = [x.matrix_world.translation for x in ordered]
        length = sum((a - b).length for a, b in zip(path, path[1:], strict=False))

        collide = list(vertices) or meshes
        if not collide and res and arm.MustardUI_RigSettings.model_body is not None:
            collide = [arm.MustardUI_RigSettings.model_body]
        for obj in collide if self.collide else ():
            colliders.objects.link(obj)

        modifier = chain.modifiers.new("Chain", "NODES")
        modifier.node_group = bpy.data.node_groups[NODE_GROUP]
        modifier_input(modifier, "Anchors").value = anchors
        modifier_input(modifier, "Colliders").value = colliders
        # Blender 5.2.0 does not set the material inputs to their defaults
        modifier_input(modifier, "Material").value = bpy.data.materials[NODE_GROUP]
        modifier_input(modifier, "Start Frame").value = scene.frame_start
        free_length = self.free_length
        if len(ordered) > 1:
            modifier_input(modifier, "Length").value = length * (1.0 + self.slack)
        else:
            modifier_input(modifier, "Length").value = HANGING
            free_length = free_length or HANGING
        modifier_input(modifier, "Free Length").value = free_length
        if free_length:
            tip = bpy.data.objects.new(f"{chain.name} Tip", None)
            collection.objects.link(tip)
            tip.empty_display_type = "CUBE"
            tip.empty_display_size = 0.02
            tip.MustardUI_tools_creators_is_created = True
            tip.MustardUI_tools_creators_type = ANCHOR_TYPE
            tip.location = path[-1] - Vector((0.0, 0.0, free_length))
            modifier_input(modifier, "Tip Control").value = tip
            modifier_input(modifier, "Hold").value = 1.0 if self.hold_tip else 0.0
        chain.update_tag()

        for obj in context.selected_objects:
            obj.select_set(False)
        chain.select_set(True)
        context.view_layer.objects.active = chain

        self.report({"INFO"}, f"MustardUI - Chain through {len(ordered)} Anchors added.")
        return {"FINISHED"}


class MustardUI_ModelToolkit_RemoveChain(bpy.types.Operator):
    """Remove the selected chains, with the Anchors and Tip Controls added with them"""

    bl_idname = "mustardui.model_toolkit_remove_chain"
    bl_label = "Remove Chain"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        return any(is_effect(m, NODE_GROUP) for x in context.selected_objects for m in x.modifiers)

    def execute(self, context):
        scene = context.scene
        for chain in [
            x
            for x in context.selected_objects
            if any(is_effect(m, NODE_GROUP) for m in x.modifiers)
        ]:
            modifier = next(m for m in chain.modifiers if is_effect(m, NODE_GROUP))
            inputs = [modifier_input(modifier, x).value for x in ("Anchors", "Colliders")]
            # Not in the first version of the node group
            tip = (
                modifier_input(modifier, "Tip Control").value
                if "Tip Control" in modifier.node_group.interface.items_tree
                else None
            )
            parent = chain.users_collection[0]
            bpy.data.objects.remove(chain)
            if tip is not None and tip.MustardUI_tools_creators_type == ANCHOR_TYPE:
                bpy.data.objects.remove(tip)
            for collection in filter(None, inputs):
                for obj in list(collection.objects):
                    if obj.MustardUI_tools_creators_type == ANCHOR_TYPE:
                        bpy.data.objects.remove(obj)
                    elif len(obj.users_collection) == 1:
                        # The objects only in the collection kept in the scene
                        scene.collection.objects.link(obj)
                bpy.data.collections.remove(collection)
            # Its collection, unless it was moved somewhere used
            if not (parent == scene.collection or parent.objects or parent.children):
                bpy.data.collections.remove(parent)
        self.report({"INFO"}, "MustardUI - Chain removed.")
        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_Chain)
    bpy.utils.register_class(MustardUI_ModelToolkit_RemoveChain)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_RemoveChain)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_Chain)
