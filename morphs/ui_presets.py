import bpy

from ..model_selection.active_object import mustardui_active_object
from .misc import get_cp_source


class MustardUI_Morphs_PresetCreate(bpy.types.Operator):
    """Create Morph preset"""

    bl_idname = "mustardui.morphs_preset_create"
    bl_label = "Morph Preset Create"
    bl_options = {"UNDO"}

    new_preset_name: bpy.props.StringProperty()

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        return res if arm is not None else False

    def execute(self, context):

        if self.new_preset_name == "":
            self.report({"ERROR"}, "MustardUI - Invalid preset name")
            return {"FINISHED"}

        res, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings
        morph_settings = arm.MustardUI_MorphsSettings

        presets = morph_settings.presets

        # Check if the name is already used, otherwise rename with .xxx Blender
        # convention
        preset_names = [x.name for x in presets]

        base_name = self.new_preset_name
        new_name = base_name
        counter = 1

        while new_name in preset_names:
            new_name = f"{base_name}.{counter:03d}"
            counter += 1

        # Add preset
        new_preset = presets.add()
        new_preset.name = new_name

        for section in morph_settings.sections:
            for morph in section.morphs:
                cp_source = get_cp_source(morph.custom_property_source, rig_settings)
                val = 0.0
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

        self.report({"INFO"}, f"MustardUI - Preset '{new_preset.name}' created")

        return {"FINISHED"}


class MustardUI_Morphs_PresetApply(bpy.types.Operator):
    """Apply Morph preset"""

    bl_idname = "mustardui.morphs_preset_apply"
    bl_label = "Morph Preset Apply"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        return res if arm is not None else False

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings
        morph_settings = arm.MustardUI_MorphsSettings

        presets = morph_settings.presets

        index = arm.mustardui_morphs_preset_uilist_index

        if len(presets) <= index:
            return {"FINISHED"}

        preset = presets[index]

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
                    cp_source[preset_morph.path] = (
                        True if abs(float(val)) > 0.001 else False
                    )
                elif isinstance(current_val, int) and not isinstance(current_val, bool):
                    cp_source[preset_morph.path] = int(val)
                else:
                    cp_source[preset_morph.path] = val

            elif (
                preset_morph.shape_key
                and rig_settings.data
                and rig_settings.data.shape_keys
            ):
                kb = rig_settings.model_body.data.shape_keys.key_blocks.get(
                    preset_morph.path
                )
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
            self.report({"INFO"}, "MustardUI - Preset '" + preset.name + "' applied.")
        else:
            self.report(
                {"WARNING"},
                "MustardUI - Preset '"
                + preset.name
                + "' applied with "
                + str(errors)
                + " missing entries.",
            )

        return {"FINISHED"}


class MUSTARDUI_UL_Morphs_Presets_UIList(bpy.types.UIList):
    """UIList for Morph Presets"""

    def poll(cls, context):
        res, obj = mustardui_active_object(context, config=0)
        return res if obj is not None else False

    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname, index
    ):
        row = layout.row(align=True)
        row.prop(
            item,
            "name",
            text="",
            emboss=False,
            translate=False,
        )
        row.separator()
        row.prop(
            item,
            "default",
            text="",
            emboss=False,
            icon="RADIOBUT_ON" if item.default else "RADIOBUT_OFF",
        )


class MustardUI_Morphs_PresetsUI(bpy.types.Operator):
    """Presets UI for Morphs"""

    bl_idname = "mustardui.morphs_presets_ui"
    bl_label = "Morph Presets"
    bl_options = {"UNDO"}

    bl_space_type = "OUTLINER"
    bl_region_type = "WINDOW"

    new_preset_name: bpy.props.StringProperty(name="New Preset Name", default="Preset")

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        return res if arm is not None else False

    def execute(self, context):
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=250)

    def draw(self, context):
        res, arm = mustardui_active_object(context, config=0)

        morph_settings = arm.MustardUI_MorphsSettings
        presets = morph_settings.presets

        preset_type = "MORPHS"

        layout = self.layout

        if len(presets) > 0:
            row = layout.row()
            row.template_list(
                "MUSTARDUI_UL_Morphs_Presets_UIList",
                "The_List",
                morph_settings,
                "presets",
                arm,
                "mustardui_morphs_preset_uilist_index",
            )
            col = row.column()
            col.operator("mustardui.morphs_preset_apply", text="", icon="PLAY")
            col.separator()

            col2 = col.column(align=True)
            col2.operator("mustardui.morphs_preset_import", text="", icon="COPYDOWN")
            col2.operator("mustardui.morphs_preset_export", text="", icon="PASTEDOWN")

            op = col2.operator("mustardui.preset_transfer", text="", icon="FORWARD")
            op.preset_type = preset_type

            col.separator()
            op = col.operator("mustardui.preset_delete", text="", icon="X")
            op.preset_type = preset_type
        else:
            row = layout.row(align=True)
            row.operator(
                "mustardui.morphs_preset_import", text="Import Preset", icon="PASTEDOWN"
            )

        layout.separator()

        row = layout.row(align=True)
        row.prop(self, "new_preset_name", text="")
        row.operator(
            "mustardui.morphs_preset_create", icon="ADD", text=""
        ).new_preset_name = self.new_preset_name


def register():
    bpy.utils.register_class(MUSTARDUI_UL_Morphs_Presets_UIList)
    bpy.utils.register_class(MustardUI_Morphs_PresetsUI)
    bpy.utils.register_class(MustardUI_Morphs_PresetCreate)
    bpy.utils.register_class(MustardUI_Morphs_PresetApply)

    bpy.types.Armature.mustardui_morphs_preset_uilist_index = bpy.props.IntProperty(
        name="", default=0
    )


def unregister():
    del bpy.types.Armature.mustardui_morphs_preset_uilist_index

    bpy.utils.unregister_class(MustardUI_Morphs_PresetApply)
    bpy.utils.unregister_class(MustardUI_Morphs_PresetCreate)
    bpy.utils.unregister_class(MustardUI_Morphs_PresetsUI)
    bpy.utils.unregister_class(MUSTARDUI_UL_Morphs_Presets_UIList)
