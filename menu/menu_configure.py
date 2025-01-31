import bpy
from . import MainPanel
from ..model_selection.active_object import *
from ..warnings.ops_fix_old_UI import check_old_UI
from .. import __package__ as base_package


row_scale = 1.2


class PANEL_PT_MustardUI_InitPanel(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_InitPanel"
    bl_label = "UI Configuration"

    url_MustardUI_ConfigGuide = "https://github.com/Mustard2/MustardUI/wiki/Developer-Guide"

    @classmethod
    def poll(cls, context):
        if check_old_UI():
            return False

        res, arm = mustardui_active_object(context, config=1)
        addon_prefs = context.preferences.addons[base_package].preferences
        return res and addon_prefs.developer

    def draw(self, context):

        layout = self.layout
        scene = context.scene

        settings = bpy.context.scene.MustardUI_Settings
        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings
        armature_settings = arm.MustardUI_ArmatureSettings
        tools_settings = arm.MustardUI_ToolsSettings
        lattice_settings = arm.MustardUI_LatticeSettings
        physics_settings = arm.MustardUI_PhysicsSettings
        addon_prefs = context.preferences.addons[base_package].preferences

        row_scale = 1.2

        # General Settings
        row = layout.row(align=False)
        row.label(text=arm.name, icon="OUTLINER_DATA_ARMATURE")
        row.operator('mustardui.configuration_smartcheck', icon="VIEWZOOM", text="")
        row.operator('mustardui.openlink', text="", icon="QUESTION").url = self.url_MustardUI_ConfigGuide

        box = layout.box()
        box.prop(rig_settings, "model_name", text="Name")
        box.prop(rig_settings, "model_body", text="Body")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_InitPanel)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_InitPanel)
