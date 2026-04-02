import bpy

from ..model_selection.active_object import mustardui_active_object
from ..warnings.ops_fix_eevee_normals import check_eevee_normals
from ..warnings.ops_fix_old_UI import check_old_UI
from ..warnings.ops_update_ui import is_ui_update
from . import MainPanel


def check_blender_version(rig_settings):
    current_blender_version = bpy.app.version
    return tuple(current_blender_version) < tuple(
        rig_settings.model_minimum_blender_version
    )


class PANEL_PT_MustardUI_Warnings(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Warnings"
    bl_label = "Warnings"
    bl_icon = "ERROR"

    @classmethod
    def poll(cls, context):

        settings = bpy.context.scene.MustardUI_Settings
        poll, obj = mustardui_active_object(context, config=0)

        if obj is not None:
            # If an old script is available, only this warning is shown
            # Fix for: https://github.com/Mustard2/MustardUI/issues/150
            if check_old_UI():
                return poll

            rig_settings = obj.MustardUI_RigSettings

            return poll and (
                check_eevee_normals(context.scene, settings)
                or not is_ui_update(rig_settings)
                or check_blender_version(rig_settings)
            )

        return poll

    def draw_header(self, context):
        self.layout.label(text="", icon="ERROR")

    def draw(self, context):

        settings = bpy.context.scene.MustardUI_Settings
        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings

        layout = self.layout

        # Old UI scripts
        if check_old_UI():
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Old UI script found!", icon="TEXT")
            col.label(text="Save and restart after using this!", icon="BLANK1")
            box.operator("mustardui.warnings_fix_old_ui", icon="BRUSH_DATA")
            # Fix for: https://github.com/Mustard2/MustardUI/issues/150
            return

        # Eevee normals enabled in Cycles
        if check_eevee_normals(context.scene, settings):
            box = layout.box()
            col = box.column(align=True)
            col.label(
                text="Eevee Optimised Normals are active with Cycles!",
                icon="NORMALS_FACE",
            )
            box.operator("mustardui.warnings_fix_eevee_normals", icon="NORMALS_FACE")

        # Check if the model is up-to-date
        if not is_ui_update(rig_settings):
            box = layout.box()

            row = box.row(align=True)
            row.label(text="UI is outdated.", icon="SHAPEKEY_DATA")
            row.operator("mustardui.update_ui", icon="X", text="").ignore = True

            box.operator("mustardui.update_ui", icon="TRIA_DOWN_BAR").ignore = False

        # Emit warning if the model is used on a different Blender version than
        # requested by the model creator
        if check_blender_version(rig_settings):
            box = layout.box()
            col = box.column(align=True)
            mbv = rig_settings.model_minimum_blender_version
            col.label(
                text="Minimum Blender version: "
                + str(mbv[0])
                + "."
                + str(mbv[1])
                + "."
                + str(mbv[2]),
                icon="BLENDER",
            )
            col.label(text="The model might not work properly.", icon="BLANK1")
            col.label(text="Update Blender to the latest version.", icon="BLANK1")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_Warnings)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Warnings)
