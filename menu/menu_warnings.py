import bpy

from . import MainPanel
from ..model_selection.active_object import *
from ..misc.prop_utils import *
from ..warnings.ops_fix_old_UI import check_old_UI
from ..warnings.ops_fix_eevee_normals import check_eevee_normals


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

            return poll and check_eevee_normals(context.scene, settings)

        return poll

    def draw_header(self, context):
        self.layout.label(text="", icon="ERROR")

    def draw(self, context):

        settings = bpy.context.scene.MustardUI_Settings

        layout = self.layout

        # Old UI scripts
        if check_old_UI():
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Old UI script found!", icon="ERROR")
            col.label(text="Save and restart after using this!", icon="BLANK1")
            box.operator("mustardui.warnings_fix_old_ui")
            # Fix for: https://github.com/Mustard2/MustardUI/issues/150
            return

        # Eevee normals enabled in Cycles
        if check_eevee_normals(context.scene, settings):
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Eevee Optimed Normals are active with Cycles!", icon="ERROR")
            box.operator("mustardui.warnings_fix_eevee_normals")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_Warnings)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Warnings)
