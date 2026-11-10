import os

import bpy
from mathutils import Vector

from .effect import effects_available, is_effect, modifier_input

NODE_GROUP = "MustardUI Rain"
MATERIAL = "MustardUI Rain"
CONTROL_TYPE = "EFFECT_RAIN"
RESOURCE = os.path.join(os.path.dirname(__file__), "resources", "rain.blend")

# Shape and modifier inputs of each kind of rain, the Density per square meter of the floor
PRESETS = {
    "RAIN": ("BOX", {}),
    "DRIZZLE": (
        "BOX",
        {
            "Density": 400.0,
            "Size": 0.001,
            "Stretch": 12.0,
            "Speed": 4.0,
            "Opacity": 0.3,
            "Splashes": 2,
            "Splash Speed": 0.6,
        },
    ),
    "STORM": (
        "BOX",
        {
            "Density": 4000.0,
            "Size": 0.002,
            "Stretch": 30.0,
            "Speed": 9.0,
            "Randomness": 0.4,
            "Opacity": 0.45,
            "Splashes": 6,
            "Splash Speed": 2.0,
        },
    ),
    "SHOWER": (
        "CONE",
        {
            "Top Radius": 0.12,
            "Density": 3000.0,
            "Size": 0.0018,
            "Stretch": 14.0,
            "Speed": 4.5,
            "Randomness": 0.2,
            "Opacity": 0.5,
            "Splashes": 3,
            "Splash Speed": 1.0,
        },
    ),
}
SHAPES = {"BOX": "Box", "CYLINDER": "Cylinder", "CONE": "Cone"}


