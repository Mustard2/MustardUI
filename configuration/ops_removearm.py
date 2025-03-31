import bpy
from bpy.props import *
from ..model_selection.active_object import *


class MustardUI_RemoveArmature(bpy.types.Operator):
    """Delete dangling armature from the File"""
    bl_idname = "mustardui.remove_armature"
    bl_label = "Delete Armature"
    bl_options = {'UNDO'}

    armature: bpy.props.StringProperty(default="")

    @classmethod
    def poll(cls, context):

        res, arm = mustardui_active_object(context, config=0)
        return res if arm is not None else False

    def execute(self, context):

        settings = bpy.context.scene.MustardUI_Settings

        if self.armature == "" or not (self.armature in [x.name for x in bpy.data.armatures if x is not None]):
            self.report({'WARNING'}, f"MustardUI - Can not remove {self.armature}")
            return {'FINISHED'}

        bpy.data.armatures.remove(bpy.data.armatures[self.armature], do_unlink=True)

        settings.viewport_model_selection = True

        bpy.ops.outliner.orphans_purge()

        self.report({'INFO'}, f"MustardUI - Removed armature {self.armature}. Switched to Viewport Model Selection")

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_RemoveArmature)


def unregister():
    bpy.utils.unregister_class(MustardUI_RemoveArmature)
