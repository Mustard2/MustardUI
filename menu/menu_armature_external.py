import bpy

from . import MainPanel
from ..settings.rig import *
from ..armature.external.mhx import panel as menu_mhx_panel
from ..armature.external.mhx_defs import panel_poll


class PANEL_PT_MustardUI_Armature_External(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Armature_External"
    bl_label = ""
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return panel_poll(cls, context)

    def draw_header(self, context):

        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings

        layout = self.layout
        rig_type = rig_settings.model_rig_type
        if rig_type == "mhx":
            layout.label(text="MHX")

    def draw(self, context):
        ob = context.object
        if not (ob and ob.get("MhxRig", False)):
            layout = self.layout
            layout.label(text="Hidden: Select MHX Armature", icon="ERROR")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_Armature_External)
    menu_mhx_panel.register()


def unregister():
    menu_mhx_panel.unregister()
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Armature_External)
