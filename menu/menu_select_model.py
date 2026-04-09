import bpy

from ..model_selection.active_object import mustardui_active_object
from ..warnings.ops_fix_old_UI import can_draw_ui
from . import MainPanel


class PANEL_PT_MustardUI_SelectModel(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_SelectModel"
    bl_label = ""

    @classmethod
    def poll(cls, context):
        if can_draw_ui():
            return False

        res, arm = mustardui_active_object(context, config=0)

        if arm is None:
            return False

        return res

    def draw_header(self, context):
        settings = bpy.context.scene.MustardUI_Settings

        poll, arm = mustardui_active_object(context, config=0)

        layout = self.layout

        row = layout.row(align=True)
        row.label(
            text="(Viewport)" if settings.viewport_model_selection else "(Direct)"
        )
        row.label(text=arm.MustardUI_RigSettings.model_name)

    def draw(self, context):
        settings = bpy.context.scene.MustardUI_Settings

        poll, arm = mustardui_active_object(context, config=0)

        layout = self.layout

        layout.operator(
            "mustardui.viewportmodelselection",
            text="Viewport Model Selection",
            icon="VIEW3D",
            depress=settings.viewport_model_selection,
        )
        layout.separator()

        for armature in [x for x in bpy.data.armatures if x.MustardUI_created]:
            row = layout.row(align=True)
            row.enabled = not settings.viewport_model_selection
            row.operator(
                "mustardui.switchmodel",
                text=armature.MustardUI_RigSettings.model_name,
                depress=armature == settings.panel_model_selection_armature
                if not settings.viewport_model_selection
                else armature == arm,
                icon="ERROR"
                if armature.MustardUI_RigSettings.model_armature_object.name
                not in bpy.context.scene.objects
                else "BLANK1",
            ).model_to_switch = armature.name
            if (
                armature.MustardUI_RigSettings.model_armature_object.name
                not in bpy.context.scene.objects
            ):
                row.operator(
                    "mustardui.remove_armature", text="", icon="X"
                ).armature = armature.name


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_SelectModel)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_SelectModel)
