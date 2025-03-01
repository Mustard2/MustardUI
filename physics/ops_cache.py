import bpy
from ..model_selection.active_object import *


class MustardUI_Physics_SyncFrames(bpy.types.Operator):
    """Synchronise the physics bake frames with the scene ones"""
    bl_idname = "mustardui.physics_bake_syncframes"
    bl_label = "Synchornise frames with scene"

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        return res

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=0)
        physics_settings = arm.MustardUI_PhysicsSettings

        physics_settings.frame_start = context.scene.frame_start
        physics_settings.frame_end = context.scene.frame_end

        return {'FINISHED'}


class MustardUI_Physics_BakeAll(bpy.types.Operator):
    """Bake All Physics"""
    bl_idname = "mustardui.physics_bake_all"
    bl_label = "Bake All"

    bake: bpy.props.BoolProperty()

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        return res

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=0)
        physics_settings = arm.MustardUI_PhysicsSettings

        physics_settings.frame_start = physics_settings.frame_start
        physics_settings.frame_end = physics_settings.frame_end

        bpy.ops.ptcache.bake_all('INVOKE_DEFAULT', bake=self.bake)

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_Physics_SyncFrames)
    bpy.utils.register_class(MustardUI_Physics_BakeAll)


def unregister():
    bpy.utils.unregister_class(MustardUI_Physics_BakeAll)
    bpy.utils.unregister_class(MustardUI_Physics_SyncFrames)
