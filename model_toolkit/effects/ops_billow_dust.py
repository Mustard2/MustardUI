import os

import bpy
from mathutils import Vector

from ...model_selection.active_object import ModelMode, mustardui_active_object
from .effect import (
    colliders_scale,
    effects_available,
    is_effect,
    modifier_input,
    remove_with_colliders,
)

NODE_GROUP = "MustardUI Billow Dust"
DUST = "MustardUI Billow Dust Dust"
GLASS = "MustardUI Billow Dust Glass"
RESOURCE = os.path.join(os.path.dirname(__file__), "resources", "billow_dust.blend")

# Modifier inputs of each kind of mesh
PRESETS = {
    "CONCRETE": {"Color": (0.72, 0.7, 0.67, 1.0), "Glass": 0.4, "Rise": 0.09},
    "BRICK": {"Color": (0.72, 0.56, 0.45, 1.0), "Glass": 0.15, "Rise": 0.09},
    "EARTH": {"Color": (0.55, 0.46, 0.36, 1.0), "Glass": 0.0, "Rise": -0.03},
}

# Powers of the scale of Colliders larger than a person the inputs are multiplied by, as for the
# Dust Puff
SCALING = {
    "Size": 1.0,
    "Contact": 1.0,
    "Debris Size": 1.0,
    "Min Speed": 0.5,
    "Rise": 0.5,
    "Growth": 0.5,
    "Lifetime": 0.5,
    "Debris Lifetime": 0.5,
    "Amount": -2.5,
    "Debris Amount": -2.5,
}


class MustardUI_ModelToolkit_BillowDust(bpy.types.Operator):
    """Burst thick billowing dust, glass shards and chips out of the active mesh where the other selected meshes, or the model body, hit it, as a building crushed.\nMore objects can be added to the Colliders collection of the effect\nBlender 5.2 or above is required"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_billow_dust"
    bl_label = "Add Billow Dust"
    bl_options = {"REGISTER", "UNDO"}

    kind: bpy.props.EnumProperty(
        name="Material",
        items=(
            ("CONCRETE", "Concrete", "Grey dust, glass shards and chips, as an office tower"),
            ("BRICK", "Brick", "Reddish dust and chips, with a few shards"),
            ("EARTH", "Earth", "Brown dust settling, and clods, as soil or a rock face"),
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

        # A copy left by a removed Billow Dust replaced, it could be of an older version
        group = bpy.data.node_groups.get(NODE_GROUP)
        if group is not None and not group.users:
            bpy.data.node_groups.remove(group)
            for name in (DUST, GLASS):
                material = bpy.data.materials.get(name)
                if material is not None and not material.users:
                    bpy.data.materials.remove(material)
        with bpy.data.libraries.load(RESOURCE) as (_, data):
            if NODE_GROUP not in bpy.data.node_groups:
                data.node_groups = [NODE_GROUP]

        # In the scene collection, out of the outfit collections not to be part of an outfit
        collection = bpy.data.collections.new(f"{target.name} Billow Dust Colliders")
        context.scene.collection.children.link(collection)
        for obj in colliders:
            collection.objects.link(obj)

        # Last, not to change the dust and the debris
        modifier = target.modifiers.new("Billow Dust", "NODES")
        modifier.node_group = bpy.data.node_groups[NODE_GROUP]
        modifier_input(modifier, "Colliders").value = collection
        # Blender 5.2.0 does not set the material inputs to their defaults
        modifier_input(modifier, "Dust Material").value = bpy.data.materials[DUST]
        modifier_input(modifier, "Glass Material").value = bpy.data.materials[GLASS]
        for name, value in PRESETS[self.kind].items():
            modifier_input(modifier, name).value = value
        scale = colliders_scale(colliders)
        for name, power in SCALING.items():
            modifier_input(modifier, name).value *= scale**power
        # On the ground, or under the mesh if lower
        corners = [target.matrix_world @ Vector(x) for x in target.bound_box]
        modifier_input(modifier, "Floor").value = min(0.0, *(x.z for x in corners))
        # Shaded from the brightest sun, by the dust itself in Cycles
        suns = [x for x in context.scene.objects if x.type == "LIGHT" and x.data.type == "SUN"]
        sun = max(suns, key=lambda x: x.data.energy, default=None)
        modifier_input(modifier, "Sun").value = sun
        modifier_input(modifier, "Shade").value = float(context.scene.render.engine != "CYCLES")
        modifier_input(modifier, "Start Frame").value = context.scene.frame_current
        # Changing the modifier inputs from Python does not tag the object
        target.update_tag()

        if not colliders:
            self.report(
                {"WARNING"},
                "MustardUI - Billow Dust added, add the objects hitting the mesh to its Colliders.",
            )
            return {"FINISHED"}
        self.report({"INFO"}, f"MustardUI - Billow Dust of {len(colliders)} objects added.")
        return {"FINISHED"}


class MustardUI_ModelToolkit_RemoveBillowDust(bpy.types.Operator):
    """Remove the Billow Dust from the selected meshes, and the Colliders collections not used anymore"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_remove_billow_dust"
    bl_label = "Remove Billow Dust"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        return any(is_effect(m, NODE_GROUP) for x in context.selected_objects for m in x.modifiers)

    def execute(self, context):
        remove_with_colliders(context, NODE_GROUP)
        self.report({"INFO"}, "MustardUI - Billow Dust removed.")
        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_BillowDust)
    bpy.utils.register_class(MustardUI_ModelToolkit_RemoveBillowDust)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_RemoveBillowDust)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_BillowDust)
