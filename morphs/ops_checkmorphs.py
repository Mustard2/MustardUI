import bpy
import re
from ..model_selection.active_object import *
from .misc import *
import itertools
from .. import __package__ as base_package
from ..menu.menu_configure import row_scale


def rename_morph(self, name):
    if not self.custom_rename:
        return name

    name = name.replace('_', ' ')

    # Add a space before a capital letter if it's preceded by a lowercase letter or another capital letter
    name = re.sub(r'(?<=[a-zA-Z])([A-Z])', r' \1', name)

    # Add a space before a number if it's preceded by a letter
    name = re.sub(r'(?<=[a-zA-Z])(\d)', r' \1', name)

    return name


class MustardUI_Morphs_Clear(bpy.types.Operator):
    """Clear the Morphs UI"""
    bl_idname = "mustardui.morphs_clear"
    bl_label = "Clear Morphs"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=1)
        morphs_settings = arm.MustardUI_MorphsSettings

        return res and morphs_settings.enable_ui and morphs_settings.sections

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=1)
        morphs_settings = arm.MustardUI_MorphsSettings

        morphs_settings.sections.clear()
        morphs_settings.diffeomorphic_genesis_version = -1
        morphs_settings.morphs_number = 0

        # Reset UI List indices
        arm.mustardui_morphs_section_uilist_index = -1

        self.report({'INFO'}, 'MustardUI - Morphs cleared.')

        return {'FINISHED'}


