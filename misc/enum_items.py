# Blender needs the strings returned by an EnumProperty items callback to stay referenced
_enum_strings = {}


def keep_enum_strings(items):
    """Return the items of an EnumProperty items callback with their strings kept alive."""
    return [
        tuple(_enum_strings.setdefault(x, x) if isinstance(x, str) else x for x in item)
        for item in items
    ]
