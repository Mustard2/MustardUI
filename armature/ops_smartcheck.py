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

        if rig_settings.model_armature_object is None:
            self.report({'WARNING'},
                        'MustardUI - An error occurred while using Armature Smart Check. '
                        'End Configuration, re-enter Configuration mode and re-try')

        found_type = ""
        found_colls = 0

        # Standard armature setup
        # Format: Collection name, name to change, icon, default
        preset_mustard_models = []

        # TODO: Implement ARP SmartCheck
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
        if hasattr(obj, '[\"rig_id\"]'):
            if addon_prefs.debug:
                print('\nMustardUI - Smart Check - Found a Rigify rig, setting layers for Rigify.')

            # Collection name, name to change, icon, default
            preset_mustard_models = [("Face", "", "USER", True),
                                     ("Face (Primary)", "", "USER", False),
                                     ("Torso", "", "", True),
                                     ("Torso (Tweak)", "", "", False),
                                     ("Fingers", "", "", True),
                                     ("Fingers (Detail)", "", "", False),
                                     ("Arm.L (IK)", "IK Arm Left", "", True),
                                     ("Arm.R (IK)", "IK Arm Right", "", True),
                                     ("Arm.L (FK)", "FK Arm Left", "", False),
                                     ("Arm.R (FK)", "FK Arm Right", "", False),
                                     ("Arm.L (Tweak)", "Tweak Arm Left", "", False),
                                     ("Arm.R (Tweak)", "Tweak Arm Right", "", False),
                                     ("Leg.L (IK)", "IK Leg Left", "", True),
                                     ("Leg.R (IK)", "IK Leg Right", "", True),
                                     ("Leg.L (FK)", "FK Leg Left", "", False),
                                     ("Leg.R (FK)", "FK Leg Right", "", False),
                                     ("Leg.L (Tweak)", "Tweak Leg Left", "", False),
                                     ("Leg.R (Tweak)", "Tweak Leg Right", "", False),
                                     ("Root", "", "", True)]

            # Mirror option enabled
            obj.MustardUI_ArmatureSettings.mirror = True

            found_type = "Rigify"

        # MHX Rig
        elif hasattr(rig_settings.model_armature_object, '[\"MhxRig\"]'):
            if addon_prefs.debug:
                print('\nMustardUI - Smart Check - Found a MHX rig, setting layers for MHX.')

            # Collection name, name to change, icon, default
            preset_mustard_models = [("Head", "", "USER", True),
                                     ("Face", "", "USER", False),
                                     ("Spine 2", "Spine", "", True),
                                     ("Spine", "Spine Advanced", "", True),
                                     ("IK Arm Left", "", "", True),
                                     ("IK Arm Right", "", "", True),
                                     ("FK Arm Left", "", "", False),
                                     ("FK Arm Right", "", "", False),
                                     ("Hand Left", "", "", False),
                                     ("Hand Right", "", "", False),
                                     ("Fingers Left", "", "", False),
                                     ("Fingers Right", "", "", False),
                                     ("IK Leg Left", "", "", True),
                                     ("IK Leg Right", "", "", True),
                                     ("FK Leg Left", "", "", False),
                                     ("FK Leg Right", "", "", False),
                                     ("Toes Left", "", "", False),
                                     ("Toes Right", "", "", False),
                                     ("Tweak", "", "", False),
                                     ("Root", "", "", True)]

            # Mirror option enabled
            obj.MustardUI_ArmatureSettings.mirror = True

            found_type = "MHX"

        # Apply preset
        if len(preset_mustard_models) > 0:

            obj.MustardUI_ArmatureSettings.mirror = True

            # Reset current armature visibility options
            for coll in obj.collections_all:
                coll.MustardUI_ArmatureBoneCollection.is_in_UI = False

            # Apply new preset
            for preset in reversed(preset_mustard_models):
                for coll in obj.collections_all:
                    if coll.name == preset[0] or coll.name == preset[1]:
                        if preset[1] != "":
                            coll.name = preset[1]
                        coll.MustardUI_ArmatureBoneCollection.is_in_UI = True
                        coll.MustardUI_ArmatureBoneCollection.default = preset[3]
                        if preset[2] != "":
                            coll.MustardUI_ArmatureBoneCollection.icon = preset[2]
                        if addon_prefs.debug:
                            print('\nMustardUI - Smart Check - Armature layer ' + str(preset[0]) + ' set.')
                        obj.collections.move(coll.index, 0)
                        found_colls += 1

        # Check for Outfit/Hair/Extras switcher
        outfits = 0
        outfit_colls = [x.collection for x in rig_settings.outfits_collections if x.collection]
        if rig_settings.extras_collection is not None:
            outfit_colls.append(rig_settings.extras_collection)
        if rig_settings.hair_collection is not None:
            outfit_colls.append(rig_settings.hair_collection)
        for coll in outfit_colls:
            for o in coll.objects:
                for bcoll in obj.collections_all:
                    if bcoll.name == o.name:
                        bcoll.MustardUI_ArmatureBoneCollection.is_in_UI = True
                        bcoll.MustardUI_ArmatureBoneCollection.outfit_switcher_enable = True
                        bcoll.MustardUI_ArmatureBoneCollection.outfit_switcher_collection = coll
                        bcoll.MustardUI_ArmatureBoneCollection.outfit_switcher_object = o
                        if addon_prefs.debug:
                            print(
                                '\nMustardUI - Smart Check - Armature layer ' + bcoll.name + ' added as Outfit Switcher.')
                        outfits += 1

        if found_type != "" and not outfits:
            if found_colls > 0:
                self.report({'INFO'},
                            f'MustardUI - Smart Check found {found_colls} collections in a \'{found_type}\' armature.')
            else:
                self.report({'WARNING'},
                            f'MustardUI - Smart Check found a \'{found_type}\' armature but no viable collection.')
        elif outfits:
            self.report({'INFO'}, 'MustardUI - Outfits Switcher bone collections were added.')
        else:
            self.report({'WARNING'},
                        'MustardUI - Smart Check found no compatible armature. No collection has been added.')

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_Armature_SmartCheck)


def unregister():
    bpy.utils.unregister_class(MustardUI_Armature_SmartCheck)
