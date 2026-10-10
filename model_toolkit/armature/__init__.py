from . import (
    ops_face_controller,
    ops_spline_ik,
)


def register():
    ops_spline_ik.register()
    ops_face_controller.register()


def unregister():
    ops_face_controller.unregister()
    ops_spline_ik.unregister()
