import bpy
from bl_operators.presets import AddPresetBase
from bl_ui.utils import PresetPanel
from ..model_selection.active_object import *


class MUI_PT_Presets(PresetPanel, bpy.types.Panel):
    bl_label = 'MustardUI Presets'
    preset_subdir = 'mustardui/configuration'
    preset_operator = 'script.execute_preset'
    preset_add_operator = 'mustardui.add_preset'


class MUI_MT_Presets(bpy.types.Menu):
    bl_label = 'MustardUI Presets'
    preset_subdir = 'mustardui/configuration'
    preset_operator = 'script.execute_preset'
    draw = bpy.types.Menu.draw_preset


class MustardUI_OT_AddPreset(AddPresetBase, bpy.types.Operator):
    bl_idname = 'mustardui.add_preset'
    bl_label = 'Add MustardUI Preset'
    preset_menu = 'MUI_MT_Presets'

    @property
    def preset_defines(self):

        res, arm = mustardui_active_object(bpy.context, config=1)

        rig_settings = arm.MustardUI_RigSettings
        model_armature_object = rig_settings.model_armature_object

        if bpy.context.scene.MustardUI_Settings.viewport_model_selection:
            return ['rig_settings = bpy.context.object.data.MustardUI_RigSettings']

        return [f'rig_settings = bpy.context.scene.objects[{repr(model_armature_object.name)}].data.MustardUI_RigSettings',
                f'morph_settings = bpy.context.scene.objects[{repr(model_armature_object.name)}].data.MustardUI_MorphsSettings']

    preset_values = [
        'rig_settings.body_enable_subdiv',
        'rig_settings.body_enable_smoothcorr',
        'rig_settings.body_enable_norm_autosmooth',
        'rig_settings.body_enable_solidify',
        'rig_settings.body_enable_preserve_volume',
        'rig_settings.body_enable_material_normal_nodes',
        'rig_settings.body_custom_properties_icons',
        'rig_settings.body_custom_properties_name_order',
        'rig_settings.body_enable_geometry_nodes',
        'rig_settings.body_enable_geometry_nodes_support',
        'rig_settings.outfits_enable_global_subsurface',
        'rig_settings.outfits_enable_global_smoothcorrection',
        'rig_settings.outfits_enable_global_surfacedeform',
        'rig_settings.outfits_enable_global_shrinkwrap',
        'rig_settings.outfits_enable_global_mask',
        'rig_settings.outfits_enable_global_solidify',
        'rig_settings.outfits_enable_global_triangulate',
        'rig_settings.outfits_enable_global_normalautosmooth',
        'rig_settings.outfit_nude',
        'rig_settings.outfit_additional_options',
        'rig_settings.outfit_custom_properties_icons',
        'rig_settings.outfit_custom_properties_name_order',
        'rig_settings.outfit_global_custom_properties_collapse',
        'rig_settings.outfit_config_subcollections',
        'rig_settings.outfits_update_tag_on_switch',
        'rig_settings.outfit_switch_armature_disable',
        'rig_settings.hair_collection',
        'rig_settings.hair_custom_properties_icons',
        'rig_settings.hair_custom_properties_name_order',
        'rig_settings.hair_switch_armature_disable',
        'rig_settings.hair_enable_global_subsurface',
        'rig_settings.hair_enable_global_smoothcorrection',
        'rig_settings.hair_enable_global_solidify',
        'rig_settings.hair_enable_global_particles',
        'rig_settings.hair_enable_global_normalautosmooth',
        'rig_settings.hair_update_tag_on_switch',
        'rig_settings.curves_hair_enable',
        'rig_settings.particle_systems_enable',
        'morphs_settings.enable_ui',
        'morphs_settings.diffeomorphic_disable_exceptions',
        'morphs_settings.diffeomorphic_emotions_custom',
        'morphs_settings.diffeomorphic_body_morphs_custom',
        'rig_settings.simplify_main_enable',
        'rig_settings.model_MustardUI_naming_convention',
        'rig_settings.links_enable',
    ]

    # Directory to store the presets
    preset_subdir = 'mustardui/configuration'


def register():
    bpy.utils.register_class(MustardUI_OT_AddPreset)
    bpy.utils.register_class(MUI_MT_Presets)
    bpy.utils.register_class(MUI_PT_Presets)


def unregister():
    bpy.utils.unregister_class(MUI_PT_Presets)
    bpy.utils.unregister_class(MUI_MT_Presets)
    bpy.utils.unregister_class(MustardUI_OT_AddPreset)
