import bpy
from . import MainPanel
from ..warnings.ops_fix_old_UI import check_old_UI


class PANEL_PT_MustardUI_Warnings(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Warnings"
    bl_label = "Warnings"
    bl_icon = "ERROR"

    @classmethod
    def poll(cls, context):
        # Check presence of old UI scripts
        return check_old_UI()

    def draw_header(self, context):
        self.layout.label(text="", icon="ERROR")

    def draw(self, context):

        layout = self.layout

        # Old UI scripts
        if check_old_UI():
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Old UI script found", icon="ERROR")
            col.label(text="Remove the scripts to avoid errors", icon="BLANK1")
            box.operator("mustardui.warnings_fix_old_ui")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_Warnings)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Warnings)
