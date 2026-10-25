import os

import bpy
from mathutils import Matrix

from .effect import (
    add_effect_modifier,
    effects_available,
    is_effect,
    modifier_input,
    new_control,
    parent_control,
)

NODE_GROUP = "MustardUI Foam"
MATERIAL = "MustardUI Foam"
BUBBLES = "MustardUI Foam Bubbles"
CONTROL_TYPE = "EFFECT_FOAM"
RESOURCE = os.path.join(os.path.dirname(__file__), "resources", "foam.blend")
# Radius and modifier inputs of each kind of foam
PRESETS = {
    "LATHER": (0.08, {}),
    "BATH": (
        0.12,
        {
            "Thickness": 0.025,
            "Clumps": 0.6,
            "Clump Scale": 15.0,
            "Lace": 0.2,
            "Bubble Size": 0.002,
            "Iridescence": 0.6,
            "Max Radius": 0.005,
        },
    ),
    "SHAVING": (
        0.06,
        {
            "Thickness": 0.015,
            "Clumps": 0.5,
            "Clump Scale": 20.0,
            "Lace": 0.08,
            "Bubble Size": 0.0004,
            "Coverage": 0.9,
            "Iridescence": 0.15,
            "Density": 3000.0,
            "Min Radius": 0.0003,
            "Max Radius": 0.0012,
        },
    ),
}


class MustardUI_ModelToolkit_Foam(bpy.types.Operator):
    """Cover the selected meshes with soap foam inside the sphere of a Control Empty, on their vertex closest to the 3D cursor, puffy clumps thinning to a lacy layer of bubbles at the border.\nThe meshes with a Foam get the new Control in its Controls collection\nBlender 5.2 or above is required"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_foam"
    bl_label = "Add Foam"
    bl_options = {"REGISTER", "UNDO"}

    def update_kind(self, context):
        self.radius = PRESETS[self.kind][0]

    kind: bpy.props.EnumProperty(
        name="Kind",
        items=(
            ("LATHER", "Soap Lather", "Foam of soap or shower gel rubbed on the skin"),
            ("BATH", "Bath Foam", "Thick foam with large bubbles, as from a bubble bath"),
            ("SHAVING", "Shaving Cream", "Dense creamy foam with tiny bubbles"),
        ),
        update=update_kind,
    )
    radius: bpy.props.FloatProperty(
        name="Radius",
        default=PRESETS["LATHER"][0],
        min=0.001,
        subtype="DISTANCE",
        description="Radius of the Control sphere",
    )

    @classmethod
    def poll(cls, context):
        return effects_available() and any(x.type == "MESH" for x in context.selected_objects)

    def execute(self, context):
        objects = [x for x in context.selected_objects if x.type == "MESH"]

        with bpy.data.libraries.load(RESOURCE) as (_, data):
            if NODE_GROUP not in bpy.data.node_groups:
                data.node_groups = [NODE_GROUP]
            data.materials = [x for x in (MATERIAL, BUBBLES) if x not in bpy.data.materials]

        # The foam placed on the rest mesh, not to move on the deformed one
        for obj in objects:
            obj.add_rest_position_attribute = True
        depsgraph = context.evaluated_depsgraph_get()

        # On the vertex closest to the 3D cursor
        cursor = context.scene.cursor.location
        source, vertex = min(
            ((x, v) for x in objects for v in x.evaluated_get(depsgraph).data.vertices),
            key=lambda p: (p[0].matrix_world @ p[1].co - cursor).length_squared,
        )
        control, _, _ = new_control(objects, "Foam", CONTROL_TYPE)
        parent_control(control, source, vertex, depsgraph)
        control.matrix_basis = Matrix.Translation(source.matrix_world @ vertex.co) @ Matrix.Scale(
            self.radius, 4
        )

        homes = set()
        for obj in objects:
            # One modifier per mesh with all its Controls, the sliding simulated on a fixed mesh
            modifier = next((m for m in obj.modifiers if is_effect(m, NODE_GROUP)), None)
            if modifier is None:
                modifier = add_effect_modifier(obj, "Foam", NODE_GROUP)
                modifier_input(modifier, "Material").value = bpy.data.materials[MATERIAL]
                modifier_input(modifier, "Bubble Material").value = bpy.data.materials[BUBBLES]
                for name, value in PRESETS[self.kind][1].items():
                    modifier_input(modifier, name).value = value
                modifier_input(modifier, "Start Frame").value = context.scene.frame_current
            controls = modifier_input(modifier, "Controls")
            # In the scene collection, out of the outfit collections not to be part of an outfit
            if controls.value is None:
                controls.value = bpy.data.collections.new(f"{obj.name} Foam")
            if controls.value not in context.scene.collection.children_recursive:
                context.scene.collection.children.link(controls.value)
            controls.value.objects.link(control)
            homes.add(controls.value)
            # Changing the modifier inputs from Python does not tag the object
            obj.update_tag()
        for collection in set(control.users_collection) - homes:
            collection.objects.unlink(control)

        # The Control selected, to be moved or scaled right away
        for obj in objects:
            obj.select_set(False)
        control.select_set(True)
        context.view_layer.objects.active = control

        self.report({"INFO"}, f"MustardUI - Foam added to {len(objects)} objects.")
        return {"FINISHED"}


class MustardUI_ModelToolkit_RemoveFoam(bpy.types.Operator):
    """Remove the Foam from the selected meshes, with the Controls and the collections not used anymore"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_remove_foam"
    bl_label = "Remove Foam"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        return any(is_effect(m, NODE_GROUP) for x in context.selected_objects for m in x.modifiers)

    def execute(self, context):
        collections = set()
        for obj in context.selected_objects:
            for modifier in [m for m in obj.modifiers if is_effect(m, NODE_GROUP)]:
                collections.add(modifier_input(modifier, "Controls").value)
                obj.modifiers.remove(modifier)

        used = {
            modifier_input(m, "Controls").value
            for x in bpy.data.objects
            for m in x.modifiers
            if is_effect(m, NODE_GROUP)
        } - {None}
        kept = {x for c in used for x in c.objects}
        for collection in collections - used - {None}:
            for control in [x for x in collection.objects if x not in kept]:
                if control.MustardUI_tools_creators_type == CONTROL_TYPE:
                    bpy.data.objects.remove(control)
            bpy.data.collections.remove(collection)

        self.report({"INFO"}, "MustardUI - Foam removed.")
        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_Foam)
    bpy.utils.register_class(MustardUI_ModelToolkit_RemoveFoam)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_RemoveFoam)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_Foam)
