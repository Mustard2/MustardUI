import bpy


def surface_deform_bind(obj, modifier):
    """Bind the Surface Deform again, to the target without subdivision and
    triangulating it while binding if refused"""

    def attempt():
        # A failed bind leaves its flag set, and the next call only clears it
        for _ in range(2):
            with bpy.context.temp_override(object=obj, active_object=obj):
                bpy.ops.object.surfacedeform_bind(modifier=modifier.name)
            if modifier.is_bound:
                return True
        return False

    # The operator unbinds the bound modifiers
    if modifier.is_bound:
        with bpy.context.temp_override(object=obj, active_object=obj):
            bpy.ops.object.surfacedeform_bind(modifier=modifier.name)
    target = modifier.target
    if target is None or target.library is not None:
        return attempt()

    # A binding without subdivision works at any level, while one made at a
    # level breaks at the lower ones
    subdivisions = [
        m for m in target.modifiers if m.type in {"SUBSURF", "MULTIRES"} and m.show_viewport
    ]
    triangulate = None
    try:
        for m in subdivisions:
            m.show_viewport = False
        bpy.context.view_layer.update()
        if not attempt():
            # Concave polygons are refused. The binding only stores the target
            # vertices, which Triangulate keeps, so it works once it is removed
            triangulate = target.modifiers.new("MustardUI Bind Triangulate", "TRIANGULATE")
            bpy.context.view_layer.update()
            attempt()
    finally:
        if triangulate is not None:
            target.modifiers.remove(triangulate)
        for m in subdivisions:
            m.show_viewport = True
        bpy.context.view_layer.update()
    return modifier.is_bound
