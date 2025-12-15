import bpy
from bpy.props import *
from ..model_selection.active_object import *
from ..physics.update_enable import enable_physics_update
from .. import __package__ as base_package
from datetime import datetime


class MustardUI_Configuration(bpy.types.Operator):
    """Configure MustardUI"""
    bl_idname = "mustardui.configuration"
    bl_label = "Configure MustardUI"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):

        settings = bpy.context.scene.MustardUI_Settings

        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings
        physics_settings = obj.MustardUI_PhysicsSettings
        tools_settings = obj.MustardUI_ToolsSettings
        addon_prefs = context.preferences.addons[base_package].preferences

        warnings = 0

        if not obj.MustardUI_enable:

            if addon_prefs.debug:
                print("\n\nMustardUI - Configuration Logs")

            # Various checks
            if rig_settings.model_body is None:
                self.report({'ERROR'}, 'MustardUI - A body mesh should be selected.')
                return {'FINISHED'}

            if rig_settings.model_name == "":
                self.report({'ERROR'}, 'MustardUI - A name should be selected.')
                return {'FINISHED'}

            # Allocate the armature object
            if not obj.MustardUI_created:
                if context.active_object is not None and context.active_object.type == "ARMATURE":
                    rig_settings.model_armature_object = context.active_object
                else:
                    self.report({'ERROR'},
                                'MustardUI - Be sure to select the armature Object in the viewport before continuing.')
                    return {'FINISHED'}

            # Check Body mesh scale
            if rig_settings.model_body.scale[0] != 1. or rig_settings.model_body.scale[1] != 1. or \
                    rig_settings.model_body.scale[2] != 1.:
                warnings = warnings + 1
                if addon_prefs.debug:
                    print(
                        'MustardUI - Configuration Warning - The selected body mesh seems not to have the scale '
                        'applied.\n This might generate issues with the tools.')

            # Check and eventually clean deleted outfit collections
            index_to_delete = []
            for x in range(len(rig_settings.outfits_collections)):
                if not hasattr(rig_settings.outfits_collections[x].collection, 'name'):
                    index_to_delete.append(x)
                    if addon_prefs.debug:
                        print('MustardUI - A ghost outfit collection has been removed.')
            for x in index_to_delete:
                rig_settings.outfits_collections.remove(x)

            if tools_settings.autoeyelid_enable:
                if ((tools_settings.autoeyelid_eyeL_shapekey == "" and tools_settings.autoeyelid_eyeR_shapekey == "")
                        and tools_settings.autoeyelid_driver_type == "SHAPE_KEY"):
                    self.report({'ERROR'},
                                'MustardUI - At least one shape key should be selected if Auto Blink tool is enabled.')
                    return {'FINISHED'}

                elif tools_settings.autoeyelid_morph == "" and tools_settings.autoeyelid_driver_type == "MORPH":
                    self.report({'ERROR'},
                                'MustardUI - At least one custom property should be selected if Auto Blink tool is '
                                'enabled.')
                    return {'FINISHED'}

                elif tools_settings.autoeyelid_morph != "" and tools_settings.autoeyelid_driver_type == "MORPH":
                    try:
                        rig_settings.model_armature_object[tools_settings.autoeyelid_morph] = float(
                            rig_settings.model_armature_object[tools_settings.autoeyelid_morph])
                    except:
                        self.report({'ERROR'},
                                    'MustardUI - The custom property selected for Auto Blink can not be found.')
                        return {'FINISHED'}

            # Check the type of the rig
            rig_recognized = 0
            if hasattr(obj, '[\"arp_updated\"]'):
                rig_settings.model_rig_type = "arp"
                rig_recognized += 1
            elif hasattr(obj, '[\"rig_id\"]'):
                rig_settings.model_rig_type = "rigify"
                rig_recognized += 1
            elif hasattr(rig_settings.model_armature_object, '[\"MhxRig\"]'):
                rig_settings.model_rig_type = "mhx"
                rig_recognized += 1
            else:
                rig_settings.model_rig_type = "other"

            if rig_recognized < 2:
                print('MustardUI - The rig has been recognized as ' + rig_settings.model_rig_type)
            else:
                warnings = warnings + 1
                if addon_prefs.debug:
                    print(
                        'MustardUI - Configuration Warning - The rig has multiple rig types. This might create '
                        'problems in the UI')

            # Check for errors in the list selection
            if len(rig_settings.outfits_list_make(context)) > 0 and rig_settings.outfits_list == "":
                try:
                    rig_settings.hair_list = rig_settings.outfits_list_make(context)[0][0]
                    warnings = warnings + 1
                    print('MustardUI - Configuration Warning - Fixed outfit_list index')
                except:
                    warnings = warnings + 1
                    if addon_prefs.debug:
                        print(
                            'MustardUI - Configuration Warning - The outfits_list property index seems to be '
                            'corrupted. Try to remove the UI and re-add it')

            if rig_settings.hair_collection is not None and rig_settings.hair_list == "":
                if len([x for x in rig_settings.hair_collection.objects if x.type == "MESH"]) > 0:
                    try:
                        rig_settings.hair_list = rig_settings.hair_list_make(context)[0][0]
                        print('MustardUI - Configuration Warning - Fixed hair_list index')
                    except:
                        warnings = warnings + 1
                        if addon_prefs.debug:
                            print(
                                'MustardUI - Configuration Warning - The hair_list property index seems to be '
                                'corrupted. Try to remove the UI and re-add it')

            # Setting the model version date if requested
            if rig_settings.model_version_date_enable:
                date = datetime.today().strftime('%d/%m/%Y')
                rig_settings.model_version_date = date
            else:
                rig_settings.model_version_date = ""

            # Clean the model temporary settings
            settings.rename_outfits_temp_class.clear()

            if warnings > 0:
                if addon_prefs.debug:
                    print("\n\n")
                self.report({'WARNING'},
                            'MustardUI - Some warning were generated during the configuration. Enable Debug mode and '
                            'check the console for more informations')
            else:
                if addon_prefs.debug:
                    print("MustardUI - Configuration Warning - No warning or errors during the configuration\n\n")
                self.report({'INFO'}, 'MustardUI - Configuration complete.')

        obj.MustardUI_enable = not obj.MustardUI_enable

        if ((settings.viewport_model_selection_after_configuration and not settings.viewport_model_selection) or (
                not settings.viewport_model_selection_after_configuration and settings.viewport_model_selection)) and not obj.MustardUI_created:
            bpy.ops.mustardui.viewportmodelselection()

        obj.MustardUI_created = True

        # Fix for #148 - https://github.com/Mustard2/MustardUI/issues/148
        for sec in rig_settings.body_custom_properties_sections:
            sec.old_name = sec.name

        # Force Physics update
        enable_physics_update(physics_settings, context)

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_Configuration)


def unregister():
    bpy.utils.unregister_class(MustardUI_Configuration)
