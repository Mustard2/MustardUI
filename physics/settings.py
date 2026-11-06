import bpy

from ..misc.geometry_nodes import simulation_bakes
from .settings_item import MustardUI_PhysicsItem
from .settings_presets import MustardUI_Physics_Preset
from .update_enable import enable_physics_update


def physics_objects(physics_settings):
    """Objects with the physics of the model: the Physics Items, the outfits, extras and hair"""
    rig_settings = physics_settings.id_data.MustardUI_RigSettings
    objects = [
        pi.object
        for pi in physics_settings.items
        if pi.object is not None and pi.type in ["CAGE", "SINGLE_ITEM", "BONES_DRIVER"]
    ]

    if rig_settings.outfit_physics_support:
        for coll in [x.collection for x in rig_settings.outfits_collections if x.collection]:
            items = coll.all_objects if rig_settings.outfit_config_subcollections else coll.objects
            objects += [x for x in items if x.type == "MESH"]

        extras = rig_settings.extras_collection
        if extras is not None:
            items = (
                extras.all_objects if rig_settings.extras_config_subcollections else extras.objects
            )
            objects += [x for x in items if x.type == "MESH"]

    if rig_settings.hair_collection is not None:
        objects += [x for x in rig_settings.hair_collection.objects if x.type == "MESH"]

    return list(dict.fromkeys(objects))


def update_frame(self, context):

    unique_objects = {x.object for x in self.items if x.object and x.unique_cache_frames}

    # Rigid Body
    if context.scene.rigidbody_world:
        context.scene.rigidbody_world.point_cache.frame_start = self.frame_start
        context.scene.rigidbody_world.point_cache.frame_end = self.frame_end

    for obj in physics_objects(self):
        unique = obj in unique_objects
        for md in obj.modifiers:
            if md.type in ["CLOTH", "SOFT_BODY"] and not unique:
                md.point_cache.frame_start = self.frame_start
                md.point_cache.frame_end = self.frame_end
            elif md.type == "PARTICLE_SYSTEM":
                psys = md.particle_system
                if psys.point_cache:
                    psys.point_cache.frame_start = self.frame_start
                    psys.point_cache.frame_end = self.frame_end
        if not unique:
            for _, bake in simulation_bakes(obj):
                bake.use_custom_simulation_frame_range = True
                bake.frame_start = self.frame_start
                bake.frame_end = self.frame_end


def poll_mesh(self, o):
    return o.type == "MESH"


class MustardUI_PhysicsSettings(bpy.types.PropertyGroup):
    # CONFIGURATION

    # Enable Physics Panel
    enable_ui: bpy.props.BoolProperty(
        default=False,
        name="Enable Physics",
        description="Enable Physics panel and tools in the UI",
    )

    # Mirror
    mirror: bpy.props.BoolProperty(
        default=False,
        name="Mirror",
        description="If two Cage Objects with .r/.l or .R/.L are available in the "
        "Physics Items list, show only one panel which updates both in the UI",
    )

    # UI

    # Switcher for Physics
    enable_physics: bpy.props.BoolProperty(
        default=False,
        name="",
        description="Enable Physics for the current model",
        update=enable_physics_update,
    )

    # Bake settings
    frame_start: bpy.props.IntProperty(
        default=1,
        min=0,
        max=1048574,
        description="Frame on which the simulation start",
        name="Start",
        update=update_frame,
    )
    frame_end: bpy.props.IntProperty(
        default=250,
        min=0,
        max=1048574,
        description="Frame on which the simulation stops",
        name="End",
        update=update_frame,
    )

    # Outfits Setup: optional custom Surface Deform target (uses the body if None)
    outfits_setup_surface_deform_target: bpy.props.PointerProperty(
        name="Target",
        description="Mesh to use as the Surface Deform target instead of the body.\n"
        "Leave empty to use the body mesh",
        type=bpy.types.Object,
        poll=poll_mesh,
    )

    # INTERNAL

    # Physics Items
    items: bpy.props.CollectionProperty(type=MustardUI_PhysicsItem)

    presets: bpy.props.CollectionProperty(type=MustardUI_Physics_Preset)


def register():
    bpy.utils.register_class(MustardUI_PhysicsSettings)
    bpy.types.Armature.MustardUI_PhysicsSettings = bpy.props.PointerProperty(
        type=MustardUI_PhysicsSettings
    )


def unregister():
    del bpy.types.Armature.MustardUI_PhysicsSettings
    bpy.utils.unregister_class(MustardUI_PhysicsSettings)
