import bpy
from ..model_selection.active_object import *
from .misc import get_cp_source


class MustardUI_Morphs_PresetCreate(bpy.types.Operator):
    """Create Morph preset"""
    bl_idname = "mustardui.morphs_preset_create"
    bl_label = "Morph Preset Create"
    bl_options = {'UNDO'}

    new_preset_name: bpy.props.StringProperty()

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        return res if arm is not None else False

    def execute(self, context):

        if self.new_preset_name == "":
            self.report({'ERROR'}, f'MustardUI - Invalid preset name')
            return {'FINISHED'}

        res, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings
        morph_settings = arm.MustardUI_MorphsSettings

        presets = morph_settings.presets

        preset_names = [x.name for x in presets]
        if self.new_preset_name in preset_names:
            self.report({'ERROR'}, f'MustardUI - Preset name already used')
            return {'FINISHED'}

        new_preset = presets.add()
        new_preset.name = self.new_preset_name

        for section in morph_settings.sections:
            for morph in section.morphs:
                cp_source = get_cp_source(morph.custom_property_source, rig_settings)
                val = 0.
                if cp_source and morph.custom_property:
                    cp = cp_source.get(morph.path)
                    if cp is not None:
                        val = cp
                elif morph.shape_key:
                    kb = rig_settings.data.shape_keys.key_blocks.get(morph.path)
                    if kb is not None:
                        val = kb.value

                if abs(float(val)) > 0.001:
                    new_morph = new_preset.morphs.add()
                    new_morph.name = morph.name
                    new_morph.path = morph.path
                    new_morph.section_name = section.name
                    new_morph.value = float(val)

                    new_morph.custom_property = morph.custom_property
                    new_morph.shape_key = morph.shape_key
                    new_morph.custom_property_source = morph.custom_property_source

        self.report({'INFO'}, f'MustardUI - Preset \'' + new_preset.name + '\' created')

        return {'FINISHED'}


class MustardUI_Morphs_PresetApply(bpy.types.Operator):
    """Apply Morph preset"""
    bl_idname = "mustardui.morphs_preset_apply"
    bl_label = "Morph Preset Create"
    bl_options = {'UNDO'}

    preset_id: bpy.props.IntProperty(default=-1)

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        return res if arm is not None else False

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings
        morph_settings = arm.MustardUI_MorphsSettings

        presets = morph_settings.presets

        preset = presets[self.preset_id]

        errors = 0

        for preset_morph in preset.morphs:
            cp_source = get_cp_source(preset_morph.custom_property_source, rig_settings)
            val = preset_morph.value
            if cp_source and preset_morph.custom_property:
                cp = cp_source.get(preset_morph.path)
                if cp is None:
                    errors += 1
                    continue

                current_val = cp
                if isinstance(current_val, bool):
                    cp_source[preset_morph.path] = True if abs(float(val)) > 0.001 else False
                elif isinstance(current_val, int) and not isinstance(current_val, bool):
                    cp_source[preset_morph.path] = int(val)
                else:
                    cp_source[preset_morph.path] = val

            elif preset_morph.shape_key and rig_settings.data and rig_settings.data.shape_keys:
                kb = rig_settings.model_body.data.shape_keys.key_blocks.get(preset_morph.path)
                if kb is None:
                    errors += 1
                    continue
                kb.value = val

        # Update everything
        if arm:
            arm.update_tag()
        if rig_settings.model_armature_object:
            rig_settings.model_armature_object.update_tag()
        if rig_settings.model_body:
            rig_settings.model_body.update_tag()
            if rig_settings.model_body.data:
                rig_settings.model_body.data.update_tag()
                rig_settings.model_body.data.update()
        bpy.context.view_layer.update()

        if errors == 0:
            self.report({'INFO'}, f'MustardUI - Preset \'' + preset.name + '\' applied.')
        else:
            self.report({'WARNING'}, f'MustardUI - Preset \'' + preset.name + '\' applied with ' + str(errors) + ' missing entries.')

        return {'FINISHED'}


class MustardUI_Morphs_PresetDelete(bpy.types.Operator):
    """Delete Morph preset"""
    bl_idname = "mustardui.morphs_preset_delete"
    bl_label = "Morph Preset Create"
    bl_options = {'UNDO'}

    preset_id: bpy.props.IntProperty(default=-1)

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        return res if arm is not None else False

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=0)
        morph_settings = arm.MustardUI_MorphsSettings

        presets = morph_settings.presets

        preset = presets[self.preset_id]
        preset_name = preset.name

        presets.remove(self.preset_id)

        self.report({'INFO'}, f'MustardUI - Preset \'' + preset_name + '\' deleted')

        return {'FINISHED'}


class MustardUI_Morphs_PresetsUI(bpy.types.Operator):
    """Presets UI for Morphs"""
    bl_idname = "mustardui.morphs_presets_ui"
    bl_label = "Morph Presets"
    bl_options = {'UNDO'}

    bl_space_type = 'OUTLINER'
    bl_region_type = 'WINDOW'

    new_preset_name: bpy.props.StringProperty(
        name="New Preset Name",
        default="Preset")

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        return res if arm is not None else False

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=250)

    def draw(self, context):
        res, arm = mustardui_active_object(context, config=0)

        morph_settings = arm.MustardUI_MorphsSettings
        presets = morph_settings.presets

        layout = self.layout

        if len(presets):
            box = layout.box()

        for pid, preset in enumerate(presets):
            row = box.row(align=True)
            row.operator("mustardui.morphs_preset_apply", text=preset.name).preset_id = pid
            row.operator("mustardui.morphs_preset_delete", text="", icon="X").preset_id = pid
            row.separator()
            row.operator("mustardui.morphs_preset_export", text="", icon="COPYDOWN").preset_id = pid

        if len(presets):
            layout.separator()

        row = layout.row(align=True)
        row.prop(self, "new_preset_name", text="")
        row.operator("mustardui.morphs_preset_create", icon="ADD", text="").new_preset_name = self.new_preset_name

        layout.separator()
        row = layout.row(align=True)
        row.operator("mustardui.morphs_preset_import", text="Import Preset", icon="PASTEDOWN")


def register():
    bpy.utils.register_class(MustardUI_Morphs_PresetsUI)
    bpy.utils.register_class(MustardUI_Morphs_PresetCreate)
    bpy.utils.register_class(MustardUI_Morphs_PresetApply)
    bpy.utils.register_class(MustardUI_Morphs_PresetDelete)


def unregister():
    bpy.utils.unregister_class(MustardUI_Morphs_PresetDelete)
    bpy.utils.unregister_class(MustardUI_Morphs_PresetApply)
    bpy.utils.unregister_class(MustardUI_Morphs_PresetCreate)
    bpy.utils.unregister_class(MustardUI_Morphs_PresetsUI)
