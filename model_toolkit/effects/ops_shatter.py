import os

import bpy
from mathutils import Vector

from ...model_selection.active_object import ModelMode, mustardui_active_object
from .effect import effects_available, is_effect, modifier_input

NODE_GROUP = "MustardUI Shatter"
DUST = "MustardUI Shatter Dust"
RESOURCE = os.path.join(os.path.dirname(__file__), "resources", "shatter.blend")

# Modifier inputs of each material, the distances as a share of the size of the mesh
PRESETS = {
    "GLASS": {
        "Pieces": 60,
        "Spread": 0.6,
        "Break Radius": 2.0,
        "Strength": 1.5,
        "Push": 0.3,
        "Scatter": 0.6,
        "Bounce": 0.3,
        "Heavy Size": 0.3,
        "Friction": 0.4,
        "Breakup": True,
        "Breakup Size": 0.15,
        "Debris": True,
        "Debris Amount": 200,
        "Debris Size": 0.015,
        "Smoke": False,
        "Smoke Amount": 200,
        "Smoke Size": 0.06,
        "Smoke Rise": -0.03,
    },
    "CERAMIC": {
        "Pieces": 25,
        "Spread": 0.8,
        "Break Radius": 2.0,
        "Strength": 2.0,
        "Push": 0.3,
        "Scatter": 0.4,
        "Bounce": 0.2,
        "Heavy Size": 0.2,
        "Friction": 0.6,
        "Breakup": True,
        "Breakup Size": 0.2,
        "Debris": True,
        "Debris Amount": 100,
        "Debris Size": 0.02,
        "Smoke": False,
        "Smoke Amount": 200,
        "Smoke Size": 0.08,
        "Smoke Rise": -0.03,
    },
    "STONE": {
        "Pieces": 60,
        "Spread": 0.3,
        "Break Radius": 0.15,
        "Strength": 1.0,
        "Push": 0.6,
        "Scatter": 0.2,
        "Bounce": 0.1,
        "Heavy Size": 0.1,
        "Friction": 0.8,
        "Floor Support": True,
        "Breakup": True,
        "Breakup Size": 0.1,
        "Debris": True,
        "Debris Amount": 150,
        "Debris Size": 0.012,
        "Smoke": True,
        "Smoke Amount": 300,
        "Smoke Size": 0.09,
        "Smoke Rise": -0.03,
    },
}
DISTANCES = {
    "Spread",
    "Break Radius",
    "Heavy Size",
    "Breakup Size",
    "Debris Size",
    "Smoke Size",
    # A speed, in sizes per second
    "Smoke Rise",
}


class MustardUI_ModelToolkit_Shatter(bpy.types.Operator):
    """Shatter the active mesh into pieces where the other selected meshes, or the model body, hit it fast enough, or when it falls on the floor.\nMore objects can be added to the Colliders collection of the effect\nBlender 5.2 or above is required"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_shatter"
    bl_label = "Add Shatter"
    bl_options = {"REGISTER", "UNDO"}

    kind: bpy.props.EnumProperty(
        name="Material",
        items=(
            ("GLASS", "Glass", "Many sharp shards, all scattering, with fine debris"),
            ("CERAMIC", "Ceramic", "Few large pieces, all falling, with debris"),
            (
                "STONE",
                "Stone",
                "A hole where it is hit, the rest staying until hit, with debris and dust",
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

        # A copy left by a removed Shatter replaced, it could be of an older version
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
        collection = bpy.data.collections.new(f"{target.name} Shatter Colliders")
        context.scene.collection.children.link(collection)
        for obj in colliders:
            collection.objects.link(obj)

        # Last, to break the mesh as seen
        modifier = target.modifiers.new("Shatter", "NODES")
        modifier.node_group = bpy.data.node_groups[NODE_GROUP]
        modifier_input(modifier, "Colliders").value = collection
        # Blender 5.2.0 does not set the material inputs to their defaults
        modifier_input(modifier, "Smoke Material").value = bpy.data.materials[DUST]
        corners = [target.matrix_world @ Vector(x) for x in target.bound_box]
        size = (Vector(map(max, *corners)) - Vector(map(min, *corners))).length
        for name, value in PRESETS[self.kind].items():
            modifier_input(modifier, name).value = value * size if name in DISTANCES else value
        # On the ground, or under the mesh if lower
        modifier_input(modifier, "Floor").value = min(0.0, *(x.z for x in corners))
        modifier_input(modifier, "Start Frame").value = context.scene.frame_current
        # Changing the modifier inputs from Python does not tag the object
        target.update_tag()

        if not colliders:
            self.report(
                {"WARNING"},
                "MustardUI - Shatter added, breaking on the floor. Add the objects hitting it to "
                "its Colliders.",
            )
            return {"FINISHED"}
        self.report({"INFO"}, f"MustardUI - Shatter by {len(colliders)} objects added.")
        return {"FINISHED"}


class MustardUI_ModelToolkit_RemoveShatter(bpy.types.Operator):
    """Remove the Shatter from the selected meshes, and the Colliders collections not used anymore"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_remove_shatter"
    bl_label = "Remove Shatter"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        return any(is_effect(m, NODE_GROUP) for x in context.selected_objects for m in x.modifiers)

    def execute(self, context):
        collections = set()
        for obj in context.selected_objects:
            for modifier in [m for m in obj.modifiers if is_effect(m, NODE_GROUP)]:
                collections.add(modifier_input(modifier, "Colliders").value)
                obj.modifiers.remove(modifier)

        used = {
            modifier_input(m, "Colliders").value
            for x in bpy.data.objects
            for m in x.modifiers
            if is_effect(m, NODE_GROUP)
        }
        for collection in collections - used - {None}:
            # The objects only in the collection kept in the scene
            for obj in [x for x in collection.objects if len(x.users_collection) == 1]:
                context.scene.collection.objects.link(obj)
            bpy.data.collections.remove(collection)

        self.report({"INFO"}, "MustardUI - Shatter removed.")
        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_Shatter)
    bpy.utils.register_class(MustardUI_ModelToolkit_RemoveShatter)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_RemoveShatter)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_Shatter)
