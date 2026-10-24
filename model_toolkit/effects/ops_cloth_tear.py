import os

import bpy
from mathutils import Matrix

from ...model_selection.active_object import ModelMode, mustardui_active_object
from .effect import (
    add_effect_modifier,
    effects_available,
    is_effect,
    modifier_input,
    new_control,
    parent_control,
)

NODE_GROUP = "MustardUI Cloth Tear"
CONTROL_TYPE = "EFFECT_CLOTH_TEAR"
RESOURCE = os.path.join(os.path.dirname(__file__), "resources", "cloth_tear.blend")


class ClothTearControl:
    """Adds a Control on the selected meshes' vertex closest to the 3D cursor to their Cloth Tear"""

    effect = "Cloth Tear"
    collection_input = "Controls"
    collection_name = "Cloth Tear"

    @classmethod
    def poll(cls, context):
        return effects_available() and any(x.type == "MESH" for x in context.selected_objects)

    def animate(self, control, frame, normal):
        """Keyframes of the Control from the frame, normal being the one of the mesh under it"""

    def execute(self, context):
        objects = [x for x in context.selected_objects if x.type == "MESH"]

        if NODE_GROUP not in bpy.data.node_groups:
            with bpy.data.libraries.load(RESOURCE) as (_, target):
                target.node_groups = [NODE_GROUP]

        for obj in objects:
            obj.add_rest_position_attribute = True
        depsgraph = context.evaluated_depsgraph_get()

        # The Control on the vertex closest to the 3D cursor, following the deformed mesh
        cursor = context.scene.cursor.location
        source, vertex = min(
            ((x, v) for x in objects for v in x.evaluated_get(depsgraph).data.vertices),
            key=lambda p: (p[0].matrix_world @ p[1].co - cursor).length_squared,
        )
        control, _, _ = new_control(objects, self.effect, CONTROL_TYPE)
        parent_control(control, source, vertex, depsgraph)
        control.matrix_basis = Matrix.Translation(source.matrix_world @ vertex.co)
        frame = context.scene.frame_current
        self.animate(control, frame, (source.matrix_world.to_3x3() @ vertex.normal).normalized())

        res, arm = mustardui_active_object(context, config=ModelMode.MODEL_TOOLKIT)
        body = arm.MustardUI_RigSettings.model_body if res else None
        homes = set()
        for obj in objects:
            # One modifier per mesh with all its Controls, the simulation needing a fixed mesh
            modifier = next((m for m in obj.modifiers if is_effect(m, NODE_GROUP)), None)
            if modifier is None:
                modifier = add_effect_modifier(obj, "Cloth Tear", NODE_GROUP)
            controls = modifier_input(modifier, self.collection_input)
            # In the scene collection, out of the outfit collections not to be part of an outfit
            if controls.value is None:
                controls.value = bpy.data.collections.new(f"{obj.name} {self.collection_name}")
            if controls.value not in context.scene.collection.children_recursive:
                context.scene.collection.children.link(controls.value)
            controls.value.objects.link(control)
            homes.add(controls.value)
            if self.physics and not modifier_input(modifier, "Physics").value:
                modifier_input(modifier, "Physics").value = True
                modifier_input(modifier, "Start Frame").value = frame
                # The body in a collection, for more colliders to be added
                if body is not None and body not in objects:
                    colliders = bpy.data.collections.new(f"{obj.name} Cloth Colliders")
                    context.scene.collection.children.link(colliders)
                    colliders.objects.link(body)
                    modifier_input(modifier, "Colliders").value = colliders
                if self.anchor in obj.vertex_groups:
                    anchor = modifier_input(modifier, "Anchor")
                    anchor.type = "ATTRIBUTE"
                    anchor.attribute_name = self.anchor
            # Changing the modifier inputs from Python does not tag the object
            obj.update_tag()
        for collection in set(control.users_collection) - homes:
            collection.objects.unlink(control)

        # The Control selected, to be moved or scaled right away, unless in an excluded collection
        try:
            control.select_set(True)
        except RuntimeError:
            pass
        else:
            for obj in objects:
                obj.select_set(False)
            context.view_layer.objects.active = control

        self.report({"INFO"}, f"MustardUI - {self.effect} added to {len(objects)} objects.")
        return {"FINISHED"}


