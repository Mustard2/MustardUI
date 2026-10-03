# Experimental: store the model settings on a Text datablock instead of the Armature.
# The depsgraph follows ID pointers stored on an Armature, pulling hidden outfits (and their
# textures) into renders; it never looks into a Text, so the settings stop doing that there.
# The storage is global: registration moves the settings properties from Armature to Text,
# and the Armature keeps Python aliases, so arm.MustardUI_RigSettings works in both modes.
import bpy
from bpy.app.handlers import persistent

from .. import __package__ as base_package

# Original definitions of the properties moved from Armature to Text
_moved = {}


def holder(arm):
    """Text storing the settings of arm, created with the settings on arm when missing."""
    text = _text(arm)
    if text is None:
        text = bpy.data.texts.new(f".MustardUI {arm.name}")
        # Without the fake user the Text is removed with the armature
        text.use_fake_user = False
        arm.MustardUI_data = text
        _move(arm, text, _names(), delete_source=True)
    return text


def settings_owner(arm):
    """ID owning the settings of arm, for UI calls that need the property name."""
    return holder(arm) if _moved else arm


def settings_armature(id_data):
    """Armature of settings owned by id_data."""
    if isinstance(id_data, bpy.types.Text):
        return next((x for x in bpy.data.armatures if _text(x) == id_data), None)
    return id_data


def remove_holder(arm):
    text = _text(arm)
    props = _idprops(arm)
    if props is not None and "MustardUI_data" in props:
        del props["MustardUI_data"]
    if text is not None and all(_text(x) != text for x in bpy.data.armatures):
        bpy.data.texts.remove(text)


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


# Storage of the properties registered with bpy.props, apart from custom ones in Blender 5.0+
def _idprops(id_data, create=False):
    if hasattr(id_data, "bl_system_properties_get"):
        return id_data.bl_system_properties_get(do_create=create)
    return id_data


def _plain(value):
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if hasattr(value, "to_list"):
        return value.to_list()
    if isinstance(value, list):
        return [_plain(x) for x in value]
    return value


def _move(source, target, names, delete_source):
    source_props = _idprops(source)
    names = [x for x in names if source_props is not None and x in source_props]
    if not names:
        return
    target_props = _idprops(target, create=True)
    for name in names:
        target_props[name] = _plain(source_props[name])
        if delete_source:
            del source_props[name]

    # Moving ID properties does not rebuild the depsgraph relations they create
    for scene in bpy.data.scenes:
        for view_layer in scene.view_layers:
            if view_layer.depsgraph is not None:
                view_layer.depsgraph.debug_tag_update()


# Reading the pointer with RNA would store an empty one on the armature
def _text(arm):
    props = _idprops(arm)
    text = props.get("MustardUI_data") if props is not None else None
    return text if isinstance(text, bpy.types.Text) else None


def _has_text_key(arm):
    props = _idprops(arm)
    return props is not None and "MustardUI_data" in props


# Armatures whose settings can be written, so not linked or overridden
def _local_armatures():
    return [x for x in bpy.data.armatures if x.library is None and x.override_library is None]


def _convert(enable):
    names = _names()
    texts = set()
    for arm in _local_armatures():
        text = _text(arm)
        if enable:
            # Duplicated armatures share the Text of the original one
            if text in texts:
                arm.MustardUI_data = text.copy()
                arm.MustardUI_data.name = f".MustardUI {arm.name}"
            text = holder(arm)
            # Texts saved before the fake user was removed
            text.use_fake_user = False
            _move(arm, text, names, delete_source=True)
            texts.add(text)
        elif _has_text_key(arm):
            # Other armatures can still share the Text, which is removed with the last one
            if text is not None:
                _move(text, arm, names, delete_source=False)
            remove_holder(arm)


@persistent
def apply(*args):
    """Move the settings of all the models to the storage chosen in the preferences."""
    addon = bpy.context.preferences.addons.get(base_package)
    prefs = addon.preferences if addon is not None else None
    enable = prefs is not None and prefs.experimental and prefs.settings_storage == "TEXT"
    if enable != bool(_moved):
        _relocate(enable)
    _convert(enable)


# Armatures added to the file, also by append, get the settings in the chosen storage
@persistent
def _depsgraph_update(scene, depsgraph):
    armatures = _local_armatures()
    if _moved:
        texts = [_text(x) for x in armatures]
        convert = None in texts or len(set(texts)) < len(texts)
    else:
        convert = any(_has_text_key(x) for x in armatures)
    if convert:
        _convert(bool(_moved))


# Each Blender session starts with Armature storage, unless disabled in the preferences
def _startup():
    addon = bpy.context.preferences.addons.get(base_package)
    prefs = addon.preferences if addon is not None else None
    if prefs is not None and prefs.settings_storage_startup and prefs.settings_storage == "TEXT":
        prefs.settings_storage = "ARMATURE"
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
    # bpy.data is not available while registering
    bpy.app.timers.register(_startup, first_interval=0)


def unregister():
    if bpy.app.timers.is_registered(_startup):
        bpy.app.timers.unregister(_startup)
    for handlers, func in _handlers:
        if func in handlers:
            handlers.remove(func)
    if _moved:
        _relocate(False)
    del bpy.types.Armature.MustardUI_data
