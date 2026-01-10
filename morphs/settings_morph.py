import bpy

cp_source = [("ARMATURE_OBJ", "Armature Object", "Armature Object", "OUTLINER_OB_ARMATURE", 0),
             ("ARMATURE_DATA", "Armature Data", "Armature Data", "ARMATURE_DATA", 1),
             ("BODY_OBJ", "Body Object", "Body Object", "OUTLINER_OB_MESH", 2),
             ("BODY_DATA", "Body Data", "Body Data", "MESH_DATA", 3)]


class MustardUI_Morph(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Name")
    path: bpy.props.StringProperty(name="Path")

    # Types for generic Morphs
    shape_key: bpy.props.BoolProperty(default=False)
    custom_property: bpy.props.BoolProperty(default=True)
    custom_property_source: bpy.props.EnumProperty(items=cp_source,
                                                   default="ARMATURE_OBJ")


class MustardUI_PresetMorph(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Name")
    path: bpy.props.StringProperty(name="Path")

    # Types for generic Morphs
    shape_key: bpy.props.BoolProperty(default=False)
    custom_property: bpy.props.BoolProperty(default=True)
    custom_property_source: bpy.props.EnumProperty(items=cp_source,
                                                   default="ARMATURE_OBJ")

    # Stored for presets usage
    value: bpy.props.FloatProperty(name="Name")


def register():
    bpy.utils.register_class(MustardUI_Morph)
    bpy.utils.register_class(MustardUI_PresetMorph)


def unregister():
    bpy.utils.unregister_class(MustardUI_PresetMorph)
    bpy.utils.unregister_class(MustardUI_Morph)
