"""Cloth Physics with the timeline: frames simulated as they play, cached and baked."""

import time

import bpy
import gpu
from gpu_extras.batch import batch_for_shader

from . import solver
from .settings import STATE, cloth_objects, current_world

TIMELINE = {}  # draw handler of the cached frames strip


@bpy.app.handlers.persistent
def frame_pre(scene, *args):
    """Cached frames into the helper meshes before the scene is evaluated (scrub, render)"""
    world = solver.WORLD["world"]
    if world is None or scene.MustardUI_ClothScene.mode != "ANIMATION":
        return
    state = world.cache.get(scene.frame_current)
    if state is not None:
        world.set_state(state)
        world.frame = scene.frame_current


@bpy.app.handlers.persistent
def frame_post(scene, *args):
    """Next frame: simulate it; the start frame restarts from the posed cloths"""
    world = solver.WORLD["world"]
    f = scene.frame_current
    if world is not None:
        # A frame change moves the body: interactive steps re-read colliders and pin sources
        world.body_dirty = world.sources_dirty = True
    if world is None or scene.MustardUI_ClothScene.mode != "ANIMATION" or f in world.cache:
        return
    if bpy.app.is_job_running("RENDER"):
        return  # renders read the cache: bake first
    if f == scene.frame_start:
        world.start(bpy.context)
    elif world.frame == f - 1:
        world.playback_step(bpy.context, scene.render.fps_base / scene.render.fps)
    else:
        return
    world.cache[f] = world.state()
    world.frame = f
    # The sidebar's status and the timeline strip follow the simulation
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type in {"VIEW_3D", "DOPESHEET_EDITOR"}:
                area.tag_redraw()


class MustardUI_ModelToolkit_ClothBake(bpy.types.Operator):
    """Simulate the scene's frame range into the cache (smooth playback, renders)"""

    bl_idname = "mustardui.model_toolkit_cloth_bake"
    bl_label = "Bake"

    @classmethod
    def poll(cls, context):
        return not STATE["running"] and cloth_objects(context) and solver.gpu_available()

    def execute(self, context):
        scene = context.scene
        try:
            world = current_world(context)
        except Exception as e:  # noqa: BLE001 - shader or mesh errors end up in the report
            self.report({"ERROR"}, f"MustardUI - {e}")
            return {"CANCELLED"}
        scene.MustardUI_ClothScene.mode = "ANIMATION"
        world.cache.clear()
        current = scene.frame_current
        wm = context.window_manager
        wm.progress_begin(scene.frame_start, scene.frame_end)
        t = time.perf_counter()
        for f in range(scene.frame_start, scene.frame_end + 1):
            scene.frame_set(f)
            wm.progress_update(f)
        wm.progress_end()
        scene.frame_set(current)
        n = scene.frame_end - scene.frame_start + 1
        self.report({"INFO"}, f"MustardUI - baked {n} frames in {time.perf_counter() - t:.1f} s")
        return {"FINISHED"}


class MustardUI_ModelToolkit_ClothFreeCache(bpy.types.Operator):
    """Forget the simulated frames"""

    bl_idname = "mustardui.model_toolkit_cloth_free_cache"
    bl_label = "Free Cache"

    def execute(self, context):
        world = solver.WORLD["world"]
        if world:
            world.cache.clear()
            world.frame = None
        return {"FINISHED"}


class MustardUI_ModelToolkit_ClothPlay(bpy.types.Operator):
    """Play the timeline from the start frame, simulating the cloths frame by frame"""

    bl_idname = "mustardui.model_toolkit_cloth_play"
    bl_label = "Play from Start"

    @classmethod
    def poll(cls, context):
        return bool(cloth_objects(context)) and solver.gpu_available()

    def execute(self, context):
        if context.screen.is_animation_playing:
            bpy.ops.screen.animation_cancel(restore_frame=False)
            return {"FINISHED"}
        try:
            current_world(context)
        except Exception as e:  # noqa: BLE001 - shader or mesh errors end up in the report
            self.report({"ERROR"}, f"MustardUI - {e}")
            return {"CANCELLED"}
        context.scene.MustardUI_ClothScene.mode = "ANIMATION"
        context.scene.frame_set(context.scene.frame_start)
        bpy.ops.screen.animation_play()
        return {"FINISHED"}


def draw_timeline_cache():
    """Simulated frames as a strip at the bottom of the Timeline / Dope Sheet"""
    scene = bpy.context.scene
    world = solver.WORLD["world"]
    if world is None or not world.cache or scene.MustardUI_ClothScene.mode != "ANIMATION":
        return
    v2d = bpy.context.region.view2d
    scale = bpy.context.preferences.system.ui_scale
    frames = sorted(world.cache)
    runs, first = [], frames[0]
    for a, b in zip(frames, frames[1:] + [None], strict=True):
        if b != a + 1:
            runs.append((first, a))
            first = b
    y0, y1 = 14 * scale, 19 * scale
    pts = []
    for a, b in runs:
        x0 = v2d.view_to_region(a - 0.5, 0, clip=False)[0]
        x1 = v2d.view_to_region(b + 0.5, 0, clip=False)[0]
        pts += [(x0, y0), (x1, y0), (x1, y1), (x0, y0), (x1, y1), (x0, y1)]
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    gpu.state.blend_set("ALPHA")
    batch = batch_for_shader(shader, "TRIS", {"pos": pts})
    shader.uniform_float("color", (1.0, 0.55, 0.15, 0.85))
    batch.draw(shader)
    gpu.state.blend_set("NONE")


classes = (
    MustardUI_ModelToolkit_ClothBake,
    MustardUI_ModelToolkit_ClothFreeCache,
    MustardUI_ModelToolkit_ClothPlay,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.app.handlers.depsgraph_update_post.append(solver.colliders_changed)
    bpy.app.handlers.load_post.append(solver.file_loaded)
    bpy.app.handlers.frame_change_pre.append(frame_pre)
    bpy.app.handlers.frame_change_post.append(frame_post)
    TIMELINE["handle"] = bpy.types.SpaceDopeSheetEditor.draw_handler_add(
        draw_timeline_cache, (), "WINDOW", "POST_PIXEL"
    )


def unregister():
    bpy.types.SpaceDopeSheetEditor.draw_handler_remove(TIMELINE.pop("handle"), "WINDOW")
    bpy.app.handlers.frame_change_post.remove(frame_post)
    bpy.app.handlers.frame_change_pre.remove(frame_pre)
    bpy.app.handlers.load_post.remove(solver.file_loaded)
    bpy.app.handlers.depsgraph_update_post.remove(solver.colliders_changed)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
