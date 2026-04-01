import bpy
from ..model_selection.active_object import mustardui_active_object
from ..physics.update_enable import enable_physics_update
from .helper_functions import outfits_update_armature_collections
from ..misc.set_bool import set_bool


class MustardUI_HairVisibility(bpy.types.Operator):
    """Switch visibility of hair objects in a collection"""
    bl_idname = "mustardui.hair_visibility"
    bl_label = "Hair Visibility"
    bl_options = {'UNDO'}

    obj_name: bpy.props.StringProperty()

    def _set_object_visibility(self, obj, visible, rig_settings):
        """Set object and relevant modifiers visibility"""
        set_bool(obj, "hide_viewport", not visible)
        set_bool(obj, "hide_render", not visible)

        for mod in [x for x in obj.modifiers if x.type in ["PARTICLE_SYSTEM", "ARMATURE"]]:
            if mod.type == "PARTICLE_SYSTEM":
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
        for obj in [x for x in hair_collection.objects if x.type != "CURVES"]:
            visible = hair_list in obj.name
            self._set_object_visibility(obj, visible, rig_settings)

        # Update armature collections visibility using the outfit-style logic
        outfits_update_armature_collections(rig_settings, arm)

        # Update tags if enabled
        if rig_settings.hair_update_tag_on_switch:
            for obj in hair_collection.objects:
                obj.update_tag()

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_HairVisibility)


def unregister():
    bpy.utils.unregister_class(MustardUI_HairVisibility)
