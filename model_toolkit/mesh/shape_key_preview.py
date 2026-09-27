import time
import traceback

import bpy
import numpy as np
from bl_operators.presets import AddPresetBase

from ... import __package__ as base_package
from ...misc.mesh_deform import write_vertex_group

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


def preview_show_result(session, show):
    """Switch the preview Shape Keys on or off, to compare before and after"""

    for obj in [session.obj] + [f.obj for f in session.solver.followers]:
        sks = obj.data.shape_keys
        sk = sks.key_blocks.get(session.key_name) if sks is not None else None
        if sk is not None:
            sk.value = 1.0 if show else 0.0


def preview_show_result_update(self, context):
    if PREVIEW_SESSION is not None:
        preview_show_result(PREVIEW_SESSION, self.MustardUI_ToolsCreators_PreviewShow)
        redraw_view3d(context)


def write_followers(solver, settings, key_name):
    """Write the Shape Keys of the objects following the main one"""

    for follower in solver.followers:
        write_shape_key(follower.obj, key_name, follower.shape(solver, settings))


def link_shape_key_driver(obj, name, source, source_name):
    """Drive the Shape Key value with the one of the source object"""

    sk = obj.data.shape_keys.key_blocks[name]
    try:
        sk.driver_remove("value")
    except TypeError:
        pass
    driver = sk.driver_add("value").driver
    driver.type = "AVERAGE"
    var = driver.variables.new()
    var.type = "SINGLE_PROP"
    var.targets[0].id = source
    escaped = bpy.utils.escape_identifier(source_name)
    var.targets[0].data_path = f'data.shape_keys.key_blocks["{escaped}"].value'


def create_followers_shape_keys(solver, settings, source, name):
    """Write the Shape Keys of the objects following the main one, driven by it"""

    for follower in solver.followers:
        if follower.enabled(settings):
            write_shape_key(follower.obj, name, follower.shape(solver, settings))
            link_shape_key_driver(follower.obj, name, source, name)


class ShapeKeyBackup:
    """Shape Key state to restore on cancel"""

    def __init__(self, obj, key_name):
        self.obj = obj
        self.key_name = key_name
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
        self.error = ""
        self.count = 0

        self.backup = ShapeKeyBackup(obj, key_name)
        self.followers_backup = [ShapeKeyBackup(f.obj, key_name) for f in solver.followers]

    def restore(self):
        for backup in [self.backup, *self.followers_backup]:
            # The object might have been removed
            try:
                backup.restore()
            except ReferenceError:
                pass


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
        context.window_manager.MustardUI_ToolsCreators_PreviewShow = True
        try:
            self.preview_update(context)
        except Exception as error:
            return self.preview_failed(context, error)

        wm = context.window_manager
        self._timer = wm.event_timer_add(0.05, window=context.window)
        wm.modal_handler_add(self)
        context.workspace.status_text_set(
            f"{self.bl_label}: change the settings in Model Toolkit > Mesh, Esc to cancel"
        )
        return {"RUNNING_MODAL"}

    def preview_update(self, context):
        session = PREVIEW_SESSION
        session.dirty = False

        start = time.perf_counter()
        co, session.count, error = session.solver.solve(context, session.settings)
        if error:
            session.error = error
        else:
            elapsed = time.perf_counter() - start
            session.error = ""
            session.info = f"{session.count} vertices {self.preview_verb} ({elapsed:.2f}s)"

        write_shape_key(session.obj, session.key_name, co)
        write_followers(session.solver, session.settings, session.key_name)
        preview_show_result(session, context.window_manager.MustardUI_ToolsCreators_PreviewShow)
        redraw_view3d(context)

    def modal(self, context, event):
        try:
            return self.preview_modal(context, event)
        except Exception as error:
            return self.preview_failed(context, error)

    def preview_modal(self, context, event):
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

        preview_show_result(session, True)
        sk = session.obj.data.shape_keys.key_blocks[session.key_name]
        name = session.settings.shape_key_name.strip()
        if name and name != sk.name:
            sk.name = name
        if session.solver.influence is not None:
            write_vertex_group(session.obj, sk.name, session.solver.influence)

        # Other objects Shape Keys follow the main one
        for follower, backup in zip(
            session.solver.followers, session.followers_backup, strict=True
        ):
            if follower.enabled(session.settings):
                follower_sk = follower.obj.data.shape_keys.key_blocks[session.key_name]
                follower_sk.name = sk.name
                link_shape_key_driver(follower.obj, follower_sk.name, session.obj, sk.name)
            else:
                backup.restore()
        return f"Shape Key '{sk.name}' created ({session.count} vertices {self.preview_verb})"

    def preview_end(self, context):
        global PREVIEW_SESSION
        PREVIEW_SESSION = None
        if getattr(self, "_timer", None) is not None:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None
        if context.workspace is not None:
            context.workspace.status_text_set(None)
        redraw_view3d(context)

    def preview_failed(self, context, error):
        traceback.print_exc()
        self.cancel(context)
        self.report({"ERROR"}, f"MustardUI - {self.bl_label} failed: {error}")
        return {"CANCELLED"}

    def cancel(self, context):
        if PREVIEW_SESSION is not None:
            PREVIEW_SESSION.restore()
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


