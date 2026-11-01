import os

import bpy

from ...model_selection.active_object import ModelMode, mustardui_active_object
from . import ops_wet
from .effect import (
    add_effect_modifier,
    colliders_scale,
    effects_available,
    is_effect,
    materials,
    modifier_input,
    new_control,
    remove_with_colliders,
    shader_nodes,
    subdivision_levels,
    unwrap_shader,
    wrap_shader,
)

NODE_GROUP = "MustardUI Footprints"
FILM = "MustardUI Footprints Film"
CONTROL_TYPE = "EFFECT_FOOTPRINTS"
RESOURCE = os.path.join(os.path.dirname(__file__), "resources", "footprints.blend")
# Edge length the Subdivisions aim at, and the radius of the puddle, for a person
EDGE_LENGTH = 0.005
PUDDLE_RADIUS = 0.4
# Powers of the scale of Colliders larger than a person the inputs are multiplied by
SCALING = {"Contact": 1, "Patch Scale": -1}


class MustardUI_ModelToolkit_Footprints(bpy.types.Operator):
    """Leave wet prints on the active mesh where the other selected meshes, or the model body, step on it, fainter at each step and drying.\nMore objects can be added to the Colliders collection of the effect\nBlender 5.2 or above is required"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_footprints"
    bl_label = "Add Wet Footprints"
    bl_options = {"REGISTER", "UNDO"}

    puddle: bpy.props.BoolProperty(
        name="Puddle",
        description="Add a puddle at the 3D cursor, wetting the Colliders stepping in it again",
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

        with bpy.data.libraries.load(RESOURCE) as (_, data):
            data.node_groups = [x for x in (NODE_GROUP, FILM) if x not in bpy.data.node_groups]

        # In the scene collection, out of the outfit collections not to be part of an outfit
        collection = bpy.data.collections.new(f"{ground.name} Footprint Colliders")
        context.scene.collection.children.link(collection)
        for obj in colliders:
            collection.objects.link(obj)

        modifier = add_effect_modifier(ground, "Wet Footprints", NODE_GROUP)
        modifier_input(modifier, "Colliders").value = collection
        scale = colliders_scale(colliders)
        for name, power in SCALING.items():
            modifier_input(modifier, name).value *= scale**power
        modifier_input(modifier, "Start Frame").value = context.scene.frame_current
        modifier_input(modifier, "Subdivisions").value = subdivision_levels(
            ground, colliders, 2.0 * modifier_input(modifier, "Contact").value, EDGE_LENGTH * scale
        )
        if self.puddle:
            control, _, _ = new_control([ground], "Wet Footprints", CONTROL_TYPE)
            control.location = context.scene.cursor.location
            radius = PUDDLE_RADIUS * scale
            control.scale = (radius, radius, radius * 0.25)
            modifier_input(modifier, "Puddle").value = True
            modifier_input(modifier, "Control").value = control
        # Changing the modifier inputs from Python does not tag the object
        ground.update_tag()
        for material in materials([ground]):
            if not shader_nodes(material, FILM):
                groups = wrap_shader(material, FILM)
                normal = ops_wet.film_normal(material)
                for group in groups if normal else ():
                    material.node_tree.links.new(normal, group.inputs["Normal"])

        if not colliders:
            self.report(
                {"WARNING"},
                "MustardUI - Wet Footprints added, add the feet stepping on it to its Colliders.",
            )
            return {"FINISHED"}
        self.report({"INFO"}, f"MustardUI - Wet Footprints of {len(colliders)} objects added.")
        return {"FINISHED"}


class MustardUI_ModelToolkit_RemoveFootprints(bpy.types.Operator):
    """Remove the Wet Footprints from the selected meshes, the film from their materials not used by other meshes with them, and the Colliders and Controls not used anymore"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_remove_footprints"
    bl_label = "Remove Wet Footprints"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        return any(is_effect(m, NODE_GROUP) for x in context.selected_objects for m in x.modifiers)

    def execute(self, context):
        controls = {
            modifier_input(m, "Control").value
            for x in context.selected_objects
            for m in x.modifiers
            if is_effect(m, NODE_GROUP)
        }
        remove_with_colliders(context, NODE_GROUP)
        printed = [
            x for x in bpy.data.objects if any(is_effect(m, NODE_GROUP) for m in x.modifiers)
        ]
        used = {
            modifier_input(m, "Control").value
            for x in printed
            for m in x.modifiers
            if is_effect(m, NODE_GROUP)
        }
        for control in controls - used - {None}:
            if control.MustardUI_tools_creators_type == CONTROL_TYPE:
                bpy.data.objects.remove(control)
        for material in materials(context.selected_objects) - materials(printed):
            for group in shader_nodes(material, FILM):
                unwrap_shader(material, group)
            # The Normal Map added for the film, if not used by another one
            for node in [n for n in material.node_tree.nodes if n.get(ops_wet.NORMAL_TAG)]:
                if not node.outputs["Normal"].is_linked:
                    material.node_tree.nodes.remove(node)

        self.report({"INFO"}, "MustardUI - Wet Footprints removed.")
        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_Footprints)
    bpy.utils.register_class(MustardUI_ModelToolkit_RemoveFootprints)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_RemoveFootprints)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_Footprints)
