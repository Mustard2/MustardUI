import bpy


# Move a modifier to index without the operator, which needs an active object and is slow
def move_modifier(obj, modifier, index):
    from_index = obj.modifiers.find(modifier.name)
    if from_index == index:
        return
    try:
        obj.modifiers.move(from_index, index)
    except RuntimeError:
        pass
    # Blocked move (move() fails, sometimes silently): the operator moves as far as allowed
    if obj.modifiers.find(modifier.name) != index:
        with bpy.context.temp_override(object=obj, active_object=obj):
            bpy.ops.object.modifier_move_to_index(modifier=modifier.name, index=index)


# Move a modifier after the last Armature and the Surface Deform/Corrective Smooth after it
def move_modifier_after_armature(obj, modifier):
    mods = list(obj.modifiers)
    arm_index = max((i for i, m in enumerate(mods) if m.type == "ARMATURE"), default=None)
    if arm_index is None:
        return
    index = arm_index + 1
    while (
        index < len(mods)
        and mods[index] != modifier
        and mods[index].type in {"SURFACE_DEFORM", "CORRECTIVE_SMOOTH"}
    ):
        index += 1
    # Moving down, the modifier leaves a gap above the target
    from_index = mods.index(modifier)
    move_modifier(obj, modifier, index if from_index >= index else index - 1)
