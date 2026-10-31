import os

import bpy
from mathutils import Matrix, Vector

from .effect import (
    RemoveEffect,
    add_effect_modifier,
    effects_available,
    is_effect,
    materials,
    modifier_input,
    new_control,
    settings_group,
    shader_nodes,
    unwrap_shader,
)

NODE_GROUP = "MustardUI Aura"
GLOW = "MustardUI Aura Glow"
MATERIAL = "MustardUI Aura Sparks"
CONTROL_TYPE = "EFFECT_AURA"
HOT_SPOT_TYPE = "EFFECT_AURA_HOT_SPOT"
RESOURCE = os.path.join(os.path.dirname(__file__), "resources", "aura.blend")
# Deform groups of the hands and feet of the MHX rigs, the Hot Spots Empties put on them
HOT_SPOT_GROUPS = (
    "hand.",
    "palm_",
    "thumb.",
    "f_index.",
    "f_middle.",
    "f_ring.",
    "f_pinky.",
    "foot.",
    "tarsal.",
    "toe.",
    "big_toe.",
    "small_toe_",
)
FOOT_GROUPS = ("foot.", "tarsal.", "toe.", "big_toe.", "small_toe_")
# Weight of the vertices on a hand or foot, and the radius of its Empty around them
HOT_SPOT_WEIGHT = 0.5
HOT_SPOT_MARGIN = 1.15
TRANSPARENT = {"BSDF_TRANSPARENT", "HOLDOUT"}


def glow_sockets(socket):
    """Shader sockets of the shaders linked to the socket, under their mixes with transparency"""
    if not socket.is_linked:
        return
    node = socket.links[0].from_node
    shaders = [x for x in node.inputs if x.type == "SHADER" and x.is_linked]
    transparent_group = node.type == "GROUP" and any(
        n.type in TRANSPARENT for n in node.node_tree.nodes
    )
    if node.type in {"MIX_SHADER", "ADD_SHADER"} or (transparent_group and shaders):
        for x in shaders:
            if x.links[0].from_node.type not in TRANSPARENT:
                yield from glow_sockets(x)
    elif node.type not in TRANSPARENT:
        yield socket


def wrap_glow(material):
    """Glow group nodes added after the shaders, given their alpha"""
    nodes, links = material.node_tree.nodes, material.node_tree.links
    outputs = [n for n in nodes if n.type == "OUTPUT_MATERIAL"]
    for socket in {x for o in outputs for x in glow_sockets(o.inputs["Surface"])}:
        source = socket.links[0].from_socket
        group = nodes.new("ShaderNodeGroup")
        group.node_tree = settings_group(GLOW)
        group.location = (source.node.location.x + 250, source.node.location.y + 150)
        links.new(source, group.inputs["Shader"])
        links.new(group.outputs["Shader"], socket)
        alpha = source.node.inputs.get("Alpha")
        if alpha is None:
            continue
        if alpha.is_linked:
            links.new(alpha.links[0].from_socket, group.inputs["Opacity"])
        else:
            group.inputs["Opacity"].default_value = alpha.default_value


def hot_spot_groups(obj):
    """Deform groups of the hands and feet of the mesh"""
    if obj.type != "MESH":
        return []
    return [x for x in obj.vertex_groups if x.name.startswith(HOT_SPOT_GROUPS)]


