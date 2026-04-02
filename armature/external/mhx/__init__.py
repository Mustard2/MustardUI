from . import props
from . import mhx_update
from . import fkik
from . import animation


def register():
    props.register()
    mhx_update.register()
    fkik.register()
    animation.register()


def unregister():
    animation.unregister()
    fkik.unregister()
    mhx_update.unregister()
    props.unregister()
