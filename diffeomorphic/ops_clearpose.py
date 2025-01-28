import bpy
from ..model_selection.active_object import *
from mathutils import Vector, Matrix


class MustardUI_DazMorphs_ClearPose(bpy.types.Operator):
    """Revert the position of all the bones to the Rest position"""
    bl_idname = "mustardui.dazmorphs_clearpose"
    bl_label = "Clear Pose"
    bl_options = {'REGISTER', 'UNDO'}

    def setWorldMatrix(self, ob, wmat):
        Zero = Vector((0, 0, 0))
        One = Vector((1, 1, 1))
        if ob.parent:
            if ob.parent_type in ['OBJECT', 'VERTEX', 'VERTEX_3']:
                ob.matrix_parent_inverse = ob.parent.matrix_world.inverted()
            elif ob.parent_type == 'BONE':
                pb = ob.parent.pose.bones[ob.parent_bone]
                ob.matrix_parent_inverse = pb.matrix.inverted()
        ob.matrix_world = wmat
        if Vector(ob.location).length < 1e-6:
            ob.location = Zero
        if Vector(ob.rotation_euler).length < 1e-6:
            ob.rotation_euler = Zero
        if (Vector(ob.scale) - One).length < 1e-6:
            ob.scale = One

    @classmethod
    def poll(cls, context):

        res, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings
        return res and rig_settings.diffeomorphic_support

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings

        warnings = 0

        try:
            unit = Matrix()
            self.setWorldMatrix(rig_settings.model_armature_object, unit)
            for pb in rig_settings.model_armature_object.pose.bones:
                pb.matrix_basis = unit
        except:
            warnings = warnings + 1

        if warnings < 1:
            self.report({'INFO'}, 'MustardUI - Pose cleared successfully')
        else:
            self.report({'ERROR'}, 'MustardUI - An error occurred while clearing the pose')

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_DazMorphs_ClearPose)


def unregister():
    bpy.utils.unregister_class(MustardUI_DazMorphs_ClearPose)
