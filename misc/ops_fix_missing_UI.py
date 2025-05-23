import bpy


class MustardUI_FixMissingUI(bpy.types.Operator):
    """Fix Missing UI in case Viewport Model selection was off and the Armature selection has been corrupted"""
    bl_idname = "mustardui.fix_missing_ui"
    bl_label = "Fix Missing UI"
    bl_options = {'UNDO'}

    def execute(self, context):

        settings = context.scene.MustardUI_Settings
        settings.viewport_model_selection = True

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_FixMissingUI)


def unregister():
    bpy.utils.unregister_class(MustardUI_FixMissingUI)
