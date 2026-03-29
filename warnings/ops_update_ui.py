import bpy
from bpy.props import *
from ..model_selection.active_object import *
from .. import bl_info


def is_ui_update(rig_settings):
    return not (
            (rig_settings.diffeomorphic_support and rig_settings.diffeomorphic_morphs_number > 0)
            or rig_settings.simplify_main_enable
            # Check if the Hair curves were enabled (behaviour was different)
            or (rig_settings.hair_collection is not None and
                any(x.type == "CURVES" for x in rig_settings.hair_collection.objects) and
                rig_settings.curves_hair_enable)
            # Check for Hair convention
            or (rig_settings.hair_collection is not None and
                rig_settings.model_MustardUI_naming_convention and
                tuple(rig_settings.model_mustardui_version) < (2026, 4, 0))
    )


class MustardUI_UpdateUI(bpy.types.Operator):
    """Update the UI to the latest feature version"""
    bl_idname = "mustardui.update_ui"
    bl_label = "Update UI"
    bl_options = {'UNDO'}

    ignore: bpy.props.BoolProperty(default=False)
    force: bpy.props.BoolProperty(default=False)

    @classmethod
    def poll(cls, context):
        poll, obj = mustardui_active_object(context, config=-1)
        return poll if obj is not None else False

    def execute(self, context):
        poll, obj = mustardui_active_object(context, config=-1)
        rig_settings = obj.MustardUI_RigSettings
        morphs_settings = obj.MustardUI_MorphsSettings
        simplify_settings = obj.MustardUI_SimplifySettings

        if self.force:
            # Check if hair convention is satisfied, if not retrigger update
            if rig_settings.hair_collection is not None:
                hair_collection = rig_settings.hair_collection
                for obj in [x for x in hair_collection.objects if x is not None]:
                    if not obj.name.startswith(f"{hair_collection.name} - "):
                        rig_settings.model_mustardui_version = (0, 0, 0)
                        break

        if is_ui_update(rig_settings):
            self.report({'INFO'}, 'MustardUI - The UI is already up-to-date.')
            return {'CANCELLED'}

        diffeomorphic_status = rig_settings.diffeomorphic_support and rig_settings.diffeomorphic_morphs_number > 0
        simplify_status = rig_settings.simplify_main_enable
        curves_hair_status = (rig_settings.hair_collection is not None and
                              any(x.type == "CURVES" for x in rig_settings.hair_collection.objects) and
                              rig_settings.curves_hair_enable)
        hair_convention_status = (rig_settings.hair_collection is not None and
                                  rig_settings.model_MustardUI_naming_convention and
                                  tuple(rig_settings.model_mustardui_version) < (2026, 4, 0))

        errors = 0

        if self.ignore:
            rig_settings.diffeomorphic_support = False
            rig_settings.simplify_main_enable = False
            rig_settings.curves_hair_enable = False
            rig_settings.model_mustardui_version = bl_info["version"]
            return {'FINISHED'}

        # Check Morphs from previous versions
        if diffeomorphic_status:
            try:
                morphs_settings.type = "DIFFEO_GENESIS_8"
                morphs_settings.enable_ui = True

                # Retrieve settings from the old Morphs implementation
                morphs_settings.diffeomorphic_emotions = rig_settings.diffeomorphic_emotions
                morphs_settings.diffeomorphic_emotions_custom = rig_settings.diffeomorphic_emotions_custom
                morphs_settings.diffeomorphic_facs_emotions = rig_settings.diffeomorphic_facs_emotions
                morphs_settings.diffeomorphic_emotions_units = rig_settings.diffeomorphic_emotions_units
                morphs_settings.diffeomorphic_facs_emotions_units = rig_settings.diffeomorphic_facs_emotions_units
                morphs_settings.diffeomorphic_body_morphs = rig_settings.diffeomorphic_body_morphs
                morphs_settings.diffeomorphic_body_morphs_custom = rig_settings.diffeomorphic_body_morphs_custom

                # To use the morphs_check operator we need to be in Configuration mode
                bpy.ops.mustardui.configuration()
                bpy.ops.mustardui.morphs_check()

                # Switch back to normal mode
                bpy.ops.mustardui.configuration()

                # Flag the error as solved
                rig_settings.diffeomorphic_support = False
            except:
                # Disable the Morphs panel if an error occurs
                morphs_settings.enable_ui = False

                # Switch out of configuration mode if needed
                if not obj.MustardUI_enable:
                    bpy.ops.mustardui.configuration()

                errors += 1

        # Check if Simplify was enabled in previous versions
        if simplify_status:
            simplify_settings.simplify_main_enable = True
            rig_settings.simplify_main_enable = False

        # Check if the Hair curves were used
        if curves_hair_status and rig_settings.hair_collection is not None:
            try:
                hair_collection = rig_settings.hair_collection

                # Create a new Extras collection if necessary
                extras_collection = rig_settings.hair_extras_collection
                if extras_collection is None:
                    hair_collection = rig_settings.hair_collection
                    extras_collection = bpy.data.collections.new(f"{hair_collection.name} Extras")
                    hair_collection.children.link(extras_collection)
                rig_settings.hair_extras_collection = extras_collection

                # Move the curves Objects inside the Extras collection
                for obj in list(hair_collection.objects):
                    if obj.type == 'CURVES':
                        hair_collection.objects.unlink(obj)
                        extras_collection.objects.link(obj)
                rig_settings.curves_hair_enable = False
            except:
                errors += 1

        # Check Hair naming convention
        if hair_convention_status and rig_settings.hair_collection is not None:
            try:
                hair_collection = rig_settings.hair_collection

                # Rename the Objects in the Hair collection
                for obj in [x for x in hair_collection.objects if x is not None]:
                    if not obj.name.startswith(f"{hair_collection.name} - "):
                        # Remove any old convention
                        obj.name = obj.name.replace(f"{rig_settings.model_name} Hair ", "")
                        obj.name = obj.name.replace(f"{rig_settings.model_name} ", "")

                        # Replace the name with the new convention
                        obj.name = f"{hair_collection.name} - " + obj.name

                # Fix the list index
                rig_settings.hair_list = rig_settings.hair_list_make(context)[0][0]

                rig_settings.model_mustardui_version = bl_info["version"]
            except:
                errors += 1

        if errors:
            self.report({'ERROR'}, 'MustardUI - An error occurred while updating the model.')
            return {'FINISHED'}

        self.report({'INFO'}, 'MustardUI - UI updated.')
        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_UpdateUI)


def unregister():
    bpy.utils.unregister_class(MustardUI_UpdateUI)