# Settings depending on the model, not saved in the presets
PRESET_EXCLUDED = {"shape_key_name", "vertex_group", "rigid_group"}


def preview_preset_classes(tool, label, settings_cls, settings_attr):
    """Presets menu and add/remove operator for the settings of a preview tool"""

    menu_name = f"MUSTARDUI_MT_ToolsCreators_{tool}Presets"
    subdir = f"mustardui/{tool.lower()}"
    menu = type(
        menu_name,
        (bpy.types.Menu,),
        {
            "bl_label": f"{label} Presets",
            "preset_subdir": subdir,
            "preset_operator": "script.execute_preset",
            "draw": bpy.types.Menu.draw_preset,
        },
    )
    add = type(
        f"MustardUI_ToolsCreators_{tool}PresetAdd",
        (AddPresetBase, bpy.types.Operator),
        {
            "__doc__": f"Add or remove a {label} preset",
            "bl_idname": f"mustardui.tools_creators_{tool.lower()}_preset_add",
            "bl_label": f"Add {label} Preset",
            "preset_menu": menu_name,
            "preset_subdir": subdir,
            "preset_defines": [f"settings = bpy.context.window_manager.{settings_attr}"],
            "preset_values": [
                f"settings.{name}"
                for name in settings_cls.__annotations__
                if name not in PRESET_EXCLUDED
            ],
        },
    )
    return menu, add


def preview_draw_presets(layout, menu, add):
    row = layout.row(align=True)
    row.menu(menu.__name__, text=menu.bl_label)
    row.operator(add.bl_idname, text="", icon="ADD")
    row.operator(add.bl_idname, text="", icon="REMOVE").remove_active = True


def preview_section(layout, idname, title, icon, default_closed=False):
    """Collapsible section of the settings, returning its column or None if closed"""

    header, body = layout.panel(idname, default_closed=default_closed)
    header.label(text=title, icon=icon)
    if body is None:
        return None
    col = body.column()
    col.use_property_split = True
    col.use_property_decorate = False
    return col


def preview_draw_vertex_group(col, settings, group, invert, obj, text):
    row = col.row(align=True)
    row.prop_search(settings, group, obj, "vertex_groups", text=text)
    sub = row.row(align=True)
    sub.enabled = bool(getattr(settings, group))
    sub.prop(settings, invert, text="", icon="ARROW_LEFTRIGHT")


def preview_draw_masks(layout, session, tool):
    """Settings restricting where the tool acts, and the rigid parts"""

    settings = session.settings
    obj = session.obj

    title = "Affected Area"
    if settings.vertex_group or settings.auto_influence:
        title += " (active)"
    col = preview_section(layout, f"mustardui_{tool}_area", title, "GROUP_VERTEX", True)
    if col is not None:
        preview_draw_vertex_group(
            col, settings, "vertex_group", "invert_vertex_group", obj, "Vertex Group"
        )
        col.prop(settings, "auto_influence", text="Around Intersections")
        row = col.row()
        row.enabled = settings.auto_influence
        row.prop(settings, "influence_radius", text="Radius")

    children = len(session.solver.children)
    title = "Rigid Parts"
    if settings.rigid_group or (settings.move_children and children):
        title += " (active)"
    col = preview_section(layout, f"mustardui_{tool}_rigid", title, "MESH_CUBE", True)
    if col is not None:
        preview_draw_vertex_group(
            col, settings, "rigid_group", "invert_rigid_group", obj, "Vertex Group"
        )
        row = col.row()
        row.enabled = bool(children)
        row.prop(settings, "move_children", text=f"Child Objects ({children})")


def preview_draw_footer(layout, session):
    if session.error:
        layout.label(text=session.error, icon="ERROR")
    else:
        addon = bpy.context.preferences.addons.get(base_package)
        if addon is not None and addon.preferences.debug:
            layout.label(text=session.info, icon="INFO")
    wm = bpy.context.window_manager
    show = wm.MustardUI_ToolsCreators_PreviewShow
    layout.prop(
        wm,
        "MustardUI_ToolsCreators_PreviewShow",
        text="Show Result",
        toggle=True,
        icon="HIDE_OFF" if show else "HIDE_ON",
    )
    row = layout.row(align=True)
    row.operator(
        "mustardui.tools_creators_preview_finish", text="Apply", icon="CHECKMARK"
    ).apply = True
    row.operator("mustardui.tools_creators_preview_finish", text="Cancel", icon="X").apply = False


def register():
    bpy.utils.register_class(MustardUI_ToolsCreators_PreviewFinish)

    bpy.types.WindowManager.MustardUI_ToolsCreators_PreviewShow = bpy.props.BoolProperty(
        name="Show Result",
        default=True,
        description="Show the result of the tool, to compare it with the original shape",
        update=preview_show_result_update,
    )


def unregister():
    del bpy.types.WindowManager.MustardUI_ToolsCreators_PreviewShow

    bpy.utils.unregister_class(MustardUI_ToolsCreators_PreviewFinish)
