import math
import os

import bpy
from mathutils import Vector

from ...model_selection.active_object import ModelMode, mustardui_active_object
from .effect import (
    add_effect_modifier,
    colliders_scale,
    effects_available,
    is_effect,
    materials,
    modifier_input,
    remove_with_colliders,
    shader_nodes,
    tint,
    untint,
)

NODE_GROUP = "MustardUI Imprints"
TINT = "MustardUI Imprints Tint"
RESOURCE = os.path.join(os.path.dirname(__file__), "resources", "imprints.blend")
# Edge length the Subdivisions aim at, and faces they do not go past
EDGE_LENGTH = 0.015
MAX_FACES = 250000

# Modifier inputs of each kind of ground
PRESETS = {
    "SNOW": {
        "Depth": 0.08,
        "Rim": 0.3,
        "Rim Width": 0.03,
        "Noise": 0.3,
        "Color": (0.82, 0.88, 1.0, 1.0),
        "Detail": 0.3,
        "Detail Scale": 60.0,
        "Recovery": 0.0,
    },
    "SAND": {
        "Depth": 0.04,
        "Rim": 0.8,
        "Rim Width": 0.03,
        "Noise": 0.4,
        "Noise Scale": 50.0,
        "Color": (0.85, 0.8, 0.74, 1.0),
        "Detail": 0.4,
        "Detail Scale": 300.0,
        "Recovery": 0.0,
    },
    "MUD": {
        "Depth": 0.06,
        "Rim": 1.0,
        "Rim Width": 0.04,
        "Noise": 0.2,
        "Color": (0.7, 0.65, 0.6, 1.0),
        "Detail": 0.5,
        "Detail Scale": 80.0,
        "Recovery": 0.0,
    },
    "ASPHALT": {
        "Depth": 0.03,
        "Rim": 1.5,
        "Rim Width": 0.06,
        "Noise": 0.15,
        "Noise Scale": 25.0,
        "Color": (0.6, 0.6, 0.6, 1.0),
        "Detail": 0.5,
        "Detail Scale": 200.0,
        "Recovery": 0.0,
        "Cracks": True,
        "Crack Width": 0.012,
        "Chunks": True,
        "Debris": True,
    },
    "CUSHION": {
        "Depth": 0.1,
        "Smooth": 0,
        "Softness": 0.12,
        "Rim": 0.0,
        "Noise": 0.0,
        "Color": (1.0, 1.0, 1.0, 1.0),
        "Detail": 0.0,
        "Recovery": 2.0,
    },
}

# Powers of the scale of Colliders larger than a person the inputs are multiplied by: the distances
# by it, as many bumps, cracks and chunks for imprints that large
SCALING = {
    "Depth": 1,
    "Rim Width": 1,
    "Softness": 1,
    "Crack Length": 1,
    "Crack Width": 1,
    "Slab Size": 1,
    "Thickness": 1,
    "Debris Size": 1,
    "Noise Scale": -1,
    "Detail Scale": -1,
    "Crack Amount": -1,
    "Debris Amount": -2,
}


