import bpy
from ..model_selection.active_object import mustardui_active_object
from ..physics.update_enable import enable_physics_update
from ..outfits.helper_functions import outfits_update_armature_collections
from ..misc.set_bool import set_bool


class MustardUI_HairVisibility(bpy.types.Operator):
    """Switch visibility of hair objects in a collection"""
    bl_idname = "mustardui.hair_visibility"
    bl_label = "Hair Visibility"
    bl_options = {'UNDO'}

    def _set_object_visibility(self, obj, visible, rig_settings):
        """Set object and relevant modifiers visibility"""
        set_bool(obj, "hide_viewport", not visible)
        set_bool(obj, "hide_render", not visible)

        for mod in [x for x in obj.modifiers if x.type in ["PARTICLE_SYSTEM", "ARMATURE", "NODES"]]:
            if mod.type in ["PARTICLE_SYSTEM", "NODES"]:
                set_bool(mod, "show_viewport", visible)
                set_bool(mod, "show_render", visible)
            else:  # ARMATURE
                set_bool(mod, "show_viewport", visible if rig_settings.hair_switch_armature_disable else True)

    def execute(self, context):

        poll, arm = mustardui_active_object(context, config=0)
        if not poll:
            self.report({'WARNING'}, "MustardUI - Active object not found.")
            return {'CANCELLED'}

        rig_settings = arm.MustardUI_RigSettings
        hair_collection = rig_settings.hair_collection
        hair_list = rig_settings.hair_list
        if not hair_collection:
            self.report({'WARNING'}, "Hair collection not defined in Rig Settings.")
            return {'CANCELLED'}

        # Loop through hair objects
        for obj in [x for x in hair_collection.objects]:
            visible = hair_list in obj.name
            self._set_object_visibility(obj, visible, rig_settings)

        # Update armature collections visibility using the outfit-style logic
        outfits_update_armature_collections(rig_settings, arm)

        # Update tags if enabled
        if rig_settings.hair_update_tag_on_switch:
            for obj in hair_collection.objects:
                obj.update_tag()

        return {'FINISHED'}


class MustardUI_HairVisibility_Extras(bpy.types.Operator):
    """Switch visibility of hair objects in a collection"""
    bl_idname = "mustardui.hair_visibility_extras"
    bl_label = "Hair Visibility Extras"
    bl_options = {'UNDO'}

    obj_name: bpy.props.StringProperty(default="")

    def _set_object_visibility(self, obj, visible, rig_settings):
        """Set object and relevant modifiers visibility"""
        set_bool(obj, "hide_viewport", not visible)
        set_bool(obj, "hide_render", not visible)

        for mod in [x for x in obj.modifiers if x.type in ["PARTICLE_SYSTEM", "ARMATURE", "NODES"]]:
            if mod.type in ["PARTICLE_SYSTEM", "NODES"]:
                set_bool(mod, "show_viewport", visible)
                set_bool(mod, "show_render", visible)
            else:  # ARMATURE
                set_bool(mod, "show_viewport", visible if rig_settings.hair_switch_armature_disable else True)

    def execute(self, context):

        poll, arm = mustardui_active_object(context, config=0)
        if not poll:
            self.report({'WARNING'}, "MustardUI - Active object not found.")
            return {'CANCELLED'}

        rig_settings = arm.MustardUI_RigSettings
        hair_extras_collection = rig_settings.hair_extras_collection
        hair_name = self.obj_name

        if not hair_extras_collection:
            self.report({'WARNING'}, "Hair Extras collection not defined in Rig Settings.")
            return {'CANCELLED'}

        obj = context.scene.objects[hair_name]
        visibility = obj.hide_viewport

        # Loop through hair objects
        for obj in [x for x in hair_extras_collection.objects if hair_name in obj.name]:
            self._set_object_visibility(obj, visibility, rig_settings)

        # Update armature collections visibility using the outfit-style logic
        outfits_update_armature_collections(rig_settings, arm)

        # Update tags if enabled
        if rig_settings.hair_update_tag_on_switch:
            for obj in hair_extras_collection.objects:
                obj.update_tag()

        return {'FINISHED'}


class MustardUI_HairVisibility_Extras_ParticleSystem(bpy.types.Operator):
    """Switch visibility of particle hair system"""
    bl_idname = "mustardui.hair_visibility_extras_particle_system"
    bl_label = "Particle Hair Visibility Extras"
    bl_options = {'UNDO'}

    obj_name: bpy.props.StringProperty(default="")
    particle_system: bpy.props.StringProperty()

    def execute(self, context):

        poll, arm = mustardui_active_object(context, config=0)
        if not poll:
            self.report({'WARNING'}, "MustardUI - Active object not found.")
            return {'CANCELLED'}

        obj = context.scene.objects[self.obj_name]

        # Loop through hair objects
        for mod in obj.modifiers:
            if mod.type == "PARTICLE_SYSTEM" and mod.name == self.particle_system:
                visibility = mod.show_viewport
                set_bool(mod, "show_viewport", not visibility)
                set_bool(mod, "show_render", not visibility)

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_HairVisibility)
    bpy.utils.register_class(MustardUI_HairVisibility_Extras)
    bpy.utils.register_class(MustardUI_HairVisibility_Extras_ParticleSystem)


def unregister():
    bpy.utils.unregister_class(MustardUI_HairVisibility_Extras_ParticleSystem)
    bpy.utils.unregister_class(MustardUI_HairVisibility_Extras)
    bpy.utils.unregister_class(MustardUI_HairVisibility)
