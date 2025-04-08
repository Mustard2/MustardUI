import bpy


# Outfit information
class MustardUI_Outfit(bpy.types.PropertyGroup):
    # Collection storing the outfit pieces
    collection: bpy.props.PointerProperty(name="Outfit Collection",
                                          type=bpy.types.Collection)


class MustardUI_OutfitSettings(bpy.types.PropertyGroup):

    # Function to enable/disable physics for the single outfit
    def update_physics(self, context):
        if self.id_data.modifiers is None:
            return

        for m in self.id_data.modifiers:
            if m.type in ["CLOTH", "SOFT_BODY"]:
                m.show_viewport = self.physics
                m.show_render = self.physics
            elif m.type in ["COLLISION"]:
                self.id_data.collision.use = self.physics

    physics: bpy.props.BoolProperty(default=False,
                                    name="Enable Physics",
                                    description="Enable Physics on the current Outfit piece",
                                    update=update_physics)

    # Variable to collapse children in Outfit pieces list
    collapse_children: bpy.props.BoolProperty(default=True, description="", name="")

    # Custom properties show
    additional_options_show: bpy.props.BoolProperty(default=False,
                                                    name="",
                                                    description="Show additional properties for the selected object")
    additional_options_show_lock: bpy.props.BoolProperty(default=False,
                                                         name="",
                                                         description="Show additional properties for the selected object")


def register():
    bpy.utils.register_class(MustardUI_Outfit)
    bpy.utils.register_class(MustardUI_OutfitSettings)

    bpy.types.Object.MustardUI_OutfitSettings = bpy.props.PointerProperty(type=MustardUI_OutfitSettings)

    bpy.types.Object.MustardUI_outfit_visibility = bpy.props.BoolProperty(default=False, name="")

    bpy.types.Object.MustardUI_outfit_lock = bpy.props.BoolProperty(default=False,
                                                                    name="",
                                                                    description="Lock/unlock the outfit")


def unregister():
    del bpy.types.Object.MustardUI_outfit_visibility

    del bpy.types.Object.MustardUI_OutfitSettings

    bpy.utils.unregister_class(MustardUI_Outfit)