class MustardUI_ModelToolkit_Imprints(bpy.types.Operator):
    """Imprint the other selected meshes, or the model body, in the active mesh, as in snow, sand, mud, asphalt or a cushion, keeping the imprints where they pass.\nMore objects can be added to the Colliders collection of the effect\nBlender 5.2 or above is required"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_imprints"
    bl_label = "Add Imprints"
    bl_options = {"REGISTER", "UNDO"}

    kind: bpy.props.EnumProperty(
        name="Ground",
        items=(
            ("SNOW", "Snow", "Deep imprints with a small rim, lasting"),
            ("SAND", "Sand", "Shallow grainy imprints with a rim, lasting"),
            ("MUD", "Mud", "Dark imprints with a high rim, lasting"),
            ("ASPHALT", "Asphalt", "Shallow imprints breaking the surface into chunks, lasting"),
            ("CUSHION", "Cushion", "Soft surface wrapping around the Colliders, filling back"),
        ),
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return effects_available() and obj is not None and obj.type == "MESH"

    def execute(self, context):
        ground = context.active_object
        colliders = [x for x in context.selected_objects if x.type == "MESH" and x != ground]
        if not colliders:
            res, arm = mustardui_active_object(context, config=ModelMode.MODEL_TOOLKIT)
            body = arm.MustardUI_RigSettings.model_body if res else None
            colliders = [body] if body is not None and body != ground else []

        with bpy.data.libraries.load(RESOURCE) as (_, data):
            data.node_groups = [x for x in (NODE_GROUP, TINT) if x not in bpy.data.node_groups]

        # In the scene collection, out of the outfit collections not to be part of an outfit
        collection = bpy.data.collections.new(f"{ground.name} Imprint Colliders")
        context.scene.collection.children.link(collection)
        for obj in colliders:
            collection.objects.link(obj)

        modifier = add_effect_modifier(ground, "Imprints", NODE_GROUP)
        modifier_input(modifier, "Colliders").value = collection
        for name, value in PRESETS[self.kind].items():
            modifier_input(modifier, name).value = value
        scale = colliders_scale(colliders)
        for name, power in SCALING.items():
            modifier_input(modifier, name).value *= scale**power
        modifier_input(modifier, "Start Frame").value = context.scene.frame_current
        # Subdivided for the longest edges to reach the edge length, without too many faces near the
        # Colliders, as only there it is subdivided
        co = [ground.matrix_world @ x.co for x in ground.data.vertices]
        length = max(
            ((co[a] - co[b]).length for a, b in (x.vertices for x in ground.data.edges)),
            default=0.0,
        )
        corners = [obj.matrix_world @ Vector(c) for obj in colliders for c in obj.bound_box]
        margin = Vector((3.0, 3.0, 3.0)) * modifier_input(modifier, "Depth").value
        low = Vector(map(min, *corners)) - margin if corners else None
        high = Vector(map(max, *corners)) + margin if corners else None
        # Of the faces larger than the Colliders only the part near them, e.g. a road under a giant
        area = math.prod(sorted(high - low)[1:]) if corners else 0.0
        faces = 0.0
        for polygon in ground.data.polygons:
            points = [co[x] for x in polygon.vertices]
            bottom, top = Vector(map(min, *points)), Vector(map(max, *points))
            if low is None:
                faces += 1.0
            elif all(bottom[i] <= high[i] and top[i] >= low[i] for i in range(3)):
                size = sorted(top - bottom)
                faces += min(area / max(size[1] * size[2], 1e-12), 1.0)
        levels = math.ceil(math.log2(max(length / (EDGE_LENGTH * scale), 1.0)))
        while levels and 4**levels * faces > MAX_FACES:
            levels -= 1
        modifier_input(modifier, "Subdivisions").value = min(levels, 16)
        # Changing the modifier inputs from Python does not tag the object
        ground.update_tag()
        for material in materials([ground]):
            if not shader_nodes(material, TINT):
                tint(material, TINT)

        if not colliders:
            self.report(
                {"WARNING"},
                "MustardUI - Imprints added, add the objects to imprint to their Colliders.",
            )
            return {"FINISHED"}
        self.report({"INFO"}, f"MustardUI - Imprints of {len(colliders)} objects added.")
        return {"FINISHED"}


class MustardUI_ModelToolkit_RemoveImprints(bpy.types.Operator):
    """Remove the Imprints from the selected meshes, the tint from their materials not used by other meshes with Imprints, and the Colliders collections not used anymore"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_remove_imprints"
    bl_label = "Remove Imprints"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        return any(is_effect(m, NODE_GROUP) for x in context.selected_objects for m in x.modifiers)

    def execute(self, context):
        remove_with_colliders(context, NODE_GROUP)
        imprinted = [
            x for x in bpy.data.objects if any(is_effect(m, NODE_GROUP) for m in x.modifiers)
        ]
        for material in materials(context.selected_objects) - materials(imprinted):
            for group in shader_nodes(material, TINT):
                untint(material, group)

        self.report({"INFO"}, "MustardUI - Imprints removed.")
        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_Imprints)
    bpy.utils.register_class(MustardUI_ModelToolkit_RemoveImprints)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_RemoveImprints)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_Imprints)
