import bpy

from . import MainPanel
from ..model_selection.active_object import *
from ..settings.rig import *


class PANEL_PT_MustardUI_Links(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Links"
    bl_label = "Links"
    bl_options = {"DEFAULT_CLOSED"}

    url_MustardUI = "https://github.com/Mustard2/MustardUI"
    url_MustardUI_ReportBug = "https://github.com/Mustard2/MustardUI/issues"
    url_MustardUI_Tutorial = "https://github.com/Mustard2/MustardUI/wiki/Tutorial"

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        if arm is not None:
            rig_settings = arm.MustardUI_RigSettings
            return res and rig_settings.links_enable
        return res

    def draw(self, context):
        poll, obj = mustardui_active_object(context, config=0)

        layout = self.layout

        if len(obj.MustardUI_Links) > 0:

            box = layout.box()
            box.label(text="Creator Links", icon="BOOKMARKS")

            for link in obj.MustardUI_Links:
                if link != '':
                    box.operator('mustardui.openlink', text=link.name, icon="URL").url = link.url

        box = layout.box()
        box.label(text="MustardUI References", icon="INFO")
        box.operator('mustardui.openlink', text="MustardUI - GitHub", icon="URL").url = self.url_MustardUI
        box.operator('mustardui.openlink', text="MustardUI - Tutorial",
                     icon="URL").url = self.url_MustardUI_Tutorial
        box.operator('mustardui.openlink', text="MustardUI - Report Bug",
                     icon="URL").url = self.url_MustardUI_ReportBug


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_Links)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Links)
