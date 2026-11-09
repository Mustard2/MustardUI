"""Cloth Physics Interactive Mode: the cloths simulated live in the viewport, with brushes."""

import time

import blf
import bpy
import gpu
import numpy as np
from bpy_extras import view3d_utils
from gpu_extras.batch import batch_for_shader
from mathutils import Vector

from .settings import STATE, cloth_objects, current_world
from .solver import WORLD, gpu_available

STATS = {}  # last interactive frame rate and brush stroke, read by tests


class MustardUI_ModelToolkit_ClothInteractive(bpy.types.Operator):
    """Simulate every enabled cloth live: drag vertices, pin, grab a range"""

    bl_idname = "mustardui.model_toolkit_cloth_interactive"
    bl_label = "Interactive Mode"

    @classmethod
    def poll(cls, context):
        return (
            not STATE["running"]
            and context.scene.MustardUI_ClothScene.mode == "INTERACTIVE"
            and context.area
            and context.area.type == "VIEW_3D"
            and cloth_objects(context)
            and gpu_available()
        )

    def invoke(self, context, event):
        try:
            self.world = current_world(context)
        except Exception as e:  # noqa: BLE001 - shader or mesh errors end up in the report
            self.report({"ERROR"}, f"MustardUI - {e}")
            return {"CANCELLED"}
        if not self.world.colliders:
            self.report({"WARNING"}, "MustardUI - no collider set")
        self.mouse = (event.mouse_region_x, event.mouse_region_y)
        self.range = False
        self.drag = None
        self.tack = np.full(
            self.world.solver.n, -1
        )  # Tack brush: tack id of each pinned vertex, -1 none
        self.stroke = False
        self.invert = False
        # Stretch edges, for the Smooth brush
        sv = self.world.solver
        self.edges = sv.springs[sv.kinds == 0]
        self.last = time.perf_counter()
        self.fps = 0.0
        self.step_ms = 0.0
        STATE.update(running=True, stop=False)
        wm = context.window_manager
        self.timer = wm.event_timer_add(1 / 60, window=context.window)
        self.draw_px = bpy.types.SpaceView3D.draw_handler_add(
            self.draw_hud, (context,), "WINDOW", "POST_PIXEL"
        )
        self.draw_3d = bpy.types.SpaceView3D.draw_handler_add(
            self.draw_pins, (), "WINDOW", "POST_VIEW"
        )
        context.workspace.status_text_set(
            "MustardUI Cloth: [1] Grab [2] Push [3] Smooth [4] Pin [5] Tack | [LMB] Apply, "
            "[Ctrl] Invert | [E] Range Grab | [ [ ] ] or [Ctrl Wheel] Radius | [P] Toggle Pin | "
            "[Alt+P] Clear Pins | [R] Reset | [Esc / RMB] Exit"
        )
        wm.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def finish(self, context):
        context.window_manager.event_timer_remove(self.timer)
        bpy.types.SpaceView3D.draw_handler_remove(self.draw_px, "WINDOW")
        bpy.types.SpaceView3D.draw_handler_remove(self.draw_3d, "WINDOW")
        context.workspace.status_text_set(None)
        STATE.update(running=False, stop=False)
        STATS["running"] = False
        self.world.solver.drag = None
        self.world.solver.upload_attach()
        if context.area:
            context.area.tag_redraw()

    # ------------------------------------------------------------ picking

    def screen(self, context, pos):
        """Region pixel coordinates and view depth of world positions."""
        m = np.array(context.region_data.perspective_matrix)
        clip = pos @ m[:3, :3].T + m[:3, 3]
        w = pos @ m[3, :3] + m[3, 3]
        xy = clip[:, :2] / np.maximum(w, 1e-6)[:, None]
        xy = (xy * 0.5 + 0.5) * (context.region.width, context.region.height)
        return xy, w

    def pick(self, context, radius_px=25):
        """Front-most vertex of all cloths near the cursor"""
        xy, w = self.screen(context, self.world.pos)
        d = np.linalg.norm(xy - self.mouse, axis=1)
        near = np.flatnonzero((d < radius_px * context.preferences.system.pixel_size) & (w > 0))
        if not len(near):
            return None
        front = near[w[near] < w[near].min() + 0.02]
        return int(front[np.argmin(d[front])])

    def cloth_of(self, i):
        return next(c for c in self.world.cloths if c.span.start <= i < c.span.stop)

    def mouse_world(self, context, depth_point):
        return np.array(
            view3d_utils.region_2d_to_location_3d(
                context.region, context.region_data, self.mouse, depth_point
            )
        )

    # ------------------------------------------------------------ brushes

    def smoothed(self, pos, idx, passes=12):
        """Brushed vertices after Laplacian passes; the rim stays put, else the patch shrinks"""
        local = np.full(len(pos), -1)
        local[idx] = np.arange(len(idx))
        e = local[self.edges]
        inside = (e >= 0).all(1)
        rim = np.zeros(len(idx), bool)
        rim[e[~inside].max(1)] = True  # the brushed end of edges leaving the brush
        e = e[inside]
        deg = np.maximum(np.bincount(e.ravel(), minlength=len(idx)), 1)[:, None]
        p = pos[idx].copy()
        for _ in range(passes):
            avg = np.stack(
                [
                    np.bincount(e[:, 0], p[e[:, 1], j], len(p))
                    + np.bincount(e[:, 1], p[e[:, 0], j], len(p))
                    for j in range(3)
                ],
                1,
            )
            p = np.where(rim[:, None], p, 0.5 * p + 0.5 * avg / deg)
        return p

    def smooth_targets(self, pos, idx, strength):
        """Toward the brushed area smoothed at its own scale (one-ring averages barely move it)"""
        return pos[idx] + (self.smoothed(pos, idx) - pos[idx]) * min(1.0, 2.0 * strength)

    def apply_brush(self, context):
        """Push, Smooth or Pin the vertices within the radius of the one under the cursor"""
        st, world = context.scene.MustardUI_ClothScene, self.world
        solver = world.solver
        i = self.pick(context)
        if i is None:
            if solver.drag is not None:
                solver.drag = None
                solver.upload_attach()
            return
        pos = world.pos
        d = np.linalg.norm(pos - pos[i], axis=1)
        idx = np.flatnonzero(d < st.brush_radius)
        w = (1 - d[idx] / st.brush_radius) ** 2
        if st.brush == "PIN":
            solver.pins[idx] = not self.invert
            self.tack[idx] = -1  # painted over: a plain pin
            solver.pin_pos[idx] = pos[idx]
            for c in world.cloths:
                if np.any((idx >= c.span.start) & (idx < c.span.stop)):
                    world.bind_pins(c)
        elif st.brush == "PUSH":
            # Into the view, Ctrl toward it: up to 6 mm per update at full strength
            view = np.array(context.region_data.view_rotation @ Vector((0.0, 0.0, -1.0)))
            step = 0.006 * st.brush_strength * (-1 if self.invert else 1)
            solver.drag = (idx, pos[idx] + view * step, 2.0e4 * w)
            if "trace" in STATS:  # GUI test: depth of the stroke along the view at each update
                STATS["trace"].append(float(np.mean(pos[idx] @ view)))
        else:
            solver.drag = (idx, self.smooth_targets(pos, idx, st.brush_strength), 1.0e5 * w)
        solver.upload_attach()
        STATS["brush"] = (st.brush, self.invert, int(i), len(idx))

    # ------------------------------------------------------------ events

    def modal(self, context, event):
        world, solver = self.world, self.world.solver
        if STATE["stop"] or context.area is None or WORLD["world"] is not world:
            self.finish(context)
            return {"FINISHED"}
        if event.type == "TIMER":
            now = time.perf_counter()
            dt = now - self.last
            if dt < 1 / 70:
                return {"PASS_THROUGH"}
            self.last = now
            self.fps = 0.9 * self.fps + 0.1 / max(dt, 1e-4)
            if self.stroke and context.scene.MustardUI_ClothScene.brush in {"PUSH", "SMOOTH"}:
                self.apply_brush(context)  # keeps working while the button is held still
            if self.drag:
                # Halfway to the mouse each step: mouse events land unevenly on the steps
                idx, start, k, anchor, offset = self.drag
                offset = offset + 0.5 * (self.mouse_world(context, anchor) - anchor - offset)
                self.drag = (idx, start, k, anchor, offset)
                world.solver.drag = (idx, start + offset, k)
                world.solver.upload_attach()
            t = time.perf_counter()
            # Fixed frame time: a varying one shifts the unconverged rest shape every frame (jitter)
            world.step(1 / 30)
            self.step_ms = 0.9 * self.step_ms + 0.1 * (time.perf_counter() - t) * 1000
            STATS.update(fps=self.fps, step_ms=self.step_ms, running=True)
            context.area.tag_redraw()
            return {"PASS_THROUGH"}

        if event.type == "MOUSEMOVE":
            self.mouse = (event.mouse_region_x, event.mouse_region_y)
            self.invert = event.ctrl
            if self.stroke:
                if context.scene.MustardUI_ClothScene.brush == "PIN":
                    self.apply_brush(context)
                return {"RUNNING_MODAL"}
            if self.drag:
                return {"RUNNING_MODAL"}  # the timer moves the grab
            return {"PASS_THROUGH"}

        # Over the header, toolbar or sidebar (they overlap the viewport): their click
        if (
            event.type == "LEFTMOUSE"
            and event.value == "PRESS"
            and any(
                r.type != "WINDOW"
                and 0 <= event.mouse_x - r.x < r.width
                and 0 <= event.mouse_y - r.y < r.height
                for r in context.area.regions
            )
        ):
            return {"PASS_THROUGH"}

        if event.type == "LEFTMOUSE" and context.scene.MustardUI_ClothScene.brush not in {
            "GRAB",
            "TACK",
        }:
            if event.value == "PRESS":
                if self.pick(context) is None:
                    return {"PASS_THROUGH"}
                self.stroke, self.invert = True, event.ctrl
                self.apply_brush(context)
                return {"RUNNING_MODAL"}
            if event.value == "RELEASE" and self.stroke:
                self.stroke = False
                solver.drag = None
                solver.upload_attach()
                return {"RUNNING_MODAL"}

        if event.type == "LEFTMOUSE":
            if event.value == "PRESS":
                i = self.pick(context)
                if i is None:
                    return {"PASS_THROUGH"}
                pos = world.pos
                d = np.linalg.norm(pos - pos[i], axis=1)
                st = context.scene.MustardUI_ClothScene
                # Clicked on a tack's dots (drawn over the cloth, maybe behind it) or near it
                near, tacked = -1, np.flatnonzero(self.tack >= 0)
                if st.brush == "TACK" and len(tacked):
                    xy, _ = self.screen(context, pos[tacked])
                    px = np.linalg.norm(xy - self.mouse, axis=1)
                    j = int(np.argmin(px))
                    if (
                        px[j] < 15 * context.preferences.system.pixel_size
                        or d[tacked[j]] < 0.5 * st.brush_radius
                    ):
                        near = tacked[j]
                if near >= 0:
                    # A tack: unpinned and dragged as a whole (Ctrl: just removed)
                    idx = np.flatnonzero(self.tack == self.tack[near])
                    solver.pins[idx] = solver.group_pins[idx]
                    self.tack[idx] = -1
                    for c in world.cloths:
                        world.bind_pins(c)
                    if event.ctrl:
                        solver.upload_attach()
                        return {"RUNNING_MODAL"}
                    k = np.full(len(idx), 5.0e4)
                else:
                    if st.brush == "TACK" and event.ctrl:
                        return {"RUNNING_MODAL"}
                    # One vertex on a stiff spring flickers (point load): a 3 cm patch with falloff
                    r, k0 = (
                        (st.brush_radius, 2.0e4)
                        if self.range or st.brush == "TACK"
                        else (0.03, 5.0e4)
                    )
                    idx = np.flatnonzero(d < r)
                    k = k0 * (1 - d[idx] / r) ** 2
                self.drag = (idx, pos[idx].copy(), k, pos[i].copy(), np.zeros(3))
                solver.drag = (idx, pos[idx].copy(), k)
                solver.upload_attach()
                return {"RUNNING_MODAL"}
            if event.value == "RELEASE" and self.drag:
                if context.scene.MustardUI_ClothScene.brush == "TACK":
                    # Pinned where released: the stiffer half of the patch, the rim relaxes
                    idx, _, k, _, _ = self.drag
                    core = idx[k >= 0.24 * k.max()]
                    self.tack[core] = self.tack.max() + 1
                    solver.pins[core] = True
                    solver.pin_pos[core] = world.pos[core]
                    for c in world.cloths:
                        if np.any((core >= c.span.start) & (core < c.span.stop)):
                            world.bind_pins(c)
                self.drag = None
                solver.drag = None
                solver.upload_attach()
                return {"RUNNING_MODAL"}

        if event.type == "P" and event.value == "PRESS":
            if event.alt:
                self.tack[:] = -1
                solver.pins[:] = solver.group_pins
                solver.pin_pos[solver.pins] = world.rest[solver.pins]
                for c in world.cloths:
                    world.bind_pins(c)
            else:
                i = self.pick(context)
                if i is not None:
                    solver.pins[i] = not solver.pins[i]
                    solver.pin_pos[i] = world.pos[i]
                    self.tack[i] = -1
                    world.bind_pins(self.cloth_of(i))
            solver.upload_attach()
            return {"RUNNING_MODAL"}

        if event.type == "E" and event.value == "PRESS":
            context.scene.MustardUI_ClothScene.brush = "GRAB"
            self.range = not self.range
            return {"RUNNING_MODAL"}

        keys = {"ONE": "GRAB", "TWO": "PUSH", "THREE": "SMOOTH", "FOUR": "PIN", "FIVE": "TACK"}
        if event.type in keys and event.value == "PRESS":
            context.scene.MustardUI_ClothScene.brush = keys[event.type]
            return {"RUNNING_MODAL"}

        # Radius: [ and ] like sculpting, or Ctrl+Wheel; the plain wheel keeps zooming the view
        grow = {"RIGHT_BRACKET": True, "LEFT_BRACKET": False}.get(event.type)
        if event.ctrl and event.type in {"WHEELUPMOUSE", "WHEELDOWNMOUSE"}:
            grow = event.type == "WHEELUPMOUSE"
        if grow is not None and event.value == "PRESS":
            st = context.scene.MustardUI_ClothScene
            st.brush_radius *= 1.15 if grow else 1 / 1.15
            return {"RUNNING_MODAL"}

        if event.type == "R" and event.value == "PRESS":
            world.reset()
            return {"RUNNING_MODAL"}

        if event.type in {"ESC", "RIGHTMOUSE"} and event.value == "PRESS":
            self.finish(context)
            return {"FINISHED"}

        return {"PASS_THROUGH"}

    # ------------------------------------------------------------ drawing

    def circle(self, context):
        return self.range or context.scene.MustardUI_ClothScene.brush != "GRAB"

    def draw_hud(self, context):
        font = 0
        scale = context.preferences.system.ui_scale
        blf.size(font, 13 * scale)
        blf.color(font, 1.0, 0.8, 0.3, 1.0)
        blf.position(font, 60 * scale, 40 * scale, 0)
        w, st = self.world, context.scene.MustardUI_ClothScene
        brush = {
            "GRAB": "Range Grab" if self.range else "Grab",
            "PUSH": "Pull" if self.invert else "Push",
            "SMOOTH": "Smooth",
            "PIN": "Unpin" if self.invert else "Pin",
            "TACK": "Remove Tack" if self.invert else "Tack",
        }[st.brush]
        info = (
            f"   {self.fps:.0f} FPS   step {self.step_ms:.1f} ms   {w.solver.n} vertices"
            if st.debug
            else ""
        )
        blf.draw(font, f"{brush}{info}")
        if self.circle(context):
            r_px = self.radius_px(context)
            shader = gpu.shader.from_builtin("UNIFORM_COLOR")
            a = np.linspace(0, 2 * np.pi, 49)
            pts = [(self.mouse[0] + r_px * np.cos(t), self.mouse[1] + r_px * np.sin(t)) for t in a]
            batch = batch_for_shader(shader, "LINE_STRIP", {"pos": pts})
            color = {
                "PUSH": (0.3, 0.7, 1.0),
                "SMOOTH": (0.4, 1.0, 0.5),
                "PIN": (1.0, 0.3, 0.3),
                "TACK": (1.0, 0.5, 0.9),
            }.get(st.brush, (1.0, 0.8, 0.3))
            shader.uniform_float("color", (*color, 0.9))
            batch.draw(shader)

    def radius_px(self, context):
        """Grab radius in pixels at the depth of the vertex under the cursor."""
        i = self.pick(context, radius_px=60)
        if i is None:
            return 30.0
        p = self.world.pos[i]
        r = context.scene.MustardUI_ClothScene.brush_radius
        right = np.array(context.region_data.view_matrix.inverted().col[0][:3])
        xy, _ = self.screen(context, np.array([p, p + right * r]))
        return float(np.linalg.norm(xy[1] - xy[0]))

    def draw_pins(self):
        pts = self.world.pos[self.world.solver.pins]
        if not len(pts):
            return
        shader = gpu.shader.from_builtin("POINT_UNIFORM_COLOR")
        gpu.state.point_size_set(6)
        batch = batch_for_shader(shader, "POINTS", {"pos": pts.astype(np.float32)})
        shader.uniform_float("color", (1.0, 0.2, 0.2, 1.0))
        batch.draw(shader)


class MustardUI_ModelToolkit_ClothStop(bpy.types.Operator):
    """Stop the interactive mode (the results stay)"""

    bl_idname = "mustardui.model_toolkit_cloth_stop"
    bl_label = "Stop Interactive Mode"

    def execute(self, context):
        STATE["stop"] = True
        return {"FINISHED"}


classes = (
    MustardUI_ModelToolkit_ClothInteractive,
    MustardUI_ModelToolkit_ClothStop,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
