import bpy
from ..model_selection.active_object import *
from .settings_item import MustardUI_PhysicsItem, mustardui_physics_item_type_dict
from .update_enable import enable_physics_update


def update_frame(self, context):

    # Rigid Body
    if context.scene.rigidbody_world:
        context.scene.rigidbody_world.point_cache.frame_start = self.frame_start
        context.scene.rigidbody_world.point_cache.frame_end = self.frame_end

    for pi in [x for x in self.items if x.type in ["CAGE", "SINGLE_ITEM", "BONES_DRIVER"]]:
        obj = pi.object
        for md in obj.modifiers:
            if md.type in ["CLOTH", "SOFT_BODY"] and not pi.unique_cache_frames:
                md.point_cache.frame_start = self.frame_start
                md.point_cache.frame_end = self.frame_end
            elif md.type == "PARTICLE_SYSTEM":
                psys = md.particle_system
                if psys.point_cache:
                    psys.point_cache.frame_start = self.frame_start
                    psys.point_cache.frame_end = self.frame_end
            #elif md.type == "DYNAMIC_PAINT":
            #    for canvas in md.canvas_settings.canvas_surfaces:
            #        canvas.frame_start = self.frame_start
            #        canvas.frame_end = self.frame_end
    return


class MustardUI_PhysicsSettings(bpy.types.PropertyGroup):
    # CONFIGURATION

    # Enable Physics Panel
    enable_ui: bpy.props.BoolProperty(default=False,
                                      name="Enable Physics",
                                      description="Enable Physics panel and tools in the UI")

    # Mirror
    mirror: bpy.props.BoolProperty(default=False,
                                   name="Mirror",
                                   description="If two Cage Objects with .r/.l or .R/.L are available in the Physics "
                                               "Items list, show only one panel which updates both in the UI")

    # UI

    # Switcher for Physics
    enable_physics: bpy.props.BoolProperty(default=False,
                                           name="",
                                           description="Enable Physics for the current model",
                                           update=enable_physics_update)

    # Bake settings
    frame_start: bpy.props.IntProperty(default=1, min=0, max=1048574,
                                       description="Frame on which the simulation start",
                                       name="Start",
                                       update=update_frame)
    frame_end: bpy.props.IntProperty(default=250, min=0, max=1048574,
                                     description="Frame on which the simulation stops",
                                     name="End",
                                     update=update_frame)

    # INTERNAL

    # Physics Items
    items: bpy.props.CollectionProperty(name="Outfits Collection List",
                                        type=MustardUI_PhysicsItem)


def register():
    bpy.utils.register_class(MustardUI_PhysicsSettings)
    bpy.types.Armature.MustardUI_PhysicsSettings = bpy.props.PointerProperty(type=MustardUI_PhysicsSettings)


def unregister():
    del bpy.types.Armature.MustardUI_PhysicsSettings
    bpy.utils.unregister_class(MustardUI_PhysicsSettings)
