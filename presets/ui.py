import bpy

from ..model_selection.active_object import mustardui_active_object
from .get_context import get_preset_context
from .types import get_preset_definition, preset_type_items


class MustardUI_PresetsUI(bpy.types.Operator):
    """Generic Presets UI"""

    bl_idname = "mustardui.presets_ui"
    bl_label = "Presets"
    bl_options = {"UNDO"}

    bl_space_type = "OUTLINER"
    bl_region_type = "WINDOW"

    preset_type: bpy.props.EnumProperty(items=preset_type_items)

    new_preset_name: bpy.props.StringProperty(default="Preset")

    force_modifiers_creation: bpy.props.BoolProperty(default=False)

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        return res and arm is not None

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=250)

    def execute(self, context):
        return {"FINISHED"}

    def draw(self, context):
        res, arm = mustardui_active_object(context, config=0)

        settings, presets, preset, index, index_prop = get_preset_context(
            arm, self.preset_type
        )

        definition = get_preset_definition(self.preset_type)
        presets = settings.presets

        layout = self.layout

        ui_list = definition["ui_list"]
        index_prop = definition["index_prop"]

        if presets:
            row = layout.row()

            # UI List
            row.template_list(
                ui_list,
                "The_List",
                settings,
                "presets",
                arm,
                index_prop,
            )

            col = row.column()

            # Apply
            op = col.operator("mustardui.preset_apply", text="", icon="PLAY")
            op.preset_type = self.preset_type

            col.separator()

            # Import / Export
            col2 = col.column(align=True)
            op = col2.operator(
                "mustardui.preset_import",
                text="",
                icon="COPYDOWN",
            )
            op.preset_type = self.preset_type
            op = col2.operator(
                "mustardui.preset_export",
                text="",
                icon="PASTEDOWN",
            )
            op.preset_type = self.preset_type

            # Transfer
            op = col2.operator("mustardui.preset_transfer", text="", icon="FORWARD")
            op.preset_type = self.preset_type

            col.separator()

            # Delete
            op = col.operator("mustardui.preset_delete", text="", icon="X")
            op.preset_type = self.preset_type

        else:
            row = layout.row(align=True)
            op = row.operator(
                "mustardui.preset_import",
                text="Import Preset",
                icon="PASTEDOWN",
            )
            op.preset_type = self.preset_type

        layout.separator()

        row = layout.row(align=True)
        row.prop(self, "new_preset_name", text="")

        op = row.operator("mustardui.preset_create", icon="ADD", text="")
        op.new_preset_name = self.new_preset_name
        op.preset_type = self.preset_type


def register():
    bpy.utils.register_class(MustardUI_PresetsUI)


def unregister():
    bpy.utils.unregister_class(MustardUI_PresetsUI)
