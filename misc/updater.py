import bpy
from bpy.props import *
from .. import bl_info


def mustardui_retrieve_remote_version():

    import requests

    v = [0, 0, 0, 0]
    b = [0, 0, 0]
    data = None

    # Import the data from the GitHub repository file
    try:
        response = requests.get("https://raw.githubusercontent.com/Mustard2/MustardUI/master/__init__.py")
        data = response.text
    except:
        return 1, v, b

    # Fetch version
    try:
        if '"version": (' in data and '"blender": (' in data:
            find = data.split('"version": (', 1)[1]
            v[0] = int(find.split(',')[0])
            v[1] = int(find.split(',')[1])
            v[2] = int(find.split(',')[2])
            v[3] = find.split(',')[3]
            v[3] = int(v[3].split(')')[0])

            find = data.split('"blender": (', 1)[1]
            b[0] = int(find.split(',')[0])
            b[1] = int(find.split(',')[1])
            b[2] = find.split(',')[2]
            b[2] = int(b[2].split(')')[0])

            return 0, v, b
    except:
        pass

    return 2, v, b


def mustardui_check_version():
    exit_code, v, b = mustardui_retrieve_remote_version()
    version = (v[0], v[1], v[2], v[3])
    if bl_info["version"] < version:
        print("MustardUI - An update is available.")
    else:
        print("MustardUI - No update available.")
    return bl_info["version"] < version


class MustardUI_Updater(bpy.types.Operator):
    """Check MustardUI version"""
    bl_idname = "mustardui.updater"
    bl_label = "Check Version"
    bl_options = {'UNDO'}

    v = [0, 0, 0, 0]
    b = [0, 0, 0, 0]

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):

        version = (self.v[0], self.v[1], self.v[2], self.v[3])
        blender = (self.b[0], self.b[1], self.b[2])

        if bl_info["version"] >= version:
            self.report({'INFO'}, "MustardUI: The current version is already up-to-date")
        else:
            if bpy.app.version >= blender:
                bpy.ops.mustardui.openlink(url="github.com/Mustard2/MustardUI/releases/latest")
            else:
                bpy.ops.mustardui.openlink(url="blender.org/download/")

        return {'FINISHED'}

    def invoke(self, context, event):

        exit_code, self.v, self.b = mustardui_retrieve_remote_version()

        if exit_code == 1:
            self.report({'ERROR'}, "MustardUI: Error while retrieving remote version. Check your connection")
            return {'FINISHED'}

        if exit_code == 2:
            self.report({'ERROR'}, "MustardUI: Can not find the version number of the remote repository")
            return {'FINISHED'}

        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):

        layout = self.layout

        version = (self.v[0], self.v[1], self.v[2], self.v[3])
        blender = (self.b[0], self.b[1], self.b[2])

        box = layout.box()

        if bl_info["version"] >= version:
            box.label(text="The current version seems up-to-date.", icon="INFO")
        else:
            if bpy.app.version >= blender:
                box.label(text="Update available!", icon="INFO")
            else:
                box.label(text="Update is available for a new Blender version!", icon="INFO")
                box.label(text="Update Blender before installing the new MustardUI.", icon="INFO")

        row = box.row()
        row.label(text="Current version: ", icon="RIGHTARROW_THIN")
        row.label(text=str(bl_info["version"][0]) + '.' + str(bl_info["version"][1]) + '.' + str(
            bl_info["version"][2]) + '.' + str(bl_info["version"][3]))
        row = box.row()
        row.label(text="Remote version: ", icon="WORLD")
        row.label(
            text=str(self.v[0]) + '.' + str(self.v[1]) + '.' + str(self.v[2]) + '.' + str(self.v[3]))

        if bl_info["version"] < version:
            if bpy.app.version >= blender:
                box = layout.box()
                box.label(text="Click 'OK' to open the latest release page.", icon="ERROR")
            else:
                row = box.row()
                row.label(text="Minimum Blender version required: ", icon="WORLD")
                row.label(
                    text=str(self.b[0]) + '.' + str(self.b[1]) + '.' + str(self.b[2]))

                box = layout.box()
                box.label(text="Click 'OK' to open the Blender download page.", icon="ERROR")


def register():
    bpy.utils.register_class(MustardUI_Updater)


def unregister():
    bpy.utils.unregister_class(MustardUI_Updater)