class MustardUI_ModelToolkit_Rain(bpy.types.Operator):
    """Add rain falling in a box, cylinder or cone on a Control Empty, splashing on the selected meshes and on the bottom of the shape.\nOther meshes can be added to the Rain Colliders collection to splash on them too.\nBlender 5.2 or above is required"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_rain"
    bl_label = "Add Rain"
    bl_options = {"REGISTER", "UNDO"}

    kind: bpy.props.EnumProperty(
        name="Preset",
        items=(
            ("RAIN", "Rain", "Steady rain"),
            ("DRIZZLE", "Drizzle", "Light rain of small and slow drops"),
            ("STORM", "Storm", "Heavy rain of large and fast drops, splashing high"),
            ("SHOWER", "Shower", "Shower head spraying a cone of water above the meshes"),
        ),
    )
    shape: bpy.props.EnumProperty(
        name="Shape",
        items=(
            ("PRESET", "Preset", "Shape of the preset: a cone for the Shower, a box otherwise"),
            ("BOX", "Box", "Rain falling from the top face of a box"),
            ("CYLINDER", "Cylinder", "Rain falling from the top face of a cylinder"),
            ("CONE", "Cone", "Rain spraying from the small top face of a cut cone, spreading"),
        ),
    )
    size: bpy.props.FloatProperty(
        name="Size",
        default=1.0,
        min=0.01,
        subtype="DISTANCE",
        description="Half width of the shape on the 3D cursor, if no mesh is selected",
    )

    @classmethod
    def poll(cls, context):
        return effects_available()

    def volume(self, objects, cursor):
        """Center and half sizes of the shape, around the objects from their lowest point. The
        Shower is narrower, from above them"""
        shower = self.kind == "SHOWER"
        if not objects:
            half, height = (
                (0.5 * self.size, 2.2 * self.size) if shower else (self.size, 3 * self.size)
            )
            return cursor + Vector((0.0, 0.0, height / 2)), Vector((half, half, height / 2))
        corners = [obj.matrix_world @ Vector(c) for obj in objects for c in obj.bound_box]
        low = Vector([min(c[i] for c in corners) for i in range(3)])
        high = Vector([max(c[i] for c in corners) for i in range(3)])
        extent = high - low
        if shower:
            half = max(extent.x, extent.y) / 2 + 0.2
            top = high.z + 0.3
        else:
            half = max(extent.x, extent.y, 0.1)
            top = high.z + max(extent.z * 0.25, 0.5)
        center = Vector(((low.x + high.x) / 2, (low.y + high.y) / 2, (low.z + top) / 2))
        return center, Vector((half, half, (top - low.z) / 2))

    def execute(self, context):
        with bpy.data.libraries.load(RESOURCE) as (_, data):
            if NODE_GROUP not in bpy.data.node_groups:
                data.node_groups = [NODE_GROUP]
            if MATERIAL not in bpy.data.materials:
                data.materials = [MATERIAL]
        group, material = bpy.data.node_groups[NODE_GROUP], bpy.data.materials[MATERIAL]
        shape, inputs = PRESETS[self.kind]
        shape = shape if self.shape == "PRESET" else self.shape
        name = self.kind.title()

        objects = [
            x
            for x in context.selected_objects
            if x.type == "MESH" and not x.MustardUI_tools_creators_type.startswith("EFFECT_")
        ]

        collection = bpy.data.collections.new(name)
        context.scene.collection.children.link(collection)

        colliders = bpy.data.collections.new(f"{name} Colliders")
        context.scene.collection.children.link(colliders)
        for obj in objects:
            colliders.objects.link(obj)

        # The cube of the box, the axes reaching the faces of the others
        control = bpy.data.objects.new(f"{name} Control", None)
        collection.objects.link(control)
        control.empty_display_type = "CUBE" if shape == "BOX" else "PLAIN_AXES"
        control.location, control.scale = self.volume(objects, context.scene.cursor.location)
        control.MustardUI_tools_creators_is_created = True
        control.MustardUI_tools_creators_type = CONTROL_TYPE

        rain = bpy.data.objects.new(name, bpy.data.meshes.new(name))
        collection.objects.link(rain)
        # The Rain follows the Control, moving the object would shift the drops
        rain.lock_location = rain.lock_rotation = rain.lock_scale = (True, True, True)
        # Thin and clear, the drops would cast dark streaks on the colliders
        rain.visible_shadow = False
        modifier = rain.modifiers.new("Rain", "NODES")
        modifier.node_group = group
        modifier_input(modifier, "Control").value = control
        modifier_input(modifier, "Colliders").value = colliders
        modifier_input(modifier, "Material").value = material
        modifier_input(modifier, "Shape").value = SHAPES[shape]
        for key, value in inputs.items():
            modifier_input(modifier, key).value = value
        rain.update_tag()

        for obj in context.selected_objects:
            obj.select_set(False)
        control.select_set(True)
        context.view_layer.objects.active = control

        self.report({"INFO"}, f"MustardUI - {name} added, splashing on {len(objects)} meshes.")
        return {"FINISHED"}


class MustardUI_ModelToolkit_RemoveRain(bpy.types.Operator):
    """Remove the selected Rains, or the Rains of the selected Controls, and their empty collections"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_remove_rain"
    bl_label = "Remove Rain"
    bl_options = {"UNDO"}

    @staticmethod
    def rains(context):
        """Rain objects, their Controls and Colliders, if the Rain or the Control is selected"""
        selected = set(context.selected_objects)
        for obj in bpy.data.objects:
            modifier = next((m for m in obj.modifiers if is_effect(m, NODE_GROUP)), None)
            if modifier is None:
                continue
            control = modifier_input(modifier, "Control").value
            if {obj, control} & selected:
                yield obj, control, modifier_input(modifier, "Colliders").value

    @classmethod
    def poll(cls, context):
        return any(cls.rains(context))

    def execute(self, context):
        rains = list(self.rains(context))
        controls = {c for _, c, _ in rains if c and c.MustardUI_tools_creators_type == CONTROL_TYPE}
        colliders = {c for _, _, c in rains}
        objects = {x for x, _, _ in rains} | controls
        collections = {c for x in objects for c in x.users_collection}
        for obj in objects:
            bpy.data.objects.remove(obj)

        # Remove the collections left empty, and the Colliders not used anymore
        for collection in collections:
            if not collection.all_objects and not collection.children:
                bpy.data.collections.remove(collection)
        used = {
            modifier_input(m, "Colliders").value
            for x in bpy.data.objects
            for m in x.modifiers
            if is_effect(m, NODE_GROUP)
        }
        for collection in colliders - used - {None}:
            # The objects only in the collection kept in the scene
            for obj in [x for x in collection.objects if len(x.users_collection) == 1]:
                context.scene.collection.objects.link(obj)
            bpy.data.collections.remove(collection)

        self.report({"INFO"}, "MustardUI - Rain removed.")
        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_Rain)
    bpy.utils.register_class(MustardUI_ModelToolkit_RemoveRain)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_RemoveRain)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_Rain)
