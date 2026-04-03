import bpy


class MustardUI_Physics_Preset(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Name")

    # Preset data in Json format
    data: bpy.props.StringProperty()

    has_cloth: bpy.props.BoolProperty()
    has_soft_body: bpy.props.BoolProperty()
    has_collision: bpy.props.BoolProperty()


def register():
    bpy.utils.register_class(MustardUI_Physics_Preset)


def unregister():
    bpy.utils.unregister_class(MustardUI_Physics_Preset)
