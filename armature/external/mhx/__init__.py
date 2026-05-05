import bpy

from . import props
from . import mhx_update
from . import fkik
from . import animation
from . import utils

classes = [
    utils.ErrorOperator,
    utils.MessageOperator,
]


def register():
    props.register()
    mhx_update.register()
    fkik.register()
    animation.register()
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    animation.unregister()
    fkik.unregister()
    mhx_update.unregister()
    props.unregister()
    for cls in classes:
        bpy.utils.unregister_class(cls)

