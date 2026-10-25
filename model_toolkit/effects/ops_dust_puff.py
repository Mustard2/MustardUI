import os

import bpy

from ...model_selection.active_object import ModelMode, mustardui_active_object
from .effect import effects_available, is_effect, modifier_input, remove_with_colliders

NODE_GROUP = "MustardUI Dust Puff"
DUST = "MustardUI Dust Puff Dust"
RESOURCE = os.path.join(os.path.dirname(__file__), "resources", "dust_puff.blend")

# Modifier inputs of each kind of ground
PRESETS = {
    "DUST": {
        "Amount": 3000.0,
        "Size": 0.06,
        "Lifetime": 1.5,
        "Rise": 0.02,
        "Color": (0.55, 0.5, 0.44, 1.0),
        "Grain Amount": 1000.0,
        "Grain Size": 0.004,
        "Grain Lifetime": 4.0,
    },
    "SAND": {
        "Amount": 1200.0,
        "Size": 0.05,
        "Lifetime": 1.2,
        "Rise": -0.05,
        "Color": (0.82, 0.74, 0.6, 1.0),
        "Grain Amount": 6000.0,
        "Grain Size": 0.002,
        "Grain Lifetime": 3.0,
    },
    "SNOW": {
        "Amount": 1500.0,
        "Size": 0.08,
        "Lifetime": 1.0,
        "Rise": -0.03,
        "Color": (0.95, 0.97, 1.0, 1.0),
        "Grain Amount": 5000.0,
        "Grain Size": 0.0025,
        "Grain Lifetime": 1.5,
    },
}


class MustardUI_ModelToolkit_DustPuff(bpy.types.Operator):
    """Kick up dust and grains from the active mesh where the other selected meshes, or the model body, hit it, as a dirt floor, sand or snow.\nMore objects can be added to the Colliders collection of the effect\nBlender 5.2 or above is required"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_dust_puff"
    bl_label = "Add Dust Puff"
    bl_options = {"REGISTER", "UNDO"}

    kind: bpy.props.EnumProperty(
        name="Ground",
        items=(
            ("DUST", "Dust", "Grey brown dust lingering in the air, with a few grains"),
            ("SAND", "Sand", "Many sand grains and a little dust settling fast"),
            ("SNOW", "Snow", "White powder and clumps settling back"),
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

        # A copy left by a removed Dust Puff replaced, it could be of an older version
        group = bpy.data.node_groups.get(NODE_GROUP)
        if group is not None and not group.users:
            bpy.data.node_groups.remove(group)
            dust = bpy.data.materials.get(DUST)
            if dust is not None and not dust.users:
                bpy.data.materials.remove(dust)
        with bpy.data.libraries.load(RESOURCE) as (_, data):
            if NODE_GROUP not in bpy.data.node_groups:
                data.node_groups = [NODE_GROUP]

        # In the scene collection, out of the outfit collections not to be part of an outfit
        collection = bpy.data.collections.new(f"{ground.name} Dust Puff Colliders")
        context.scene.collection.children.link(collection)
        for obj in colliders:
            collection.objects.link(obj)

        # Last, not to subdivide the grains
        modifier = ground.modifiers.new("Dust Puff", "NODES")
        modifier.node_group = bpy.data.node_groups[NODE_GROUP]
        modifier_input(modifier, "Colliders").value = collection
        # Blender 5.2.0 does not set the material inputs to their defaults
        modifier_input(modifier, "Dust Material").value = bpy.data.materials[DUST]
        for name, value in PRESETS[self.kind].items():
            modifier_input(modifier, name).value = value
        modifier_input(modifier, "Start Frame").value = context.scene.frame_current
        # Changing the modifier inputs from Python does not tag the object
        ground.update_tag()

        if not colliders:
            self.report(
                {"WARNING"},
                "MustardUI - Dust Puff added, add the objects hitting the ground to its Colliders.",
            )
            return {"FINISHED"}
        self.report({"INFO"}, f"MustardUI - Dust Puff of {len(colliders)} objects added.")
        return {"FINISHED"}


class MustardUI_ModelToolkit_RemoveDustPuff(bpy.types.Operator):
    """Remove the Dust Puff from the selected meshes, and the Colliders collections not used anymore"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_remove_dust_puff"
    bl_label = "Remove Dust Puff"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        return any(is_effect(m, NODE_GROUP) for x in context.selected_objects for m in x.modifiers)

    def execute(self, context):
        remove_with_colliders(context, NODE_GROUP)
        self.report({"INFO"}, "MustardUI - Dust Puff removed.")
        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_DustPuff)
    bpy.utils.register_class(MustardUI_ModelToolkit_RemoveDustPuff)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_RemoveDustPuff)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_DustPuff)
