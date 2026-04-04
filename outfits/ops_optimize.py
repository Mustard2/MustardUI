import bpy
from bpy.props import IntProperty

from ..model_selection.active_object import mustardui_active_object
from ..tools.simplify import simplify_extras, simplify_outfits


class MustardUI_Outfits_SwitchGlobal(bpy.types.Operator):
    """Enable/disable all modifiers/model_selection that might impact on viewport performance"""  # noqa: E501

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

        if rig_settings.outfits_enable_global_subsurface:
            rig_settings.outfits_global_subsurface = self.enable
        if rig_settings.outfits_enable_global_mask:
            rig_settings.outfits_global_mask = self.enable
        if rig_settings.outfits_enable_global_smoothcorrection:
            rig_settings.outfits_global_smoothcorrection = self.enable
        if rig_settings.outfits_enable_global_shrinkwrap:
            rig_settings.outfits_global_shrinkwrap = self.enable
        if rig_settings.outfits_enable_global_solidify:
            rig_settings.outfits_global_solidify = self.enable
        if rig_settings.outfits_enable_global_triangulate:
            rig_settings.outfits_global_triangulate = self.enable

        return {"FINISHED"}


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
            if "mustardui_outfit_show" not in arm:
                outfits_global_subsurface = rig_settings.outfits_global_subsurface
                outfits_global_mask = rig_settings.outfits_global_mask
                outfits_global_smoothcorrection = (
                    rig_settings.outfits_global_smoothcorrection
                )
                outfits_global_shrinkwrap = rig_settings.outfits_global_shrinkwrap
                outfits_global_solidify = rig_settings.outfits_global_solidify
                outfits_global_triangulate = rig_settings.outfits_global_triangulate
                outfits_list = rig_settings.outfits_list
                arm["mustardui_outfit_show"] = {
                    "outfits_global_subsurface": outfits_global_subsurface,
                    "outfits_global_mask": outfits_global_mask,
                    "outfits_global_smoothcorrection": outfits_global_smoothcorrection,
                    "outfits_global_shrinkwrap": outfits_global_shrinkwrap,
                    "outfits_global_solidify": outfits_global_solidify,
                    "outfits_global_triangulate": outfits_global_triangulate,
                    "outfits_list": outfits_list,
                }

        simplify_outfits(rig_settings, self.enable)
        simplify_extras(rig_settings, self.enable)

        if not self.enable:
            if "mustardui_outfit_show" in arm:
                for key, value in arm["mustardui_outfit_show"].items():
                    setattr(rig_settings, key, value)
                del arm["mustardui_outfit_show"]

        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_Outfits_SwitchGlobal)
    bpy.utils.register_class(MustardUI_Outfit_DisableViewport)


def unregister():
    bpy.utils.unregister_class(MustardUI_Outfit_DisableViewport)
    bpy.utils.unregister_class(MustardUI_Outfits_SwitchGlobal)
