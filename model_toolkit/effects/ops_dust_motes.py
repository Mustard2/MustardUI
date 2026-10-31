import os

import bpy
from mathutils import Vector

from ...model_selection.active_object import ModelMode, mustardui_active_object
from .effect import effects_available, is_effect, modifier_input

NODE_GROUP = "MustardUI Dust Motes"
MOTES = "MustardUI Dust Motes"
HAZE = "MustardUI Dust Motes Haze"
RESOURCE = os.path.join(os.path.dirname(__file__), "resources", "dust_motes.blend")
# Space around the objects the box fills, in m, and its size without objects
MARGIN = 0.75
SIZE = 2.0

# Modifier inputs of each kind of air
PRESETS = {
    "SUNBEAM": {
        "Density": 800.0,
        "Size": 0.0012,
        "Brightness": 10.0,
        "Twinkle": 0.5,
        "Swirl Speed": 0.005,
        "Haze": 0.1,
    },
    "ROOM": {
        "Density": 500.0,
        "Size": 0.001,
        "Brightness": 8.0,
        "Twinkle": 0.3,
        "Swirl Speed": 0.003,
        "Haze": 0.0,
    },
    "DUSTY": {
        "Density": 6000.0,
        "Size": 0.0016,
        "Brightness": 6.0,
        "Twinkle": 0.6,
        "Swirl Speed": 0.015,
        "Haze": 0.3,
    },
}


class MustardUI_ModelToolkit_DustMotes(bpy.types.Operator):
    """Fill a box around the selected meshes, or the model, with dust motes floating in the air, shining where the lights reach them.\nScale and move the box to fill the space in view\nBlender 5.2 or above is required"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_dust_motes"
    bl_label = "Add Dust Motes"
    bl_options = {"REGISTER", "UNDO"}

    kind: bpy.props.EnumProperty(
        name="Air",
        items=(
            ("SUNBEAM", "Sunbeam", "Motes and a light haze showing the light beams"),
            ("ROOM", "Room", "A few motes in clear and still air"),
            ("DUSTY", "Dusty", "Many motes swirling in thick haze"),
        ),
    )

    @classmethod
    def poll(cls, context):
        return effects_available()

    def execute(self, context):
        objects = [x for x in context.selected_objects if x.type == "MESH"]
        if not objects:
            res, arm = mustardui_active_object(context, config=ModelMode.MODEL_TOOLKIT)
            body = arm.MustardUI_RigSettings.model_body if res else None
            objects = [body] if body is not None else []
        if objects:
            corners = [x.matrix_world @ Vector(c) for x in objects for c in x.bound_box]
            low = Vector(map(min, *corners)) - Vector((MARGIN, MARGIN, 0.0))
            high = Vector(map(max, *corners)) + Vector((MARGIN, MARGIN, MARGIN))
        else:
            low = context.scene.cursor.location - Vector((SIZE, SIZE, SIZE)) / 2
            high = low + Vector((SIZE, SIZE, SIZE))

        # A copy left by removed Dust Motes replaced, it could be of an older version
        group = bpy.data.node_groups.get(NODE_GROUP)
        if group is not None and not group.users:
            bpy.data.node_groups.remove(group)
            for name in (MOTES, HAZE):
                material = bpy.data.materials.get(name)
                if material is not None and not material.users:
                    bpy.data.materials.remove(material)
        with bpy.data.libraries.load(RESOURCE) as (_, data):
            if NODE_GROUP not in bpy.data.node_groups:
                data.node_groups = [NODE_GROUP]

        # A box at the origin of the object, in the middle of its floor
        center = Vector(((low.x + high.x) / 2, (low.y + high.y) / 2, low.z))
        size = high - low
        mesh = bpy.data.meshes.new("Dust Motes")
        mesh.from_pydata(
            [
                ((x - 0.5) * size.x, (y - 0.5) * size.y, z * size.z)
                for x in (0, 1)
                for y in (0, 1)
                for z in (0, 1)
            ],
            [],
            [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)],
        )
        box = bpy.data.objects.new("Dust Motes", mesh)
        # In the scene collection, out of the outfit collections not to be part of an outfit
        context.scene.collection.objects.link(box)
        box.location = center

        modifier = box.modifiers.new("Dust Motes", "NODES")
        modifier.node_group = bpy.data.node_groups[NODE_GROUP]
        # Blender 5.2.0 does not set the material inputs to their defaults
        modifier_input(modifier, "Motes Material").value = bpy.data.materials[MOTES]
        modifier_input(modifier, "Haze Material").value = bpy.data.materials[HAZE]
        for name, value in PRESETS[self.kind].items():
            modifier_input(modifier, name).value = value
        box.update_tag()

        for obj in context.selected_objects:
            obj.select_set(False)
        box.select_set(True)
        context.view_layer.objects.active = box

        self.report({"INFO"}, "MustardUI - Dust Motes added, scale the box to fill the view.")
        return {"FINISHED"}


class MustardUI_ModelToolkit_RemoveDustMotes(bpy.types.Operator):
    """Remove the selected Dust Motes boxes"""

    bl_idname = "mustardui.model_toolkit_remove_dust_motes"
    bl_label = "Remove Dust Motes"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        return any(is_effect(m, NODE_GROUP) for x in context.selected_objects for m in x.modifiers)

    def execute(self, context):
        for obj in [
            x
            for x in context.selected_objects
            if any(is_effect(m, NODE_GROUP) for m in x.modifiers)
        ]:
            bpy.data.objects.remove(obj)
        self.report({"INFO"}, "MustardUI - Dust Motes removed.")
        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_DustMotes)
    bpy.utils.register_class(MustardUI_ModelToolkit_RemoveDustMotes)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_RemoveDustMotes)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_DustMotes)
