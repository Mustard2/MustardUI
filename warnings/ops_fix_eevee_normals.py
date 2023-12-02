import bpy
from bpy.props import *
from ..model_selection.active_object import *


def check_eevee_normals(scene, settings):
    return scene.render.engine == "CYCLES" and settings.material_normal_nodes


class MustardUI_Warnings_FixEeveeNormals(bpy.types.Operator):
    """Eevee Optimized Normals can lead to graphic artifacts in Cycles, and should be disabled"""
    bl_idname = "mustardui.warnings_fix_eevee_normals"
    bl_label = "Turn off Eevee Optimized Normals"
    bl_options = {'UNDO'}

    enable: BoolProperty(default=True)

    @classmethod
    def poll(cls, context):
        settings = bpy.context.scene.MustardUI_Settings
        return check_eevee_normals(context.scene, settings)

    def execute(self, context):
        settings = context.scene.MustardUI_Settings

        settings.material_normal_nodes = False

        self.report({'INFO'}, 'MustardUI - Disabled Eevee Optimized Normals.')

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_Warnings_FixEeveeNormals)


def unregister():
    bpy.utils.unregister_class(MustardUI_Warnings_FixEeveeNormals)
