import bpy
from bpy.props import *
from ..model_selection.active_object import *


def check_old_UI():
    # Check presence of old UI scripts
    for file in bpy.data.texts:
        if "mustard_ui.py" in file.name:
            return True
    return False


class MustardUI_Warnings_FixOldUI(bpy.types.Operator):
    """Remove old and unused old UI. Remember to save and restart Blender after using this tool"""
    bl_idname = "mustardui.warnings_fix_old_ui"
    bl_label = "Remove Outdated UI scripts"
    bl_options = {'UNDO'}

    enable: BoolProperty(default=True)

    @classmethod
    def poll(cls, context):
        return check_old_UI()

    def execute(self, context):

        # Number of UI scripts removed
        nc = 0

        # Number of errors
        ne = 0

        for file in bpy.data.texts:
            if "mustard_ui.py" in file.name:
                try:
                    bpy.data.texts.remove(file)
                except:
                    ne += 1
                nc += 1

        if ne > 0:
            self.report({'ERROR'}, 'MustardUI - An error occurred while removing '
                        + str(ne) + ' scripts (' + str(nc) + ' removed).')

        self.report({'INFO'}, 'MustardUI - Removed ' + str(nc) + ' scripts. Restart Blender!')

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_Warnings_FixOldUI)


def unregister():
    bpy.utils.unregister_class(MustardUI_Warnings_FixOldUI)
