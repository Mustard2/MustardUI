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
        return res

    def draw(self, context):
        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings

        layout = self.layout

        if rig_settings.url_website != '' or rig_settings.url_patreon != '' or rig_settings.url_twitter != '' or rig_settings.url_smutbase != '' or rig_settings.url_documentation != '' or rig_settings.url_reportbug != '':

            box = layout.box()
            box.label(text="Social profiles/contacts", icon="BOOKMARKS")

            if rig_settings.url_website != '':
                box.operator('mustardui.openlink', text="Website", icon="URL").url = rig_settings.url_website
            if rig_settings.url_patreon != '':
                box.operator('mustardui.openlink', text="Patreon", icon="URL").url = rig_settings.url_patreon
            if rig_settings.url_twitter != '':
                box.operator('mustardui.openlink', text="Twitter", icon="URL").url = rig_settings.url_twitter
            if rig_settings.url_smutbase != '':
                box.operator('mustardui.openlink', text="SmutBase", icon="URL").url = rig_settings.url_smutbase
            if rig_settings.url_documentation != '':
                box.operator('mustardui.openlink', text="Documentation",
                             icon="URL").url = rig_settings.url_documentation
            if rig_settings.url_reportbug != '':
                box.operator('mustardui.openlink', text="Report a Bug", icon="URL").url = rig_settings.url_reportbug

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