class MustardUI_ModelToolkit_ClothTear(ClothTearControl, bpy.types.Operator):
    """Tear the selected meshes inside the sphere of a Control Empty, on their vertex closest to the 3D cursor, growing to the Radius, with frayed threads on the edge.\nThe meshes with a Cloth Tear get the new Control in its Controls collection\nBlender 5.2 or above is required"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_cloth_tear"
    bl_label = "Add Cloth Tear"
    bl_options = {"REGISTER", "UNDO"}

    radius: bpy.props.FloatProperty(
        name="Radius",
        default=0.05,
        min=0.001,
        subtype="DISTANCE",
        description="Radius of the Control sphere at the end of the tear",
    )
    duration: bpy.props.IntProperty(
        name="Duration",
        default=24,
        min=1,
        description="Frames for the Control to grow from a quarter of the Radius to the Radius, "
        "from the current frame",
    )
    physics: bpy.props.BoolProperty(
        name="Physics",
        description="Tear whole pieces, hanging from the cloth or falling, simulated from the "
        "current frame and colliding with the model body",
    )
    anchor: bpy.props.StringProperty(
        name="Anchor",
        description="Vertex Group holding the cloth with Physics: the parts cut off from it "
        "fall. Empty for the parts cut off from the top of the cloth to fall",
    )

    def draw(self, context):
        self.layout.prop(self, "radius")
        self.layout.prop(self, "duration")
        self.layout.prop(self, "physics")
        if self.physics and context.active_object and context.active_object.type == "MESH":
            self.layout.prop_search(self, "anchor", context.active_object, "vertex_groups")

    def animate(self, control, frame, normal):
        # From a quarter of the Radius, the current frame last to leave the Control at its value
        for f, scale in ((frame + self.duration, self.radius), (frame, self.radius / 4)):
            control.scale = (scale, scale, scale)
            control.keyframe_insert("scale", frame=f)


class MustardUI_ModelToolkit_ClothRip(ClothTearControl, bpy.types.Operator):
    """Rip the selected meshes by pulling them with a Pull Empty, grabbing the cloth in its sphere on their vertex closest to the 3D cursor and moving away from them, with Physics.\nThe meshes with a Cloth Tear get the new Pull in its Pulls collection\nBlender 5.2 or above is required"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_cloth_rip"
    bl_label = "Add Cloth Rip"
    bl_options = {"REGISTER", "UNDO"}

    effect = "Cloth Rip"
    collection_input = "Pulls"
    collection_name = "Cloth Pulls"
    physics = True

    radius: bpy.props.FloatProperty(
        name="Radius",
        default=0.04,
        min=0.001,
        subtype="DISTANCE",
        description="Radius of the Pull sphere, grabbing the cloth inside it",
    )
    distance: bpy.props.FloatProperty(
        name="Distance",
        default=0.2,
        subtype="DISTANCE",
        description="Distance of the Pull away from the mesh at the end of the Duration",
    )
    duration: bpy.props.IntProperty(
        name="Duration",
        default=24,
        min=1,
        description="Frames for the Pull to move the Distance away, from the current frame",
    )
    anchor: bpy.props.StringProperty(
        name="Anchor",
        description="Vertex Group holding the cloth: the parts cut off from it fall. Empty for "
        "the parts cut off from the top of the cloth to fall",
    )

    def draw(self, context):
        self.layout.prop(self, "radius")
        self.layout.prop(self, "distance")
        self.layout.prop(self, "duration")
        if context.active_object and context.active_object.type == "MESH":
            self.layout.prop_search(self, "anchor", context.active_object, "vertex_groups")

    def animate(self, control, frame, normal):
        control.scale = (self.radius, self.radius, self.radius)
        # Out of the mesh along its normal, the current frame last to leave the Pull there
        start = control.location.copy()
        for f, location in (
            (frame + self.duration, start + normal * self.distance),
            (frame, start),
        ):
            control.location = location
            control.keyframe_insert("location", frame=f)


class MustardUI_ModelToolkit_RemoveClothTear(bpy.types.Operator):
    """Remove the Cloth Tear and Cloth Rip from the selected meshes, with the Controls, the Pulls and the collections not used anymore"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_remove_cloth_tear"
    bl_label = "Remove Cloth Tear"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        return any(is_effect(m, NODE_GROUP) for x in context.selected_objects for m in x.modifiers)

    def execute(self, context):
        inputs = ("Controls", "Pulls", "Colliders")
        collections = set()
        for obj in context.selected_objects:
            for modifier in [m for m in obj.modifiers if is_effect(m, NODE_GROUP)]:
                collections.update(modifier_input(modifier, x).value for x in inputs)
                obj.modifiers.remove(modifier)

        used = {
            modifier_input(m, i).value
            for x in bpy.data.objects
            for m in x.modifiers
            if is_effect(m, NODE_GROUP)
            for i in inputs
        } - {None}
        kept = {x for c in used for x in c.objects}
        for collection in collections - used - {None}:
            for control in [x for x in collection.objects if x not in kept]:
                if control.MustardUI_tools_creators_type == CONTROL_TYPE:
                    bpy.data.objects.remove(control)
            bpy.data.collections.remove(collection)

        self.report({"INFO"}, "MustardUI - Cloth Tear removed.")
        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_ClothTear)
    bpy.utils.register_class(MustardUI_ModelToolkit_ClothRip)
    bpy.utils.register_class(MustardUI_ModelToolkit_RemoveClothTear)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_RemoveClothTear)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_ClothRip)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_ClothTear)
