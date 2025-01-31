import bpy
from . import MainPanel
from ..model_selection.active_object import *
from ..warnings.ops_fix_old_UI import check_old_UI
from .. import __package__ as base_package


class PANEL_PT_MustardUI_InitPanel_Tools(MainPanel, bpy.types.Panel):
    bl_label = "Tools"
    bl_parent_id = "PANEL_PT_MustardUI_InitPanel"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        if check_old_UI():
            return False

        res, arm = mustardui_active_object(context, config=1)
        addon_prefs = context.preferences.addons[base_package].preferences
        return res and addon_prefs.developer

    def draw_header(self, context):
        layout = self.layout
        layout.label(text="", icon="TOOL_SETTINGS")

    def draw(self, context):

        layout = self.layout

        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings
        tools_settings = arm.MustardUI_ToolsSettings
        lattice_settings = arm.MustardUI_LatticeSettings

        box = layout.box()
        box.label(text="Enable Tools", icon="MODIFIER")
        col = box.column(align=True)
        col.prop(rig_settings, 'simplify_main_enable')
        col.prop(tools_settings, 'childof_enable')
        col.prop(tools_settings, 'autobreath_enable')
        col.prop(tools_settings, 'autoeyelid_enable')
        col.prop(lattice_settings, 'lattice_panel_enable')

        if tools_settings.autoeyelid_enable:
            box = layout.box()
            box.label(text="Auto Blink Tool Settings", icon="HIDE_OFF")
            box.prop(tools_settings, 'autoeyelid_driver_type', text="Type")
            col = box.column(align=True)
            if tools_settings.autoeyelid_driver_type == "SHAPE_KEY":
                col.prop_search(tools_settings, "autoeyelid_eyeL_shapekey", rig_settings.model_body.data.shape_keys,
                                "key_blocks")
                col.prop_search(tools_settings, "autoeyelid_eyeR_shapekey", rig_settings.model_body.data.shape_keys,
                                "key_blocks")
            else:
                col.prop(tools_settings, "autoeyelid_morph")

        if lattice_settings.lattice_panel_enable:
            box = layout.box()
            box.label(text="Lattice Tool Settings", icon="MOD_LATTICE")
            box.prop(lattice_settings, 'lattice_object')
            box.operator('mustardui.tools_latticesetup', text="Lattice Setup").mod = 0
            box.operator('mustardui.tools_latticesetup', text="Lattice Clean").mod = 1


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_InitPanel_Tools)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_InitPanel_Tools)
