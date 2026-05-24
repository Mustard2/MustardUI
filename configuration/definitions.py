import bpy


class MustardUI_QuickSetupOutfit(bpy.types.PropertyGroup):
    collection: bpy.props.PointerProperty(name="Collection", type=bpy.types.Collection)
    enabled: bpy.props.BoolProperty(name="Include as Outfit", default=False)


class MustardUI_QuickSetupHairObject(bpy.types.PropertyGroup):
    object: bpy.props.PointerProperty(name="Object", type=bpy.types.Object)
    enabled: bpy.props.BoolProperty(name="Include as Hair", default=False)


def register():
    from ..settings.rig import MustardUI_RigSettings

    bpy.utils.register_class(MustardUI_QuickSetupOutfit)
    bpy.utils.register_class(MustardUI_QuickSetupHairObject)

    MustardUI_RigSettings.quick_setup_outfit_collections = bpy.props.CollectionProperty(
        type=MustardUI_QuickSetupOutfit
    )
    MustardUI_RigSettings.quick_setup_outfit_index = bpy.props.IntProperty(
        name="", default=0
    )
    MustardUI_RigSettings.quick_setup_hair_objects = bpy.props.CollectionProperty(
        type=MustardUI_QuickSetupHairObject
    )
    MustardUI_RigSettings.quick_setup_hair_index = bpy.props.IntProperty(
        name="", default=0
    )


def unregister():
    from ..settings.rig import MustardUI_RigSettings

    del MustardUI_RigSettings.quick_setup_hair_index
    del MustardUI_RigSettings.quick_setup_hair_objects
    del MustardUI_RigSettings.quick_setup_outfit_index
    del MustardUI_RigSettings.quick_setup_outfit_collections

    bpy.utils.unregister_class(MustardUI_QuickSetupHairObject)
    bpy.utils.unregister_class(MustardUI_QuickSetupOutfit)
