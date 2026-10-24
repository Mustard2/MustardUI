import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree


def effects_available():
    return bpy.app.version >= (5, 2, 0)


def is_effect(modifier, node_group):
    return (
        modifier.type == "NODES"
        and modifier.node_group is not None
        and modifier.node_group.name.startswith(node_group)
    )


def modifier_input(modifier, name):
    identifier = next(
        x.identifier
        for x in modifier.node_group.interface.items_tree
        if x.item_type == "SOCKET" and x.in_out == "INPUT" and x.name == name
    )
    return getattr(modifier.properties.inputs, identifier)


def new_control(objects, effect, creators_type):
    """Empty at the center of the bounding box of the objects, returned with its corners"""
    corners = [obj.matrix_world @ Vector(c) for obj in objects for c in obj.bound_box]
    low = Vector([min(c[i] for c in corners) for i in range(3)])
    high = Vector([max(c[i] for c in corners) for i in range(3)])

    name = f"Effect Control {effect}"
    if len(objects) == 1:
        name = f"{objects[0].name} {name}"
    control = bpy.data.objects.new(name, None)
    objects[0].users_collection[0].objects.link(control)
    control.empty_display_type = "SPHERE"
    control.location = (low + high) / 2
    control.MustardUI_tools_creators_is_created = True
    control.MustardUI_tools_creators_type = creators_type
    return control, low, high


def parent_control(control, obj, vertex, depsgraph):
    """Parent the Control to the bone deforming the evaluated vertex the most, or to the mesh"""
    # The vertex in the original mesh from its rest position
    rest = obj.evaluated_get(depsgraph).data.attributes["rest_position"]
    rest = rest.data[vertex.index].vector
    kd = KDTree(len(obj.data.vertices))
    for x in obj.data.vertices:
        kd.insert(x.co, x.index)
    kd.balance()
    armature = next((m.object for m in obj.modifiers if m.type == "ARMATURE" and m.object), None)
    bones = armature.pose.bones if armature else {}
    group = max(
        (
            x
            for x in obj.data.vertices[kd.find(rest)[1]].groups
            if obj.vertex_groups[x.group].name in bones
        ),
        key=lambda x: x.weight,
        default=None,
    )
    if group:
        bone = bones[obj.vertex_groups[group.group].name]
        control.parent = armature
        control.parent_type = "BONE"
        control.parent_bone = bone.name
        # The bone parent matrix is at its tail
        parent = armature.matrix_world @ bone.matrix
        parent.translation = armature.matrix_world @ bone.tail
    else:
        control.parent = obj
        parent = obj.matrix_world
    control.matrix_parent_inverse = parent.inverted()


def add_effect_modifier(obj, name, node_group, control=None):
    modifier = obj.modifiers.new(name, "NODES")
    modifier.node_group = bpy.data.node_groups[node_group]
    if control:
        modifier_input(modifier, "Control").value = control

    # Before the subdivision, to work on the low poly mesh, and the strands, not to affect them.
    # Multires can't have modifiers above it
    index = next(
        (
            i
            for i, m in enumerate(obj.modifiers)
            if m.type == "SUBSURF" or is_effect(m, "MustardUI Sticky Strands")
        ),
        None,
    )
    if index is not None:
        obj.modifiers.move(len(obj.modifiers) - 1, index)
    return modifier


def materials(objects):
    return {
        s.material for x in objects for s in x.material_slots if s.material and s.material.node_tree
    }


def shader_nodes(material, node_group):
    return [
        n
        for n in material.node_tree.nodes
        if n.type == "GROUP" and n.node_tree and n.node_tree.name.startswith(node_group)
    ]


def wrap_shader(material, node_group):
    """Group nodes of the shader node group added between the surface shaders and the outputs"""
    nodes, links = material.node_tree.nodes, material.node_tree.links
    groups = []
    for output in [n for n in nodes if n.type == "OUTPUT_MATERIAL"]:
        surface = output.inputs["Surface"]
        if not surface.is_linked:
            continue
        group = nodes.new("ShaderNodeGroup")
        group.node_tree = bpy.data.node_groups[node_group]
        group.location = output.location
        output.location.x += 250
        links.new(surface.links[0].from_socket, group.inputs["Shader"])
        links.new(group.outputs["Shader"], surface)
        groups.append(group)
    return groups


def unwrap_shader(material, group):
    """Remove the group node, linking its shader input to its users"""
    nodes, links = material.node_tree.nodes, material.node_tree.links
    shader = group.inputs["Shader"].links
    for socket in [x.to_socket for x in group.outputs["Shader"].links]:
        if shader:
            links.new(shader[0].from_socket, socket)
        if socket.node.type == "OUTPUT_MATERIAL":
            socket.node.location = group.location
    nodes.remove(group)


class RemoveEffect:
    """Base of the operators removing an effect, and its Controls not used anymore"""

    bl_options = {"UNDO"}

    effect = ""
    node_group = ""
    creators_type = ""
    done = "removed"

    @classmethod
    def poll(cls, context):
        return any(
            is_effect(m, cls.node_group) for x in context.selected_objects for m in x.modifiers
        )

    def execute(self, context):
        controls = set()
        for obj in context.selected_objects:
            for modifier in [m for m in obj.modifiers if is_effect(m, self.node_group)]:
                controls.add(modifier_input(modifier, "Control").value)
                obj.modifiers.remove(modifier)

        used = {
            modifier_input(m, "Control").value
            for x in bpy.data.objects
            for m in x.modifiers
            if is_effect(m, self.node_group)
        }
        for control in controls - used - {None}:
            if control.MustardUI_tools_creators_type == self.creators_type:
                bpy.data.objects.remove(control)

        self.report({"INFO"}, f"MustardUI - {self.effect} {self.done}.")
        return {"FINISHED"}
