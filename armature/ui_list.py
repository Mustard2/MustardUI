import bpy
from bpy.props import *


class MUSTARDUI_UL_Armature_UIList(bpy.types.UIList):
    """UIList for Armature layers properties"""

    def draw_item(self, _context, layout, armature, bcoll, _icon, _active_data, _active_propname, _index):

        settings = bpy.context.scene.MustardUI_Settings

        bcoll_settings = bcoll.MustardUI_ArmatureBoneCollection

        active_bone = armature.edit_bones.active or armature.bones.active
        has_active_bone = active_bone and bcoll.name in active_bone.collections

        row = layout.row(align=True)

        # Check if the icon should be drawn
        for b in armature.collections_all:
            if b.MustardUI_ArmatureBoneCollection.icon != "NONE":
                row.label(text="", icon=bcoll_settings.icon if bcoll_settings.icon != "NONE" else "BLANK1")
                break

        if settings.advanced:
            row.prop(bcoll, "name", text="", emboss=False,
                        icon='DOT' if has_active_bone else 'BLANK1')
        else:
            row.prop(bcoll, "name", text="", emboss=False)

        if armature.override_library:
            icon = 'LIBRARY_DATA_OVERRIDE' if bcoll.is_local_override else 'BLANK1'
            row.prop(
                bcoll,
                "is_local_override",
                text="",
                emboss=False,
                icon=icon)

        row.label(text="", icon="EXPERIMENTAL" if bcoll_settings.advanced else "BLANK1")
        row.label(text="", icon="MOD_CLOTH" if bcoll_settings.outfit_switcher_enable else "BLANK1")

        row = layout.row(align=True)
        col = row.column()
        col.enabled = not bcoll_settings.outfit_switcher_enable
        col.prop(bcoll_settings, "is_in_UI", text="", emboss=False,
                 icon='GREASEPENCIL' if bcoll_settings.is_in_UI else 'OUTLINER_DATA_GP_LAYER')

        if settings.advanced:
            row.prop(bcoll, "is_visible", text="", emboss=False, icon='HIDE_OFF' if bcoll.is_visible else 'HIDE_ON')


def register():
    bpy.utils.register_class(MUSTARDUI_UL_Armature_UIList)

    bpy.types.Scene.mustardui_armature_uilist_index = IntProperty(name="", default=0)


def unregister():
    bpy.utils.unregister_class(MUSTARDUI_UL_Armature_UIList)
