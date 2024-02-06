import bpy
from bpy.props import *

from ..model_selection.active_object import *


# Check presence of old UI scripts
def check_old_UI():
    import bpy

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

    def invoke(self, context, event):

        return context.window_manager.invoke_props_dialog(self, width=450)

    def draw(self, context):

        layout = self.layout
        box = layout.box()

        box.label(text="This script removes all old MustardUI script", icon="INFO")
        box.label(text="Ignore the errors, and save and restart Blender after using this!", icon="ERROR")

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

        self.report({'INFO'}, 'MustardUI - Removed ' + str(nc) + ' scripts. Save and restart Blender!')

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_Warnings_FixOldUI)


def unregister():
    bpy.utils.unregister_class(MustardUI_Warnings_FixOldUI)
