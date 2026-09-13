# Armature data of the only item (modifier or constraint) of item_type targeting an
# Armature, or None if there is no such item or more than one
def single_armature_data(items, item_type, target_attr):
    found = None
    for item in items:
        if item.type != item_type:
            continue
        target = getattr(item, target_attr)
        if target is None or target.type != "ARMATURE" or target.data is None:
            continue
        if found is not None:
            return None
        found = target.data
    return found


# Function to decide the active object for showing properties in the UI
def mustardui_active_object(context, config=0):
    settings = context.scene.MustardUI_Settings

    # Quick Setup mode: always use the viewport active object, returns True only if
    # the armature has never been configured with MustardUI (MustardUI_created=False).
    if config == 2:
        if context.active_object is None:
            return False, None
        obj = context.active_object
        if obj.type != "ARMATURE" or obj.data is None:
            return False, None
        arm = obj.data
        return not arm.MustardUI_created and settings.viewport_model_selection, arm

    # If Viewport Model Selection is enabled, the active object will be the active
    # object only if it is an armature
    # If not an Armature, additional checks are made to determine the active object:
    # - is the object parent to an armature,
    # - the object has only one armature modifier with a valid object
    # - the object has only one ChildOf modifier with a valid target
    # The above are tested one after another, starting with the first which is the
    # least expensive to check
    if settings.viewport_model_selection:
        if context.active_object is None:
            return False, None

        obj = context.active_object

        arm = None
        if obj.data is not None and obj.type == "ARMATURE":
            arm = obj.data
        if obj.type == "MESH":
            parent = obj.parent
            if parent is not None and parent.type == "ARMATURE" and parent.data is not None:
                arm = parent.data
            if arm is None:
                arm = single_armature_data(obj.modifiers, "ARMATURE", "object")
            if arm is None:
                arm = single_armature_data(obj.constraints, "CHILD_OF", "target")

        if arm is None:
            return False, None

        if config == 1:
            return not arm.MustardUI_enable, arm
        elif config == 0:
            return arm.MustardUI_enable, arm
        elif config == -1:
            return True, arm

        return False, None

    # If Viewport Model Selection is false, use the UI with the armature selected
    # in the model panel
    else:
        if settings.panel_model_selection_armature is not None:
            if config == 1:
                return (
                    not settings.panel_model_selection_armature.MustardUI_enable,
                    settings.panel_model_selection_armature,
                )
            elif config == 0:
                return (
                    settings.panel_model_selection_armature.MustardUI_enable,
                    settings.panel_model_selection_armature,
                )
            elif config == -1:
                return True, settings.panel_model_selection_armature

    return False, None


def active_object_operator_poll(context, config=0):
    poll, arm = mustardui_active_object(context, config=config)
    return poll if arm is not None else False
