import bpy

from ..misc.set_bool import set_bool
from ..model_selection.active_object import (
    active_object_operator_poll,
    mustardui_active_object,
)
from ..outfits.helper_functions import outfits_update_armature_collections


def set_object_visibility(obj, visible, rig_settings):
    """Set object and relevant modifiers visibility"""
    set_bool(obj, "hide_viewport", not visible)
    set_bool(obj, "hide_render", not visible)

    for mod in [
        x for x in obj.modifiers if x.type in ["PARTICLE_SYSTEM", "ARMATURE", "NODES"]
    ]:
        if mod.type in ["PARTICLE_SYSTEM", "NODES"]:
            set_bool(mod, "show_viewport", visible)
            set_bool(mod, "show_render", visible)
        else:  # ARMATURE
            set_bool(
                mod,
                "show_viewport",
                visible if rig_settings.hair_switch_armature_disable else True,
            )


def update_hair_extras_collection_visibility(hair_extras_collection):
    # Sync the collection visibility with the objects visibility
    hidden = all(x.hide_viewport for x in hair_extras_collection.objects)
    hair_extras_collection.hide_viewport = hidden
    hair_extras_collection.hide_render = hidden


def set_hair_extra_visibility(context, obj, visible):
    # Shared visibility update used by both the operator and the UI toggle
    poll, arm = mustardui_active_object(context, config=0)
    if not poll:
        return False

    rig_settings = arm.MustardUI_RigSettings
    hair_extras_collection = rig_settings.hair_extras_collection
    if not hair_extras_collection:
        return False

    extra_objects = [x for x in hair_extras_collection.objects if obj.name == x.name]
    if len(extra_objects) == 0:
        return False

    for extra_obj in extra_objects:
        set_object_visibility(extra_obj, visible, rig_settings)

    update_hair_extras_collection_visibility(hair_extras_collection)

    outfits_update_armature_collections(rig_settings, arm)

    if rig_settings.hair_update_tag_on_switch:
        for extra_obj in hair_extras_collection.objects:
            extra_obj.update_tag()

    return True


def get_hair_extra_visibility(obj):
    return not obj.hide_viewport


def set_hair_extra_visibility_prop(obj, value):
    set_hair_extra_visibility(bpy.context, obj, value)


def _apply_visibility_to_main_hair(rig_settings, predicate):
    # Iterates direct children of hair_collection only — nested
    # sub-collections (hair_extras_collection, hair_switch_collection) are
    # intentionally untouched so users who organise them under hair_collection
    # in the outliner aren't dragged into cascade-hides.
    hair_collection = rig_settings.hair_collection
    if hair_collection is None:
        return

    hair_objs = list(hair_collection.objects)
    for obj in hair_objs:
        if obj.type not in {"MESH", "CURVES"}:
            continue
        visible = predicate(obj.name)
        set_object_visibility(obj, visible, rig_settings)
        parent_armature = obj.find_armature()
        if parent_armature is not None and parent_armature in hair_objs:
            set_object_visibility(parent_armature, visible, rig_settings)

    if rig_settings.hair_update_tag_on_switch:
        for obj in hair_collection.objects:
            obj.update_tag()


def hide_all_main_hair(rig_settings):
    """Hide every main-hair piece in hair_collection (direct children only).

    Used by the outfit code when an outfit piece linked into
    ``hair_switch_collection`` becomes visible: the main hair gets out of the
    way without cascade-hiding any nested sub-collections.
    """
    _apply_visibility_to_main_hair(rig_settings, lambda _name: False)


def apply_hair_list_visibility(rig_settings):
    """Restore main-hair visibility per ``rig_settings.hair_list`` selection.

    Used by the outfit code when a hair-switching piece becomes hidden, to
    bring back the currently selected hair (matches the semantics of the
    ``mustardui.hair_visibility`` operator).
    """
    hair_list = rig_settings.hair_list
    _apply_visibility_to_main_hair(rig_settings, lambda name: name == hair_list)


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
        hair_list = rig_settings.hair_list
        if not hair_collection:
            self.report({"WARNING"}, "Hair collection not defined in Rig Settings.")
            return {"CANCELLED"}

        # Loop through hair objects
        hair_collection_objs = [x for x in hair_collection.objects]
        for obj in [x for x in hair_collection_objs if x.type in {"MESH", "CURVES"}]:
            visible = hair_list == obj.name

            set_object_visibility(obj, visible, rig_settings)

            parent_armature = obj.find_armature()
            if parent_armature is not None and parent_armature in hair_collection_objs:
                set_object_visibility(parent_armature, visible, rig_settings)

        # Update armature collections visibility using the outfit-style logic
        outfits_update_armature_collections(rig_settings, arm)

        # Update tags if enabled
        if rig_settings.hair_update_tag_on_switch:
            for obj in hair_collection.objects:
                obj.update_tag()

        return {"FINISHED"}


class MustardUI_HairVisibility_Extras(bpy.types.Operator):
    """Switch visibility of hair objects in a collection.

    Note: the in-panel UI no longer invokes this operator (it uses the
    ``MustardUI_hair_extra_visibility`` BoolProperty on Object so that
    drag-toggle works). This operator is kept as a public API entry
    point for keymaps and external scripts referencing ``bl_idname``.
    """

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
            self.report(
                {"WARNING"}, "Hair Extras collection not defined in Rig Settings."
            )
            return {"CANCELLED"}

        obj = context.scene.objects[hair_name]
        visibility = obj.hide_viewport

        set_hair_extra_visibility(context, obj, visibility)

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
        obj = context.scene.objects[self.obj_name]

        # Loop through hair objects
        for mod in obj.modifiers:
            if mod.type == "PARTICLE_SYSTEM" and mod.name == self.mod_name:
                visibility = mod.show_viewport
                set_bool(mod, "show_viewport", not visibility)
                set_bool(mod, "show_render", not visibility)

        return {"FINISHED"}


def register():
    # Bool property used to enable drag-toggle interactions in the UI
    bpy.types.Object.MustardUI_hair_extra_visibility = bpy.props.BoolProperty(
        default=False,
        name="",
        description="Toggle Hair Extra visibility",
        get=get_hair_extra_visibility,
        set=set_hair_extra_visibility_prop,
    )
    bpy.utils.register_class(MustardUI_HairVisibility)
    bpy.utils.register_class(MustardUI_HairVisibility_Extras)
    bpy.utils.register_class(MustardUI_HairVisibility_Extras_ParticleSystem)


def unregister():
    bpy.utils.unregister_class(MustardUI_HairVisibility_Extras_ParticleSystem)
    bpy.utils.unregister_class(MustardUI_HairVisibility_Extras)
    bpy.utils.unregister_class(MustardUI_HairVisibility)
    del bpy.types.Object.MustardUI_hair_extra_visibility
