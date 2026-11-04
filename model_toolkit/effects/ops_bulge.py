import os

import bpy
from mathutils import Vector

from .effect import (
    add_effect_modifier,
    effects_available,
    is_effect,
    modifier_input,
    remove_with_colliders,
)

NODE_GROUP = "MustardUI Bulge"
RESOURCE = os.path.join(os.path.dirname(__file__), "resources", "bulge.blend")


def thickness(obj):
    """Middle size of the bounding box of the object, e.g. the diameter of a cylinder"""
    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    return sorted(Vector(map(max, *corners)) - Vector(map(min, *corners)))[1]


class MustardUI_ModelToolkit_Bulge(bpy.types.Operator):
    """Bulge the active mesh over the other selected meshes where they are inside it, e.g. an object pushed under the skin, jiggling as they move.\nMore objects can be added to the Colliders collection of the effect\nBlender 5.2 or above is required"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_bulge"
    bl_label = "Add Bulge"
    bl_options = {"REGISTER", "UNDO"}

    jiggle: bpy.props.BoolProperty(
        name="Jiggle",
        default=True,
        description="Bulge springing after the Colliders as they move, simulated from the "
        "current frame. It can be toggled later in the Jiggle panel of the modifier",
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return effects_available() and obj is not None and obj.type == "MESH"

    def execute(self, context):
        target = context.active_object
        colliders = [x for x in context.selected_objects if x.type == "MESH" and x != target]

        if NODE_GROUP not in bpy.data.node_groups:
            with bpy.data.libraries.load(RESOURCE) as (_, data):
                data.node_groups = [NODE_GROUP]

        # In the scene collection, out of the outfit collections not to be part of an outfit
        collection = bpy.data.collections.new(f"{target.name} Bulge Colliders")
        context.scene.collection.children.link(collection)
        for obj in colliders:
            collection.objects.link(obj)

        modifier = add_effect_modifier(target, "Bulge", NODE_GROUP)
        modifier_input(modifier, "Colliders").value = collection
        # Spreading about as far as the Colliders are thick, in the space of the mesh
        if colliders:
            scale = max(target.matrix_world.to_scale())
            width = max(thickness(x) for x in colliders) / max(scale, 1e-6)
            modifier_input(modifier, "Width").value = width
            modifier_input(modifier, "Entry Fade").value = width / 4
        modifier_input(modifier, "Jiggle").value = self.jiggle
        modifier_input(modifier, "Start Frame").value = context.scene.frame_current
        # Changing the modifier inputs from Python does not tag the object
        target.update_tag()

        if not colliders:
            self.report(
                {"WARNING"},
                "MustardUI - Bulge added, add the objects bulging the mesh to its Colliders.",
            )
            return {"FINISHED"}
        self.report({"INFO"}, f"MustardUI - Bulge of {len(colliders)} objects added.")
        return {"FINISHED"}


class MustardUI_ModelToolkit_RemoveBulge(bpy.types.Operator):
    """Remove the Bulge from the selected meshes, and the Colliders collections not used anymore"""

    bl_idname = "mustardui.model_toolkit_remove_bulge"
    bl_label = "Remove Bulge"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        return any(is_effect(m, NODE_GROUP) for x in context.selected_objects for m in x.modifiers)

    def execute(self, context):
        remove_with_colliders(context, NODE_GROUP)
        self.report({"INFO"}, "MustardUI - Bulge removed.")
        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_Bulge)
    bpy.utils.register_class(MustardUI_ModelToolkit_RemoveBulge)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_RemoveBulge)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_Bulge)
