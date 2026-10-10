from datetime import date

import bpy

from ..model_selection.active_object import (
    ModelMode,
    active_object_operator_poll,
    mustardui_active_object,
)


class MustardUI_VersionDateToday(bpy.types.Operator):
    """Set the version date to today"""

    bl_idname = "mustardui.version_date_today"
    bl_label = "Today"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        return active_object_operator_poll(context, config=ModelMode.CONFIG)

    def execute(self, context):
        res, arm = mustardui_active_object(context, config=ModelMode.CONFIG)
        rig_settings = arm.MustardUI_RigSettings

        today = date.today()
        if rig_settings.model_version_date_format in ["MDY", "MDY2"]:
            rig_settings.model_version_date_vector = (today.month, today.day, today.year)
        else:
            rig_settings.model_version_date_vector = (today.day, today.month, today.year)

        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_VersionDateToday)


def unregister():
    bpy.utils.unregister_class(MustardUI_VersionDateToday)
