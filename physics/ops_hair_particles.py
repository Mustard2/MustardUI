import bpy
from ..model_selection.active_object import *


# Function to format dynamic name
def format_dynamic_name(x):
    return x.particle_system.name if not ("Dynamic" in x.particle_system.name) else x.particle_system.name.replace(
        "Dynamic", "").lstrip().rstrip()


class MustardUI_Physics_ParticleHair_Switch(bpy.types.Operator):
    """Enable/Disable particle Hair on the Object"""
    bl_idname = "mustardui.physics_particlehair_switch"
    bl_label = "Particle Hair Simulation"

    obj: bpy.props.StringProperty(default="")
    enable: bpy.props.BoolProperty(default=True)

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        return res

    def execute(self, context):

        scene = context.scene

        if not (self.obj in scene.objects):
            return {'FINISHED'}

        o = scene.objects[self.obj]

        mod_particle_system = [x for x in o.modifiers if x.type == "PARTICLE_SYSTEM" if "Dynamic" in x.particle_system.name]

        for mod in mod_particle_system:
            mod.particle_system.use_hair_dynamics = self.enable

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_Physics_ParticleHair_Switch)


def unregister():
    bpy.utils.unregister_class(MustardUI_Physics_ParticleHair_Switch)
