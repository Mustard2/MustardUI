import bpy

from ...misc.get_ui_objects import get_ui_mesh_objects
from ...model_selection.active_object import (
    ModelMode,
    active_object_operator_poll,
    mustardui_active_object,
)

# Scale exponents keeping the look; springs and Uniform Pressure are size-independent
CLOTH_SCALING = {
    "settings.mass": -1,
    "settings.air_damping": -1,
    "settings.tension_damping": -1,
    "settings.compression_damping": -1,
    "settings.shear_damping": -1,
    "settings.bending_damping": -1,
    "settings.pressure_factor": -2,
    "settings.fluid_density": -4,
    "settings.target_volume": 3,
    "settings.internal_spring_max_length": 1,
    "settings.effector_weights.gravity": 1,
    "collision_settings.distance_min": 1,
    "collision_settings.self_distance_min": 1,
    "collision_settings.impulse_clamp": 1,
    "collision_settings.self_impulse_clamp": 1,
}
# Particle hair children do not follow the object scale in Kink Amplitude and Simple Radius
HAIR_SCALING = {"settings.kink_amplitude": 1}
SIMPLE_CHILDREN_SCALING = {"settings.child_radius": 1}
# Hair not groomed is regenerated at every change with the Hair Length in world space, but not
# by animation: animated, it follows the object scale
GENERATED_HAIR_SCALING = {"settings.hair_length": 1}
# Hair Dynamics take gravity from the particle settings, and keep their bending damping
HAIR_DYNAMICS_SCALING = {
    "cloth.settings.mass": -1,
    "cloth.settings.air_damping": -1,
    "cloth.settings.voxel_cell_size": 1,
    "cloth.collision_settings.distance_min": 1,
    "settings.effector_weights.gravity": 1,
}
COLLISION_SCALING = {
    "collision.thickness_outer": 1,
    "collision.thickness_inner": 1,
}

# Name of the armature scale variable of the drivers added by Animate
SCALE_VARIABLE = "mustardui_scale"


