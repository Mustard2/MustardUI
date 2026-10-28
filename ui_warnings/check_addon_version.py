from .. import bl_info


# Checks if the model has been configured with a MustardUI version more recent than
# the installed one
def check_addon_version(rig_settings):
    model_version = tuple(rig_settings.model_mustardui_version_saved)

    # Models configured before this check was introduced have no version saved
    if model_version == (0, 0, 0):
        return False

    return tuple(bl_info["version"]) < model_version
