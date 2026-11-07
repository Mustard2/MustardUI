import json
import os
import subprocess
import tempfile

import bpy
from bpy_extras.io_utils import ExportHelper

from ...model_selection.active_object import ModelMode, mustardui_active_object

WORKER = os.path.join(os.path.dirname(__file__), "worker.py")


def mhx_rig(context):
    """The MHX armature object of the model, or None."""
    _, arm = mustardui_active_object(context, config=ModelMode.ANY)
    if arm is None:
        return None
    rig = next((o for o in bpy.data.objects if o.data is arm), None)
    return rig if rig is not None and rig.get("MhxRig") else None


class ExportToUnreal(ExportHelper):
    """Runs the export in a background Blender, working on a copy of the file."""

    bl_options = {"REGISTER"}
    filename_ext = ".fbx"
    filter_glob: bpy.props.StringProperty(default="*.fbx", options={"HIDDEN"})

    @classmethod
    def poll(cls, context):
        if mhx_rig(context) is None:
            cls.poll_message_set("Only available for MHX armatures")
            return False
        return True

    def settings(self):
        return {}

    def execute(self, context):
        self.folder = tempfile.TemporaryDirectory(prefix="mustardui_unreal_")
        blend = os.path.join(self.folder.name, "scene.blend")
        bpy.ops.wm.save_as_mainfile(filepath=blend, copy=True, check_existing=False)
        self.result = os.path.join(self.folder.name, "result.json")
        path = os.path.join(self.folder.name, "settings.json")
        with open(path, "w") as file:
            json.dump(
                {
                    "rig": mhx_rig(context).name,
                    "filepath": bpy.path.abspath(self.filepath),
                    "result": self.result,
                    **self.settings(),
                },
                file,
            )
        self.log = open(os.path.join(self.folder.name, "log.txt"), "w+")
        self.process = subprocess.Popen(
            [
                bpy.app.binary_path,
                "--background",
                blend,
                "--factory-startup",
                "--disable-autoexec",
                "--python-exit-code",
                "1",
                "--python",
                WORKER,
                "--",
                path,
            ],
            stdout=self.log,
            stderr=subprocess.STDOUT,
        )
        if bpy.app.background:
            self.process.wait()
            return self.finish(context)
        self.timer = context.window_manager.event_timer_add(0.5, window=context.window)
        context.window_manager.modal_handler_add(self)
        context.workspace.status_text_set(
            "MustardUI - Exporting to Unreal in the background, Esc to cancel"
        )
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if event.type == "ESC" and event.value == "PRESS":
            self.process.kill()
            self.process.wait()
            self.report({"WARNING"}, "MustardUI - Export to Unreal cancelled")
            self.cleanup(context)
            return {"CANCELLED"}
        if event.type != "TIMER" or self.process.poll() is None:
            return {"PASS_THROUGH"}
        self.cleanup(context, keep_folder=True)
        return self.finish(context)

    def cleanup(self, context, keep_folder=False):
        context.window_manager.event_timer_remove(self.timer)
        context.workspace.status_text_set(None)
        if not keep_folder:
            self.log.close()
            self.folder.cleanup()

    def finish(self, context):
        self.log.seek(0)
        output = self.log.read()
        self.log.close()
        info = json.load(open(self.result)) if os.path.exists(self.result) else {}
        self.folder.cleanup()
        if not info or "error" in info:
            print(output)
            reason = info.get("error", "see the console")
            self.report({"ERROR"}, f"MustardUI - Export to Unreal failed: {reason}")
            return {"CANCELLED"}
        details = ", ".join(f"{value} {key}" for key, value in info.items())
        self.report({"INFO"}, f"MustardUI - Exported {os.path.basename(self.filepath)} ({details})")
        return {"FINISHED"}


class MustardUI_UnrealTools_ExportCharacter(ExportToUnreal, bpy.types.Operator):
    """Export the visible meshes of the MHX model and a skeleton with Unreal bone names.
    Facial controls are baked to morph targets. The open file is not changed"""

    bl_idname = "mustardui.unreal_tools_export_character"
    bl_label = "Export Character"

    def settings(self):
        return {"mode": "CHARACTER"}


def action_items(self, context):
    # Blender needs the strings of the enum to stay referenced
    action_items.items = [(a.name, a.name, "") for a in bpy.data.actions]
    return action_items.items


class MustardUI_UnrealTools_ExportAnimation(ExportToUnreal, bpy.types.Operator):
    """Export an action of the MHX model for the skeleton of Export Character.
    The open file is not changed"""

    bl_idname = "mustardui.unreal_tools_export_animation"
    bl_label = "Export Animation"

    action: bpy.props.EnumProperty(name="Action", items=action_items)
    frame_start: bpy.props.IntProperty(
        name="First Frame", default=0, min=0, description="0 starts where the action starts"
    )
    frame_end: bpy.props.IntProperty(
        name="Last Frame", default=0, min=0, description="0 ends where the action ends"
    )
    height_offset: bpy.props.FloatProperty(
        name="Height Offset",
        default=0.0,
        subtype="DISTANCE",
        unit="NONE",
        description="Centimeters added to the body height, if the feet hover or sink",
    )

    @classmethod
    def poll(cls, context):
        if not super().poll(context):
            return False
        if not bpy.data.actions:
            cls.poll_message_set("The file has no actions")
            return False
        return True

    def execute(self, context):
        # Actions without users would be left out of the copy of the file
        action = bpy.data.actions[self.action]
        fake_user = action.use_fake_user
        action.use_fake_user = True
        result = super().execute(context)
        action.use_fake_user = fake_user
        return result

    def settings(self):
        return {
            "mode": "ANIMATION",
            "action": self.action,
            "frame_start": self.frame_start,
            "frame_end": self.frame_end,
            "height_offset": self.height_offset,
        }

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.prop(self, "action")
        layout.prop(self, "frame_start")
        layout.prop(self, "frame_end")
        layout.prop(self, "height_offset")


def register():
    bpy.utils.register_class(MustardUI_UnrealTools_ExportCharacter)
    bpy.utils.register_class(MustardUI_UnrealTools_ExportAnimation)


def unregister():
    bpy.utils.unregister_class(MustardUI_UnrealTools_ExportAnimation)
    bpy.utils.unregister_class(MustardUI_UnrealTools_ExportCharacter)