def add_hot_spots(context, armature, obj):
    """Collection of Empties on the bones of the hands and feet, around their vertices"""
    clusters = {}
    for group in hot_spot_groups(obj):
        limb = "Foot" if group.name.startswith(FOOT_GROUPS) else "Hand"
        clusters.setdefault((limb, group.name.rsplit(".", 1)[-1]), []).append(group)

    collection = bpy.data.collections.new(f"{armature.name} Aura Hot Spots")
    context.scene.collection.children.link(collection)
    # The mesh at rest in the armature space
    to_armature = armature.matrix_world.inverted() @ obj.matrix_world
    for (limb, side), groups in clusters.items():
        indices = {x.index for x in groups}
        weights = dict.fromkeys(indices, 0.0)
        points = []
        for vertex in obj.data.vertices:
            weight = 0.0
            for x in vertex.groups:
                if x.group in indices:
                    weight += x.weight
                    weights[x.group] += x.weight
            if weight >= HOT_SPOT_WEIGHT:
                points.append(to_armature @ vertex.co)
        bones = [x for x in groups if x.name in armature.data.bones]
        if not points or not bones:
            continue
        center = sum(points, Vector()) / len(points)
        radius = max((x - center).length for x in points) * HOT_SPOT_MARGIN

        # On the hand or foot bone, else the one moving the most of them, where they are in the pose
        bones = [x for x in bones if x.name.startswith(("hand.", "foot."))] or bones
        bone = max(bones, key=lambda x: weights[x.index]).name
        rest = armature.data.bones[bone].matrix_local
        posed = armature.pose.bones[bone].matrix @ rest.inverted() @ center
        empty = bpy.data.objects.new(f"{armature.name} Aura {limb}.{side}", None)
        collection.objects.link(empty)
        empty.empty_display_type = "SPHERE"
        empty.MustardUI_tools_creators_is_created = True
        empty.MustardUI_tools_creators_type = HOT_SPOT_TYPE
        empty.parent = armature
        empty.parent_type = "BONE"
        empty.parent_bone = bone
        scale = radius * armature.matrix_world.to_scale().x
        empty.matrix_world = Matrix.LocRotScale(armature.matrix_world @ posed, None, (scale,) * 3)
    return collection


