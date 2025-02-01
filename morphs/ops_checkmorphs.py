import bpy
from ..model_selection.active_object import *
from .misc import *
import itertools
from .. import __package__ as base_package


class MustardUI_DazMorphs_CheckMorphs(bpy.types.Operator):
    """Search for morphs to display in the UI External Morphs panel"""
    bl_idname = "mustardui.morphs_check"
    bl_label = "Check Morphs"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):

        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings
        return res and rig_settings.diffeomorphic_support

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings
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

        # Clean the morphs
        rig_settings.diffeomorphic_morphs_list.clear()

        # TYPE: 0: Emotion Units, 1: Emotions, 2: FACS Emotion Units, 3: FACS Emotions, 4: Body Morphs

        # Default lists
        facs_emotions_default_list = ['facs_ctrl_Afraid', 'facs_ctrl_Angry', 'facs_ctrl_Flirting', 'facs_ctrl_Frown',
                                      'facs_ctrl_Shock', 'facs_ctrl_SmileFullFace', 'facs_ctrl_SmileOpenFullFace',
                                      'facs_ctrl_Surprised']

        # Emotions Units
        if rig_settings.diffeomorphic_emotions_units:
            emotions_units = [x for x in rig_settings.model_armature_object.keys() if (
                    'eCTRL' in x or 'ECTRL' in x) and not "HD" in x and not "eCTRLSmile" in x and not 'eCTRLv' in x and sum(
                1 for c in x if c.isupper()) >= 6]

            for emotion in emotions_units:
                name = emotion[len('eCTRL')] + ''.join(
                    [c if not c.isupper() else ' ' + c for c in emotion[len('eCTRL') + 1:]])
                mustardui_add_dazmorph(rig_settings.diffeomorphic_morphs_list, [name, emotion, 0])

        # Emotions
        if rig_settings.diffeomorphic_emotions:

            emotions = [x for x in rig_settings.model_armature_object.keys() if
                        'eCTRL' in x and not "HD" in x and not 'eCTRLv' in x and (
                                sum(1 for c in x if c.isupper()) < 6 or "eCTRLSmile" in x)]

            # Custom Diffeomorphic emotions
            emotions_custom = []
            for string in [x for x in rig_settings.diffeomorphic_emotions_custom.split(',') if x != '']:
                for x in [x for x in rig_settings.model_armature_object.keys() if not "Adjust Custom" in x]:
                    if string in x:
                        emotions_custom.append(x)

            for emotion in emotions:
                name = emotion[len('eCTRL')] + ''.join(
                    [c if not c.isupper() else ' ' + c for c in emotion[len('eCTRL') + 1:]])
                mustardui_add_dazmorph(rig_settings.diffeomorphic_morphs_list, [name, emotion, 1])
            for emotion in emotions_custom:
                mustardui_add_dazmorph(rig_settings.diffeomorphic_morphs_list, [emotion, emotion, 1])

        # FACS Emotions Units
        if rig_settings.diffeomorphic_facs_emotions_units:

            facs_emotions_units = []
            facs_emotions_units.append([x for x in rig_settings.model_armature_object.keys() if
                                        'facs_ctrl_' in x and not x in facs_emotions_default_list])
            facs_emotions_units.append([x for x in rig_settings.model_armature_object.keys() if
                                        'facs_bs_' in x and sum(1 for c in x if c.isupper()) >= 2])
            facs_emotions_units.append([x for x in rig_settings.model_armature_object.keys() if
                                        'facs_jnt_' in x and sum(1 for c in x if c.isupper()) >= 2])
            facs_emotions_units = itertools.chain.from_iterable(facs_emotions_units)

            for emotion in facs_emotions_units:
                name = emotion[emotion.rfind('_', 0, 12) + 1] + ''.join(
                    [c if not c.isupper() else ' ' + c for c in emotion[emotion.rfind('_', 0, 12) + 2:]])
                name = name.removesuffix('_div2')
                mustardui_add_dazmorph(rig_settings.diffeomorphic_morphs_list, [name, emotion, 2])

        # FACS Emotions
        if rig_settings.diffeomorphic_facs_emotions:

            facs_emotions = [x for x in rig_settings.model_armature_object.keys() if x in facs_emotions_default_list]
            for emotion in facs_emotions:
                name = emotion[len('facs_ctrl_')] + ''.join(
                    [c if not c.isupper() else ' ' + c for c in emotion[len('facs_ctrl_') + 1:]])
                mustardui_add_dazmorph(rig_settings.diffeomorphic_morphs_list, [name, emotion, 3])

        # Body Morphs
        if rig_settings.diffeomorphic_body_morphs:

            body_morphs_FBM = [x for x in rig_settings.model_armature_object.keys() if
                               'FBM' in x and sum(1 for c in x if c.isdigit()) < 1 and sum(
                                   1 for c in x if c.isupper()) < 6]
            body_morphs_CTRLB = [x for x in rig_settings.model_armature_object.keys() if
                                 'CTRLBreasts' in x and not 'pCTRLBreasts' in x and sum(
                                     1 for c in x if c.isupper()) < 10]
            body_morphs_PBM = [x for x in rig_settings.model_armature_object.keys() if
                               'PBMBreasts' in x and sum(1 for c in x if c.isupper()) < 10]

            # Custom Diffeomorphic emotions
            body_morphs_custom = []
            for string in [x for x in rig_settings.diffeomorphic_body_morphs_custom.split(',') if x != '']:
                for x in [x for x in rig_settings.model_armature_object.keys() if not "Adjust Custom" in x]:
                    if string in x:  # and sum(1 for c in x if c.isupper()) < 6:
                        body_morphs_custom.append(x)

            for morph in body_morphs_FBM:
                name = morph[len('FBM')] + ''.join([c if not c.isupper() else ' ' + c for c in morph[len('FBM') + 1:]])
                mustardui_add_dazmorph(rig_settings.diffeomorphic_morphs_list, [name, morph, 4])
            for morph in body_morphs_CTRLB:
                name = morph[len('CTRL')] + ''.join(
                    [c if not c.isupper() else ' ' + c for c in morph[len('CTRL') + 1:]])
                mustardui_add_dazmorph(rig_settings.diffeomorphic_morphs_list, [name, morph, 4])
            for morph in body_morphs_PBM:
                name = morph[len('PBM')] + ''.join([c if not c.isupper() else ' ' + c for c in morph[len('PBM') + 1:]])
                mustardui_add_dazmorph(rig_settings.diffeomorphic_morphs_list, [name, morph, 4])
            for morph in body_morphs_custom:
                mustardui_add_dazmorph(rig_settings.diffeomorphic_morphs_list, [morph, morph, 4])

        properties_number = 0
        if addon_prefs.debug:
            print("\nMustardUI - Diffeomorphic Daz Morphs found\n")

        # Print the options
        for el in rig_settings.diffeomorphic_morphs_list:
            if addon_prefs.debug:
                print(el.name + " with path " + el.path + ", type: " + str(el.type))
            properties_number = properties_number + 1

        rig_settings.diffeomorphic_morphs_number = properties_number

        if len(rig_settings.diffeomorphic_morphs_list):
            self.report({'INFO'}, 'MustardUI - Diffeomorphic Daz Morphs check completed.')
        else:
            self.report({'WARNING'}, 'MustardUI - No Diffeomorphic Daz Morph found.')

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_DazMorphs_CheckMorphs)


def unregister():
    bpy.utils.unregister_class(MustardUI_DazMorphs_CheckMorphs)
