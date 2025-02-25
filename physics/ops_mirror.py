import bpy
from ..model_selection.active_object import *
from ..misc.mirror import check_mirror


def mirror_cloth(obj, obj_mirror) -> bool:

    cloth = None
    cache = None
    collisions = None
    for m in obj.modifiers:
        if m.type == "CLOTH":
            cloth = m.settings
            cache = m.point_cache
            collisions = m.collision_settings
            break
    if cloth is None:
        return False

    cloth_mirror = None
    cache_mirror = None
    collisions_mirror = None
    for m in obj_mirror.modifiers:
        if m.type == "CLOTH":
            cloth_mirror = m.settings
            cache_mirror = m.point_cache
            collisions_mirror = m.collision_settings
            break
    if cloth_mirror is None:
        return False

    # Copy settings
    cloth_mirror.quality = cloth.quality

    cloth_mirror.time_scale = cloth.time_scale
    cloth_mirror.mass = cloth.mass
    cloth_mirror.air_damping = cloth.air_damping

    cloth_mirror.tension_stiffness = cloth.tension_stiffness
    cloth_mirror.compression_stiffness = cloth.compression_stiffness
    cloth_mirror.shear_stiffness = cloth.shear_stiffness
    cloth_mirror.bending_stiffness = cloth.bending_stiffness

    cloth_mirror.tension_damping = cloth.tension_damping
    cloth_mirror.compression_damping = cloth.compression_damping
    cloth_mirror.shear_damping = cloth.shear_damping
    cloth_mirror.bending_damping = cloth.bending_damping

    cloth_mirror.use_internal_springs = cloth.use_internal_springs
    cloth_mirror.internal_spring_max_length = cloth.internal_spring_max_length
    cloth_mirror.internal_spring_max_diversion = cloth.internal_spring_max_diversion
    cloth_mirror.internal_spring_normal_check = cloth.internal_spring_normal_check
    cloth_mirror.internal_tension_stiffness = cloth.internal_tension_stiffness
    cloth_mirror.internal_compression_stiffness = cloth.internal_compression_stiffness
    cloth_mirror.internal_tension_stiffness_max = cloth.internal_tension_stiffness_max
    cloth_mirror.internal_compression_stiffness_max = cloth.internal_compression_stiffness_max

    cloth_mirror.use_pressure = cloth.use_pressure
    cloth_mirror.uniform_pressure_force = cloth.uniform_pressure_force
    cloth_mirror.use_pressure_volume = cloth.use_pressure_volume
    cloth_mirror.target_volume = cloth.target_volume
    cloth_mirror.pressure_factor = cloth.pressure_factor
    cloth_mirror.fluid_density = cloth.fluid_density

    cache_mirror.frame_start = cache.frame_start
    cache_mirror.frame_end = cache.frame_end

    cloth_mirror.pin_stiffness = cloth.pin_stiffness
    cloth_mirror.use_sewing_springs = cloth.use_sewing_springs
    cloth_mirror.sewing_force_max = cloth.sewing_force_max
    cloth_mirror.shrink_min = cloth.shrink_min
    cloth_mirror.use_dynamic_mesh = cloth.use_dynamic_mesh

    collisions_mirror.use_collision = collisions.use_collision
    collisions_mirror.collision_quality = collisions.collision_quality
    collisions_mirror.distance_min = collisions.distance_min
    collisions_mirror.impulse_clamp = collisions.impulse_clamp

    collisions_mirror.use_self_collision = collisions.use_self_collision
    collisions_mirror.self_friction = collisions.self_friction
    collisions_mirror.self_distance_min = collisions.self_distance_min
    collisions_mirror.self_impulse_clamp = collisions.self_impulse_clamp

    return True


def mirror_soft_body(obj, obj_mirror) -> bool:

    softbody = None
    cache = None
    for m in obj.modifiers:
        if m.type == "SOFT_BODY":
            softbody = m.settings
            cache = m.point_cache
            break
    if softbody is None:
        return False

    softbody_mirror = None
    cache_mirror = None
    for m in obj_mirror.modifiers:
        if m.type == "SOFT_BODY":
            softbody_mirror = m.settings
            cache_mirror = m.point_cache
            break
    if softbody_mirror is None:
        return False

    softbody_mirror.friction = softbody.friction
    softbody_mirror.mass = softbody.mass
    softbody_mirror.speed = softbody.speed

    cache_mirror.frame_start = cache.frame_start
    cache_mirror.frame_end = cache.frame_end

    return True


class MustardUI_PhysicsItem_Mirror(bpy.types.Operator):
    """Mirror the settings of this Physics Item"""
    bl_idname = "mustardui.physics_mirror"
    bl_label = "Mirror Physics Item"
    bl_options = {'UNDO'}

    obj_name: bpy.props.StringProperty(default="")

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)

        return res

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=0)
        physics_settings = arm.MustardUI_PhysicsSettings

        obj = context.scene.objects[self.obj_name]

        obj_mirror = None
        for on in [x for x in physics_settings.items if x.object != obj]:
            if check_mirror(self.obj_name, on.object.name, left=True) or check_mirror(self.obj_name, on.object.name, left=False):
                obj_mirror = on.object
                break
        if obj_mirror is None:
            self.report({'WARNING'}, 'MustardUI - No Object as target for mirror found.')

        # Cloth Settings
        cloth = mirror_cloth(obj, obj_mirror)

        # Soft Body Settings
        soft_body = mirror_soft_body(obj, obj_mirror)

        arm.update_tag()

        if cloth or soft_body:
            self.report({'INFO'}, 'MustardUI - Physics Item settings mirrored.')
        else:
            self.report({'WARNING'}, 'MustardUI - An error occurred while mirroring settings.')

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_PhysicsItem_Mirror)


def unregister():
    bpy.utils.unregister_class(MustardUI_PhysicsItem_Mirror)
