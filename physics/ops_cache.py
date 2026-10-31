import bpy

from ..misc.geometry_nodes import simulation_bakes
from ..model_selection.active_object import (
    ModelMode,
    active_object_operator_poll,
    mustardui_active_object,
)
from .settings import physics_objects


class MustardUI_Physics_SyncFrames(bpy.types.Operator):
    """Synchronize the physics bake frames with the scene ones"""

    bl_idname = "mustardui.physics_bake_syncframes"
    bl_label = "Synchronise frames with scene"

    @classmethod
    def poll(cls, context):
        return active_object_operator_poll(context, config=ModelMode.USER)

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=ModelMode.USER)
        physics_settings = arm.MustardUI_PhysicsSettings

        physics_settings.frame_start = context.scene.frame_start
        physics_settings.frame_end = context.scene.frame_end

        return {"FINISHED"}


class MustardUI_Physics_BakeAll(bpy.types.Operator):
    """Bake All Physics"""

    bl_idname = "mustardui.physics_bake_all"
    bl_label = "Bake All"

    bake: bpy.props.BoolProperty()

    @classmethod
    def poll(cls, context):
        return active_object_operator_poll(context, config=ModelMode.USER)

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=ModelMode.USER)
        physics_settings = arm.MustardUI_PhysicsSettings

        physics_settings.frame_start = physics_settings.frame_start
        physics_settings.frame_end = physics_settings.frame_end

        # The Geometry Nodes simulations of the enabled physics, the other ones are Point Caches
        if self.bake:
            for obj in physics_objects(physics_settings):
                if obj.hide_viewport or obj.name not in context.view_layer.objects:
                    continue
                for modifier, bake in simulation_bakes(obj):
                    if modifier.show_viewport:
                        bpy.ops.object.geometry_node_bake_single(
                            session_uid=obj.session_uid,
                            modifier_name=modifier.name,
                            bake_id=bake.bake_id,
                        )

        bpy.ops.ptcache.bake_all("INVOKE_DEFAULT", bake=self.bake)

        return {"FINISHED"}


class MustardUI_Physics_BakeDeleteAll(bpy.types.Operator):
    """Delete the bakes of all the physics, Geometry Nodes simulations included"""

    bl_idname = "mustardui.physics_bake_delete_all"
    bl_label = "Delete All Bake"

    @classmethod
    def poll(cls, context):
        return active_object_operator_poll(context, config=ModelMode.USER)

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=ModelMode.USER)

        for obj in physics_objects(arm.MustardUI_PhysicsSettings):
            for modifier, bake in simulation_bakes(obj):
                bpy.ops.object.geometry_node_bake_delete_single(
                    session_uid=obj.session_uid, modifier_name=modifier.name, bake_id=bake.bake_id
                )

        bpy.ops.ptcache.free_bake_all()

        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_Physics_SyncFrames)
    bpy.utils.register_class(MustardUI_Physics_BakeAll)
    bpy.utils.register_class(MustardUI_Physics_BakeDeleteAll)


def unregister():
    bpy.utils.unregister_class(MustardUI_Physics_BakeDeleteAll)
    bpy.utils.unregister_class(MustardUI_Physics_BakeAll)
    bpy.utils.unregister_class(MustardUI_Physics_SyncFrames)
