import math
import os

import bpy

from ...model_selection.active_object import ModelMode, mustardui_active_object
from .effect import (
    add_effect_modifier,
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
        "Recovery": 0.0,
    },
    "SAND": {
        "Depth": 0.04,
        "Rim": 0.8,
        "Rim Width": 0.03,
        "Noise": 0.4,
        "Noise Scale": 50.0,
        "Color": (0.85, 0.8, 0.74, 1.0),
        "Recovery": 0.0,
    },
    "MUD": {
        "Depth": 0.06,
        "Rim": 1.0,
        "Rim Width": 0.04,
        "Noise": 0.2,
        "Color": (0.7, 0.65, 0.6, 1.0),
        "Recovery": 0.0,
    },
    "CUSHION": {
        "Depth": 0.1,
        "Smooth": 0,
        "Softness": 0.12,
        "Rim": 0.0,
        "Noise": 0.0,
        "Color": (1.0, 1.0, 1.0, 1.0),
        "Recovery": 2.0,
    },
}


class MustardUI_ModelToolkit_Imprints(bpy.types.Operator):
    """Imprint the other selected meshes, or the model body, in the active mesh, as in snow, sand, mud or a cushion, keeping the imprints where they pass.\nMore objects can be added to the Colliders collection of the effect\nBlender 5.2 or above is required"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_imprints"
    bl_label = "Add Imprints"
    bl_options = {"REGISTER", "UNDO"}

    kind: bpy.props.EnumProperty(
        name="Ground",
        items=(
            ("SNOW", "Snow", "Deep imprints with a small rim, lasting"),
            ("SAND", "Sand", "Shallow grainy imprints with a rim, lasting"),
            ("MUD", "Mud", "Dark imprints with a high rim, lasting"),
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
        modifier_input(modifier, "Start Frame").value = context.scene.frame_current
        # Subdivided for the longest edges to reach the edge length, without too many faces
        co = [ground.matrix_world @ x.co for x in ground.data.vertices]
        length = max(
            ((co[a] - co[b]).length for a, b in (x.vertices for x in ground.data.edges)),
            default=0.0,
        )
        faces = max(len(ground.data.polygons), 1)
        levels = min(
            math.ceil(math.log2(max(length / EDGE_LENGTH, 1.0))),
            int(math.log(max(MAX_FACES / faces, 1.0), 4)),
            8,
        )
        modifier_input(modifier, "Subdivisions").value = levels
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
