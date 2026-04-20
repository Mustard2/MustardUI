from collections import Counter

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

        armatures = [x for x in bpy.data.armatures if x.MustardUI_created]

        # Create a dictionary to count how many times each model_name appears
        model_name_count = Counter(
            armature.MustardUI_RigSettings.model_name for armature in armatures
        )

        model_name = arm.MustardUI_RigSettings.model_name
        armature_name = arm.name

        # Show armature name in parentheses only if the model name is duplicated
        if model_name_count[model_name] > 1:
            display_name = f"{model_name} ({armature_name})"
        else:
            display_name = model_name

        layout = self.layout

        row = layout.row(align=True)
        row.label(
            text="(Viewport)" if settings.viewport_model_selection else "(Direct)"
        )
        row.label(text=display_name)

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

        armatures = [x for x in bpy.data.armatures if x.MustardUI_created]

        # Create a dictionary to count how many times each model_name appears
        model_name_count = Counter(
            armature.MustardUI_RigSettings.model_name for armature in armatures
        )

        for armature in armatures:
            model_name = armature.MustardUI_RigSettings.model_name
            armature_name = armature.name

            # Show armature name in parentheses only if the model name is duplicated
            if model_name_count[model_name] > 1:
                display_name = f"{model_name} ({armature_name})"
            else:
                display_name = model_name

            # Show the name
            row = layout.row(align=True)
            row.operator(
                "mustardui.select_model",
                text=display_name,
                depress=armature == settings.panel_model_selection_armature
                if not settings.viewport_model_selection
                else armature == arm,
                icon="ERROR"
                if armature.MustardUI_RigSettings.model_armature_object.name
                not in bpy.context.scene.objects
                else "BLANK1",
            ).model_to_select = armature_name

            row2 = row.row(align=True)
            # Button to remove or clean the model from the scene
            if (
                armature.MustardUI_RigSettings.model_armature_object.name
                not in bpy.context.scene.objects
            ):
                row2.enabled = not settings.viewport_model_selection
                row2.operator(
                    "mustardui.remove_armature", text="", icon="BRUSH_DATA"
                ).armature = armature_name
            else:
                row2.enabled = (
                    armature == settings.panel_model_selection_armature
                    and not settings.viewport_model_selection
                )
                row2.operator("mustardui.remove", text="", icon="TRASH")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_SelectModel)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_SelectModel)
