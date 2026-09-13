import bpy

from ..custom_properties.misc import mustardui_cp_apply_on_switch
from ..misc.set_bool import set_bool
from ..model_selection.active_object import (
    active_object_operator_poll,
    mustardui_active_object,
)
from ..outfits.helper_functions import (
    find_layer_collection,
    outfits_update_armature_collections,
    update_masks,
)
from .helper_functions import (
    apply_hair_visibility,
    hair_switcher_active,
    set_object_visibility,
)


class MustardUI_HairVisibility(bpy.types.Operator):
    """Switch visibility of hair objects in a collection"""

    bl_idname = "mustardui.hair_visibility"
    bl_label = "Hair Visibility"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        return active_object_operator_poll(context, config=0)

    def execute(self, context):

        poll, arm = mustardui_active_object(context, config=0)

        rig_settings = arm.MustardUI_RigSettings
        hair_collection = rig_settings.hair_collection
        if not hair_collection:
            self.report({"WARNING"}, "MustardUI - Hair collection not defined in Rig Settings.")
            return {"CANCELLED"}

        # An Outfit piece with a dedicated Hair is enabled: keep every Hair Object
        # hidden to avoid loading a Hair on top of it. The selection is still stored,
        # and it is restored as soon as that Outfit piece is disabled
        apply_hair_visibility(rig_settings, force_hidden=hair_switcher_active(rig_settings))

        # Custom Properties/Actions on Switch
        hair_names = {x.name for x in hair_collection.objects}
        mustardui_cp_apply_on_switch(
            arm,
            arm.MustardUI_CustomPropertiesHair,
            lambda cp: (
                None
                if cp.hair is None or cp.hair.name not in hair_names
                else not cp.hair.hide_viewport
            ),
        )

        # Masks
        update_masks(context, rig_settings)

        # Update armature collections visibility using the outfit-style logic
        outfits_update_armature_collections(rig_settings, arm)

        # Update tags if enabled
        if rig_settings.hair_update_tag_on_switch:
            for obj in hair_collection.objects:
                obj.update_tag()

        return {"FINISHED"}


class MustardUI_HairVisibility_Extras(bpy.types.Operator):
    """Switch visibility of hair objects in a collection"""

    bl_idname = "mustardui.hair_visibility_extras"
    bl_label = "Hair Visibility Extras"
    bl_options = {"UNDO"}

    obj_name: bpy.props.StringProperty(default="")

    @classmethod
    def poll(cls, context):
        return active_object_operator_poll(context, config=0)

    def execute(self, context):

        poll, arm = mustardui_active_object(context, config=0)

        rig_settings = arm.MustardUI_RigSettings
        hair_extras_collection = rig_settings.hair_extras_collection
        hair_name = self.obj_name

        if not hair_extras_collection:
            self.report({"WARNING"}, "Hair Extras collection not defined in Rig Settings.")
            return {"CANCELLED"}

        obj = context.scene.objects.get(hair_name)
        if obj is None:
            self.report({"WARNING"}, f'MustardUI - Object "{hair_name}" not found.')
            return {"CANCELLED"}
        visibility = obj.hide_viewport

        # Loop through hair objects
        for obj in [x for x in hair_extras_collection.objects if hair_name == x.name]:
            set_object_visibility(obj, visibility, rig_settings)

        # Custom Properties/Actions on Switch
        mustardui_cp_apply_on_switch(
            arm,
            arm.MustardUI_CustomPropertiesHair,
            lambda cp: visibility if cp.hair is not None and cp.hair.name == hair_name else None,
        )

        hidden = all(x.hide_viewport for x in hair_extras_collection.objects)
        hair_extras_collection.hide_viewport = hidden
        hair_extras_collection.hide_render = hidden

        # Exclude the Collection
        lc = find_layer_collection(context.view_layer.layer_collection, hair_extras_collection)
        if lc is not None:
            set_bool(lc, "exclude", hidden)

        # Masks
        update_masks(context, rig_settings)

        # Update armature collections visibility using the outfit-style logic
        outfits_update_armature_collections(rig_settings, arm)

        # Update tags if enabled
        if rig_settings.hair_update_tag_on_switch:
            for obj in hair_extras_collection.objects:
                obj.update_tag()

        return {"FINISHED"}


class MustardUI_HairVisibility_Extras_ParticleSystem(bpy.types.Operator):
    """Switch visibility of particle hair system"""

    bl_idname = "mustardui.hair_visibility_extras_particle_system"
    bl_label = "Particle Hair Visibility Extras"
    bl_options = {"UNDO"}

    obj_name: bpy.props.StringProperty(default="")
    mod_name: bpy.props.StringProperty()

    @classmethod
    def poll(cls, context):
        return active_object_operator_poll(context, config=0)

    def execute(self, context):
        obj = context.scene.objects.get(self.obj_name)
        if obj is None:
            self.report({"WARNING"}, f'MustardUI - Object "{self.obj_name}" not found.')
            return {"CANCELLED"}

        # Loop through hair objects
        for mod in obj.modifiers:
            if mod.type == "PARTICLE_SYSTEM" and mod.name == self.mod_name:
                visibility = mod.show_viewport
                set_bool(mod, "show_viewport", not visibility)
                set_bool(mod, "show_render", not visibility)

        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_HairVisibility)
    bpy.utils.register_class(MustardUI_HairVisibility_Extras)
    bpy.utils.register_class(MustardUI_HairVisibility_Extras_ParticleSystem)


def unregister():
    bpy.utils.unregister_class(MustardUI_HairVisibility_Extras_ParticleSystem)
    bpy.utils.unregister_class(MustardUI_HairVisibility_Extras)
    bpy.utils.unregister_class(MustardUI_HairVisibility)
