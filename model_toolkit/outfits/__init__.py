from . import ops_fit_to_body, ops_squish


def register():
    ops_squish.register()
    ops_fit_to_body.register()


def unregister():
    ops_fit_to_body.unregister()
    ops_squish.unregister()
