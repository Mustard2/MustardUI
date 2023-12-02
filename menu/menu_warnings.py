import bpy
from . import MainPanel
from ..warnings.ops_fix_old_UI import check_old_UI
from ..warnings.ops_fix_eevee_normals import check_eevee_normals


class PANEL_PT_MustardUI_Warnings(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Warnings"
    bl_label = "Warnings"
    bl_icon = "ERROR"

    @classmethod
    def poll(cls, context):
        # Check presence of old UI scripts
        settings = bpy.context.scene.MustardUI_Settings
        return check_old_UI() or check_eevee_normals(context.scene, settings)

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
            box.operator("mustardui.warnings_fix_old_ui")

        if check_eevee_normals(context.scene, settings):
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Eevee Optimed Normals are active with Cycles!", icon="ERROR")
            box.operator("mustardui.warnings_fix_eevee_normals")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_Warnings)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Warnings)
