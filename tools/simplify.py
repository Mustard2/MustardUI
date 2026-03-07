import bpy
from ..model_selection.active_object import *
from .. import __package__ as base_package


class MustardUI_SimplifySettings(bpy.types.PropertyGroup):
    simplify_main_enable: bpy.props.BoolProperty(
        name="Simplify",
        default=False,
        description="Enable the Simplify tool for better viewport performance"
    )

    def update_simplify(self, context):
        bpy.ops.mustardui.update_simplify()
        return

    simplify_enable: bpy.props.BoolProperty(
        name="Simplify Options",
        default=False,
        description="Enable Simplify options to increase viewport performance",
        update=update_simplify
    )

    simplify_blender: bpy.props.BoolProperty(
        name="Blender Simplify",
        default=False,
        description="Enable Blender Simplify when Simplify is enabled"
    )

    simplify_normals_optimize: bpy.props.BoolProperty(
        name="Affect Eevee Normals Optimization",
        default=False,
        description="Optimize Eevee normals when Simplify is enabled"
    )

    simplify_subdiv: bpy.props.BoolProperty(
        name="Affect Subdivision (Viewport)",
        default=True,
        description="Disable Subdivision Surface modifiers when Simplify is enabled"
    )

    simplify_normals_autosmooth: bpy.props.BoolProperty(
        name="Affect Normals Auto-Smooth",
        default=True
    )

    simplify_outfit_switch_nude: bpy.props.BoolProperty(
        name="Switch to Nude",
        default=False
    )

    simplify_outfit_global: bpy.props.BoolProperty(
        name="Disable Outfit Global Properties",
        default=True
    )

    simplify_extras: bpy.props.BoolProperty(
        name="Hide Extras",
        default=True
    )

    simplify_hair: bpy.props.BoolProperty(
        name="Hide Hair (Viewport)",
        default=True
    )

    simplify_particles: bpy.props.BoolProperty(
        name="Disable Particles",
        default=True,
        description="Disable particle system modifiers when Simplify is enabled"
    )

    simplify_hair_global: bpy.props.BoolProperty(
        name="Disable Hair Global Properties",
        default=True
    )

    simplify_armature_child: bpy.props.BoolProperty(
        name="Hide Armature Children (Viewport)",
        default=True,
        description="Disables all objects parented to the Armature, except the Body"
    )

    simplify_morphs: bpy.props.BoolProperty(
        name="Disable Morphs",
        default=True
    )

    simplify_physics: bpy.props.BoolProperty(
        name="Disable Physics",
        default=False
    )

    simplify_force_no_physics: bpy.props.BoolProperty(
        name="Force Disable Physics",
        default=False,
        description="Force-disable all physics modifiers on all scene objects"
    )

    simplify_force_no_particles: bpy.props.BoolProperty(
        name="Force Disable Particle Systems",
        default=False,
        description="Force-disable all particle system modifiers on all scene objects"
    )


