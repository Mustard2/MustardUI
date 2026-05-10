import bpy

from ..misc.set_bool import set_bool
from ..model_selection.active_object import mustardui_active_object
from ..physics.update_enable import enable_physics_update
from .helper_functions import outfits_update_armature_collections


def set_outfit_visibility(context, obj, desired_visible, include_children=False):
    # Shared visibility update used by both the operator and the UI toggle
    poll, arm = mustardui_active_object(context, config=0)
    if not poll:
        return False

    rig_settings = arm.MustardUI_RigSettings
    armature_settings = arm.MustardUI_ArmatureSettings
    physics_settings = arm.MustardUI_PhysicsSettings
    outfit_cp = arm.MustardUI_CustomPropertiesOutfit

    hair_collection = rig_settings.hair_collection
    hair_switch_collection = rig_settings.hair_switch_collection

    def apply_visibility(o, visible):
        hidden = not visible

        # Object visibility
        set_bool(o, "hide_viewport", hidden)
        set_bool(o, "hide_render", hidden)
        set_bool(o, "MustardUI_outfit_visibility", hidden)

        # Shape Keys and their drivers
        if (
            rig_settings.outfit_switch_shape_keys_disable
            and o.type == "MESH"
            and o.data
            and o.data.shape_keys
        ):
            for key in o.data.shape_keys.key_blocks:
                set_bool(key, "mute", hidden)
            if o.data.shape_keys.animation_data and o.data.shape_keys.animation_data.drivers:
                for fcurve in o.data.shape_keys.animation_data.drivers:
                    set_bool(fcurve, "mute", hidden)

        if (
            rig_settings.outfit_switch_armature_disable
            or rig_settings.outfit_switch_modifiers_disable
        ):
            for mod in o.modifiers:
                if (
                    mod.type == "ARMATURE"
                    and rig_settings.outfit_switch_armature_disable
                ):
                    set_bool(mod, "show_viewport", visible)
                    continue

                if not rig_settings.outfit_switch_modifiers_disable:
                    continue

                if (
                    mod.type == "CORRECTIVE_SMOOTH"
                    and rig_settings.outfits_enable_global_smoothcorrection
                ):
                    desired = visible if rig_settings.outfits_global_smoothcorrection else False
                    set_bool(mod, "show_viewport", desired)
                elif (
                    mod.type == "SHRINKWRAP"
                    and rig_settings.outfits_enable_global_shrinkwrap
                ):
                    desired = visible if rig_settings.outfits_global_shrinkwrap else False
                    set_bool(mod, "show_viewport", desired)
                elif (
                    mod.type == "SUBSURF"
                    and rig_settings.outfits_enable_global_subsurface
                ):
                    desired = visible if rig_settings.outfits_global_subsurface else False
                    set_bool(mod, "show_viewport", desired)

        # Hair visibility
        if (
            hair_collection is not None
            and o.type in ["MESH", "ARMATURE"]
            and hair_switch_collection is not None
            and o.name in hair_switch_collection.all_objects.keys()
        ):
            hair_collection.hide_viewport = visible
            hair_collection.hide_render = visible

        # Custom properties
        ui_data_cache = {}
        for cp in outfit_cp:
            if cp.outfit_piece != o:
                continue
            if not (cp.outfit_enable_on_switch or cp.outfit_disable_on_switch):
                continue

            prop = cp.prop_name
            ui_data = ui_data_cache.get(prop)
            if ui_data is None:
                ui_data = arm.id_properties_ui(prop).as_dict()
                ui_data_cache[prop] = ui_data

            if visible and cp.outfit_enable_on_switch:
                if arm[prop] != ui_data["max"]:
                    arm[prop] = ui_data["max"]
            elif hidden and cp.outfit_disable_on_switch:
                if arm[prop] != ui_data["default"]:
                    arm[prop] = ui_data["default"]

        # Body mask modifiers
        body = rig_settings.model_body
        if body:
            for mod in body.modifiers:
                if (
                    mod.type in ["MASK", "VERTEX_WEIGHT_MIX"]
                    and obj.name in mod.name.split("|")
                    and rig_settings.outfits_global_mask
                ):
                    set_bool(mod, "show_viewport", visible)
                    set_bool(mod, "show_render", visible)

    apply_visibility(obj, desired_visible)

    if include_children:
        # Apply to children if requested by the operator
        for child in obj.children:
            if (not child.hide_viewport) != desired_visible:
                apply_visibility(child, desired_visible)

    # Physics update
    if physics_settings.enable_ui:
        enable_physics_update(physics_settings, context)

    # Update tags
    if rig_settings.outfits_update_tag_on_switch:
        arm.update_tag()
        obj.update_tag()
        for child in obj.children:
            child.update_tag()

    # Extras collection visibility
    extras = rig_settings.extras_collection
    hidden = None
    if extras:
        items = (
            extras.all_objects if rig_settings.outfit_config_subcollections else extras.objects
        )
        hidden = all(x.hide_render for x in items)
        set_bool(extras, "hide_viewport", hidden)
        set_bool(extras, "hide_render", hidden)

    # Armature collections
    if armature_settings.outfits:
        outfits_update_armature_collections(rig_settings, arm, is_extras_hidden=hidden)

    return True


def get_outfit_toggle_visibility(obj):
    return not obj.hide_viewport


def set_outfit_toggle_visibility(obj, value):
    set_outfit_visibility(bpy.context, obj, value)


class MustardUI_OutfitVisibility(bpy.types.Operator):
    """Change the visibility of the selected object"""

    bl_idname = "mustardui.object_visibility"
    bl_label = "Object Visibility"
    bl_options = {"UNDO"}

    obj: bpy.props.StringProperty()
    shift: bpy.props.BoolProperty(default=False)

    def invoke(self, context, event):
        if not self.shift:
            self.shift = event.shift
        return self.execute(context)

    def execute(self, context):
        scene = context.scene
        obj = scene.objects.get(self.obj)

        if obj is None:
            self.report({"WARNING"}, f'MustardUI - Object "{self.obj}" not found.')
            return {"CANCELLED"}

        set_outfit_visibility(context, obj, obj.hide_viewport, include_children=self.shift)

        # Body is required for the body-mask sync inside set_outfit_visibility;
        # warn once per click if it is missing (was reported per-object in the old code).
        poll, arm = mustardui_active_object(context, config=0)
        if poll and not arm.MustardUI_RigSettings.model_body:
            self.report(
                {"WARNING"}, "MustardUI - Outfit Body has not been specified."
            )

        self.shift = False
        return {"FINISHED"}


def register():
    # Bool property used to enable drag-toggle interactions in the UI
    bpy.types.Object.MustardUI_outfit_toggle_visibility = bpy.props.BoolProperty(
        default=False,
        name="",
        description="Toggle Outfit visibility",
        get=get_outfit_toggle_visibility,
        set=set_outfit_toggle_visibility,
    )
    bpy.utils.register_class(MustardUI_OutfitVisibility)


def unregister():
    bpy.utils.unregister_class(MustardUI_OutfitVisibility)
    del bpy.types.Object.MustardUI_outfit_toggle_visibility
