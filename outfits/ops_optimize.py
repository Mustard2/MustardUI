import bpy
from bpy.props import *
from ..misc.set_bool import set_bool
from ..model_selection.active_object import *


class MustardUI_Outfits_SwitchGlobal(bpy.types.Operator):
    """Enable/disable all modifiers/model_selection that might impact on viewport performance"""
    bl_idname = "mustardui.outfits_switchglobal"
    bl_label = "Outfits Property Switch"

    enable: IntProperty(default=False)

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        return res if arm is not None else False

    def execute(self, context):
        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings

        rig_settings.outfits_global_subsurface = self.enable
        rig_settings.outfits_global_smoothcorrection = self.enable
        rig_settings.outfits_global_shrinkwrap = self.enable
        rig_settings.outfits_global_mask = self.enable
        rig_settings.outfits_global_solidify = self.enable
        rig_settings.outfits_global_triangulate = self.enable

        return {'FINISHED'}


class MustardUI_Outfit_DisableViewport(bpy.types.Operator):
    """Enable/disable Outfits to increase Viewport performance"""
    bl_idname = "mustardui.outfit_disable_viewport"
    bl_label = "Outfits Disable Viewport"

    enable: IntProperty(default=False)

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        return res if arm is not None else False

    def execute(self, context):
        poll, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings

        if self.enable:
            for coll in [x.collection for x in rig_settings.outfits_collections if x.collection is not None]:
                set_bool(coll, "hide_viewport", self.enable)
        else:
            current_outfit = rig_settings.outfits_list
            rig_settings.outfits_list = current_outfit

        extras = rig_settings.extras_collection
        if rig_settings.extras_collection is not None:
            if self.enable:
                set_bool(extras, "hide_viewport", True)
            else:
                items = extras.all_objects if rig_settings.outfit_config_subcollections else extras.objects
                hidden = all(x.hide_render for x in items)
                set_bool(extras, "hide_viewport", hidden)

        # Save Global settings if needed
        if self.enable:
            if "mustardui_outfit_show" not in arm:
                arm["mustardui_outfit_show"] = {
                    "outfits_global_subsurface": rig_settings.outfits_global_subsurface,
                    "outfits_global_mask": rig_settings.outfits_global_mask,
                    "outfits_global_smoothcorrection": rig_settings.outfits_global_smoothcorrection,
                    "outfits_global_shrinkwrap": rig_settings.outfits_global_shrinkwrap,
                    "outfits_global_solidify": rig_settings.outfits_global_solidify,
                    "outfits_global_triangulate": rig_settings.outfits_global_triangulate
                }
            if len(rig_settings.outfits_list) > 1:
                if rig_settings.outfits_enable_global_subsurface:
                    rig_settings.outfits_global_subsurface = False
                if rig_settings.outfits_enable_global_mask:
                    rig_settings.outfits_global_mask = False
                if rig_settings.outfits_enable_global_smoothcorrection:
                    rig_settings.outfits_global_smoothcorrection = False
                if rig_settings.outfits_enable_global_shrinkwrap:
                    rig_settings.outfits_global_shrinkwrap = False
                if rig_settings.outfits_enable_global_solidify:
                    rig_settings.outfits_global_solidify = False
                if rig_settings.outfits_enable_global_triangulate:
                    rig_settings.outfits_global_triangulate = False
        else:
            # When this is turned off, restore saved state
            if "mustardui_outfit_show" in arm:
                for key, value in arm["mustardui_outfit_show"].items():
                    setattr(rig_settings, key, value)
                del arm["mustardui_outfit_show"]

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_Outfits_SwitchGlobal)
    bpy.utils.register_class(MustardUI_Outfit_DisableViewport)


def unregister():
    bpy.utils.unregister_class(MustardUI_Outfit_DisableViewport)
    bpy.utils.unregister_class(MustardUI_Outfits_SwitchGlobal)
