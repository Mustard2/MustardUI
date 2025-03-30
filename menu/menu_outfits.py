import bpy
from . import MainPanel
from ..model_selection.active_object import *
from ..misc.ui_collapse import ui_collapse_prop
from ..warnings.ops_fix_old_UI import check_old_UI
from ..settings.rig import *
from .misc import *


def extract_items(collection, subcollections):
    items = [x for x in (collection.all_objects if subcollections else collection.objects)]
    return [x for x in items if x.parent is None or x.parent not in items]


# Type: 0 - Standrd, 1 - Locked Objects, 2 - Extras
def draw_outfit_piece(layout, obj, arm, rig_settings, settings, otype=0, level=0):

    if otype < 0 or otype > 3:
        return

    if level > 3:
        return

    col = layout.column(align=True)
    row = col.row(align=True)
    for lvl in range(level):
        row.label(text="", icon="BLANK1")

    collapse = False
    if obj.children:
        collapse = not ui_collapse_prop(row, obj, 'MustardUI_outfit_collapse_children', "", icon="",
                                        align=False, use_layout=True, emboss=True, invert_checkbox=True)

    if rig_settings.model_MustardUI_naming_convention:
        if otype == 0:
            coll_name = rig_settings.outfits_list+' - '
        elif otype == 1:
            coll_name = rig_settings.model_name+' '
        else:
            coll_name = rig_settings.extras_collection.name+' - '
        row.operator("mustardui.object_visibility",
                     text=obj.name[len(coll_name):],
                     icon='OUTLINER_OB_' + obj.type, depress=not obj.hide_viewport).obj = obj.name
    else:
        row.operator("mustardui.object_visibility", text=obj.name, icon='OUTLINER_OB_' + obj.type,
                     depress=not obj.hide_viewport).obj = obj.name

    # Outfit custom properties
    co_coll = None
    if otype == 0:
        co_coll = bpy.data.collections[rig_settings.outfits_list]
    elif otype == 2:
        co_coll = rig_settings.extras_collection

    if rig_settings.outfit_custom_properties_name_order:
        custom_properties_obj = sorted([x for x in arm.MustardUI_CustomPropertiesOutfit if
                                        (x.outfit == co_coll if otype != 1 else True) and x.outfit_piece == obj and not x.hidden],
                                       key=lambda x: x.name)
    else:
        custom_properties_obj = [x for x in arm.MustardUI_CustomPropertiesOutfit if
                                 (x.outfit == co_coll if otype != 1 else True) and x.outfit_piece == obj and not x.hidden]

    if len(custom_properties_obj) > 0 and rig_settings.outfit_additional_options:
        row.prop(obj, "MustardUI_additional_options_show", toggle=True, icon="PREFERENCES")
        if obj.MustardUI_additional_options_show:
            row2 = col.row(align=True)
            for lvl in range(level):
                row2.label(text="", icon="BLANK1")
            mustardui_custom_properties_print(arm, settings, custom_properties_obj,
                                              row2, rig_settings.outfit_custom_properties_icons)

    if otype != 2:
        row.prop(obj, "MustardUI_outfit_lock", toggle=True,
                 icon='LOCKED' if obj.MustardUI_outfit_lock else 'UNLOCKED')

    if not collapse:
        for c in obj.children:
            draw_outfit_piece(layout, c, arm, rig_settings, settings, otype, level + 1)


