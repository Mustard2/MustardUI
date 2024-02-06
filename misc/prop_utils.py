import bpy


def property_value(obj, prop):
    if hasattr(obj, prop):
        return eval("obj." + prop) if hasattr(obj, prop) else False
    return False
