import math
import os

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

from .effect import (
    RemoveEffect,
    add_effect_modifier,
    effects_available,
    is_effect,
    modifier_input,
    parent_control,
)

NODE_GROUP = "MustardUI Shrinkwrap"
# Version of the bundled node group, the VERSION of its build script
VERSION = 22
RESOURCE = os.path.join(os.path.dirname(__file__), "resources", "shrinkwrap.blend")
# Distances of the effect, in the space of the mesh
DISTANCES = ("Thickness", "Spread", "Stretch")


class MustardUI_ModelToolkit_Shrinkwrap(bpy.types.Operator):
    """Push the active mesh softly out of the other selected meshes, keeping its volume, e.g. lips around a cylinder, the contact dragged along as they slide. With Opening, the mesh in a Zone placed around the opening is moved out from it smoothly instead.\nMore objects can be added to the Colliders collection of the effect, and a Vertex Group can limit the parts pushed\nBlender 5.2 or above is required"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_shrinkwrap"
    bl_label = "Add Shrinkwrap"
    bl_options = {"REGISTER", "UNDO"}

    opening: bpy.props.BoolProperty(
        name="Opening",
        default=False,
        description="Move the mesh smoothly out from a Zone placed where the first Collider goes "
        "into it, e.g. the mouth, keeping each part on its side. The Zone is an Empty to move "
        "and scale if needed, and it can be toggled in the Opening panel of the modifier",
        options={"SKIP_SAVE"},
    )
    friction: bpy.props.BoolProperty(
        name="Friction",
        default=True,
        description="Contact dragged along by the Colliders sliding on the mesh, simulated from "
        "the current frame. It can be toggled later in the Friction panel of the modifier",
        options={"SKIP_SAVE"},
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return effects_available() and obj is not None and obj.type == "MESH"

    def execute(self, context):
        target = context.active_object
        colliders = [x for x in context.selected_objects if x.type == "MESH" and x != target]

        # Appended if not in the file or older than the bundled one
        old = bpy.data.node_groups.get(NODE_GROUP)
        if old is None or old.get("MustardUI Version", 1) < VERSION:
            with bpy.data.libraries.load(RESOURCE) as (_, data):
                data.node_groups = [NODE_GROUP]
            if old is not None:
                # The modifiers move to the new one, set one by one as user_remap does not
                # set up their simulations, crashing Blender
                for modifier in [m for x in bpy.data.objects for m in x.modifiers]:
                    if modifier.type == "NODES" and modifier.node_group == old:
                        modifier.node_group = data.node_groups[0]
                bpy.data.node_groups.remove(old)
                data.node_groups[0].name = NODE_GROUP

        zone = place_zone(context, target, colliders[0]) if self.opening and colliders else None

        # In the scene collection, out of the outfit collections not to be part of an outfit
        collection = bpy.data.collections.new(f"{target.name} Shrinkwrap Colliders")
        context.scene.collection.children.link(collection)
        for obj in colliders:
            collection.objects.link(obj)

        modifier = add_effect_modifier(target, "Shrinkwrap", NODE_GROUP)
        modifier_input(modifier, "Colliders").value = collection
        scale = max(max(target.matrix_world.to_scale()), 1e-6)
        for name in DISTANCES:
            modifier_input(modifier, name).value /= scale
        modifier_input(modifier, "Friction").value = self.friction
        modifier_input(modifier, "Start Frame").value = context.scene.frame_current
        if zone is not None:
            modifier_input(modifier, "Opening").value = True
            modifier_input(modifier, "Zone").value = zone
            # Settling without wobbling, the lips released by the Colliders
            modifier_input(modifier, "Damping").value = 1.0
        # Changing the modifier inputs from Python does not tag the object
        target.update_tag()

        if not colliders:
            self.report(
                {"WARNING"},
                "MustardUI - Shrinkwrap added, add the objects pushing the mesh to its Colliders.",
            )
            return {"FINISHED"}
        self.report({"INFO"}, f"MustardUI - Shrinkwrap of {len(colliders)} objects added.")
        return {"FINISHED"}


def place_zone(context, target, collider):
    """Empty where the long axis of the collider goes into the mesh, at the first narrowing of
    the mesh around it from the end out of the mesh, as large as twice and a half the collider
    is thick, following the bone deforming the mesh there"""
    sizes = list(collider.dimensions)
    along = sizes.index(max(sizes))
    axis = (collider.matrix_world.to_3x3() @ Matrix.Identity(3)[along]).normalized()
    center = collider.matrix_world @ (sum((Vector(c) for c in collider.bound_box), Vector()) / 8)
    thick = sorted(sizes)[1] / 2

    target.add_rest_position_attribute = True
    depsgraph = context.evaluated_depsgraph_get()
    mesh = target.evaluated_get(depsgraph).data
    points = [target.matrix_world @ v.co for v in mesh.vertices]
    tree = BVHTree.FromPolygons(points, [p.vertices[:] for p in mesh.polygons])

    # Mesh around the axis along the collider: rays hitting it and their mean distance
    side = axis.orthogonal().normalized()
    directions = [Matrix.Rotation(i * math.tau / 16, 3, axis) @ side for i in range(16)]
    samples = []
    for i in range(129):
        point = center + axis * (max(sizes) * (i / 128 - 0.5))
        hits = [h[3] for h in (tree.ray_cast(point, d) for d in directions) if h[0] is not None]
        samples.append((point, len(hits), sum(hits) / max(len(hits), 1)))
    # From the end out of the mesh, into the opening down to its narrowest part
    if samples[-1][1] < samples[0][1]:
        samples.reverse()
    neck, narrowest = [], math.inf
    for point, count, radius in samples if samples[0][1] < 12 else ():
        if count < 12 and not neck:
            continue
        if count < 12 or radius > narrowest * 1.05:
            break
        narrowest = min(narrowest, radius)
        neck.append((point, radius))
    neck = [p for p, r in neck if r <= narrowest * 1.05]
    if neck:
        entry = sum(neck, Vector()) / len(neck)
    else:
        entry = center + axis * axis.dot(tree.find_nearest(center)[0] - center)

    zone = bpy.data.objects.new(f"{target.name} Shrinkwrap Zone", None)
    target.users_collection[0].objects.link(zone)
    zone.empty_display_type = "CUBE"
    vertex = min(mesh.vertices, key=lambda v: (target.matrix_world @ v.co - entry).length_squared)
    parent_control(zone, target, vertex, depsgraph)
    zone.matrix_basis = Matrix.LocRotScale(
        entry, axis.to_track_quat("Z", "Y"), Vector((thick * 2.5, thick * 2.5, thick * 1.5))
    )
    return zone


def zone_of(modifier):
    """Zone of the Shrinkwrap modifier, None for other modifiers and older ones without it"""
    if (
        not is_effect(modifier, NODE_GROUP)
        or "Zone" not in modifier.node_group.interface.items_tree
    ):
        return None
    return modifier_input(modifier, "Zone").value


class MustardUI_ModelToolkit_RemoveShrinkwrap(RemoveEffect, bpy.types.Operator):
    """Remove the Shrinkwrap from the selected meshes, and the Colliders collections not used anymore"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_remove_shrinkwrap"
    bl_label = "Remove Shrinkwrap"

    effect = "Shrinkwrap"
    node_group = NODE_GROUP
    controls = False
    colliders = True

    def execute(self, context):
        zones = {zone_of(m) for x in context.selected_objects for m in x.modifiers}
        result = super().execute(context)
        # The Zones not used anymore
        used = {zone_of(m) for x in bpy.data.objects for m in x.modifiers}
        for zone in zones - used - {None}:
            bpy.data.objects.remove(zone)
        return result


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_Shrinkwrap)
    bpy.utils.register_class(MustardUI_ModelToolkit_RemoveShrinkwrap)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_RemoveShrinkwrap)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_Shrinkwrap)
