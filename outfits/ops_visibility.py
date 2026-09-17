import bpy

from ..custom_properties.misc import mustardui_cp_apply_on_switch
from ..hair.helper_functions import apply_hair_visibility, hair_switcher_active
from ..misc.set_bool import set_bool
from ..model_selection.active_object import (
    active_object_operator_poll,
    mustardui_active_object,
)
from ..physics.update_enable import enable_physics_update
from .helper_functions import (
    get_mask_visibility,
    outfits_update_armature_collections,
    update_extras_visibility,
    update_masks,
)


# Switch the visibility of an outfit piece, and of its children with shift
# Returns {piece name: visible} of the switched pieces
def switch_outfit_piece(arm, obj, shift=False):
    rig_settings = arm.MustardUI_RigSettings
    outfit_cp = arm.MustardUI_CustomPropertiesOutfit

    hair_collection = rig_settings.hair_collection
    hair_switch_collection = rig_settings.hair_switch_collection

    switched = {}

    def apply_visibility(o):
        # Object visibility
        visible = not o.hide_viewport

        set_bool(o, "hide_viewport", visible)
        set_bool(o, "hide_render", visible)
        set_bool(o, "MustardUI_outfit_visibility", visible)

        # Shape Keys and their drivers
        if (
            rig_settings.outfit_switch_shape_keys_disable
            and o.type == "MESH"
            and o.data
            and o.data.shape_keys
        ):
            for key in o.data.shape_keys.key_blocks:
                set_bool(key, "mute", visible)
            if o.data.shape_keys.animation_data and o.data.shape_keys.animation_data.drivers:
                for fcurve in o.data.shape_keys.animation_data.drivers:
                    set_bool(fcurve, "mute", visible)

        # Modifier visibility
        if (
            rig_settings.outfit_switch_armature_disable
            or rig_settings.outfit_switch_modifiers_disable
        ):
            for mod in o.modifiers:
                if mod.type == "ARMATURE" and rig_settings.outfit_switch_armature_disable:
                    set_bool(mod, "show_viewport", not visible)
                    continue

                if not rig_settings.outfit_switch_modifiers_disable:
                    continue

                if (
                    mod.type == "CORRECTIVE_SMOOTH"
                    and rig_settings.outfits_enable_global_smoothcorrection
                ):
                    desired = not visible if rig_settings.outfits_global_smoothcorrection else False
                    set_bool(mod, "show_viewport", desired)
                elif mod.type == "SHRINKWRAP" and rig_settings.outfits_enable_global_shrinkwrap:
                    desired = not visible if rig_settings.outfits_global_shrinkwrap else False
                    set_bool(mod, "show_viewport", desired)
                elif mod.type == "SUBSURF" and rig_settings.outfits_enable_global_subsurface:
                    desired = not visible if rig_settings.outfits_global_subsurface else False
                    set_bool(mod, "show_viewport", desired)

        # Hair visibility — toggle direct children of hair_collection
        # individually so nested sub-collections (extras, switcher) are
        # not cascade-hidden by Blender's collection visibility.
        if (
            hair_collection is not None
            and o.type in ["MESH", "ARMATURE"]
            and hair_switch_collection is not None
            and o.name in hair_switch_collection.all_objects
        ):
            apply_hair_visibility(rig_settings, force_hidden=hair_switcher_active(rig_settings))

        # Custom Properties/Actions on Switch
        mustardui_cp_apply_on_switch(
            arm,
            outfit_cp,
            lambda cp: not visible if cp.outfit_piece == o else None,
        )

        switched[o.name] = not o.hide_viewport

    # Apply to main object
    apply_visibility(obj)

    # Apply to children if shift is pressed
    if shift:

        def apply_visibility_recursive(parent, depth=0):
            if depth >= 3:
                return
            for child in parent.children:
                if child.hide_viewport != obj.hide_viewport:
                    apply_visibility(child)
                apply_visibility_recursive(child, depth + 1)

        apply_visibility_recursive(obj)

    return switched


# Update the whole model once after switching the given pieces with switch_outfit_piece
def update_model_after_pieces_switch(context, arm, objects, switched):
    rig_settings = arm.MustardUI_RigSettings
    armature_settings = arm.MustardUI_ArmatureSettings
    physics_settings = arm.MustardUI_PhysicsSettings

    # Masks
    visibility = get_mask_visibility(rig_settings)
    for name, visible in switched.items():
        visibility.setdefault(name, visible and rig_settings.outfits_global_mask)
    update_masks(context, rig_settings, visibility)

    # Extras
    hidden = update_extras_visibility(context, rig_settings)

    # Physics update
    if physics_settings.enable_ui:
        enable_physics_update(physics_settings, context)

    # Update tags
    if rig_settings.outfits_update_tag_on_switch:
        arm.update_tag()

        def update_tags_recursive(parent, depth=0):
            if depth >= 3:
                return
            parent.update_tag()
            for child in parent.children:
                update_tags_recursive(child, depth + 1)

        for obj in objects:
            update_tags_recursive(obj)

    # Armature collections
    if armature_settings.outfits:
        outfits_update_armature_collections(rig_settings, arm, is_extras_hidden=hidden)


class MustardUI_OutfitVisibility(bpy.types.Operator):
    """Change the visibility of the selected object"""

    bl_idname = "mustardui.object_visibility"
    bl_label = "Object Visibility"
    bl_options = {"UNDO"}

    obj: bpy.props.StringProperty()
    shift: bpy.props.BoolProperty(default=False)

    @classmethod
    def poll(cls, context):
        return active_object_operator_poll(context, config=-1)

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

        poll, arm = mustardui_active_object(context, config=0)

        switched = switch_outfit_piece(arm, obj, self.shift)
        update_model_after_pieces_switch(context, arm, [obj], switched)

        self.shift = False
        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_OutfitVisibility)


def unregister():
    bpy.utils.unregister_class(MustardUI_OutfitVisibility)
