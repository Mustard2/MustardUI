import bpy
from . import MainPanel
from ..model_selection.active_object import *
from ..warnings.ops_fix_old_UI import check_old_UI
from .. import __package__ as base_package
from .menu_configure import row_scale


class PANEL_PT_MustardUI_InitPanel_Armature(MainPanel, bpy.types.Panel):
    bl_label = "Armature"
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
        layout.label(text="", icon="ARMATURE_DATA")

    def draw(self, context):

        layout = self.layout
        scene = context.scene

        settings = bpy.context.scene.MustardUI_Settings
        res, arm = mustardui_active_object(context, config=1)
        armature_settings = arm.MustardUI_ArmatureSettings

        box = layout.box()
        box.label(text="General Settings", icon="MODIFIER")
        box.prop(armature_settings, 'mirror')

        box = layout.box()
        row = box.row()
        row.label(text="Bone Collections", icon="BONE_DATA")
        row.operator("Mustardui.armature_smartcheck", text="", icon="VIEWZOOM")

        active_bcoll = arm.collections.active

        rows = 1
        if active_bcoll:
            rows = 4

        row = box.row()

        row.template_list(
            "MUSTARDUI_UL_Armature_UIList",
            "collections_all",
            arm,
            "collections_all",
            arm.collections,
            "active_index",
            rows=rows,
        )

        col = row.column(align=True)
        if settings.advanced:
            col.operator("armature.collection_add", icon='ADD', text="")
            col.operator("armature.collection_remove", icon='REMOVE', text="")
        if active_bcoll:
            col.separator()
            col.operator("armature.collection_move", icon='TRIA_UP', text="").direction = 'UP'
            col.operator("armature.collection_move", icon='TRIA_DOWN', text="").direction = 'DOWN'
            col.separator()

        if settings.advanced:
            row = box.row()

            sub = row.row(align=True)
            sub.operator("armature.collection_assign", text="Assign")
            sub.operator("armature.collection_unassign", text="Remove")

            sub = row.row(align=True)
            sub.operator("armature.collection_select", text="Select")
            sub.operator("armature.collection_deselect", text="Deselect")

        if arm.collections.active_index > -1:

            collections = arm.collections_all
            bcoll = collections[arm.collections.active_index]
            bcoll_settings = bcoll.MustardUI_ArmatureBoneCollection

            col = box.column(align=True)
            row = col.row()
            row.enabled = not bcoll_settings.outfit_switcher_enable
            row.prop(bcoll_settings, 'icon')
            row = col.row()
            row.enabled = not bcoll_settings.outfit_switcher_enable
            row.prop(bcoll_settings, 'advanced')
            row = col.row()
            row.enabled = not bcoll_settings.outfit_switcher_enable
            row.prop(bcoll_settings, 'default')

            col = box.column(align=True)
            col.prop(bcoll_settings, 'outfit_switcher_enable')
            if bcoll_settings.outfit_switcher_enable:
                col.prop(bcoll_settings, 'outfit_switcher_collection', text="Collection")
                if bcoll_settings.outfit_switcher_collection is not None:
                    col.prop(bcoll_settings, 'outfit_switcher_object', text="Object")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_InitPanel_Armature)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_InitPanel_Armature)
