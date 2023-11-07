import bpy
from bpy.props import *
from ..model_selection.active_object import *


class MustardUI_GlobalOutfitPropSwitch(bpy.types.Operator):
    """Enable/disable all modifiers/model_selection that might impact on viewport performance"""
    bl_idname = "mustardui.switchglobal_outfits"
    bl_label = "Outfits Property Switch"

    enable: IntProperty(default=False)

    def execute(self, context):
        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings

        rig_settings.outfits_global_subsurface = self.enable
        rig_settings.outfits_global_smoothcorrection = self.enable
        rig_settings.outfits_global_shrinkwrap = self.enable
        rig_settings.outfits_global_mask = self.enable
        rig_settings.outfits_global_solidify = self.enable
        rig_settings.outfits_global_triangulate = self.enable
        rig_settings.outfits_global_normalautosmooth = self.enable

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_GlobalOutfitPropSwitch)


def unregister():
    bpy.utils.unregister_class(MustardUI_GlobalOutfitPropSwitch)
