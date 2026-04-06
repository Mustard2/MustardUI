import bpy
from bpy.props import IntProperty

from ..model_selection.active_object import mustardui_active_object
from ..tools.simplify import simplify_hair


class MustardUI_Hair_SwitchGlobal(bpy.types.Operator):
    """Enable/disable all modifiers/model_selection that might impact on viewport performance"""  # noqa: E501

    bl_idname = "mustardui.hair_switchglobal"
    bl_label = "Hair Property Switch"

    enable: IntProperty(default=False)

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        return res if arm is not None else False

    def execute(self, context):
        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings

        if rig_settings.hair_enable_global_subsurface:
            rig_settings.hair_global_subsurface = self.enable
        if rig_settings.hair_enable_global_smoothcorrection:
            rig_settings.hair_global_smoothcorrection = self.enable
        if rig_settings.hair_enable_global_solidify:
            rig_settings.hair_global_solidify = self.enable
        if rig_settings.hair_enable_global_particles:
            rig_settings.hair_global_particles = self.enable

        return {"FINISHED"}


class MustardUI_Hair_DisableViewport(bpy.types.Operator):
    """Enable/disable Outfits to increase Viewport performance"""

    bl_idname = "mustardui.hair_disable_viewport"
    bl_label = "hair Disable Viewport"

    enable: IntProperty(default=False)

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        return res if arm is not None else False

    def execute(self, context):
        poll, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings

        if self.enable:
            if "mustardui_hair_show" not in arm:
                hair_global_subsurface = rig_settings.hair_global_subsurface
                hair_global_smoothcorrection = rig_settings.hair_global_smoothcorrection
                hair_global_solidify = rig_settings.hair_global_solidify
                hair_global_particles = rig_settings.hair_global_particles
                arm["mustardui_hair_show"] = {
                    "hair_global_subsurface": hair_global_subsurface,
                    "hair_global_smoothcorrection": hair_global_smoothcorrection,
                    "hair_global_solidify": hair_global_solidify,
                    "hair_global_particles": hair_global_particles,
                }

        simplify_hair(rig_settings, self.enable)

        if not self.enable:
            if "mustardui_hair_show" in arm:
                for key, value in arm["mustardui_hair_show"].items():
                    setattr(rig_settings, key, value)
                del arm["mustardui_hair_show"]

        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_Hair_SwitchGlobal)
    bpy.utils.register_class(MustardUI_Hair_DisableViewport)


def unregister():
    bpy.utils.unregister_class(MustardUI_Hair_DisableViewport)
    bpy.utils.unregister_class(MustardUI_Hair_SwitchGlobal)