class MustardUI_ModelToolkit_Aura(bpy.types.Operator):
    """Make the selected meshes glow in pulses and throw sparks rising from them, by the Glow of a Control Empty at the feet of their model.\nOn MHX models only the outline of the hands and feet glows\nBlender 5.2 or above is required"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_aura"
    bl_label = "Add Aura"
    bl_options = {"REGISTER", "UNDO"}

    pulses: bpy.props.IntProperty(
        name="Pulses", default=3, min=1, max=20, description="Times the meshes glow"
    )
    duration: bpy.props.IntProperty(
        name="Duration", default=36, min=4, description="Frames of each pulse"
    )
    pause: bpy.props.IntProperty(
        name="Pause", default=24, min=2, description="Frames between the pulses"
    )

    @classmethod
    def poll(cls, context):
        return effects_available() and any(
            x.type in {"MESH", "CURVES"} for x in context.selected_objects
        )

    def add_control(self, context, root):
        """Empty at the feet of the model, following it, its Glow keyed in pulses"""
        meshes = [x for x in root.children_recursive if x.type == "MESH" and x.visible_get()]
        control, low, high = new_control(meshes or [root], "Aura", CONTROL_TYPE)
        # In the scene collection, out of the outfit collections not to be part of an outfit
        control.users_collection[0].objects.unlink(control)
        context.scene.collection.objects.link(control)
        control.empty_display_type = "SINGLE_ARROW"
        control.empty_display_size = high.z - low.z
        control.location = ((low.x + high.x) / 2, (low.y + high.y) / 2, low.z)
        control.parent = root
        control.matrix_parent_inverse = root.matrix_world.inverted()

        control["Glow"] = 0.0
        control.id_properties_ui("Glow").update(
            min=0.0, soft_max=1.0, description="How much the model glows"
        )
        start = context.scene.frame_current
        fade = min(self.pause, self.duration) / 2
        for _ in range(self.pulses):
            end = start + self.duration
            for f, glow in (
                (start, 0.0),
                (start + self.duration / 4, 1.0),
                (end, 1.0),
                (end + fade, 0.0),
            ):
                control["Glow"] = glow
                control.keyframe_insert('["Glow"]', frame=f)
            start = end + self.pause
        control["Glow"] = 0.0
        return control

    def execute(self, context):
        objects = [x for x in context.selected_objects if x.type in {"MESH", "CURVES"}]

        with bpy.data.libraries.load(RESOURCE) as (_, data):
            data.node_groups = [x for x in (NODE_GROUP, GLOW) if x not in bpy.data.node_groups]
            if MATERIAL not in bpy.data.materials:
                data.materials = [MATERIAL]

        controls, hot_spots = {}, {}
        for obj in objects:
            root = obj.find_armature() or obj
            if root not in controls:
                control = next(
                    (x for x in root.children if x.MustardUI_tools_creators_type == CONTROL_TYPE),
                    None,
                )
                controls[root] = control or self.add_control(context, root)
                # The Hot Spots of the model, or new ones on the hands and feet of MHX models
                hot_spots[root] = next(
                    (
                        modifier_input(m, "Hot Spots").value
                        for x in root.children_recursive
                        for m in x.modifiers
                        if is_effect(m, NODE_GROUP)
                    ),
                    None,
                )
                source = max(
                    (x for x in objects if (x.find_armature() or x) == root and hot_spot_groups(x)),
                    key=lambda x: len(x.data.vertices),
                    default=None,
                )
                if hot_spots[root] is None and source is not None and root.type == "ARMATURE":
                    hot_spots[root] = add_hot_spots(context, root, source)
            if any(is_effect(m, NODE_GROUP) for m in obj.modifiers):
                continue

            if obj.type == "MESH":
                # The shimmer and sparks placed on the rest mesh, not to move on the deformed one
                obj.add_rest_position_attribute = True
            modifier = add_effect_modifier(obj, "Aura", NODE_GROUP, controls[root])
            # Blender 5.2.0 does not set the material inputs to their defaults
            modifier_input(modifier, "Sparks Material").value = bpy.data.materials[MATERIAL]
            driver = modifier_input(modifier, "Glow").driver_add("value").driver
            variable = driver.variables.new()
            variable.targets[0].id = controls[root]
            variable.targets[0].data_path = '["Glow"]'
            driver.expression = variable.name
            if hot_spots[root] is not None:
                modifier_input(modifier, "Hot Spots").value = hot_spots[root]
                # The outline on the Hot Spots only
                modifier_input(modifier, "Body Glow").value = 0.0
            # Changing the modifier inputs from Python does not tag the object
            obj.update_tag()
        for material in materials(objects):
            if not shader_nodes(material, GLOW):
                wrap_glow(material)

        self.report({"INFO"}, f"MustardUI - Aura added to {len(objects)} objects.")
        return {"FINISHED"}


class MustardUI_ModelToolkit_RemoveAura(RemoveEffect, bpy.types.Operator):
    """Remove the Aura from the selected meshes, the glow from their materials not used by other meshes with it, and the Controls and Hot Spots not used anymore"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_remove_aura"
    bl_label = "Remove Aura"

    effect = "Aura"
    node_group = NODE_GROUP
    creators_type = CONTROL_TYPE

    def execute(self, context):
        selected = set(context.selected_objects)
        collections = set()
        for obj in selected:
            for modifier in [m for m in obj.modifiers if is_effect(m, NODE_GROUP)]:
                modifier_input(modifier, "Glow").driver_remove("value")
                collections.add(modifier_input(modifier, "Hot Spots").value)
        result = super().execute(context)
        used = {
            modifier_input(m, "Hot Spots").value
            for x in bpy.data.objects
            for m in x.modifiers
            if is_effect(m, NODE_GROUP)
        }
        # The Empties added on the hands and feet, others kept in the scene
        for collection in collections - used - {None}:
            for obj in list(collection.objects):
                if obj.MustardUI_tools_creators_type == HOT_SPOT_TYPE:
                    bpy.data.objects.remove(obj)
                elif len(obj.users_collection) == 1:
                    context.scene.collection.objects.link(obj)
            bpy.data.collections.remove(collection)
        glowing = materials(
            x for x in bpy.data.objects if any(is_effect(m, NODE_GROUP) for m in x.modifiers)
        )
        for material in materials(selected) - glowing:
            for group in shader_nodes(material, GLOW):
                unwrap_shader(material, group)
        return result


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_Aura)
    bpy.utils.register_class(MustardUI_ModelToolkit_RemoveAura)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_RemoveAura)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_Aura)
