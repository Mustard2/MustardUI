import bpy
from . import MainPanel
from ..model_selection.active_object import *
from ..settings.rig import *
from .misc import *


class PANEL_PT_MustardUI_Outfits(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Outfits"
    bl_label = "Outfits"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):

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

        else:

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

                items = bpy.data.collections[rig_settings.outfits_list].all_objects if rig_settings.outfit_config_subcollections else bpy.data.collections[rig_settings.outfits_list].objects

                if len(items) > 0:

                    # Global outfit custom properties
                    if rig_settings.outfit_custom_properties_name_order:
                        custom_properties = sorted([x for x in arm.MustardUI_CustomPropertiesOutfit if
                                                    x.outfit == bpy.data.collections[
                                                        rig_settings.outfits_list] and x.outfit_piece == None and not x.hidden and (
                                                        not x.advanced if not settings.advanced else True)],
                                                   key=lambda x: x.name)
                    else:
                        custom_properties = [x for x in arm.MustardUI_CustomPropertiesOutfit if
                                             x.outfit == bpy.data.collections[
                                                 rig_settings.outfits_list] and x.outfit_piece == None and not x.hidden and (
                                                 not x.advanced if not settings.advanced else True)]

                    if len(custom_properties) > 0 and rig_settings.outfit_additional_options:
                        row.prop(rig_settings, "outfit_global_custom_properties_collapse", text="", toggle=True,
                                 icon="PREFERENCES")
                        if rig_settings.outfit_global_custom_properties_collapse:
                            mustardui_custom_properties_print(arm, settings, rig_settings, custom_properties, box,
                                                              rig_settings.outfit_custom_properties_icons)

                    for obj in sorted(items, key=lambda x: x.name):

                        col = box.column(align=True)
                        row = col.row(align=True)

                        if rig_settings.model_MustardUI_naming_convention:
                            row.operator("mustardui.object_visibility",
                                         text=obj.name[len(rig_settings.outfits_list + ' - '):],
                                         icon='OUTLINER_OB_' + obj.type, depress=not obj.hide_viewport).obj = obj.name
                        else:
                            row.operator("mustardui.object_visibility", text=obj.name, icon='OUTLINER_OB_' + obj.type,
                                         depress=not obj.hide_viewport).obj = obj.name

                        # Outfit custom properties
                        if rig_settings.outfit_custom_properties_name_order:
                            custom_properties_obj = sorted([x for x in arm.MustardUI_CustomPropertiesOutfit if
                                                            x.outfit == bpy.data.collections[
                                                                rig_settings.outfits_list] and x.outfit_piece == obj and not x.hidden],
                                                           key=lambda x: x.name)
                        else:
                            custom_properties_obj = [x for x in arm.MustardUI_CustomPropertiesOutfit if
                                                     x.outfit == bpy.data.collections[
                                                         rig_settings.outfits_list] and x.outfit_piece == obj and not x.hidden]

                        if len(custom_properties_obj) > 0 and rig_settings.outfit_additional_options:
                            row.prop(obj, "MustardUI_additional_options_show", toggle=True, icon="PREFERENCES")
                            if obj.MustardUI_additional_options_show:
                                mustardui_custom_properties_print(arm, settings, rig_settings, custom_properties_obj,
                                                                  col, rig_settings.outfit_custom_properties_icons)

                        row.prop(obj, "MustardUI_outfit_lock", toggle=True,
                                 icon='LOCKED' if obj.MustardUI_outfit_lock else 'UNLOCKED')

                else:
                    box.label(text="This Collection seems empty", icon="ERROR")

            # Locked objects list
            locked_objects = []
            for coll in [x for x in rig_settings.outfits_collections if x.collection != None]:
                items = coll.collection.all_objects if rig_settings.outfit_config_subcollections else coll.collection.objects
                for obj in items:
                    if obj.MustardUI_outfit_lock:
                        locked_objects.append(obj)
            if len(locked_objects) > 0:
                box.separator()
                box.label(text="Locked objects:", icon="LOCKED")
                for obj in locked_objects:

                    col = box.column(align=True)
                    row = col.row(align=True)

                    if rig_settings.model_MustardUI_naming_convention:
                        row.operator("mustardui.object_visibility", text=obj.name[len(rig_settings.model_name):],
                                     icon='OUTLINER_OB_' + obj.type, depress=not obj.hide_viewport).obj = obj.name
                    else:
                        row.operator("mustardui.object_visibility", text=obj.name, icon='OUTLINER_OB_' + obj.type,
                                     depress=not obj.hide_viewport).obj = obj.name

                    if rig_settings.outfit_custom_properties_name_order:
                        custom_properties_obj = sorted([x for x in arm.MustardUI_CustomPropertiesOutfit if
                                                        x.outfit_piece == obj and not x.hidden and (
                                                            not x.advanced if not settings.advanced else True)],
                                                       key=lambda x: x.name)
                    else:
                        custom_properties_obj = [x for x in arm.MustardUI_CustomPropertiesOutfit if
                                                 x.outfit_piece == obj and not x.hidden and (
                                                     not x.advanced if not settings.advanced else True)]
                    if len(custom_properties_obj) > 0 and rig_settings.outfit_additional_options:
                        row.prop(bpy.data.objects[obj.name], "MustardUI_additional_options_show_lock", toggle=True,
                                 icon="PREFERENCES")
                        if obj.MustardUI_additional_options_show_lock:
                            mustardui_custom_properties_print(arm, settings, rig_settings, custom_properties_obj, col,
                                                              rig_settings.outfit_custom_properties_icons)

                    row.prop(obj, "MustardUI_outfit_lock", toggle=True,
                             icon='LOCKED' if obj.MustardUI_outfit_lock else 'UNLOCKED')

            # Outfit global properties
            if rig_settings.outfits_enable_global_subsurface or rig_settings.outfits_enable_global_smoothcorrection or rig_settings.outfits_enable_global_shrinkwrap or rig_settings.outfits_enable_global_mask or rig_settings.outfits_enable_global_solidify or rig_settings.outfits_enable_global_triangulate or rig_settings.outfits_enable_global_normalautosmooth:

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
                if rig_settings.outfits_enable_global_mask:
                    col.prop(rig_settings, "outfits_global_mask")
                if rig_settings.outfits_enable_global_solidify:
                    col.prop(rig_settings, "outfits_global_solidify")
                if rig_settings.outfits_enable_global_triangulate:
                    col.prop(rig_settings, "outfits_global_triangulate")
                if rig_settings.outfits_enable_global_normalautosmooth:
                    col.prop(rig_settings, "outfits_global_normalautosmooth")

        # Extras
        if rig_settings.extras_collection is not None:

            eitems = (
                rig_settings.extras_collection.all_objects if rig_settings.outfit_config_subcollections else rig_settings.extras_collection.objects)

            if len(eitems) > 0:

                box = layout.box()

                if rig_settings.extras_collapse_enable:
                    row = box.row(align=False)
                    row.prop(rig_settings, "extras_collapse",
                             icon="TRIA_DOWN" if not rig_settings.extras_collapse else "TRIA_RIGHT", icon_only=True,
                             emboss=False)
                    row.label(text="Extras")
                else:
                    box.label(text="Extras", icon="PLUS")

                if not rig_settings.extras_collapse or not rig_settings.extras_collapse_enable:
                    # Global outfit custom properties
                    for obj in sorted(eitems, key=lambda x: x.name):

                        col = box.column(align=True)
                        row = col.row(align=True)

                        if rig_settings.model_MustardUI_naming_convention:
                            row.operator("mustardui.object_visibility",
                                         text=obj.name[len(rig_settings.extras_collection.name + ' - '):],
                                         icon='OUTLINER_OB_' + obj.type, depress=not obj.hide_viewport).obj = obj.name
                        else:
                            row.operator("mustardui.object_visibility", text=obj.name, icon='OUTLINER_OB_' + obj.type,
                                         depress=not obj.hide_viewport).obj = obj.name
                        if rig_settings.outfit_custom_properties_name_order:
                            custom_properties_obj = sorted([x for x in arm.MustardUI_CustomPropertiesOutfit if
                                                            x.outfit == rig_settings.extras_collection and x.outfit_piece == obj and not x.hidden],
                                                           key=lambda x: x.name)
                        else:
                            custom_properties_obj = [x for x in arm.MustardUI_CustomPropertiesOutfit if
                                                     x.outfit == rig_settings.extras_collection and x.outfit_piece == obj and not x.hidden]
                        if len(custom_properties_obj) > 0 and rig_settings.outfit_additional_options:
                            row.prop(obj, "MustardUI_additional_options_show", toggle=True, icon="PREFERENCES")
                            if obj.MustardUI_additional_options_show:
                                mustardui_custom_properties_print(arm, settings, rig_settings, custom_properties_obj,
                                                                  col, rig_settings.outfit_custom_properties_icons)


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_Outfits)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Outfits)