class MustardUI_ModelToolkit_ScaleCharacter(bpy.types.Operator):
    bl_idname = "mustardui.model_toolkit_scale_character"
    bl_label = "Scale Character"
    bl_description = (
        "Scale the model armature, with the particle hair and physics settings that do not "
        "follow the object scale, so that the hair and the physics keep their look"
    )
    bl_options = {"REGISTER", "UNDO"}

    scale: bpy.props.FloatProperty(
        name="Scale",
        description="Factor the character is scaled by",
        default=1.0,
        min=0.001,
        soft_min=0.01,
        soft_max=100.0,
    )
    armature: bpy.props.BoolProperty(
        name="Armature",
        description="Scale the armature object. Disable it if the model is already scaled",
        default=True,
    )
    hair: bpy.props.BoolProperty(
        name="Hair",
        description="Scale the particle hair settings that do not follow the object scale: the "
        "Kink Amplitude and Simple Radius of the children, and the Hair Length if not groomed",
        default=True,
    )
    hair_physics: bpy.props.BoolProperty(
        name="Hair Physics",
        description="Scale the Hair Dynamics settings of the particle hair",
        default=True,
    )
    physics: bpy.props.BoolProperty(
        name="Physics",
        description="Scale the Cloth and Collision settings",
        default=True,
    )
    animate: bpy.props.BoolProperty(
        name="Animate",
        description="Keyframe the armature scale from the current frame to the end of the "
        "Duration. The physics settings follow it by drivers, at any growth given to its "
        "keyframes, and the particle hair settings are keyed on the same frames",
    )
    duration: bpy.props.IntProperty(
        name="Duration",
        default=48,
        min=1,
        description="Frames to reach the new scale, from the current frame",
    )

    @classmethod
    def poll(cls, context):
        return active_object_operator_poll(context, config=ModelMode.MODEL_TOOLKIT)

    def execute(self, context):
        res, arm = mustardui_active_object(context, config=ModelMode.MODEL_TOOLKIT)
        rig_settings = arm.MustardUI_RigSettings
        arm_obj = rig_settings.model_armature_object
        if arm_obj is None:
            self.report({"WARNING"}, "MustardUI - The model armature object is not set.")
            return {"CANCELLED"}

        frame = context.scene.frame_current
        # Armature scale the current settings are for
        rest_scale = sum(arm_obj.matrix_world.to_scale()) / 3

        objects = {
            *arm_obj.children_recursive,
            *get_ui_mesh_objects(rig_settings),
            *[x.object for x in arm.MustardUI_PhysicsSettings.items if x.object],
        }

        clamped = set()
        scaled = set()
        for obj in objects:
            hair = [x for x in obj.particle_systems if x.settings.type == "HAIR"]
            targets = []
            if self.hair:
                targets += [(x, HAIR_SCALING) for x in hair]
                targets += [
                    (x, SIMPLE_CHILDREN_SCALING) for x in hair if x.settings.child_type == "SIMPLE"
                ]
                if not self.animate:
                    targets += [(x, GENERATED_HAIR_SCALING) for x in hair if not x.is_edited]
            if self.hair_physics:
                targets += [(x, HAIR_DYNAMICS_SCALING) for x in hair if x.use_hair_dynamics]
            if self.physics:
                targets += [(m, CLOTH_SCALING) for m in obj.modifiers if m.type == "CLOTH"]
                if any(m.type == "COLLISION" for m in obj.modifiers):
                    targets.append((obj, COLLISION_SCALING))

            for base, scaling in targets:
                for path, exponent in scaling.items():
                    owner_path, prop = path.rsplit(".", 1)
                    owner = base.path_resolve(owner_path)
                    rna = owner.bl_rna.properties[prop]
                    anim = owner.id_data.animation_data
                    # Settings shared by more objects (e.g. Particle Settings) are scaled once, and
                    # the driven ones already follow the armature scale
                    if (owner.as_pointer(), prop) in scaled or (
                        anim and anim.drivers.find(owner.path_from_id(prop))
                    ):
                        continue
                    scaled.add((owner.as_pointer(), prop))
                    # Not animatable as read at the simulation start: kept for the start frame
                    if self.animate and not rna.is_animatable:
                        continue

                    value = getattr(owner, prop)
                    new_value = value * self.scale**exponent
                    if not rna.hard_min <= new_value <= rna.hard_max:
                        clamped.add(prop)
                    if not self.animate:
                        setattr(owner, prop, new_value)
                    elif isinstance(owner.id_data, bpy.types.ParticleSettings):
                        # Drivers of Particle Settings may run after the hair is built, so they
                        # are keyed as the armature, exact as their scale exponent is 1
                        owner.keyframe_insert(prop, frame=frame)
                        setattr(owner, prop, new_value)
                        owner.keyframe_insert(prop, frame=frame + self.duration)
                    else:
                        driver = owner.driver_add(prop).driver
                        driver.type = "SCRIPTED"
                        var = driver.variables.new()
                        var.name = SCALE_VARIABLE
                        var.type = "TRANSFORMS"
                        var.targets[0].id = arm_obj
                        var.targets[0].transform_type = "SCALE_AVG"
                        var.targets[0].transform_space = "WORLD_SPACE"
                        # pow() keeps it a simple expression, running without Python scripts
                        driver.expression = (
                            f"{value / rest_scale**exponent!r} * pow({SCALE_VARIABLE}, {exponent})"
                        )

        if self.armature or self.animate:
            if self.animate:
                arm_obj.keyframe_insert("scale", frame=frame)
            arm_obj.scale = arm_obj.scale * self.scale
            if self.animate:
                arm_obj.keyframe_insert("scale", frame=frame + self.duration)
                # Back to the scale of the current frame
                context.scene.frame_set(frame)

        if clamped:
            self.report(
                {"WARNING"},
                f"MustardUI - Character scaled, but some values hit the Blender limits: "
                f"{', '.join(sorted(clamped))}.",
            )
        else:
            self.report({"INFO"}, "MustardUI - Character scaled.")
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "scale")
        col = layout.column(align=True)
        # Animate always keys the armature
        row = col.row()
        row.active = not self.animate
        row.prop(self, "armature")
        col.prop(self, "hair")
        col.prop(self, "hair_physics")
        col.prop(self, "physics")

        layout.separator()

        row = layout.row()
        row.prop(self, "animate")
        sub = row.row()
        sub.enabled = self.animate
        sub.prop(self, "duration")


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_ScaleCharacter)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_ScaleCharacter)
