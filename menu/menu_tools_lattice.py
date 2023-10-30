import bpy
from . import MainPanel
from ..model_selection.active_object import *
from ..settings.rig import *
from ..tools.lattice import *


class PANEL_PT_MustardUI_Tools_Lattice(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Tools_Lattice"
    bl_label = "Body Shape"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):

        res, obj = mustardui_active_object(context, config=0)

        if obj is not None:
            lattice_settings = obj.MustardUI_LatticeSettings
            poll = lattice_settings.lattice_panel_enable

            return poll and res

        else:
            return res

    def draw_header(self, context):

        poll, obj = mustardui_active_object(context, config=0)
        lattice_settings = obj.MustardUI_LatticeSettings

        self.layout.prop(lattice_settings, "lattice_enable", text="", toggle=False)

    def draw(self, context):

        settings = bpy.context.scene.MustardUI_Settings
        poll, obj = mustardui_active_object(context, config=0)
        lattice_settings = obj.MustardUI_LatticeSettings

        layout = self.layout

        if not lattice_settings.lattice_enable:
            layout.enabled = False

        box = layout.box()
        box.label(text="Shape settings", icon="MOD_LATTICE")
        row = box.row(align=True)
        row.label(text="Shape")
        row.scale_x = 2.
        row.prop(lattice_settings, "lattice_keys")
        row = box.row(align=True)
        if lattice_settings.lattice_keys == "Base":
            row.enabled = False
        row.prop(lattice_settings, "lattice_key_value")
        if settings.advanced:
            row = box.row(align=True)
            if lattice_settings.lattice_keys == "Base":
                row.enabled = False
            row.label(text="Interpolation")
            row.scale_x = 2.
            row.prop(lattice_settings, "lattice_interpolation")

        box = layout.box()
        box.label(text="Custom Lattice Shape", icon="PLUS")
        box.label(text="   - Run Custom Shape")
        box.label(text="   - Move the vertices")
        box.label(text="   - Apply shape")
        if lattice_settings.lattice_mod_status:
            box.operator("mustardui.tools_lattice", text="Apply shape", depress=True, icon="EDITMODE_HLT").mod = 1
        else:
            row = box.row(align=True)
            if lattice_settings.lattice_keys != lattice_settings.lattice_modifiers_name + "Custom":
                row.enabled = False
            row.operator("mustardui.tools_lattice", text="Custom shape", icon="EDITMODE_HLT").mod = 0
        row = box.row(align=True)
        if lattice_settings.lattice_keys != lattice_settings.lattice_modifiers_name + "Custom":
            row.enabled = False
        row.operator("mustardui.tools_lattice", text="Reset Custom shape", icon="CANCEL").mod = 2


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_Tools_Lattice)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Tools_Lattice)
