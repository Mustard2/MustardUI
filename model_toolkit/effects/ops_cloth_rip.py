import os

import bpy
from mathutils import Matrix, Vector

from ...model_selection.active_object import ModelMode, mustardui_active_object
from .effect import (
    add_effect_modifier,
    effects_available,
    is_effect,
    meshes_or_control,
    modifier_input,
    new_control,
    parent_control,
    with_vertices,
)

NODE_GROUP = "MustardUI Cloth Rip"
CONTROL_TYPE = "EFFECT_CLOTH_RIP"
RESOURCE = os.path.join(os.path.dirname(__file__), "resources", "cloth_rip.blend")
# Hold of the cloth on the shape of the mesh without an Anchor
SHAPE = 0.4


class MustardUI_ModelToolkit_ClothRip(bpy.types.Operator):
    """Rip the selected meshes with a Pull Empty, simulated as cloth around it on the Cloth Dynamics of Blender: the Pull grabs the cloth around its sphere on their vertex closest to the 3D cursor and moves out of them or down them, the cloth near it tearing along ragged lines, held in the Pull until it is scaled to 0. The whole cloth is simulated from the current frame, held on the shape of the mesh and by an Anchor Vertex Group: play the animation from there, not to skip frames of the simulation.\nThe meshes with a Cloth Rip get the new Pull in its Pulls collection\nBlender 5.2 or above is required"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_cloth_rip"
    bl_label = "Add Cloth Rip"
    bl_options = {"REGISTER", "UNDO"}

    radius: bpy.props.FloatProperty(
        name="Radius",
        default=0.04,
        min=0.001,
        subtype="DISTANCE",
        description="Radius of the Pull sphere, grabbing the cloth around it",
    )
    direction: bpy.props.EnumProperty(
        name="Direction",
        items=(
            ("OUT", "Out", "Away from the mesh along its normal, tearing a piece out"),
            ("DOWN", "Down", "Down along the mesh, tearing it open along the way"),
        ),
        default="OUT",
        description="Direction the Pull moves in",
    )
    distance: bpy.props.FloatProperty(
        name="Distance",
        default=0.3,
        subtype="DISTANCE",
        description="Distance the Pull moves at the end of the Duration",
    )
    duration: bpy.props.IntProperty(
        name="Duration",
        default=24,
        min=1,
        description="Frames for the Pull to move the Distance away, from the current frame",
    )
    anchor: bpy.props.StringProperty(
        name="Anchor",
        description="Vertex Group pinning the cloth to the mesh, e.g. a collar, the rest "
        "simulated freely. Empty for the cloth to be held on the shape of the mesh instead",
    )
    hold: bpy.props.BoolProperty(
        name="Hold",
        default=True,
        description="Keep the torn cloth in the Pull. Off for the Pull to let go at the end of "
        "the Duration, scaled to 0, the cloth falling",
    )

    @classmethod
    def poll(cls, context):
        return effects_available() and meshes_or_control(context, CONTROL_TYPE)

    def draw(self, context):
        self.layout.prop(self, "radius")
        self.layout.prop(self, "direction")
        self.layout.prop(self, "distance")
        self.layout.prop(self, "duration")
        self.layout.prop(self, "hold")
        if context.active_object and context.active_object.type == "MESH":
            self.layout.prop_search(self, "anchor", context.active_object, "vertex_groups")

    def execute(self, context):
        objects = with_vertices(context, [x for x in context.selected_objects if x.type == "MESH"])
        if not objects:
            self.report({"WARNING"}, "MustardUI - Select meshes with vertices first.")
            return {"CANCELLED"}

        if NODE_GROUP not in bpy.data.node_groups:
            with bpy.data.libraries.load(RESOURCE) as (_, target):
                target.node_groups = [NODE_GROUP]

        for obj in objects:
            obj.add_rest_position_attribute = True
        depsgraph = context.evaluated_depsgraph_get()

        # The Pull on the vertex closest to the 3D cursor, following the deformed mesh
        cursor = context.scene.cursor.location
        source, vertex = min(
            ((x, v) for x in objects for v in x.evaluated_get(depsgraph).data.vertices),
            key=lambda p: (p[0].matrix_world @ p[1].co - cursor).length_squared,
        )
        pull, _, _ = new_control(objects, "Cloth Rip", CONTROL_TYPE)
        parent_control(pull, source, vertex, depsgraph)
        pull.matrix_basis = Matrix.Translation(source.matrix_world @ vertex.co)
        frame = context.scene.frame_current
        normal = (source.matrix_world.to_3x3() @ vertex.normal).normalized()
        self.animate(pull, frame, normal)

        res, arm = mustardui_active_object(context, config=ModelMode.MODEL_TOOLKIT)
        body = arm.MustardUI_RigSettings.model_body if res else None
        if body is None:
            # The body of the model deforming the meshes, when not the one selected in the panel
            for obj in objects:
                armature = next((m.object for m in obj.modifiers if m.type == "ARMATURE"), None)
                if armature is not None and armature.data.MustardUI_created:
                    body = armature.data.MustardUI_RigSettings.model_body
                    break
        homes = set()
        for obj in objects:
            # One modifier per mesh with all its Pulls, the simulation needing a fixed mesh
            modifier = next((m for m in obj.modifiers if is_effect(m, NODE_GROUP)), None)
            if modifier is None:
                modifier = add_effect_modifier(obj, "Cloth Rip", NODE_GROUP)
                modifier_input(modifier, "Start Frame").value = frame
                # The body in a collection, for more colliders to be added
                if body is not None and body not in objects:
                    colliders = bpy.data.collections.new(f"{obj.name} Cloth Rip Colliders")
                    context.scene.collection.children.link(colliders)
                    colliders.objects.link(body)
                    modifier_input(modifier, "Colliders").value = colliders
                if self.anchor in obj.vertex_groups:
                    anchor = modifier_input(modifier, "Anchor")
                    anchor.type = "ATTRIBUTE"
                    anchor.attribute_name = self.anchor
                else:
                    # Nothing pinning the cloth, held on the shape of the mesh not to slide off
                    modifier_input(modifier, "Shape").value = SHAPE
            pulls = modifier_input(modifier, "Pulls")
            # In the scene collection, out of the outfit collections not to be part of an outfit
            if pulls.value is None:
                pulls.value = bpy.data.collections.new(f"{obj.name} Cloth Rip Pulls")
            if pulls.value not in context.scene.collection.children_recursive:
                context.scene.collection.children.link(pulls.value)
            pulls.value.objects.link(pull)
            homes.add(pulls.value)
            # Changing the modifier inputs from Python does not tag the object
            obj.update_tag()
        for collection in set(pull.users_collection) - homes:
            collection.objects.unlink(pull)

        # The Pull selected, to be moved right away, unless in an excluded collection
        try:
            pull.select_set(True)
        except RuntimeError:
            pass
        else:
            for obj in objects:
                obj.select_set(False)
            context.view_layer.objects.active = pull

        self.report({"INFO"}, f"MustardUI - Cloth Rip added to {len(objects)} objects.")
        return {"FINISHED"}

    def animate(self, pull, frame, normal):
        """Keyframes of the Pull from the frame, out of the mesh along its normal or down it"""
        direction = normal
        if self.direction == "DOWN":
            down = Vector((0.0, 0.0, -1.0))
            # Along the surface, the normal out of it a little not to go through the mesh
            along = down - down.project(normal)
            direction = (along.normalized() if along.length > 1e-4 else down) + normal * 0.2
        # The current frame last to leave the Pull there
        start = pull.location.copy()
        for f, location in (
            (frame + self.duration, start + direction * self.distance),
            (frame, start),
        ):
            pull.location = location
            pull.keyframe_insert("location", frame=f)
        radius = (self.radius, self.radius, self.radius)
        if self.hold:
            pull.scale = radius
            return
        # Letting go at the end, scaled to 0 the frame after the last of the pull
        for f, scale in (
            (frame + self.duration + 1, (0.0, 0.0, 0.0)),
            (frame + self.duration, radius),
            (frame, radius),
        ):
            pull.scale = scale
            pull.keyframe_insert("scale", frame=f)


class MustardUI_ModelToolkit_RemoveClothRip(bpy.types.Operator):
    """Remove the Cloth Rip from the selected meshes, with the Pulls and the collections not used anymore"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_remove_cloth_rip"
    bl_label = "Remove Cloth Rip"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        return any(is_effect(m, NODE_GROUP) for x in context.selected_objects for m in x.modifiers)

    def execute(self, context):
        inputs = ("Pulls", "Colliders")
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
            for obj in [x for x in collection.objects if x not in kept]:
                if obj.MustardUI_tools_creators_type == CONTROL_TYPE:
                    bpy.data.objects.remove(obj)
                elif len(obj.users_collection) == 1:
                    context.scene.collection.objects.link(obj)
            bpy.data.collections.remove(collection)

        self.report({"INFO"}, "MustardUI - Cloth Rip removed.")
        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_ClothRip)
    bpy.utils.register_class(MustardUI_ModelToolkit_RemoveClothRip)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_RemoveClothRip)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_ClothRip)
