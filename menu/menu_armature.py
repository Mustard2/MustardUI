import bpy

from . import MainPanel
from ..model_selection.active_object import *
from ..warnings.ops_fix_old_UI import check_old_UI
from ..settings.rig import *
from ..misc.mirror import check_mirror


def draw_armature_button(bcoll, bcoll_settings, bcolls, armature_settings, layout):

    def draw_with_icon(layout, prop, prop_name, name, icon):

        row = layout.row(align=True)
        if prop.children:
            show_children = prop.MustardUI_ArmatureBoneCollection.show_children
            row.prop(prop.MustardUI_ArmatureBoneCollection, "show_children", toggle=True, icon="TRIA_DOWN" if show_children else "TRIA_RIGHT")

        if icon != "NONE":
            row.prop(prop, prop_name,
                     text=name,
                     toggle=True,
                     icon=icon)
        else:
            row.prop(prop, prop_name,
                     text=name,
                     toggle=True)

    def draw_children(layout, bcoll):
        if bcoll.children and bcoll.MustardUI_ArmatureBoneCollection.show_children:
            for c in bcoll.children:
                row = layout.row(align=True)
                row.label(icon="BLANK1")
                draw_with_icon(row, c, "is_visible", c.name, c.MustardUI_ArmatureBoneCollection.icon)

    if not armature_settings.mirror:
        row = layout.row()
        draw_with_icon(row, bcoll, "is_visible", bcoll.name, bcoll_settings.icon)
        draw_children(layout, bcoll)
        return

    for b in bcolls:
        if check_mirror(bcoll.name, b.name, left=True):
            row = layout.row()
            draw_with_icon(row, bcoll, "is_visible", bcoll.name, bcoll_settings.icon)
            r_icon = b.MustardUI_ArmatureBoneCollection.icon
            draw_with_icon(row, b, "is_visible", b.name, r_icon)
            return
        elif check_mirror(bcoll.name, b.name, left=False):
            return

    row = layout.row()
    draw_with_icon(row, bcoll, "is_visible", bcoll.name, bcoll_settings.icon)

    draw_children(layout, bcoll)


class PANEL_PT_MustardUI_Armature(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Armature"
    bl_label = "Armature"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):

        if check_old_UI():
            return False

        res, obj = mustardui_active_object(context, config=0)

        if obj is not None:
            rig_settings = obj.MustardUI_RigSettings
            armature_settings = obj.MustardUI_ArmatureSettings
            bcolls = obj.collections_all

            if len(bcolls) < 1:
                return False

            enabled_colls = [x for x in bcolls if x.MustardUI_ArmatureBoneCollection.is_in_UI]

            if rig_settings.hair_collection is not None:
                return res and (len(enabled_colls) > 0 or (len([x for x in rig_settings.hair_collection.objects if
                                                                x.type == "ARMATURE"]) > 1 and armature_settings.enable_automatic_hair))
            else:
                return res and len(enabled_colls) > 0
        else:
            return res

    def draw(self, context):

        settings = bpy.context.scene.MustardUI_Settings
        poll, obj = mustardui_active_object(context, config=0)
        armature_settings = obj.MustardUI_ArmatureSettings
        rig_settings = obj.MustardUI_RigSettings

        bcolls = obj.collections

        box = self.layout

        draw_separator = False
        if rig_settings.hair_collection is not None and armature_settings.enable_automatic_hair:
            if len([x for x in rig_settings.hair_collection.objects if x.type == "ARMATURE"]) > 0:
                box.prop(armature_settings, "hair", toggle=True, icon="CURVES")
                draw_separator = True

        if len(rig_settings.outfits_list) > 0:
            if len([x for x in bcolls if x.MustardUI_ArmatureBoneCollection.outfit_switcher_enable]):
                box.prop(armature_settings, "outfits", toggle=True, icon="MOD_CLOTH")
                draw_separator = True

        if draw_separator:
            box.separator()

        enabled_colls = [x for x in bcolls if x.MustardUI_ArmatureBoneCollection.is_in_UI]

        box.use_property_split = False
        box.use_property_decorate = True  # No animation.

        for bcoll in enabled_colls:
            bcoll_settings = bcoll.MustardUI_ArmatureBoneCollection
            if (bcoll_settings.advanced and settings.advanced) or not bcoll_settings.advanced:
                draw_armature_button(bcoll, bcoll_settings, enabled_colls, armature_settings, box)

        box.separator()
        box.operator('mustardui.armature_reset_bcoll', icon="LOOP_BACK", text="Reset Layers Visibility")
        box.operator('mustardui.armature_clearpose', icon="OUTLINER_OB_ARMATURE", text="Reset Pose")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_Armature)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Armature)
