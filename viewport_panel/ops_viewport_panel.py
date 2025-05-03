import bpy
from .. import __package__ as base_package
from ..model_selection.active_object import *


class VIEW3D_MT_PIE_MustardUI_ViewportPieMenu(bpy.types.Menu):
    # label is displayed at the center of the pie menu.
    bl_label = "MustardUI"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        pie.operator('mustardui.viewportmodelselection', text="Viewport Model Selection", icon="VIEW3D")
        pie.operator('wm.call_panel', icon="ARMATURE_DATA",
                     text="Armature Collections").name = "PANEL_PT_MustardUI_Armature"
        pie.operator('wm.call_panel', icon="PHYSICS",
                     text="Physics").name = "PANEL_PT_MustardUI_Physics"


# Operator for key press detection and calling the pie menu
class MustardUI_ViewportPieMenu_KeymapOperator(bpy.types.Operator):
    bl_idname = "mustardui.viewport_pie_menu_keymap_operator"
    bl_label = "MustardUI Viewport Menu"

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        addon_prefs = context.preferences.addons[base_package].preferences
        return addon_prefs.experimental and (res if arm is not None else False)

    def execute(self, context):
        bpy.ops.wm.call_menu_pie(name="VIEW3D_MT_PIE_MustardUI_ViewportPieMenu")
        return {'FINISHED'}


# Register classes and keymap
def register():
    bpy.utils.register_class(VIEW3D_MT_PIE_MustardUI_ViewportPieMenu)
    bpy.utils.register_class(MustardUI_ViewportPieMenu_KeymapOperator)

    # Set up the keymap to listen for the 'F' key press in 3D View
    wm = bpy.context.window_manager
    keymap = wm.keyconfigs.active.keymaps['3D View']
    keymap_item = keymap.keymap_items.new(MustardUI_ViewportPieMenu_KeymapOperator.bl_idname, type='M', alt=True, shift=True, value='PRESS')


# Unregister everything
def unregister():
    bpy.utils.unregister_class(VIEW3D_MT_PIE_MustardUI_ViewportPieMenu)
    bpy.utils.unregister_class(MustardUI_ViewportPieMenu_KeymapOperator)

    # Remove keymap item
    wm = bpy.context.window_manager
    keymap = wm.keyconfigs.active.keymaps['3D View']
    for item in keymap.keymap_items:
        if item.idname == MustardUI_ViewportPieMenu_KeymapOperator.bl_idname:
            keymap.keymap_items.remove(item)
