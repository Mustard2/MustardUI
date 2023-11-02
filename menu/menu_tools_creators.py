import bpy
from . import MainPanel
from ..model_selection.active_object import *


class PANEL_PT_MustardUI_ToolsCreators(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_ToolsCreators"
    bl_label = "Creator Tools"

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=1)
        addon_prefs = context.preferences.addons["MustardUI"].preferences
        return res and addon_prefs.developer and addon_prefs.experimental

    def draw(self, context):

        layout = self.layout

        box = layout.box()

        box.label(text="Affect Transform on Bone Constraints", icon="CONSTRAINT_BONE")
        row = box.row(align=True)
        row.operator('mustardui.tools_creators_affect_transform', text="Enable").enable = True
        row.operator('mustardui.tools_creators_affect_transform', text="Disable").enable = False


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_ToolsCreators)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ToolsCreators)
