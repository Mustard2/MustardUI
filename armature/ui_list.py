import bpy
from bpy.props import *
from ..model_selection.active_object import *


class MUSTARDUI_UL_Armature_UIList(bpy.types.UIList):
    """UIList for Armature layers properties"""

    def draw_item(self, _context, layout, armature, bcoll, _icon, _active_data, _active_propname, _index):
        settings = bpy.context.scene.MustardUI_Settings

        bcoll_settings = bcoll.MustardUI_ArmatureBoneCollection

        active_bone = armature.edit_bones.active or armature.bones.active
        has_active_bone = active_bone and bcoll.name in active_bone.collections

        row = layout.row(align=True)

        collections = armature.collections_all

        # Check if the icon should be drawn
        for b in collections:
            if b.MustardUI_ArmatureBoneCollection.icon != "NONE":
                row.label(text="", icon=bcoll_settings.icon if bcoll_settings.icon != "NONE" else "BLANK1")
                break

        # Display name with icon if advanced settings are enabled
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
                 icon='CHECKBOX_HLT' if bcoll_settings.is_in_UI else 'CHECKBOX_DEHLT')

        if settings.advanced:
            row.prop(bcoll, "is_visible", text="", emboss=False, icon='HIDE_OFF' if bcoll.is_visible else 'HIDE_ON')


class MUSTARDUI_UL_Armature_UIList_Children(bpy.types.UIList):
    """UIList for Armature layers properties"""

    def draw_item(self, _context, layout, armature, bcoll, _icon, _active_data, _active_propname, _index):
        settings = bpy.context.scene.MustardUI_Settings

        bcoll_settings = bcoll.MustardUI_ArmatureBoneCollection

        active_bone = armature.id_data.edit_bones.active or armature.id_data.bones.active
        has_active_bone = active_bone and bcoll.name in active_bone.collections

        row = layout.row(align=True)

        collections = armature.id_data.collections_all

        # Check if the icon should be drawn
        for b in collections:
            if b.MustardUI_ArmatureBoneCollection.icon != "NONE":
                row.label(text="", icon=bcoll_settings.icon if bcoll_settings.icon != "NONE" else "BLANK1")
                break

        # Display name with icon if advanced settings are enabled
        if settings.advanced:
            row.prop(bcoll, "name", text="", emboss=False,
                     icon='DOT' if has_active_bone else 'BLANK1')
        else:
            row.prop(bcoll, "name", text="", emboss=False)

        if armature.id_data.override_library:
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
                 icon='CHECKBOX_HLT' if bcoll_settings.is_in_UI else 'CHECKBOX_DEHLT')

        if settings.advanced:
            row.prop(bcoll, "is_visible", text="", emboss=False, icon='HIDE_OFF' if bcoll.is_visible else 'HIDE_ON')


def register():
    bpy.utils.register_class(MUSTARDUI_UL_Armature_UIList)
    bpy.utils.register_class(MUSTARDUI_UL_Armature_UIList_Children)

    bpy.types.Scene.mustardui_armature_uilist_index = IntProperty(name="", default=0)


def unregister():
    del bpy.types.Scene.mustardui_armature_uilist_index

    bpy.utils.unregister_class(MUSTARDUI_UL_Armature_UIList_Children)
    bpy.utils.unregister_class(MUSTARDUI_UL_Armature_UIList)