class MustardUI_Morphs_Check(bpy.types.Operator):
    """Search for morphs to display in the UI External Morphs panel"""
    bl_idname = "mustardui.morphs_check"
    bl_label = "Check Morphs"
    bl_options = {'UNDO'}

    custom_rename: bpy.props.BoolProperty(default=False,
                                          name="Attempt Renaming",
                                          description="Apply a predefined set of rules to attempt a better renaming of the Morphs")
    clear_existing_morphs: bpy.props.BoolProperty(default=False,
                                                  name="Clear Existing Morphs",
                                                  description="Remove existing Morphs from the sections before re-adding them")

    @classmethod
    def poll(cls, context):

        res, arm = mustardui_active_object(context, config=1)
        morphs_settings = arm.MustardUI_MorphsSettings

        if morphs_settings.type == "GENERIC":
            return res and morphs_settings.enable_ui and morphs_settings.sections
        return res and morphs_settings.enable_ui

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings
        morphs_settings = arm.MustardUI_MorphsSettings
        addon_prefs = context.preferences.addons[base_package].preferences

        # Try to assign the rig object
        if not arm.MustardUI_created:
            if context.active_object is not None and context.active_object.type == "ARMATURE":
                rig_settings.model_armature_object = context.active_object
            else:
                self.report({'ERROR'},
                            'MustardUI - You need to complete the first configuration before being able to add Morphs '
                            'to the UI.')
                return {'FINISHED'}

        # Clean the existing morph settings
        if self.clear_existing_morphs:
            for section in morphs_settings.sections:
                section.morphs.clear()

        properties_number = 0

        if morphs_settings.type == "DIFFEO_GENESIS_8" or morphs_settings.type == "DIFFEO_GENESIS_9":

            # TYPE: 0: Emotion Units, 1: Emotions, 2: FACS Emotion Units, 3: FACS Emotions, 4: Body Morphs

            # Default lists
            facs_emotions_default_list = ['facs_ctrl_Afraid', 'facs_ctrl_Angry', 'facs_ctrl_Flirting', 'facs_ctrl_Frown',
                                          'facs_ctrl_Shock', 'facs_ctrl_SmileFullFace', 'facs_ctrl_SmileOpenFullFace',
                                          'facs_ctrl_Surprised']

            # Emotions Units
            mustardui_add_section(morphs_settings.sections, ["Emotion Units"], is_internal=True, diffeomorphic=0)
            if morphs_settings.diffeomorphic_emotions_units and morphs_settings.type == "DIFFEO_GENESIS_8":
                emotions_units = [x for x in rig_settings.model_armature_object.keys() if (
                        'eCTRL' in x or 'ECTRL' in x) and not "HD" in x and not "eCTRLSmile" in x and not 'eCTRLv' in x and sum(
                    1 for c in x if c.isupper()) >= 6]

                for emotion in emotions_units:
                    name = emotion[len('eCTRL')] + ''.join(
                        [c if not c.isupper() else ' ' + c for c in emotion[len('eCTRL') + 1:]])
                    mustardui_add_morph(morphs_settings.sections[0].morphs, [name, emotion])

            # Emotions
            mustardui_add_section(morphs_settings.sections, ["Emotions"], is_internal=True, diffeomorphic=1)
            if morphs_settings.diffeomorphic_emotions and morphs_settings.type == "DIFFEO_GENESIS_8":

                emotions = [x for x in rig_settings.model_armature_object.keys() if
                            'eCTRL' in x and not "HD" in x and not 'eCTRLv' in x and (
                                    sum(1 for c in x if c.isupper()) < 6 or "eCTRLSmile" in x)]

                # Custom Diffeomorphic emotions
                emotions_custom = []
                for string in [x for x in morphs_settings.diffeomorphic_emotions_custom.split(',') if x != '']:
                    for x in [x for x in rig_settings.model_armature_object.keys() if not "Adjust Custom" in x]:
                        if string in x:
                            emotions_custom.append(x)

                for emotion in emotions:
                    name = emotion[len('eCTRL')] + ''.join(
                        [c if not c.isupper() else ' ' + c for c in emotion[len('eCTRL') + 1:]])
                    mustardui_add_morph(morphs_settings.sections[1].morphs, [name, emotion])
                for emotion in emotions_custom:
                    mustardui_add_morph(morphs_settings.sections[1].morphs, [emotion, emotion])

            # FACS Emotions Units
            sec = "Advanced Emotion Units" if morphs_settings.type == "DIFFEO_GENESIS_8" else "Emotion Units"
            mustardui_add_section(morphs_settings.sections, [sec], is_internal=True, diffeomorphic=2)
            if morphs_settings.diffeomorphic_facs_emotions_units:

                facs_emotions_units = []
                facs_emotions_units.append([x for x in rig_settings.model_armature_object.keys() if
                                            'facs_ctrl_' in x and x not in facs_emotions_default_list])
                facs_emotions_units.append([x for x in rig_settings.model_armature_object.keys() if
                                            'facs_bs_' in x and sum(1 for c in x if c.isupper()) >= 2])
                facs_emotions_units.append([x for x in rig_settings.model_armature_object.keys() if
                                            'facs_jnt_' in x and sum(1 for c in x if c.isupper()) >= 2])
                facs_emotions_units = itertools.chain.from_iterable(facs_emotions_units)

                for emotion in facs_emotions_units:
                    name = emotion[emotion.rfind('_', 0, 12) + 1] + ''.join(
                        [c if not c.isupper() else ' ' + c for c in emotion[emotion.rfind('_', 0, 12) + 2:]])
                    name = name.removesuffix('_div2')
                    mustardui_add_morph(morphs_settings.sections[2].morphs, [name, emotion])

            # FACS Emotions
            sec = "Advanced Emotions" if morphs_settings.type == "DIFFEO_GENESIS_8" else "Emotions"
            mustardui_add_section(morphs_settings.sections, [sec], is_internal=True, diffeomorphic=3)
            if morphs_settings.diffeomorphic_facs_emotions:

                facs_emotions = [x for x in rig_settings.model_armature_object.keys() if x in facs_emotions_default_list]

                # For Genesis 9, add also custom emotions to the panel
                emotions_custom = []
                if morphs_settings.type == "DIFFEO_GENESIS_9":
                    emotions_custom = []
                    for string in [x for x in morphs_settings.diffeomorphic_emotions_custom.split(',') if x != '']:
                        for x in [x for x in rig_settings.model_armature_object.keys() if not "Adjust Custom" in x]:
                            if string in x:
                                emotions_custom.append(x)

                for emotion in facs_emotions:
                    name = emotion[len('facs_ctrl_')] + ''.join(
                        [c if not c.isupper() else ' ' + c for c in emotion[len('facs_ctrl_') + 1:]])
                    mustardui_add_morph(morphs_settings.sections[3].morphs, [name, emotion])

                for emotion in emotions_custom:
                    mustardui_add_morph(morphs_settings.sections[3].morphs, [emotion, emotion])

            # Body Morphs for Genesis 8
            mustardui_add_section(morphs_settings.sections, ["Body"], is_internal=True, diffeomorphic=4)
            if morphs_settings.diffeomorphic_body_morphs:

                body_morphs_FBM = [x for x in rig_settings.model_armature_object.keys() if
                                   'FBM' in x and sum(1 for c in x if c.isdigit()) < 1 and sum(
                                       1 for c in x if c.isupper()) < 6]
                body_morphs_bs = [x for x in rig_settings.model_armature_object.keys() if
                                  'body_bs_' in x and sum(1 for c in x if c.isdigit()) < 1 and sum(
                                      1 for c in x if c.isupper()) < 6]
                body_morphs_CTRLB = [x for x in rig_settings.model_armature_object.keys() if
                                     'CTRLBreasts' in x and 'pCTRLBreasts' not in x and sum(
                                         1 for c in x if c.isupper()) < 10]
                body_morphs_ctrl = [x for x in rig_settings.model_armature_object.keys() if
                                    'body_ctrl_' in x and sum(1 for c in x if c.isdigit()) < 1 and sum(
                                        1 for c in x if c.isupper()) < 6]
                body_morphs_PBM = [x for x in rig_settings.model_armature_object.keys() if
                                   'PBMBreasts' in x and sum(1 for c in x if c.isupper()) < 10]

                # Custom Diffeomorphic emotions
                body_morphs_custom = []
                for string in [x for x in morphs_settings.diffeomorphic_body_morphs_custom.split(',') if x != '']:
                    for x in [x for x in rig_settings.model_armature_object.keys() if not "Adjust Custom" in x]:
                        if string in x:  # and sum(1 for c in x if c.isupper()) < 6:
                            body_morphs_custom.append(x)

                for morph in body_morphs_FBM:
                    name = morph[len('FBM')] + ''.join([c if not c.isupper() else ' ' + c for c in morph[len('FBM') + 1:]])
                    mustardui_add_morph(morphs_settings.sections[4].morphs, [name, morph])
                for morph in body_morphs_bs:
                    name = morph[len('body_bs_')] + ''.join([c if not c.isupper() else ' ' + c for c in morph[len('body_bs_') + 1:]])
                    mustardui_add_morph(morphs_settings.sections[4].morphs, [name, morph])
                for morph in body_morphs_CTRLB:
                    name = morph[len('CTRL')] + ''.join(
                        [c if not c.isupper() else ' ' + c for c in morph[len('CTRL') + 1:]])
                    mustardui_add_morph(morphs_settings.sections[4].morphs, [name, morph])
                for morph in body_morphs_ctrl:
                    name = morph[len('body_ctrl_')] + ''.join([c if not c.isupper() else ' ' + c for c in morph[len('body_ctrl_') + 1:]])
                    mustardui_add_morph(morphs_settings.sections[4].morphs, [name, morph])
                for morph in body_morphs_PBM:
                    name = morph[len('PBM')] + ''.join([c if not c.isupper() else ' ' + c for c in morph[len('PBM') + 1:]])
                    mustardui_add_morph(morphs_settings.sections[4].morphs, [name, morph])
                for morph in body_morphs_custom:
                    mustardui_add_morph(morphs_settings.sections[4].morphs, [morph, morph])

                morphs_settings.diffeomorphic_genesis_version = 8 if morphs_settings.type == "DIFFEO_GENESIS_8" else 9

        for i, section in enumerate(morphs_settings.sections):

            shape_keys = section.shape_keys
            custom_properties = section.custom_properties
            custom_properties_source = section.custom_properties_source
            string = section.string

            strings = string.split(",")

            if custom_properties:
                cp_source = get_cp_source(custom_properties_source, rig_settings)
                if cp_source is None:
                    continue
                custom_props = [x for x in cp_source.keys() if any(s in x for s in strings)]
                for morph in custom_props:
                    mustardui_add_morph(morphs_settings.sections[i].morphs, [rename_morph(self, morph), morph], custom_property=True, custom_property_source=custom_properties_source)

            if shape_keys:
                sks = [x.name for x in rig_settings.model_body.data.shape_keys.key_blocks if
                       any(s in x.name for s in strings)]
                for morph in sks:
                    mustardui_add_morph(morphs_settings.sections[i].morphs, [rename_morph(self, morph), morph], custom_property=False)

        morphs_settings.diffeomorphic_genesis_version = -1 if morphs_settings.type == "GENERIC" else morphs_settings.diffeomorphic_genesis_version

        if addon_prefs.debug:
            print("\nMustardUI - Morphs found\n")

        # Print the options
        for section in morphs_settings.sections:
            for morph in section.morphs:
                if addon_prefs.debug:
                    print(f"  {repr(morph.name)} in section: {repr(section.name)}")
                properties_number = properties_number + 1

        morphs_settings.morphs_number = properties_number

        if properties_number:
            self.report({'INFO'}, 'MustardUI - Morphs check completed.')
        else:
            self.report({'WARNING'}, 'MustardUI - No Morph found.')

        return {'FINISHED'}

    def invoke(self, context, event):
        res, arm = mustardui_active_object(context, config=1)
        morphs_settings = arm.MustardUI_MorphsSettings

        if morphs_settings.diffeomorphic_genesis_version == 8:
            morphs_settings.type = "DIFFEO_GENESIS_8"
        elif morphs_settings.diffeomorphic_genesis_version == 9:
            morphs_settings.type = "DIFFEO_GENESIS_9"

        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):

        res, arm = mustardui_active_object(context, config=1)
        morphs_settings = arm.MustardUI_MorphsSettings

        layout = self.layout

        col = layout.column()
        col.prop(self, "custom_rename")
        col.prop(self, "clear_existing_morphs")

        if morphs_settings.type in ["DIFFEO_GENESIS_8", "DIFFEO_GENESIS_9"]:
            layout.separator()

            col = layout.column()
            if morphs_settings.type == "DIFFEO_GENESIS_8":
                col.prop(morphs_settings, "diffeomorphic_emotions_units")
                col.prop(morphs_settings, "diffeomorphic_emotions")
                if morphs_settings.diffeomorphic_emotions:
                    row = col.row(align=True)
                    row.label(text="Custom morphs")
                    row.scale_x = row_scale
                    row.prop(morphs_settings, "diffeomorphic_emotions_custom", text="")

            if morphs_settings.type == "DIFFEO_GENESIS_8":
                col.prop(morphs_settings, "diffeomorphic_facs_emotions_units")
                col.prop(morphs_settings, "diffeomorphic_facs_emotions")
            else:
                col.prop(morphs_settings, "diffeomorphic_facs_emotions_units", text="Emotions Units Morphs")
                col.prop(morphs_settings, "diffeomorphic_facs_emotions", text="Emotions Morphs")
                if morphs_settings.diffeomorphic_facs_emotions:
                    row = col.row(align=True)
                    row.label(text="Custom morphs")
                    row.scale_x = row_scale
                    row.prop(morphs_settings, "diffeomorphic_emotions_custom", text="")

            col.prop(morphs_settings, "diffeomorphic_body_morphs")
            if morphs_settings.diffeomorphic_body_morphs:
                row = col.row(align=True)
                row.label(text="Custom morphs")
                row.scale_x = row_scale
                row.prop(morphs_settings, "diffeomorphic_body_morphs_custom", text="")


def register():
    bpy.utils.register_class(MustardUI_Morphs_Check)
    bpy.utils.register_class(MustardUI_Morphs_Clear)


def unregister():
    bpy.utils.unregister_class(MustardUI_Morphs_Clear)
    bpy.utils.unregister_class(MustardUI_Morphs_Check)
