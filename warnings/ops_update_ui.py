import bpy

from ..model_selection.active_object import mustardui_active_object


def is_ui_update(rig_settings):
    return not (
        (
            rig_settings.diffeomorphic_support
            and rig_settings.diffeomorphic_morphs_number > 0
        )
        or rig_settings.simplify_main_enable
    )


class MustardUI_UpdateUI(bpy.types.Operator):
    """Update the UI to the latest feature version"""

    bl_idname = "mustardui.update_ui"
    bl_label = "Update UI"
    bl_options = {"UNDO"}

    ignore: bpy.props.BoolProperty(default=False)

    @classmethod
    def poll(cls, context):
        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings
        return (poll and not is_ui_update(rig_settings)) if obj is not None else False

    def execute(self, context):
        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings
        morphs_settings = obj.MustardUI_MorphsSettings
        simplify_settings = obj.MustardUI_SimplifySettings

        diffeomorphic_status = (
            rig_settings.diffeomorphic_support
            and rig_settings.diffeomorphic_morphs_number > 0
        )
        simplify_status = rig_settings.simplify_main_enable

        if self.ignore:
            rig_settings.diffeomorphic_support = False
            rig_settings.simplify_main_enable = False
            return {"FINISHED"}

        # Check Morphs from previous versions
        if diffeomorphic_status:
            try:
                morphs_settings.type = "DIFFEO_GENESIS_8"
                morphs_settings.enable_ui = True

                # Retrieve settings from the old Morphs implementation
                morphs_settings.diffeomorphic_emotions = (
                    rig_settings.diffeomorphic_emotions
                )
                morphs_settings.diffeomorphic_emotions_custom = (
                    rig_settings.diffeomorphic_emotions_custom
                )
                morphs_settings.diffeomorphic_facs_emotions = (
                    rig_settings.diffeomorphic_facs_emotions
                )
                morphs_settings.diffeomorphic_emotions_units = (
                    rig_settings.diffeomorphic_emotions_units
                )
                morphs_settings.diffeomorphic_facs_emotions_units = (
                    rig_settings.diffeomorphic_facs_emotions_units
                )
                morphs_settings.diffeomorphic_body_morphs = (
                    rig_settings.diffeomorphic_body_morphs
                )
                morphs_settings.diffeomorphic_body_morphs_custom = (
                    rig_settings.diffeomorphic_body_morphs_custom
                )

                # To use the morphs_check operator we need to be in Configuration mode
                bpy.ops.mustardui.configuration()
                bpy.ops.mustardui.morphs_check()

                # Switch back to normal mode
                bpy.ops.mustardui.configuration()

                # Flag the error as solved
                rig_settings.diffeomorphic_support = False
            except Exception:
                # Disable the Morphs panel if an error occurs
                morphs_settings.enable_ui = False

                # Switch out of configuration mode if needed
                if not obj.MustardUI_enable:
                    bpy.ops.mustardui.configuration()

                self.report(
                    {"ERROR"}, "MustardUI - An error occurred while updating the model."
                )
                return {"FINISHED"}

        # Check if Simplify was enabled in previous versions
        if simplify_status:
            simplify_settings.simplify_main_enable = True
            rig_settings.simplify_main_enable = False

        self.report({"INFO"}, "MustardUI - UI updated.")
        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_UpdateUI)


def unregister():
    bpy.utils.unregister_class(MustardUI_UpdateUI)
