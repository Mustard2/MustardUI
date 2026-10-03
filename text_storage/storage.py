# Experimental: model settings on a Text, where the depsgraph does not follow their pointers
import bpy
from bpy.app.handlers import persistent

from .. import __package__ as base_package

# Original definitions of the properties moved from Armature to Text
_moved = {}
# Number of armatures at the last conversion, to convert the new ones
_armatures = 0


def text_of(arm):
    """Text storing the settings of arm, if any."""
    # Reading the pointer with RNA would store an empty one on the armature
    props = system_properties(arm)
    text = props.get("MustardUI_data") if props is not None else None
    return text if isinstance(text, bpy.types.Text) else None


def holder(arm):
    """Text storing the settings of arm, created with the settings on arm when missing."""
    text = text_of(arm)
    if text is None:
        text = _new_text(arm)
        if _move(arm, text, _names(), delete_source=True):
            _tag_relations()
    return text


def settings_owner(arm):
    """ID owning the settings of arm, for UI calls that need the property name."""
    return holder(arm) if _moved else arm


def remove_holder(arm):
    text = text_of(arm)
    props = system_properties(arm)
    if props is not None and "MustardUI_data" in props:
        del props["MustardUI_data"]
    if text is not None and all(text_of(x) != text for x in bpy.data.armatures):
        bpy.data.texts.remove(text)


def store_on_armature(arm):
    """Move the settings of arm from its Text back to it, as with Armature storage."""
    text = text_of(arm)
    # Other armatures can still share the Text, which is removed with the last one
    moved = text is not None and _move(text, arm, _names(), delete_source=False)
    remove_holder(arm)
    return moved


# Settings properties that can store ID pointers: property groups, collections and IDs
def _names():
    if _moved:
        return list(_moved)
    return [
        name
        for name, value in vars(bpy.types.Armature).items()
        if isinstance(value, bpy.props._PropertyDeferred)
        and value.function in {bpy.props.PointerProperty, bpy.props.CollectionProperty}
        and name.lower().startswith("mustardui")
        and name != "MustardUI_data"
    ]


# The Armature keeps aliases of the moved properties, as arm.MustardUI_RigSettings
def _relocate(enable):
    if enable:
        for name in _names():
            _moved[name] = vars(bpy.types.Armature)[name]
            delattr(bpy.types.Armature, name)
            setattr(bpy.types.Text, name, _moved[name])
            setattr(bpy.types.Armature, name, property(lambda arm, n=name: getattr(holder(arm), n)))
    else:
        for name, deferred in _moved.items():
            delattr(bpy.types.Armature, name)
            delattr(bpy.types.Text, name)
            setattr(bpy.types.Armature, name, deferred)
        _moved.clear()


def _new_text(arm, source=None):
    """New Text assigned to arm, a copy of source if given."""
    text = source.copy() if source is not None else bpy.data.texts.new("")
    # Linked armatures and draw callbacks can not store the Text, which is then removed
    try:
        text.name = f".MustardUI {arm.name}"
        # Without the fake user the Text is removed with the armature
        text.use_fake_user = False
        arm.MustardUI_data = text
    except (AttributeError, TypeError):
        bpy.data.texts.remove(text)
        raise
    return text


def system_properties(id_data, create=False):
    """Storage of the properties registered with bpy.props, apart from custom ones in 5.0+."""
    if bpy.app.version >= (5, 0):
        return id_data.bl_system_properties_get(do_create=create)
    return id_data


def _move(source, target, names, delete_source):
    source_props = system_properties(source)
    names = [x for x in names if source_props is not None and x in source_props]
    if names:
        target_props = system_properties(target, create=True)
        for name in names:
            target_props[name] = source_props[name]
            if delete_source:
                del source_props[name]
    return bool(names)


# Moving ID properties does not rebuild the depsgraph relations they create
def _tag_relations():
    for scene in bpy.data.scenes:
        for view_layer in scene.view_layers:
            if view_layer.depsgraph is not None:
                view_layer.depsgraph.debug_tag_update()


# Armatures whose settings can be written, so not linked or overridden
def _local_armatures():
    return [x for x in bpy.data.armatures if x.library is None and x.override_library is None]


def _convert(enable):
    global _armatures
    names = _names()
    texts = set()
    moved = False
    for arm in _local_armatures():
        text = text_of(arm)
        if enable:
            # Duplicated armatures share the Text of the original one
            if text is None or text in texts:
                text = _new_text(arm, text)
            # Texts saved before the fake user was removed
            if text.use_fake_user:
                text.use_fake_user = False
            moved |= _move(arm, text, names, delete_source=True)
            texts.add(text)
        else:
            moved |= store_on_armature(arm)
    if moved:
        _tag_relations()
    # Counted after the conversion, to retry it if it fails
    _armatures = len(bpy.data.armatures)


@persistent
def apply(*args):
    """Move the settings of all the models to the storage chosen in the preferences."""
    addon = bpy.context.preferences.addons.get(base_package)
    prefs = addon.preferences if addon is not None else None
    enable = prefs is not None and prefs.experimental and prefs.settings_storage == "TEXT"
    if enable != bool(_moved):
        _relocate(enable)
    _convert(enable)


@persistent
def _depsgraph_update(scene, depsgraph):
    # Text storage: armatures without their own Text, e.g. new, duplicated or made local
    if _moved:
        texts = [text_of(x) for x in _local_armatures()]
        if None in texts or len(set(texts)) < len(texts):
            _convert(True)
    # Armature storage: new armatures, e.g. appended with a Text
    elif len(bpy.data.armatures) != _armatures:
        _convert(False)


# Each Blender session starts with Armature storage, unless disabled in the preferences
def _startup():
    addon = bpy.context.preferences.addons.get(base_package)
    prefs = addon.preferences if addon is not None else None
    if prefs is not None and prefs.settings_storage_startup and prefs.settings_storage == "TEXT":
        # Its update applies the storage
        prefs.settings_storage = "ARMATURE"
    else:
        apply()


_handlers = (
    (bpy.app.handlers.load_post, apply),
    (bpy.app.handlers.undo_post, apply),
    (bpy.app.handlers.redo_post, apply),
    (bpy.app.handlers.depsgraph_update_post, _depsgraph_update),
)


def register():
    bpy.types.Armature.MustardUI_data = bpy.props.PointerProperty(type=bpy.types.Text)
    for handlers, func in _handlers:
        handlers.append(func)
    # bpy.data is not available while registering, and the timer survives the startup file load
    bpy.app.timers.register(_startup, first_interval=0, persistent=True)


def unregister():
    if bpy.app.timers.is_registered(_startup):
        bpy.app.timers.unregister(_startup)
    for handlers, func in _handlers:
        if func in handlers:
            handlers.remove(func)
    if _moved:
        _relocate(False)
    del bpy.types.Armature.MustardUI_data
