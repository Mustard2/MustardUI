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
