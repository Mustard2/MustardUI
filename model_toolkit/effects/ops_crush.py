import math
import os

import bpy
import numpy as np
from mathutils import Vector

from ...model_selection.active_object import ModelMode, mustardui_active_object
from .effect import (
    add_effect_modifier,
    effects_available,
    is_effect,
    modifier_input,
    remove_with_colliders,
)

NODE_GROUP = "MustardUI Crush"
RESOURCE = os.path.join(os.path.dirname(__file__), "resources", "crush.blend")
# Edge length the Subdivisions aim at, as a share of the size of the mesh, and faces they do not
# go past
EDGE_LENGTH = 0.01
MAX_FACES = 200000

# Modifier inputs of each material, the distances as a share of the size of the mesh, the Flat
# Height of its height
PRESETS = {
    "METAL": {
        "Stiffness": 0.3,
        "Flat Height": 0.1,
        "Bulge": 0.0,
        "Crumple": 0.0,
        "Crumple Size": 0.04,
        "Buckle": 0.8,
    },
    "CARDBOARD": {
        "Stiffness": 0.15,
        "Flat Height": 0.06,
        "Bulge": 0.4,
        "Crumple": 0.5,
        "Crumple Size": 0.08,
        "Buckle": 0.6,
    },
    "CLAY": {
        "Stiffness": 0.1,
        "Flat Height": 0.2,
        "Bulge": 1.0,
        "Crumple": 0.0,
        "Crumple Size": 0.05,
        "Buckle": 0.0,
    },
    # Floors of 3 m, whatever its size
    "BUILDING": {
        "Stiffness": 0.02,
        "Flat Height": 0.03,
        "Floor Height": 3.0,
        "Bulge": 0.5,
        "Crumple": 0.3,
        "Crumple Size": 0.01,
        "Buckle": 0.0,
        "Debris": True,
    },
}
DISTANCES = {"Stiffness", "Crumple Size"}
# Size of the largest loose parts thrown by chance, and their speed in sizes per second, as a share
# of the size of the mesh
PART_SIZE = 0.15
SPEED = 1.0
# Size and speed of the debris chips as shares of the size of the mesh, and about how many there
# are once all of it is crushed
DEBRIS_SIZE = 0.01
DEBRIS_SPEED = 0.1
DEBRIS_CHIPS = 1000


class MustardUI_ModelToolkit_Crush(bpy.types.Operator):
    """Crush the active mesh where the other selected meshes, or the model body, press it down, flattening it on the plane under it and keeping it crushed, as a car stepped on.\nMore objects can be added to the Colliders collection of the effect\nBlender 5.2 or above is required"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_crush"
    bl_label = "Add Crush"
    bl_options = {"REGISTER", "UNDO"}

    kind: bpy.props.EnumProperty(
        name="Material",
        items=(
            ("METAL", "Metal", "Stiff, buckling at a few creases around the Colliders"),
            ("CARDBOARD", "Cardboard", "Large folds and bulging sides"),
            ("CLAY", "Clay", "Smooth, squashed and spreading out to the sides"),
            (
                "BUILDING",
                "Building",
                "Floors of 3 m crushed one after the other from the top, throwing debris",
            ),
        ),
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return effects_available() and obj is not None and obj.type == "MESH"

    def execute(self, context):
        target = context.active_object
        colliders = [x for x in context.selected_objects if x.type == "MESH" and x != target]
        if not colliders:
            res, arm = mustardui_active_object(context, config=ModelMode.MODEL_TOOLKIT)
            body = arm.MustardUI_RigSettings.model_body if res else None
            colliders = [body] if body is not None and body != target else []

        # A copy left by a removed Crush replaced, it could be of an older version
        group = bpy.data.node_groups.get(NODE_GROUP)
        if group is not None and not group.users:
            bpy.data.node_groups.remove(group)
        with bpy.data.libraries.load(RESOURCE) as (_, data):
            if NODE_GROUP not in bpy.data.node_groups:
                data.node_groups = [NODE_GROUP]

        # In the scene collection, out of the outfit collections not to be part of an outfit
        collection = bpy.data.collections.new(f"{target.name} Crush Colliders")
        context.scene.collection.children.link(collection)
        for obj in colliders:
            collection.objects.link(obj)

        corners = [target.matrix_world @ Vector(x) for x in target.bound_box]
        extent = Vector(map(max, *corners)) - Vector(map(min, *corners))
        size = extent.length
        # Subdivided for the longest edges to reach the edge length, without too many faces, as
        # the mesh is after its modifiers, e.g. other effects already subdividing it
        mesh = target.evaluated_get(context.evaluated_depsgraph_get()).data
        co = np.empty(len(mesh.vertices) * 3)
        mesh.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3) @ np.array(target.matrix_world.to_3x3()).T
        edges = np.empty(len(mesh.edges) * 2, dtype=np.int32)
        mesh.edges.foreach_get("vertices", edges)
        edges = edges.reshape(-1, 2)
        length = np.linalg.norm(co[edges[:, 0]] - co[edges[:, 1]], axis=1).max(initial=0.0)
        levels = min(
            math.ceil(math.log2(max(length / max(EDGE_LENGTH * size, 1e-6), 1.0))),
            int(math.log(max(MAX_FACES / max(len(mesh.polygons), 1), 1.0), 4)),
            8,
        )

        modifier = add_effect_modifier(target, "Crush", NODE_GROUP)
        modifier_input(modifier, "Colliders").value = collection
        for name, value in PRESETS[self.kind].items():
            modifier_input(modifier, name).value = value * size if name in DISTANCES else value
        modifier_input(modifier, "Flat Height").value *= extent.z
        modifier_input(modifier, "Part Size").value = PART_SIZE * size
        modifier_input(modifier, "Speed").value = SPEED * size
        modifier_input(modifier, "Debris Size").value = DEBRIS_SIZE * size
        modifier_input(modifier, "Debris Speed").value = DEBRIS_SPEED * size
        modifier_input(modifier, "Debris Amount").value = DEBRIS_CHIPS / max(size * size, 1e-6)
        modifier_input(modifier, "Start Frame").value = context.scene.frame_current
        modifier_input(modifier, "Subdivisions").value = levels
        # Changing the modifier inputs from Python does not tag the object
        target.update_tag()

        if not colliders:
            self.report(
                {"WARNING"},
                "MustardUI - Crush added, add the objects crushing it to its Colliders.",
            )
            return {"FINISHED"}
        self.report({"INFO"}, f"MustardUI - Crush by {len(colliders)} objects added.")
        return {"FINISHED"}


class MustardUI_ModelToolkit_RemoveCrush(bpy.types.Operator):
    """Remove the Crush from the selected meshes, and the Colliders collections not used anymore"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_remove_crush"
    bl_label = "Remove Crush"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        return any(is_effect(m, NODE_GROUP) for x in context.selected_objects for m in x.modifiers)

    def execute(self, context):
        remove_with_colliders(context, NODE_GROUP)
        self.report({"INFO"}, "MustardUI - Crush removed.")
        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_Crush)
    bpy.utils.register_class(MustardUI_ModelToolkit_RemoveCrush)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_RemoveCrush)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_Crush)
