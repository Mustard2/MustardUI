import os

import bpy

from . import ops_wet
from .effect import (
    SETTINGS,
    RemoveEffect,
    add_effect_modifier,
    effects_available,
    is_effect,
    materials,
    modifier_input,
    new_control,
    parent_control,
    settings_group,
    shader_nodes,
    unwrap_shader,
    wrap_shader,
)

NODE_GROUP = "MustardUI Dirt"
FILM = "MustardUI Dirt Film"
MATERIAL = "MustardUI Dirt Grains"
CONTROL_TYPE = "EFFECT_DIRT"
RESOURCE = os.path.join(os.path.dirname(__file__), "resources", "dirt.blend")
# Share of the Control radius the bounding box of the meshes is within
COVER = 0.55
# Modifier and film inputs of each kind of dirt
PRESETS = {
    "MUD": (
        {"Ground": 1.0, "Cavities": 0.3, "Grains": True, "Density": 2000.0},
        {
            "Color": (0.11, 0.055, 0.025, 1.0),
            "Roughness": 0.85,
            "Coverage": 0.6,
            "Stain": 0.5,
            "Moisture": 0.5,
            "Cracks": 0.5,
            "Splatter": 0.5,
            "Bump": 0.5,
        },
    ),
    "DUST": (
        {"Ground": 0.3, "Cavities": 0.6, "Grains": False},
        {
            "Color": (0.36, 0.27, 0.19, 1.0),
            "Roughness": 1.0,
            "Coverage": 0.3,
            "Stain": 0.8,
            "Moisture": 0.0,
            "Cracks": 0.0,
            "Splatter": 0.2,
            "Bump": 0.1,
        },
    ),
    "GRIME": (
        {"Ground": 0.2, "Cavities": 0.7, "Grains": False},
        {
            "Color": (0.04, 0.035, 0.03, 1.0),
            "Roughness": 0.6,
            "Coverage": 0.15,
            "Stain": 0.7,
            "Moisture": 0.1,
            "Cracks": 0.0,
            "Splatter": 0.3,
            "Bump": 0.05,
        },
    ),
    "SAND": (
        {
            "Ground": 0.6,
            "Cavities": 0.3,
            "Grains": True,
            "Density": 40000.0,
            "Min Size": 0.0002,
            "Max Size": 0.0008,
        },
        {
            "Color": (0.5, 0.34, 0.17, 1.0),
            "Roughness": 0.9,
            "Coverage": 0.3,
            "Stain": 0.4,
            "Moisture": 0.2,
            "Cracks": 0.0,
            "Splatter": 0.0,
            "Bump": 0.2,
        },
    ),
}


class MustardUI_ModelToolkit_Dirt(bpy.types.Operator):
    """Dirty the selected meshes inside the sphere of a Control Empty covering them, the bottom of the sphere the dirtiest, with grains of dirt and a layer of dirt on their materials.\nThe dirt shows only on the meshes with the effect, its shader settings are shared by them\nBlender 5.2 or above is required"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_dirt"
    bl_label = "Add Dirt"
    bl_options = {"REGISTER", "UNDO"}

    kind: bpy.props.EnumProperty(
        name="Kind",
        items=(
            ("MUD", "Mud", "Brown mud splashed from the ground, cracking as it dries"),
            ("DUST", "Dust", "Pale dust in the creases"),
            ("GRIME", "Grime", "Dark smudges of grime and soot"),
            ("SAND", "Sand", "Grains of sand stuck on the skin"),
        ),
        description="Kind of dirt, setting the shader of all the dirty meshes",
    )

    @classmethod
    def poll(cls, context):
        return effects_available() and any(x.type == "MESH" for x in context.selected_objects)

    def execute(self, context):
        objects = [x for x in context.selected_objects if x.type == "MESH"]

        with bpy.data.libraries.load(RESOURCE) as (_, data):
            data.node_groups = [x for x in (NODE_GROUP, FILM) if x not in bpy.data.node_groups]
            if MATERIAL not in bpy.data.materials:
                data.materials = [MATERIAL]

        # The dirt placed on the rest mesh, not to move on the deformed one
        for obj in objects:
            obj.add_rest_position_attribute = True
        depsgraph = context.evaluated_depsgraph_get()

        # Covering the meshes, following the vertex closest to its center
        control, low, high = new_control(objects, "Dirt", CONTROL_TYPE)
        radius = (high - low).length / 2 / COVER
        control.scale = (radius, radius, radius)
        source, vertex = min(
            ((x, v) for x in objects for v in x.evaluated_get(depsgraph).data.vertices),
            key=lambda p: (p[0].matrix_world @ p[1].co - control.location).length_squared,
        )
        parent_control(control, source, vertex, depsgraph)
        # In the scene collection, not to be listed only under its bone parent in the Outliner
        control.users_collection[0].objects.unlink(control)
        context.scene.collection.objects.link(control)

        inputs, film = PRESETS[self.kind]
        for obj in objects:
            modifier = add_effect_modifier(obj, "Dirt", NODE_GROUP, control)
            for name, value in inputs.items():
                modifier_input(modifier, name).value = value
            modifier_input(modifier, "Material").value = bpy.data.materials[MATERIAL]
            modifier_input(modifier, "Start Frame").value = context.scene.frame_current
            # Changing the modifier inputs from Python does not tag the object
            obj.update_tag()
        for material in materials(objects) | {bpy.data.materials[MATERIAL]}:
            if not shader_nodes(material, FILM):
                groups = wrap_shader(material, FILM)
                normal = ops_wet.film_normal(material)
                for group in groups if normal else ():
                    material.node_tree.links.new(normal, group.inputs["Normal"])
        settings = settings_group(FILM).nodes[SETTINGS]
        for name, value in film.items():
            settings.inputs[name].default_value = value

        self.report({"INFO"}, f"MustardUI - Dirt added to {len(objects)} objects.")
        return {"FINISHED"}


class MustardUI_ModelToolkit_RemoveDirt(RemoveEffect, bpy.types.Operator):
    """Remove the Dirt from the selected meshes, the dirt layer from their materials not used by other dirty meshes, and the Controls not used anymore"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_remove_dirt"
    bl_label = "Remove Dirt"

    effect = "Dirt"
    node_group = NODE_GROUP
    creators_type = CONTROL_TYPE

    def execute(self, context):
        result = super().execute(context)
        dirty = materials(
            x for x in bpy.data.objects if any(is_effect(m, NODE_GROUP) for m in x.modifiers)
        )
        for material in materials(context.selected_objects) - dirty:
            for group in shader_nodes(material, FILM):
                unwrap_shader(material, group)
            # The Normal Map added for the film, if not used by another one
            nodes = material.node_tree.nodes
            for node in [n for n in nodes if n.get(ops_wet.NORMAL_TAG)]:
                if not node.outputs["Normal"].is_linked:
                    nodes.remove(node)
        return result


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_Dirt)
    bpy.utils.register_class(MustardUI_ModelToolkit_RemoveDirt)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_RemoveDirt)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_Dirt)
