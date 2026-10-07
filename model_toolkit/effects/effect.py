import bpy
from mathutils import Vector


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


def add_effect_modifier(obj, name, node_group, control):
    modifier = obj.modifiers.new(name, "NODES")
    modifier.node_group = bpy.data.node_groups[node_group]
    modifier_input(modifier, "Control").value = control

    # Before the subdivision, to work on the low poly mesh
    subdivision = next(
        (i for i, m in enumerate(obj.modifiers) if m.type in {"SUBSURF", "MULTIRES"}), None
    )
    if subdivision is not None:
        obj.modifiers.move(len(obj.modifiers) - 1, subdivision)
    return modifier


class RemoveEffect:
    """Base of the operators removing an effect, and its Controls not used anymore"""

    bl_options = {"UNDO"}

    effect = ""
    node_group = ""
    creators_type = ""

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

        self.report({"INFO"}, f"MustardUI - {self.effect} removed.")
        return {"FINISHED"}
