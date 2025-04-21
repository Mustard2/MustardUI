import bpy
from bl_operators.presets import AddPresetBase
from bl_ui.utils import PresetPanel
from ..model_selection.active_object import *


class MUI_PT_PhysicsClothPresets(PresetPanel, bpy.types.Panel):
    bl_label = "MustardUI Cloth Presets"
    preset_subdir = "mustardui/physics_cloth"
    preset_operator = "script.execute_preset"
    preset_add_operator = "mustardui.add_physics_cloth_preset"


class MUI_MT_PhysicsClothPresets(bpy.types.Menu):
    bl_label = 'MustardUI Cloth Presets'
    preset_subdir = 'mustardui/physics_cloth'
    preset_operator = 'script.execute_preset'
    draw = bpy.types.Menu.draw_preset


class MustardUI_OT_AddPhysicsClothPreset(AddPresetBase, bpy.types.Operator):
    bl_idname = 'mustardui.add_physics_cloth_preset'
    bl_label = 'Add MustardUI Cloth Preset'
    preset_menu = 'MUI_MT_PhysicsClothPresets'

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(bpy.context, config=0)
        physics_settings = arm.MustardUI_PhysicsSettings

        if arm is None:
            return False

        index = arm.mustardui_physics_items_uilist_index
        if index >= len(physics_settings.items):
            return False

        pi = physics_settings.items[arm.mustardui_physics_items_uilist_index]
        pi_object = pi.object

        if pi_object is None:
            return False

        pi_mod = ""
        for mod in pi_object.modifiers:
            if mod.type == "CLOTH":
                pi_mod = mod.name

        return res and pi_mod != ""

    preset_defines = [
        "obj = bpy.context.active_object",
        "modifier = next(i for i in obj.modifiers if i.type == 'CLOTH')",
    ]

    @property
    def preset_values(self):
        preset_values = [

            "modifier.settings.quality",
            "modifier.settings.mass",
            "modifier.settings.air_damping",
            "modifier.settings.time_scale",
            "modifier.settings.tension_stiffness",
            "modifier.settings.compression_stiffness",
            "modifier.settings.shear_stiffness",
            "modifier.settings.bending_stiffness",
            "modifier.settings.tension_damping",
            "modifier.settings.compression_damping",
            "modifier.settings.shear_damping",
            "modifier.settings.bending_damping",
            "modifier.settings.bending_model",
            "modifier.settings.pin_stiffness",
            "modifier.settings.use_dynamic_mesh",
            "modifier.settings.use_internal_springs",
            "modifier.collision_settings.use_collision",
            "modifier.settings.use_pressure",
            "modifier.settings.uniform_pressure_force",
            "modifier.settings.shrink_min",
            "modifier.settings.use_dynamic_mesh",
            "modifier.settings.use_pressure_volume",
            "modifier.settings.target_volume",
            "modifier.settings.pressure_factor",
            "modifier.settings.fluid_density",
            "modifier.collision_settings.collision_quality",
            "modifier.collision_settings.distance_min",
            "modifier.collision_settings.use_self_collision",
            "modifier.collision_settings.self_friction",
            "modifier.collision_settings.self_distance_min",
            "modifier.collision_settings.self_impulse_clamp",
            "modifier.settings.vertex_group_mass",
            "modifier.settings.tension_stiffness_max",
            "modifier.settings.compression_stiffness_max",
            "modifier.settings.shear_stiffness_max",
            "modifier.settings.bending_stiffness_max",
            "modifier.settings.use_sewing_springs",
            "modifier.settings.sewing_force_max",
            "modifier.settings.effector_weights.gravity",
            "modifier.settings.effector_weights.all",
            "modifier.settings.effector_weights.force",
            "modifier.settings.effector_weights.vortex",
            "modifier.settings.effector_weights.magnetic",
            "modifier.settings.effector_weights.harmonic",
            "modifier.settings.effector_weights.charge",
            "modifier.settings.effector_weights.lennardjones",
            "modifier.settings.effector_weights.wind",
            "modifier.settings.effector_weights.curve_guide",
            "modifier.settings.effector_weights.texture",
            "modifier.settings.effector_weights.smokeflow",
            "modifier.settings.effector_weights.turbulence",
            "modifier.settings.effector_weights.drag",
            "modifier.settings.effector_weights.boid"

        ]

        preset_values_angular = [
            "modifier.settings.vertex_group_intern",
            "modifier.settings.internal_tension_stiffness",
            "modifier.settings.internal_compression_stiffness",
            "modifier.settings.internal_tension_stiffness_max",
            "modifier.settings.internal_compression_stiffness_max",
        ]

        obj = bpy.context.active_object
        modifier = next(i for i in obj.modifiers if i.type == 'CLOTH')

        if modifier.settings.bending_model == "ANGULAR":
            for preset in preset_values_angular:
                preset_values.append(preset)
        return preset_values

    def execute(self, context):
        # Save original active object
        original_active = context.view_layer.objects.active

        # Set selected pi.object as active
        res, arm = mustardui_active_object(context, config=0)
        index = arm.mustardui_physics_items_uilist_index
        pi = arm.MustardUI_PhysicsSettings.items[index]
        target_obj = pi.object

        # Save visibility settings of the object
        visibility = target_obj.hide_viewport

        if target_obj is None:
            self.report({'ERROR'}, "No object to apply preset to.")
            return {'CANCELLED'}

        target_obj.hide_viewport = False
        context.view_layer.objects.active = target_obj

        # Call AddPresetBase to apply to that object
        result = super().execute(context)

        # Restore visibility
        target_obj.hide_viewport = visibility

        # Restore original active object
        context.view_layer.objects.active = original_active

        return result

    preset_subdir = "mustardui/physics_cloth"


def register():
    bpy.utils.register_class(MUI_PT_PhysicsClothPresets)
    bpy.utils.register_class(MUI_MT_PhysicsClothPresets)
    bpy.utils.register_class(MustardUI_OT_AddPhysicsClothPreset)


def unregister():
    bpy.utils.unregister_class(MustardUI_OT_AddPhysicsClothPreset)
    bpy.utils.unregister_class(MUI_MT_PhysicsClothPresets)
    bpy.utils.unregister_class(MUI_PT_PhysicsClothPresets)
