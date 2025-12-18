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

    def _set_object_visibility(self, obj, rig_settings):
        """Set object and modifier visibility only if it actually differs"""
        visible = not obj.hide_viewport

        # Object visibility
        set_bool(obj, "hide_viewport", visible)
        set_bool(obj, "hide_render", visible)
        set_bool(obj, "MustardUI_outfit_visibility", visible)

        # Modifier visibility
        if rig_settings.outfit_switch_armature_disable or rig_settings.outfit_switch_modifiers_disable:
            for mod in obj.modifiers:
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

        # Update object visibility
        self._set_object_visibility(obj, rig_settings)
        visible = not obj.hide_viewport

        # Update custom properties
        ui_data_cache = {}
        for cp in outfit_cp:
            if cp.outfit_piece != obj:
                continue
            if not (cp.outfit_enable_on_switch or cp.outfit_disable_on_switch):
                continue

            prop = cp.prop_name
            ui_data = ui_data_cache.get(prop)
            if ui_data is None:
                ui_data = arm.id_properties_ui(prop).as_dict()
                ui_data_cache[prop] = ui_data

            if visible and cp.outfit_enable_on_switch:
                if arm[prop] != ui_data['max']:
                    arm[prop] = ui_data['max']
            elif not visible and cp.outfit_disable_on_switch:
                if arm[prop] != ui_data['default']:
                    arm[prop] = ui_data['default']

        # Update extras collection visibility
        extras = rig_settings.extras_collection
        if extras:
            items = extras.all_objects if rig_settings.outfit_config_subcollections else extras.objects
            hidden = all(x.hide_render for x in items)
            set_bool(extras, "hide_viewport", hidden)
            set_bool(extras, "hide_render", hidden)

        # Update body mask modifiers
        body = rig_settings.model_body
        if body:
            for mod in body.modifiers:
                if mod.type == "MASK" and self.obj in mod.name and rig_settings.outfits_global_mask:
                    set_bool(mod, "show_viewport", not obj.hide_viewport)
                    set_bool(mod, "show_render", not obj.hide_viewport)
        else:
            self.report({'WARNING'}, 'MustardUI - Outfit Body has not been specified.')

        # Update armature bone collections visibility
        if armature_settings.outfits:
            outfits_update_armature_collections(rig_settings, arm)

        # Propagate shift-click visibility to children
        if self.shift:
            for child in obj.children:
                if child.hide_viewport != obj.hide_viewport:
                    self._set_object_visibility(child, rig_settings)

        self.shift = False

        # Physics update
        if physics_settings.enable_ui:
            enable_physics_update(physics_settings, context)

        # Update object and children tags
        if rig_settings.outfits_update_tag_on_switch:
            arm.update_tag()
            obj.update_tag()
            for child in obj.children:
                child.update_tag()

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_OutfitVisibility)


def unregister():
    bpy.utils.unregister_class(MustardUI_OutfitVisibility)