class PANEL_PT_MustardUI_Outfits(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Outfits"
    bl_label = "Outfits"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):

        if check_old_UI():
            return False

        res, arm = mustardui_active_object(context, config=0)

        if arm is not None:

            rig_settings = arm.MustardUI_RigSettings

            # Check if one of these should be shown in the UI
            outfits_avail = len([x for x in rig_settings.outfits_collections if x.collection is not None]) > 0

            if rig_settings.extras_collection is not None:
                items = rig_settings.extras_collection.all_objects if rig_settings.outfit_config_subcollections else rig_settings.extras_collection.objects
                extras_avail = len(items) > 0
            else:
                extras_avail = False

            return res and (outfits_avail or extras_avail) if arm is not None else False

        return res

    def draw(self, context):

        settings = bpy.context.scene.MustardUI_Settings

        poll, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings

        layout = self.layout

        # Outfit list
        if len([x for x in rig_settings.outfits_collections if x.collection is not None]) > 0:

            box = layout.box()
            box.label(text="Outfits list", icon="MOD_CLOTH")
            row = box.row(align=True)
            row.prop(rig_settings, "outfits_list", text="")

            if rig_settings.outfits_list != "Nude":

                collection = bpy.data.collections[rig_settings.outfits_list]
                items = extract_items(collection, rig_settings.outfit_config_subcollections)

                if len(items) > 0:

                    # Global outfit custom properties
                    if rig_settings.outfit_custom_properties_name_order:
                        custom_properties = sorted([x for x in arm.MustardUI_CustomPropertiesOutfit if
                                                    x.outfit == bpy.data.collections[
                                                        rig_settings.outfits_list] and x.outfit_piece is None and not x.hidden and (
                                                        not x.advanced if not settings.advanced else True)],
                                                   key=lambda x: x.name)
                    else:
                        custom_properties = [x for x in arm.MustardUI_CustomPropertiesOutfit if
                                             x.outfit == bpy.data.collections[
                                                 rig_settings.outfits_list] and x.outfit_piece is None and not x.hidden and (
                                                 not x.advanced if not settings.advanced else True)]

                    if len(custom_properties) > 0 and rig_settings.outfit_additional_options:
                        row.prop(rig_settings, "outfit_global_custom_properties_collapse", text="", toggle=True,
                                 icon="PREFERENCES")
                        if rig_settings.outfit_global_custom_properties_collapse:
                            mustardui_custom_properties_print(arm, settings, custom_properties, box,
                                                              rig_settings.outfit_custom_properties_icons)

                    for obj in sorted(items, key=lambda x: x.name):
                        draw_outfit_piece(box, obj, arm, rig_settings, settings, 0, 0)

                else:
                    box.label(text="This Collection seems empty", icon="ERROR")

            # Locked objects
            locked_objects = []
            for coll in [x for x in rig_settings.outfits_collections if x.collection is not None]:
                items = coll.collection.all_objects if rig_settings.outfit_config_subcollections else coll.collection.objects
                for obj in items:
                    if obj.MustardUI_outfit_lock and obj.parent not in locked_objects:
                        locked_objects.append(obj)

            if len(locked_objects) > 0:
                box.separator()
                box.label(text="Locked objects:", icon="LOCKED")
                for obj in locked_objects:
                    draw_outfit_piece(box, obj, arm, rig_settings, settings, 1, 0)

            # Extras
            if rig_settings.extras_collection is not None:

                eitems = extract_items(rig_settings.extras_collection,
                                       rig_settings.outfit_config_subcollections)

                if len(eitems) > 0:

                    box = layout.box()

                    if ui_collapse_prop(box, rig_settings, 'extras_collapse', "Extras", icon="", align=False):
                        for obj in sorted(eitems, key=lambda x: x.name):
                            draw_outfit_piece(box, obj, arm, rig_settings, settings, 2, 0)

            # Outfit global properties
            if rig_settings.outfits_enable_global_subsurface or rig_settings.outfits_enable_global_smoothcorrection or rig_settings.outfits_enable_global_shrinkwrap or rig_settings.outfits_enable_global_surfacedeform or rig_settings.outfits_enable_global_mask or rig_settings.outfits_enable_global_solidify or rig_settings.outfits_enable_global_triangulate or rig_settings.outfits_enable_global_normalautosmooth:

                box = layout.box()
                row = box.row(align=True)
                row.label(text="Global Properties", icon="MODIFIER")
                row.operator('mustardui.switchglobal_outfits', text="", icon="RESTRICT_VIEW_OFF").enable = True
                row.operator('mustardui.switchglobal_outfits', text="", icon="RESTRICT_VIEW_ON").enable = False
                col = box.column(align=True)
                if rig_settings.outfits_enable_global_subsurface:
                    col.prop(rig_settings, "outfits_global_subsurface")
                if rig_settings.outfits_enable_global_smoothcorrection:
                    col.prop(rig_settings, "outfits_global_smoothcorrection")
                if rig_settings.outfits_enable_global_shrinkwrap:
                    col.prop(rig_settings, "outfits_global_shrinkwrap")
                if rig_settings.outfits_enable_global_surfacedeform:
                    col.prop(rig_settings, "outfits_global_surfacedeform")
                if rig_settings.outfits_enable_global_mask:
                    col.prop(rig_settings, "outfits_global_mask")
                if rig_settings.outfits_enable_global_solidify:
                    col.prop(rig_settings, "outfits_global_solidify")
                if rig_settings.outfits_enable_global_triangulate:
                    col.prop(rig_settings, "outfits_global_triangulate")
                if rig_settings.outfits_enable_global_normalautosmooth:
                    col.prop(rig_settings, "outfits_global_normalautosmooth")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_Outfits)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Outfits)
