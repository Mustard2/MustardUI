import bpy
from bpy.props import *
from ..model_selection.active_object import *


class MustardUI_Configuration_SmartCheck(bpy.types.Operator):
    """Search for MustardUI configuration options based on the name of the model and its body"""
    bl_idname = "mustardui.configuration_smartcheck"
    bl_label = "Smart Search."
    bl_options = {'UNDO'}

    smartcheck_custom_properties: bpy.props.BoolProperty(name="Body Custom Properties",
                                                         default=True,
                                                         description="Search for Body Custom Properties that respects "
                                                                     "MustardUI Naming Convention.\nThis will "
                                                                     "overwrite previous manual modifications of "
                                                                     "custom properties found with this tool")
    smartcheck_outfits: bpy.props.BoolProperty(name="Outfits", default=True)

    @classmethod
    def poll(cls, context):

        res, arm = mustardui_active_object(context, config=1)

        if arm is not None:
            rig_settings = arm.MustardUI_RigSettings
            return (rig_settings.model_MustardUI_naming_convention and rig_settings.model_body is not None
                    and rig_settings.model_name != "")
        else:
            return False

    def execute(self, context):

        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings
        #armature_settings = obj.MustardUI_ArmatureSettings
        tools_settings = obj.MustardUI_ToolsSettings
        addon_prefs = context.preferences.addons["MustardUI"].preferences

        # Try to assign the rig object
        if not obj.MustardUI_created:
            if context.active_object is not None and context.active_object.type == "ARMATURE":
                rig_settings.model_armature_object = context.active_object

        # Initialize Smart Check header
        if addon_prefs.debug:
            print('\nMustardUI - Smart Check - Start\n')

        if self.smartcheck_custom_properties:
            if addon_prefs.debug:
                print('MustardUI - Smart Check - Searching for body additional options\n')
            # Check for body additional properties
            bpy.ops.mustardui.property_smartcheck()

        # Search for oufit collections
        if self.smartcheck_outfits:
            if addon_prefs.debug:
                print('\nMustardUI - Smart Check - Searching for outfits\n')
            bpy.ops.mustardui.outfits_smartcheck()

        # Search for hair
        if addon_prefs.debug:
            print('\nMustardUI - Smart Check - Searching for hair.')
        hair_collections = [x for x in bpy.data.collections if
                            (rig_settings.model_name in x.name) and ('Hair' in x.name)]
        if rig_settings.hair_collection is None:
            if len(hair_collections) == 1:
                rig_settings.hair_collection = hair_collections[0]
                print('\nMustardUI - Smart Check - ' + hair_collections[0].name + ' set as Hair collection')
            elif len(hair_collections) == 0:
                print(
                    '\nMustardUI - Smart Check - Can not find any Hair collection compatible with MustardUI naming '
                    'convention.')
            else:
                print(
                    '\nMustardUI - Smart Check - More than 1 collection has been found. No collection has been set as '
                    'the Hair one to avoid un-wanted behaviour.')
        else:
            print('\nMustardUI - Smart Check - Hair collection already defined. Skipping this part.')

        # Search for extras
        if addon_prefs.debug:
            print('\nMustardUI - Smart Check - Searching for extras.')

        if rig_settings.extras_collection is None:
            extras_collections = [x for x in bpy.data.collections if
                                  (rig_settings.model_name in x.name) and ('Extras' in x.name)]
            if len(extras_collections) == 1:
                rig_settings.extras_collection = extras_collections[0]
                print('\nMustardUI - Smart Check - ' + extras_collections[0].name + ' set as Extras collection')
            elif len(extras_collections) == 0:
                print(
                    '\nMustardUI - Smart Check - Can not find any Extras collection compatible with MustardUI naming '
                    'convention.')
            else:
                print(
                    '\nMustardUI - Smart Check - More than 1 collection has been found. No collection has been set as '
                    'the Extras one to avoid un-wanted behaviour.')
        else:
            print('\nMustardUI - Smart Check - Extras collection already defined. Skipping this part.')

        # Standard armature setup
        # preset_Mustard_models = []
        #
        # if hasattr(obj, '[\"arp_updated\"]'):
        #     if settings.debug:
        #         print('\nMustardUI - Smart Check - Found an ARP rig, version: \'' + obj["arp_updated"] + '\' .')
        #     print('\nMustardUI - Smart Check - Setting layers as for Mustard models.')
        #
        #     preset_Mustard_models = [(0, "Main", False),
        #                              (1, "Advanced", False),
        #                              (7, "Extra", False),
        #                              (10, "Child Of - Ready", False),
        #                              (31, "Rigging - Ready", True)]
        #
        # elif hasattr(obj, '[\"rig_id\"]'):
        #     if settings.debug:
        #         print('\nMustardUI - Smart Check - Found a Rigify rig.')
        #     print('\nMustardUI - Smart Check - Setting layers for Rigify.')
        #
        #     preset_Mustard_models = [(1, "Face", False),
        #                              (2, "Face (details)", False),
        #                              (3, "Torso", False),
        #                              (4, "Torso (Tweak)", False),
        #                              (5, "Fingers", False),
        #                              (6, "Fingers (Tweak)", False),
        #                              (7, "Arm.L (IK)", False),
        #                              (10, "Arm.R (IK)", False),
        #                              (8, "Arm.L (FK)", False),
        #                              (11, "Arm.R (FK)", False),
        #                              (9, "Arm.L (Tweak)", False),
        #                              (12, "Arm.R (Tweak)", False),
        #                              (13, "Leg.L (IK)", False),
        #                              (16, "Leg.R (IK)", False),
        #                              (14, "Leg.L (FK)", False),
        #                              (17, "Leg.R (FK)", False),
        #                              (15, "Leg.L (Tweak)", False),
        #                              (18, "Leg.R (Tweak)", False),
        #                              (28, "Root", False)]
        #
        # elif rig_settings.model_armature_object is not None:
        #     if hasattr(rig_settings.model_armature_object, '[\"MhxRig\"]'):
        #         if settings.debug:
        #             print('\nMustardUI - Smart Check - Found a MHX rig.')
        #         print('\nMustardUI - Smart Check - Setting layers for MHX.')
        #
        #         preset_Mustard_models = [(10, "Face", False),
        #                                  (8, "Face (details)", False),
        #                                  (1, "Spine", False),
        #                                  (2, "Arm.L (IK)", False),
        #                                  (18, "Arm.R (IK)", False),
        #                                  (3, "Arm.L (FK)", False),
        #                                  (19, "Arm.R (FK)", False),
        #                                  (4, "Leg.L (IK)", False),
        #                                  (20, "Leg.R (IK)", False),
        #                                  (5, "Leg.L (FK)", False),
        #                                  (21, "Leg.R (FK)", False),
        #                                  (12, "Extra.L", False),
        #                                  (28, "Extra.R", False),
        #                                  (6, "Hand.L", False),
        #                                  (22, "Hand.R", False),
        #                                  (7, "Fingers.L", False),
        #                                  (23, "Fingers.R", False),
        #                                  (13, "Toes.L", False),
        #                                  (29, "Toes.R", False),
        #                                  (9, "Tweak", False),
        #                                  (0, "Root", False)]
        #
        # if len(preset_Mustard_models) > 0:
        #
        #     if len(armature_settings.layers) < 1:
        #         bpy.ops.mustardui.armature_initialize(clean=False)
        #
        #     for layer in preset_Mustard_models:
        #         if not armature_settings.config_layer[layer[0]]:
        #             armature_settings.config_layer[layer[0]] = True
        #             armature_settings.layers[layer[0]].name = layer[1]
        #             armature_settings.layers[layer[0]].advanced = layer[2]
        #             armature_settings.layers[layer[0]].layer_config_collapse = True
        #             if settings.debug:
        #                 print('\nMustardUI - Smart Check - Armature layer ' + str(layer[0]) + ' set.')
        #         else:
        #             if settings.debug:
        #                 print('\nMustardUI - Smart Check - Armature layer ' + str(layer[0]) + ' already defined.')

        # Lips Shrinkwrap
        if tools_settings.lips_shrinkwrap_armature_object is None:
            tools_settings.lips_shrinkwrap_armature_object = rig_settings.model_body.find_armature()

        # End of debug messages
        if addon_prefs.debug:
            print('\nMustardUI - Smart Check - End')

        self.report({'INFO'}, 'MustardUI - Smart Check complete.')

        return {'FINISHED'}

    def invoke(self, context, event):
        addon_prefs = context.preferences.addons["MustardUI"].preferences
        return context.window_manager.invoke_props_dialog(self, width=550 if addon_prefs.debug else 450)

    def draw(self, context):

        layout = self.layout

        box = layout.box()
        box.label(text="Categories to Smart Check", icon="VIEWZOOM")
        col = box.column()
        col.prop(self, 'smartcheck_custom_properties')
        col.prop(self, 'smartcheck_outfits')


def register():
    bpy.utils.register_class(MustardUI_Configuration_SmartCheck)


def unregister():
    bpy.utils.unregister_class(MustardUI_Configuration_SmartCheck)