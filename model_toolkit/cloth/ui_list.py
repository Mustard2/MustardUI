import bpy
import gpu
import numpy as np
from gpu_extras.batch import batch_for_shader

from .settings import cloth_objects

VIEWPORT = {}  # draw handler of the Soft Radius spheres


class MUSTARDUI_UL_ClothPinEmpties_UIList(bpy.types.UIList):
    """Pin Empties of the cloth: the Empty, the radius it pins and its Soft Radius"""

    def draw_item(self, _context, layout, _data, item, _icon, _active_data, _active_prop, _index):
        row = layout.row(align=True)
        row.prop(item, "empty", text="", emboss=False, icon="EMPTY_AXIS")
        row.prop(item, "radius", text="")
        row.prop(item, "soft_radius", text="")


# Unit circles around the three axes, as line segments: the sphere Empties are drawn with
_a = np.linspace(0, 2 * np.pi, 49)
_c = np.column_stack([np.cos(_a), np.sin(_a), np.zeros_like(_a)])
_c = np.repeat(_c, 2, axis=0)[1:-1]
CIRCLES = np.concatenate([_c, _c[:, [0, 2, 1]], _c[:, [2, 0, 1]]])


def draw_soft_radius():
    """The Soft Radius of each visible Pin Empty, as a sphere in the Empty's colors"""
    context = bpy.context
    overlay = context.space_data.overlay
    if not (overlay.show_overlays and overlay.show_extras):
        return
    theme = context.preferences.themes[0].view_3d
    lines = {}
    for o in cloth_objects(context):
        for x in o.MustardUI_Cloth.pin_empties:
            empty = x.empty
            if x.soft_radius > 0 and empty and empty.visible_get():
                color = (
                    theme.object_active
                    if empty == context.active_object
                    else theme.object_selected
                    if empty.select_get()
                    else theme.empty
                )
                center = np.array(empty.matrix_world.translation)
                lines.setdefault(tuple(color), []).append(CIRCLES * x.soft_radius + center)
    if not lines:
        return
    shader = gpu.shader.from_builtin("POLYLINE_UNIFORM_COLOR")
    shader.uniform_float("viewportSize", gpu.state.viewport_get()[2:])
    shader.uniform_float("lineWidth", context.preferences.system.pixel_size)
    gpu.state.depth_test_set("LESS_EQUAL")
    gpu.state.blend_set("ALPHA")
    for color, pts in lines.items():
        shader.uniform_float("color", (*color, 0.8))
        batch_for_shader(shader, "LINES", {"pos": np.concatenate(pts).tolist()}).draw(shader)
    gpu.state.blend_set("NONE")
    gpu.state.depth_test_set("NONE")


def register():
    bpy.utils.register_class(MUSTARDUI_UL_ClothPinEmpties_UIList)
    VIEWPORT["handle"] = bpy.types.SpaceView3D.draw_handler_add(
        draw_soft_radius, (), "WINDOW", "POST_VIEW"
    )


def unregister():
    bpy.types.SpaceView3D.draw_handler_remove(VIEWPORT.pop("handle"), "WINDOW")
    bpy.utils.unregister_class(MUSTARDUI_UL_ClothPinEmpties_UIList)
