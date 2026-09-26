import time

import bpy
import numpy as np

from ..misc.mesh_deform import write_vertex_group

# Running preview session, only one at a time
PREVIEW_SESSION = None


def preview_running():
    return PREVIEW_SESSION is not None


def preview_session(tool):
    session = PREVIEW_SESSION
    return session if session is not None and session.tool == tool else None


def preview_settings_update(self, context):
    if PREVIEW_SESSION is not None:
        PREVIEW_SESSION.dirty = True


def write_shape_key(obj, name, co):
    mesh = obj.data
    if mesh.shape_keys is None:
        obj.shape_key_add(name="Basis", from_mix=False)
    sk = mesh.shape_keys.key_blocks.get(name)
    if sk is None:
        sk = obj.shape_key_add(name=name, from_mix=False)
    sk.data.foreach_set("co", co.ravel())
    sk.value = 1.0
    mesh.update()
    return sk


def redraw_view3d(context):
    if context.window is None:
        return
    for area in context.window.screen.areas:
        if area.type == "VIEW_3D":
            area.tag_redraw()


class ShapeKeyPreviewSession:
    """State of the running preview"""

    def __init__(self, tool, obj, key_name, solver, settings):
        self.tool = tool
        self.obj = obj
        self.key_name = key_name
        self.solver = solver
        self.settings = settings
        self.dirty = True
        self.finish = ""
        self.info = ""
        self.count = 0

        # Backup to restore on cancel
        sks = obj.data.shape_keys
        self.had_shape_keys = sks is not None
        self.backup = None
        sk = sks.key_blocks.get(key_name) if sks is not None else None
        if sk is not None:
            co = np.empty(len(sk.data) * 3, dtype=np.float32)
            sk.data.foreach_get("co", co)
            self.backup = (co, sk.value)

    def restore(self):
        obj = self.obj
        sks = obj.data.shape_keys
        sk = sks.key_blocks.get(self.key_name) if sks is not None else None
        if self.backup is not None and sk is not None:
            sk.data.foreach_set("co", self.backup[0])
            sk.value = self.backup[1]
        elif sk is not None:
            if self.had_shape_keys:
                obj.shape_key_remove(sk)
            else:
                obj.shape_key_clear()
        obj.data.update()


class ShapeKeyPreviewOperator:
    """Operator mixin to create a Shape Key with a live preview.
    Subclasses define preview_tool, preview_verb and preview_settings(context)"""

    preview_tool = ""
    preview_verb = ""

    def preview_start(self, context, obj, key_name, solver):
        global PREVIEW_SESSION
        PREVIEW_SESSION = ShapeKeyPreviewSession(
            self.preview_tool, obj, key_name, solver, self.preview_settings(context)
        )
        self.preview_update(context)

        wm = context.window_manager
        self._timer = wm.event_timer_add(0.05, window=context.window)
        wm.modal_handler_add(self)
        context.workspace.status_text_set(
            f"{self.bl_label}: change the settings in Creator Tools > Mesh, Esc to cancel"
        )
        return {"RUNNING_MODAL"}

    def preview_update(self, context):
        session = PREVIEW_SESSION
        session.dirty = False

        start = time.perf_counter()
        co, session.count, error = session.solver.solve(context, session.settings)
        if error:
            session.info = error
        else:
            elapsed = time.perf_counter() - start
            session.info = f"{session.count} vertices {self.preview_verb} ({elapsed:.2f}s)"

        write_shape_key(session.obj, session.key_name, co)
        redraw_view3d(context)

    def modal(self, context, event):
        session = PREVIEW_SESSION
        # The object might have been removed
        try:
            _ = session.obj.name
        except ReferenceError:
            self.preview_end(context)
            return {"CANCELLED"}

        if session.finish == "APPLY":
            return self.preview_apply(context)
        if session.finish == "CANCEL" or (event.type == "ESC" and event.value == "PRESS"):
            session.restore()
            self.preview_end(context)
            return {"CANCELLED"}

        # Undo would free the data used by the preview
        if event.type in {"Z", "Y"} and (event.ctrl or event.oskey):
            return {"RUNNING_MODAL"}

        if event.type == "TIMER" and session.dirty and session.obj.mode == "OBJECT":
            self.preview_update(context)

        return {"PASS_THROUGH"}

    def preview_apply(self, context):
        session = PREVIEW_SESSION

        if not session.count:
            session.restore()
            self.preview_end(context)
            self.report({"WARNING"}, f"MustardUI - No vertex {self.preview_verb}")
            return {"CANCELLED"}

        message = self.preview_finish(context, session)
        self.preview_end(context)
        self.report({"INFO"}, f"MustardUI - {message}")
        return {"FINISHED"}

    def preview_finish(self, context, session):
        """Finalize the Shape Key, returning the report message"""

        sk = session.obj.data.shape_keys.key_blocks[session.key_name]
        name = session.settings.shape_key_name.strip()
        if name and name != sk.name:
            sk.name = name
        if session.solver.influence is not None:
            write_vertex_group(session.obj, sk.name, session.solver.influence)
        return f"Shape Key '{sk.name}' created ({session.count} vertices {self.preview_verb})"

    def preview_end(self, context):
        global PREVIEW_SESSION
        PREVIEW_SESSION = None
        context.window_manager.event_timer_remove(self._timer)
        if context.workspace is not None:
            context.workspace.status_text_set(None)
        redraw_view3d(context)

    def cancel(self, context):
        try:
            PREVIEW_SESSION.restore()
        except ReferenceError:
            pass
        self.preview_end(context)


class MustardUI_ToolsCreators_PreviewFinish(bpy.types.Operator):
    """Apply or cancel the Shape Key preview"""

    bl_idname = "mustardui.tools_creators_preview_finish"
    bl_label = "Finish Preview"
    bl_options = {"INTERNAL"}

    apply: bpy.props.BoolProperty(default=True)

    @classmethod
    def poll(cls, context):
        return PREVIEW_SESSION is not None

    def execute(self, context):
        PREVIEW_SESSION.finish = "APPLY" if self.apply else "CANCEL"
        return {"FINISHED"}


def preview_draw_footer(layout, session):
    layout.label(text=session.info, icon="INFO")
    row = layout.row(align=True)
    row.operator(
        "mustardui.tools_creators_preview_finish", text="Apply", icon="CHECKMARK"
    ).apply = True
    row.operator("mustardui.tools_creators_preview_finish", text="Cancel", icon="X").apply = False


def register():
    bpy.utils.register_class(MustardUI_ToolsCreators_PreviewFinish)


def unregister():
    bpy.utils.unregister_class(MustardUI_ToolsCreators_PreviewFinish)
