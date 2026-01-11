import bpy
from ..model_selection.active_object import *
from ..physics.update_enable import enable_physics_update
from .helper_functions import outfits_update_armature_collections
from ..misc.set_bool import set_bool


class MustardUI_OutfitVisibility(bpy.types.Operator):
    """Change the visibility of the selected object"""
    bl_idname = "mustardui.object_visibility"
    bl_label = "Object Visibility"
    bl_options = {'UNDO'}

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
            self.report({'WARNING'}, f'MustardUI - Object "{self.obj}" not found.')
            return {'CANCELLED'}

        poll, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings
        armature_settings = arm.MustardUI_ArmatureSettings
        physics_settings = arm.MustardUI_PhysicsSettings
        outfit_cp = arm.MustardUI_CustomPropertiesOutfit

        hair_collection = rig_settings.hair_collection
        hair_switch_collection = rig_settings.hair_switch_collection

        # ------------------- PER-OBJECT UPDATES ------------------- #
        def apply_visibility(o):
            # Object visibility
            visible = not o.hide_viewport

            set_bool(o, "hide_viewport", visible)
            set_bool(o, "hide_render", visible)
            set_bool(o, "MustardUI_outfit_visibility", visible)

            # Shape Keys and their drivers
            if rig_settings.outfit_switch_shape_keys_disable and obj.type == "MESH" and obj.data and obj.data.shape_keys:
                for key in obj.data.shape_keys.key_blocks:
                    set_bool(key, "mute", visible)
                if obj.data.shape_keys.animation_data and obj.data.shape_keys.animation_data.drivers:
                    for fcurve in obj.data.shape_keys.animation_data.drivers:
                        set_bool(fcurve, "mute", visible)

            # Modifier visibility
            if rig_settings.outfit_switch_armature_disable or rig_settings.outfit_switch_modifiers_disable:
                for mod in o.modifiers:
                    if mod.type == "ARMATURE" and rig_settings.outfit_switch_armature_disable:
                        set_bool(mod, "show_viewport", not visible)
                        continue

                    if not rig_settings.outfit_switch_modifiers_disable:
                        continue

                    if mod.type == "CORRECTIVE_SMOOTH" and rig_settings.outfits_enable_global_smoothcorrection:
                        desired = not visible if rig_settings.outfits_global_smoothcorrection else False
                        set_bool(mod, "show_viewport", desired)
                    elif mod.type == "SHRINKWRAP" and rig_settings.outfits_enable_global_shrinkwrap:
                        desired = not visible if rig_settings.outfits_global_shrinkwrap else False
                        set_bool(mod, "show_viewport", desired)
                    elif mod.type == "SUBSURF" and rig_settings.outfits_enable_global_subsurface:
                        desired = not visible if rig_settings.outfits_global_subsurface else False
                        set_bool(mod, "show_viewport", desired)

            # Hair visibility
            if (hair_collection is not None
                    and o.type == "MESH"
                    and hair_switch_collection is not None
                    and o.name in hair_switch_collection.all_objects.keys()):
                hair_collection.hide_viewport = not visible
                hair_collection.hide_render = not visible

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

                if not visible and cp.outfit_enable_on_switch:
                    if arm[prop] != ui_data['max']:
                        arm[prop] = ui_data['max']
                elif visible and cp.outfit_disable_on_switch:
                    if arm[prop] != ui_data['default']:
                        arm[prop] = ui_data['default']

            # Body mask modifiers
            body = rig_settings.model_body
            if body:
                for mod in body.modifiers:
                    if mod.type == "MASK" and self.obj in mod.name and rig_settings.outfits_global_mask:
                        set_bool(mod, "show_viewport", not o.hide_viewport)
                        set_bool(mod, "show_render", not o.hide_viewport)
            else:
                self.report({'WARNING'}, 'MustardUI - Outfit Body has not been specified.')

        # Apply to main object
        apply_visibility(obj)

        # Apply to children if shift is pressed
        if self.shift:
            for child in obj.children:
                if child.hide_viewport != obj.hide_viewport:
                    apply_visibility(child)

        # ------------------- GLOBAL UPDATES ------------------- #
        # Armature collections
        if armature_settings.outfits:
            outfits_update_armature_collections(rig_settings, arm)

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
        if extras:
            items = extras.all_objects if rig_settings.outfit_config_subcollections else extras.objects
            hidden = all(x.hide_render for x in items)
            set_bool(extras, "hide_viewport", hidden)
            set_bool(extras, "hide_render", hidden)

        self.shift = False
        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_OutfitVisibility)


def unregister():
    bpy.utils.unregister_class(MustardUI_OutfitVisibility)
