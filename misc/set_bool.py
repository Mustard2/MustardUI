import bpy


# Helper to set a boolean attribute only if it differs from the current value
def set_bool(obj, attr, value):
    if getattr(obj, attr) != value:
        setattr(obj, attr, value)