class MUSTARDUI_OT_UpdateSimplify(bpy.types.Operator):
    bl_idname = "mustardui.update_simplify"
    bl_label = "Update Simplify"
    bl_description = "Apply Simplify settings to improve viewport performance"

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        simplify_settings = context.scene.MustardUI_SimplifySettings

        return res and simplify_settings.simplify_main_enable

    def execute(self, context):
        settings = context.scene.MustardUI_Settings
        simplify_settings = context.scene.MustardUI_SimplifySettings

        poll, arm = mustardui_active_object(context, config=0)
        addon_prefs = context.preferences.addons[base_package].preferences

        rig_settings = arm.MustardUI_RigSettings
        physics_settings = arm.MustardUI_PhysicsSettings if arm else None
        morphs_settings = arm.MustardUI_MorphsSettings if arm else None

        # Blender Simplify
        if simplify_settings.simplify_blender:
            context.scene.render.use_simplify = simplify_settings.simplify_enable

        # Body
        if simplify_settings.simplify_enable:
            if rig_settings.body_enable_subdiv:
                rig_settings.body_subdiv_view = not simplify_settings.simplify_enable
            if rig_settings.body_enable_smoothcorr:
                rig_settings.body_smooth_corr = not simplify_settings.simplify_enable
            if rig_settings.body_enable_norm_autosmooth:
                rig_settings.body_norm_autosmooth = not simplify_settings.simplify_enable
            if rig_settings.body_enable_geometry_nodes:
                rig_settings.body_geometry_nodes = not simplify_settings.simplify_enable
            if rig_settings.body_enable_solidify:
                rig_settings.body_solidify = not simplify_settings.simplify_enable

        # Eevee Optimized Normals
        if simplify_settings.simplify_normals_optimize:
            settings.material_normal_nodes = simplify_settings.simplify_enable

        # Outfits
        if len(rig_settings.outfits_list) > 1 and simplify_settings.simplify_outfit_global:
            if simplify_settings.simplify_subdiv and rig_settings.outfits_enable_global_subsurface and simplify_settings.simplify_enable:
                rig_settings.outfits_global_subsurface = not simplify_settings.simplify_enable
            if rig_settings.outfits_enable_global_mask:
                rig_settings.outfits_global_mask = not simplify_settings.simplify_enable
            if rig_settings.outfits_enable_global_smoothcorrection:
                rig_settings.outfits_global_smoothcorrection = not simplify_settings.simplify_enable
            if rig_settings.outfits_enable_global_shrinkwrap:
                rig_settings.outfits_global_shrinkwrap = not simplify_settings.simplify_enable
            if rig_settings.outfits_enable_global_solidify:
                rig_settings.outfits_global_solidify = not simplify_settings.simplify_enable
            if rig_settings.outfits_enable_global_triangulate:
                rig_settings.outfits_global_triangulate = not simplify_settings.simplify_enable
            if simplify_settings.simplify_normals_autosmooth and rig_settings.outfits_enable_global_normalautosmooth:
                rig_settings.outfits_global_normalautosmooth = not simplify_settings.simplify_enable
        if rig_settings.outfit_nude and simplify_settings.simplify_outfit_switch_nude and simplify_settings.simplify_enable:
            rig_settings.outfits_list = "Nude"

        if rig_settings.extras_collection and simplify_settings.simplify_extras:
            items = rig_settings.extras_collection.all_objects if rig_settings.outfit_config_subcollections else rig_settings.extras_collection.objects
            for obj in items:
                if simplify_settings.simplify_enable:
                    status = obj.MustardUI_outfit_visibility != simplify_settings.simplify_enable
                    if status:
                        bpy.ops.mustardui.object_visibility(obj=obj.name)
                    obj.MustardUI_OutfitSettings.simplify_status = status
                elif not simplify_settings.simplify_enable and obj.MustardUI_OutfitSettings.simplify_status:
                    if obj.MustardUI_outfit_visibility != simplify_settings.simplify_enable:
                        bpy.ops.mustardui.object_visibility(obj=obj.name)
                    obj.MustardUI_OutfitSettings.simplify_status = False

        # Hair
        if rig_settings.hair_collection:
            rig_settings.hair_collection.hide_viewport = simplify_settings.simplify_enable if simplify_settings.simplify_hair else False

            if simplify_settings.simplify_hair_global:
                if simplify_settings.simplify_subdiv and rig_settings.hair_enable_global_subsurface and simplify_settings.simplify_enable:
                    rig_settings.hair_global_subsurface = not simplify_settings.simplify_enable
                if rig_settings.hair_enable_global_smoothcorrection:
                    rig_settings.hair_global_smoothcorrection = not simplify_settings.simplify_enable
                if rig_settings.hair_enable_global_solidify:
                    rig_settings.hair_global_solidify = not simplify_settings.simplify_enable
                if simplify_settings.simplify_normals_autosmooth and rig_settings.hair_enable_global_normalautosmooth:
                    rig_settings.hair_global_normalautosmooth = not simplify_settings.simplify_enable

        # Particle Systems
        if simplify_settings.simplify_particles and simplify_settings.simplify_enable:
            if rig_settings.particle_systems_enable:
                for ps in [x for x in rig_settings.model_body.modifiers if x.type == "PARTICLE_SYSTEM"]:
                    ps.show_viewport = not simplify_settings.simplify_enable
            if rig_settings.hair_collection and rig_settings.hair_enable_global_particles:
                rig_settings.hair_global_particles = not simplify_settings.simplify_enable
                for obj in rig_settings.hair_collection.objects:
                    for ps in [x for x in obj.modifiers if x.type == "PARTICLE_SYSTEM"]:
                        ps.show_viewport = not simplify_settings.simplify_enable

        # Armature Children
        child_all = [x for x in rig_settings.model_armature_object.children if x != rig_settings.model_body]
        child = child_all.copy()

        if rig_settings.extras_collection:
            items = rig_settings.extras_collection.all_objects if rig_settings.outfit_config_subcollections else rig_settings.extras_collection.objects
            for obj in [x for x in items if x in child_all]:
                child.remove(obj)
        if rig_settings.hair_collection:
            for obj in [x for x in rig_settings.hair_collection.objects if x in child_all]:
                child.remove(obj)
        for col in rig_settings.outfits_collections:
            items = col.collection.all_objects if rig_settings.outfit_config_subcollections else col.collection.objects
            for obj in [x for x in items if x in child_all]:
                child.remove(obj)
        if physics_settings:
            for obj in [x.object for x in physics_settings.items if x.object in child_all]:
                child.remove(obj)

        for c in child:
            c.hide_viewport = simplify_settings.simplify_enable if simplify_settings.simplify_armature_child else False
            for mod in c.modifiers:
                if mod.type in ["SUBSURF", "SHRINKWRAP", "CORRECTIVE_SMOOTH", "SOLIDIFY", "PARTICLE_SYSTEM", "CLOTH"]:
                    mod.show_viewport = not simplify_settings.simplify_enable if simplify_settings.simplify_armature_child else True

        # Morphs
        if morphs_settings and morphs_settings.enable_ui and simplify_settings.simplify_morphs:
            morphs_settings.diffeomorphic_enable = not simplify_settings.simplify_enable

        # Physics
        if simplify_settings.simplify_physics and physics_settings and len(physics_settings.items) > 0:
            physics_settings.enable_physics = not simplify_settings.simplify_enable

        # Force Disable Physics
        if simplify_settings.simplify_force_no_physics and simplify_settings.simplify_enable:
            for obj in context.scene.objects:
                for mod in [x for x in obj.modifiers if x.type in ["SOFT_BODY", "CLOTH", "COLLISION"]]:
                    if mod.type == "COLLISION" and obj.collision:
                        obj.collision.use = not simplify_settings.simplify_enable
                    else:
                        mod.show_viewport = not simplify_settings.simplify_enable
                    if addon_prefs.debug:
                        print(f"MustardUI - Disabled {mod.type} modifier on: {obj.name}")

        # Force Disable Particles
        if simplify_settings.simplify_force_no_particles and simplify_settings.simplify_enable:
            for obj in context.scene.objects:
                for ps in [x for x in obj.modifiers if x.type == "PARTICLE_SYSTEM"]:
                    ps.show_viewport = not simplify_settings.simplify_enable
                    if addon_prefs.debug:
                        print(f"MustardUI - Disabled {ps.type} modifier on: {obj.name}")

        # Update all objects
        for obj in context.scene.objects:
            obj.update_tag()

        return {'FINISHED'}


# ------------------------------------------------------------------------
#    Register
# ------------------------------------------------------------------------
def register():
    bpy.utils.register_class(MustardUI_SimplifySettings)
    bpy.utils.register_class(MUSTARDUI_OT_UpdateSimplify)
    bpy.types.Scene.MustardUI_SimplifySettings = bpy.props.PointerProperty(type=MustardUI_SimplifySettings)


def unregister():
    bpy.utils.unregister_class(MustardUI_SimplifySettings)
    bpy.utils.unregister_class(MUSTARDUI_OT_UpdateSimplify)
    del bpy.types.Scene.MustardUI_SimplifySettings
