import os

import bpy

from ...model_selection.active_object import ModelMode, mustardui_active_object
from .effect import (
    RemoveEffect,
    add_effect_modifier,
    colliders_scale,
    effects_available,
    is_effect,
    materials,
    modifier_input,
    shader_nodes,
    tint,
    untint,
)

NODE_GROUP = "MustardUI Cracks"
TINT = "MustardUI Cracks Tint"
RESOURCE = os.path.join(os.path.dirname(__file__), "resources", "cracks.blend")

# Modifier inputs of each kind of ground
PRESETS = {
    "ASPHALT": {
        "Size": 0.12,
        "Shards": 0.5,
        "Thickness": 0.025,
        "Spread": 0.15,
        "Lift": 0.03,
        "Tilt": 0.45,
        "Scatter": 0.04,
        "Color": (0.04, 0.04, 0.04, 1.0),
        "Debris Amount": 1500.0,
        "Debris Size": 0.012,
    },
    "CONCRETE": {
        "Size": 0.25,
        "Shards": 0.3,
        "Thickness": 0.06,
        "Gap": 0.004,
        "Spread": 0.25,
        "Lift": 0.03,
        "Tilt": 0.3,
        "Scatter": 0.04,
        "Color": (0.3, 0.29, 0.27, 1.0),
        "Debris Amount": 600.0,
        "Debris Size": 0.02,
    },
    "ICE": {
        "Size": 0.3,
        "Shards": 0.5,
        "Thickness": 0.03,
        "Gap": 0.002,
        "Spread": 0.5,
        "Lift": 0.005,
        "Tilt": 0.1,
        "Scatter": 0.01,
        "Jolt": 0.3,
        "Color": (0.7, 0.85, 0.95, 1.0),
        "Debris Amount": 300.0,
        "Debris Size": 0.01,
    },
    "EARTH": {
        "Size": 0.08,
        "Shards": 0.3,
        "Thickness": 0.015,
        "Gap": 0.004,
        "Spread": 0.1,
        "Lift": 0.015,
        "Tilt": 0.35,
        "Scatter": 0.02,
        "Color": (0.1, 0.06, 0.035, 1.0),
        "Debris Amount": 2500.0,
        "Debris Size": 0.007,
    },
}

# Powers of the scale of Colliders larger than a person the inputs are multiplied by: the distances
# by it, the speeds by its square root, as for a person that large moving naturally, the thrown
# ones going by the square root of the hit, and as many pebbles per hit
SCALING = {
    "Size": 1.0,
    "Thickness": 1.0,
    "Gap": 1.0,
    "Spread": 1.0,
    "Contact": 1.0,
    "Lift": 1.0,
    "Scatter": 1.0,
    "Debris Size": 1.0,
    "Min Speed": 0.5,
    "Jolt": 0.25,
    "Debris Speed": 0.25,
    "Debris Amount": -2.0,
}


class MustardUI_ModelToolkit_Cracks(bpy.types.Operator):
    """Break the active mesh into plates where the other selected meshes, or the model body, hit it, as asphalt, concrete, ice or dry earth, throwing up pebbles.\nMore objects can be added to the Colliders collection of the effect\nBlender 5.2 or above is required"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_cracks"
    bl_label = "Add Cracks"
    bl_options = {"REGISTER", "UNDO"}

    kind: bpy.props.EnumProperty(
        name="Ground",
        items=(
            ("ASPHALT", "Asphalt", "Thin dark plates and shards, tilted and pushed around"),
            ("CONCRETE", "Concrete", "Large thick slabs, with a few pebbles"),
            ("ICE", "Ice", "Large thin plates cracking far around, barely moving"),
            ("EARTH", "Earth", "Small thin plates of dry earth, with many pebbles"),
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

        # A copy left by removed Cracks replaced, it could be of an older version
        group = bpy.data.node_groups.get(NODE_GROUP)
        if group is not None and not group.users:
            bpy.data.node_groups.remove(group)
        with bpy.data.libraries.load(RESOURCE) as (_, data):
            data.node_groups = [x for x in (NODE_GROUP, TINT) if x not in bpy.data.node_groups]

        # In the scene collection, out of the outfit collections not to be part of an outfit
        collection = bpy.data.collections.new(f"{ground.name} Cracks Colliders")
        context.scene.collection.children.link(collection)
        for obj in colliders:
            collection.objects.link(obj)

        modifier = add_effect_modifier(ground, "Cracks", NODE_GROUP)
        modifier_input(modifier, "Colliders").value = collection
        for name, value in PRESETS[self.kind].items():
            modifier_input(modifier, name).value = value
        scale = colliders_scale(colliders)
        for name, power in SCALING.items():
            modifier_input(modifier, name).value *= scale**power
        modifier_input(modifier, "Start Frame").value = context.scene.frame_current
        # Changing the modifier inputs from Python does not tag the object
        ground.update_tag()
        for material in materials([ground]):
            if not shader_nodes(material, TINT):
                tint(material, TINT)

        if not colliders:
            self.report(
                {"WARNING"},
                "MustardUI - Cracks added, add the objects breaking the mesh to their Colliders.",
            )
            return {"FINISHED"}
        self.report({"INFO"}, f"MustardUI - Cracks of {len(colliders)} objects added.")
        return {"FINISHED"}


class MustardUI_ModelToolkit_RemoveCracks(RemoveEffect, bpy.types.Operator):
    """Remove the Cracks from the selected meshes, the tint from their materials not used by other meshes with Cracks, and the Colliders collections not used anymore"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_remove_cracks"
    bl_label = "Remove Cracks"

    effect = "Cracks"
    node_group = NODE_GROUP
    controls = False
    colliders = True

    def execute(self, context):
        result = super().execute(context)
        cracked = [
            x for x in bpy.data.objects if any(is_effect(m, NODE_GROUP) for m in x.modifiers)
        ]
        for material in materials(context.selected_objects) - materials(cracked):
            for group in shader_nodes(material, TINT):
                untint(material, group)
        return result


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_Cracks)
    bpy.utils.register_class(MustardUI_ModelToolkit_RemoveCracks)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_RemoveCracks)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_Cracks)
