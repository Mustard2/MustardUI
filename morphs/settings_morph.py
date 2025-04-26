import bpy


class MustardUI_Morph(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Name")
    path: bpy.props.StringProperty(name="Path")

    # Types for generic Morphs
    shape_key: bpy.props.BoolProperty(default=False)
    custom_property: bpy.props.BoolProperty(default=True)


def register():
    bpy.utils.register_class(MustardUI_Morph)


def unregister():
    bpy.utils.unregister_class(MustardUI_Morph)
