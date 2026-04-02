import bpy

from . import MainPanel
from ..model_selection.active_object import *
from ..warnings.ops_fix_old_UI import check_old_UI
from ..settings.rig import *


class PANEL_PT_MustardUI_Links(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Links"
    bl_label = "Links"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        if check_old_UI():
            return False

        res, arm = mustardui_active_object(context, config=0)
        if arm is not None:
            rig_settings = arm.MustardUI_RigSettings
            return res and rig_settings.links_enable and arm.MustardUI_Links
        return res

    def draw(self, context):
        poll, arm = mustardui_active_object(context, config=0)

        layout = self.layout

        for link in arm.MustardUI_Links:
            if link != '':
                layout.operator('mustardui.openlink', text=link.name, icon="URL").url = link.url


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_Links)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Links)
