import bpy
from ..model_selection.active_object import *
from ..physics.update_enable import enable_physics_update
from .helper_functions import outfits_update_armature_collections
from ..misc.set_bool import set_bool


def _set_modifier_visibility(mod, value):
    if mod.show_viewport != value:
        mod.show_viewport = value


# Operator to switch visibility of an object
class MustardUI_CompleteOutfitVisibility(bpy.types.Operator):
    bl_idname = "mustardui.outfit_visibility"
    bl_label = "Update Outfits Visibility"
    bl_options = {'UNDO'}

    def execute(self, context):

        poll, arm = mustardui_active_object(context, config=0)
        if not poll:
            self.report({'WARNING'}, "No active MustardUI armature")
            return {'CANCELLED'}

        rig_settings = arm.MustardUI_RigSettings
        arm_settings = arm.MustardUI_ArmatureSettings
        physics = arm.MustardUI_PhysicsSettings
        body = rig_settings.model_body

        outfits_list = rig_settings.outfits_list
        use_subcollections = rig_settings.outfit_config_subcollections

        # Cache flags
        arm_disable = rig_settings.outfit_switch_armature_disable
        mods_disable = rig_settings.outfit_switch_modifiers_disable
        sk_disable = rig_settings.outfit_switch_shape_keys_disable

        smooth = rig_settings.outfits_enable_global_smoothcorrection and rig_settings.outfits_global_smoothcorrection
        shrink = rig_settings.outfits_enable_global_shrinkwrap and rig_settings.outfits_global_shrinkwrap
        subsurf = rig_settings.outfits_enable_global_subsurface and rig_settings.outfits_global_subsurface
        mask = rig_settings.outfits_global_mask

        # Collections, objects, modifiers, masks
        for col_entry in rig_settings.outfits_collections:

            col = col_entry.collection
            if not col:
                continue

            items = col.all_objects if use_subcollections else col.objects

            is_active = (col.name == outfits_list)
            locked_collection = any(o.MustardUI_outfit_lock for o in items)

            any_object_visible = False

            for obj in items:

                hidden_flag = obj.MustardUI_outfit_visibility

                locked = obj.MustardUI_outfit_lock

                if locked_collection and not is_active:
                    show_obj = not hidden_flag if locked else locked
                elif is_active:
                    show_obj = not hidden_flag
                else:
                    show_obj = False

                set_bool(obj, "hide_viewport", not show_obj)
                set_bool(obj, "hide_render", not show_obj)

                # Check Hair Visibility against the Hair Switcher Collection
                hair_collection = rig_settings.hair_collection
                if (hair_collection is not None
                        and obj.type == "MESH"
                        and rig_settings.hair_switch_collection is not None
                        and obj.name in rig_settings.hair_switch_collection.all_objects.keys()):
                    set_bool(hair_collection, "hide_viewport", show_obj)
                    set_bool(hair_collection, "hide_render", show_obj)

                if show_obj:
                    any_object_visible = True

                # Shape Keys and their drivers
                if sk_disable and obj.type == "MESH" and obj.data and obj.data.shape_keys:
                    for key in obj.data.shape_keys.key_blocks:
                        set_bool(key, "mute", not show_obj)
                    if obj.data.shape_keys.animation_data and obj.data.shape_keys.animation_data.drivers:
                        for fcurve in obj.data.shape_keys.animation_data.drivers:
                            set_bool(fcurve, "mute", not show_obj)

                # Modifiers
                if arm_disable or mods_disable:
                    for mod in obj.modifiers:
                        if mod.type == "ARMATURE" and arm_disable:
                            # If we are switching to the active outfit
                            if is_active:
                                desired = True
                            # If the collection has locked objects but this obj is not the active one
                            elif locked_collection and not is_active:
                                desired = not obj.MustardUI_outfit_visibility if locked else locked
                            # All other outfits
                            else:
                                desired = False

                            set_bool(mod, "show_viewport", desired)
                            continue

                        if not mods_disable:
                            continue

                        if mod.type == "CORRECTIVE_SMOOTH" and smooth:
                            set_bool(mod, "show_viewport", show_obj)
                        elif mod.type == "SHRINKWRAP" and shrink:
                            set_bool(mod, "show_viewport", show_obj)
                        elif mod.type == "SUBSURF" and subsurf:
                            set_bool(mod, "show_viewport", show_obj)

                # Body masks
                if body:
                    mask_visible = (is_active or locked) and show_obj and mask
                    for mod in body.modifiers:
                        if mod.type in ["MASK", "VERTEX_WEIGHT_MIX"] and mod.name.endswith(obj.name):
                            set_bool(mod, "show_viewport", mask_visible)
                            set_bool(mod, "show_render", mask_visible)

            # Collection visibility AFTER objects
            col_visible = is_active or locked_collection or any_object_visible
            set_bool(col, "hide_viewport", not col_visible)
            set_bool(col, "hide_render", not col_visible)

        # Armature layers
        if arm_settings.outfits:
            outfits_update_armature_collections(rig_settings, arm)

        # Custom properties
        ui_cache = {}
        outfit_nude = rig_settings.outfit_nude

        for cp in arm.MustardUI_CustomPropertiesOutfit:

            if not (cp.outfit_enable_on_switch or cp.outfit_disable_on_switch):
                continue
            if not outfit_nude and not cp.outfit:
                continue

            prop = cp.prop_name
            if prop not in arm.keys():
                continue

            ui = ui_cache.get(prop)
            if ui is None:
                ui = arm.id_properties_ui(prop).as_dict()
                ui_cache[prop] = ui

            desired = None

            if cp.outfit:
                if cp.outfit_piece:
                    piece = cp.outfit_piece
                    piece_visible = not piece.hide_viewport
                    piece_locked = piece.MustardUI_outfit_lock

                    if (
                        cp.outfit.name == outfits_list
                        and piece_visible
                        and cp.outfit_enable_on_switch
                    ):
                        desired = ui['max']
                    elif cp.outfit.name != outfits_list and cp.outfit_disable_on_switch:
                        desired = ui['max'] if piece_locked and piece_visible else ui['default']
                else:
                    if cp.outfit.name == outfits_list and cp.outfit_enable_on_switch:
                        desired = ui['max']
                    elif cp.outfit.name != outfits_list and cp.outfit_disable_on_switch:
                        desired = ui['default']

            elif outfit_nude:
                if outfits_list == "Nude" and cp.outfit_enable_on_switch:
                    desired = ui['max']
                elif outfits_list != "Nude" and cp.outfit_disable_on_switch:
                    desired = ui['default']

            if desired is not None and arm[prop] != desired:
                arm[prop] = desired

        # Physics & update tag
        if physics.enable_ui:
            enable_physics_update(physics, context)

        if rig_settings.outfits_update_tag_on_switch:
            arm.update_tag()

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_CompleteOutfitVisibility)


def unregister():
    bpy.utils.unregister_class(MustardUI_CompleteOutfitVisibility)
