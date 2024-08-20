import bpy
from bpy.props import *
from ..model_selection.active_object import *
from ..misc.prop_utils import *
from .. import __package__ as base_package


class MustardUI_Armature_SmartCheck(bpy.types.Operator):
    """Check if a known armature type (ARP, Rigify, MHX) is available, and automatically set the Armature panel"""
    bl_idname = "mustardui.armature_smartcheck"
    bl_label = "Armature Smart Check"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):

        res, arm = mustardui_active_object(context, config=1)
        return res

    def execute(self, context):

        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings
        addon_prefs = context.preferences.addons[base_package].preferences

        found_type = ""
        found_colls = 0

        # Standard armature setup
        preset_Mustard_models = []

        # TODO: Implement Rigify and ARP SmartCheck
        #
        # if hasattr(obj, '[\"arp_updated\"]'):
        #     if settings.debug:
        #         print('\nMustardUI - Smart Check - Found an ARP rig, version: \'' + obj["arp_updated"] + '\' .')
        #     print('\nMustardUI - Smart Check - Setting layers as for Mustard models.')
        #
        #     preset_Mustard_models = [("Main", False),
        #                              ("Advanced", False),
        #                              ("Extra", False),
        #                              ("Child Of - Ready", False),
        #                              ("Rigging - Ready", True)]
        #
        # elif hasattr(obj, '[\"rig_id\"]'):
        #     if settings.debug:
        #         print('\nMustardUI - Smart Check - Found a Rigify rig.')
        #     print('\nMustardUI - Smart Check - Setting layers for Rigify.')
        #
        #     preset_Mustard_models = [("Face", False),
        #                              ("Face (details)", False),
        #                              ("Torso", False),
        #                              ("Torso (Tweak)", False),
        #                              ("Fingers", False),
        #                              ("Fingers (Tweak)", False),
        #                              ("Arm.L (IK)", False),
        #                              ("Arm.R (IK)", False),
        #                              ("Arm.L (FK)", False),
        #                              ("Arm.R (FK)", False),
        #                              ("Arm.L (Tweak)", False),
        #                              ("Arm.R (Tweak)", False),
        #                              ("Leg.L (IK)", False),
        #                              ("Leg.R (IK)", False),
        #                              ("Leg.L (FK)", False),
        #                              ("Leg.R (FK)", False),
        #                              ("Leg.L (Tweak)", False),
        #                              ("Leg.R (Tweak)", False),
        #                              ("Root", False)]
        #
        # MHX Rig
        if rig_settings.model_armature_object is not None and hasattr(rig_settings.model_armature_object,
                                                                      '[\"MhxRig\"]'):
            if addon_prefs.debug:
                print('\nMustardUI - Smart Check - Found a MHX rig, setting layers for MHX.')

            preset_Mustard_models = [("Head", False, "USER"),
                                     ("Face", False, "USER"),
                                     ("Spine", False, ""),
                                     ("IK Arm Left", False, ""),
                                     ("IK Arm Right", False, ""),
                                     ("FK Arm Left", False, ""),
                                     ("FK Arm Right", False, ""),
                                     ("Hand Left", False, ""),
                                     ("Hand Right", False, ""),
                                     ("Fingers Left", False, ""),
                                     ("Fingers Right", False, ""),
                                     ("IK Leg Left", False, ""),
                                     ("IK Leg Right", False, ""),
                                     ("FK Leg Left", False, ""),
                                     ("FK Leg Right", False, ""),
                                     ("Toes Left", False, ""),
                                     ("Toes Right", False, ""),
                                     ("Tweak", False, ""),
                                     ("Root", False, "")]

            # Mirror option enabled
            obj.MustardUI_ArmatureSettings.mirror = True

            found_type = "MHX"

        # Apply preset
        if len(preset_Mustard_models) > 0:

            obj.MustardUI_ArmatureSettings.mirror = True

            # Reset current armature visibility options
            for coll in obj.collections_all:
                coll.MustardUI_ArmatureBoneCollection.is_in_UI = False

            # Apply new preset
            for preset in reversed(preset_Mustard_models):
                for coll in obj.collections_all:
                    if coll.name == preset[0]:
                        coll.MustardUI_ArmatureBoneCollection.is_in_UI = True
                        if preset[2] != "":
                            coll.MustardUI_ArmatureBoneCollection.icon = preset[2]
                        if addon_prefs.debug:
                            print('\nMustardUI - Smart Check - Armature layer ' + str(preset[0]) + ' set.')
                        obj.collections.move(coll.index, 0)
                        found_colls += 1

        if found_type != "":
            if found_colls > 0:
                self.report({'INFO'}, f'MustardUI - Smart Check found {found_colls} collections in a \'{found_type}\' armature.')
            else:
                self.report({'INFO'}, f'MustardUI - Smart Check found a \'{found_type}\' armature but no viable collection.')
        else:
            self.report({'ERROR'}, 'MustardUI - Smart Check found no compatible armature.')

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_Armature_SmartCheck)


def unregister():
    bpy.utils.unregister_class(MustardUI_Armature_SmartCheck)
