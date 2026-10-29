# Model settings on a Text, where the depsgraph does not follow their pointers
from contextlib import contextmanager

import bpy
from bpy.app.handlers import persistent

from .. import __package__ as base_package

# Original definitions of the properties moved from Armature to Text
_moved = {}
# Number of armatures at the last conversion, to convert the new ones
_armatures = 0
# Scene property with the IDs added to the depsgraph by evaluated()
_EVALUATED = "MustardUI_evaluated"
# Drivers keep the armature as target, as the undo can keep them pointing to a removed Text
_THROUGH_TEXT = "MustardUI_data."


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
            _retarget_drivers([arm], True)
            _tag_relations()
    return text


@contextmanager
def evaluated(ids):
    """IDs in the depsgraph in the context, as with Armature storage, e.g. to bind hidden ones."""
    scene = bpy.context.scene
    if not _moved or _EVALUATED in scene:
        yield
        return
    scene[_EVALUATED] = {str(i): x for i, x in enumerate(ids) if x is not None}
    _tag_relations()
    try:
        yield
    finally:
        del scene[_EVALUATED]
        _tag_relations()


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
    if moved:
        _retarget_drivers([arm], False)
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
    # Draw callbacks can not store the Text, which is then removed
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
            if name in target_props:
                del target_props[name]
            target_props[name] = source_props[name]
            if delete_source:
                del source_props[name]
    return bool(names)


def _remap(props, mapping):
    """Replace the IDs in the ID properties props by their values in mapping, if any."""
    remapped = False
    for key in props.keys():
        value = props[key]
        if isinstance(value, bpy.types.ID):
            if value in mapping:
                props[key] = mapping[value]
                remapped = True
        elif hasattr(value, "keys"):
            remapped |= _remap(value, mapping)
        elif isinstance(value, list):
            for item in value:
                if hasattr(item, "keys"):
                    remapped |= _remap(item, mapping)
    return remapped


def _driver_targets(arms):
    """Driver targets reading the settings of arms, with the IDs of the drivers."""
    prefixes = tuple(_names())
    users = bpy.data.user_map(subset=arms)
    for id_data in set(arms).union(*users.values()):
        anim = getattr(id_data, "animation_data", None)
        if anim is None or id_data.library is not None:
            continue
        for fcurve in anim.drivers:
            for var in fcurve.driver.variables:
                for target in var.targets:
                    path = target.data_path.removeprefix(_THROUGH_TEXT)
                    if target.id in arms and path.startswith(prefixes):
                        yield id_data, target


def _retarget_drivers(arms, enable):
    """Drivers reading the settings of arms, through their Text while it stores them."""
    for _, target in list(_driver_targets(arms)):
        path = target.data_path.removeprefix(_THROUGH_TEXT)
        target.data_path = _THROUGH_TEXT + path if enable else path


# Moving ID properties does not rebuild the depsgraph relations they create
def _tag_relations():
    for scene in bpy.data.scenes:
        for view_layer in scene.view_layers:
            if view_layer.depsgraph is not None:
                view_layer.depsgraph.debug_tag_update()


def _convert(enable):
    global _armatures
    names = _names()
    texts = set()
    moved = False
    overrides = []
    # Linked and overridden armatures too, as draw callbacks can not create their Text
    for arm in bpy.data.armatures:
        text = text_of(arm)
        if enable:
            if arm.override_library is not None:
                overrides.append(arm)
            # Duplicated armatures share the Text of the original one
            if text is None or text in texts:
                text = _new_text(arm, text)
            # Texts saved before the fake user was removed
            if text.use_fake_user:
                text.use_fake_user = False
            if _move(arm, text, names, delete_source=True):
                _retarget_drivers([arm], True)
                moved = True
            texts.add(text)
        else:
            moved |= store_on_armature(arm)
    # Overrides get the settings of the linked armature from its Text, not remapped to them
    if overrides:
        mapping = {
            x.override_library.reference: x
            for prop in bpy.data.bl_rna.properties
            if prop.type == "COLLECTION"
            for x in getattr(bpy.data, prop.identifier)
            if isinstance(x, bpy.types.ID) and x.override_library is not None
        }
        for arm in overrides:
            moved |= _remap(system_properties(text_of(arm)), mapping)
    if moved:
        _tag_relations()
    # Counted after the conversion, to retry it if it fails
    _armatures = len(bpy.data.armatures)


@persistent
def apply(*args):
    """Move the settings of all the models to the storage chosen in the preferences."""
    addon = bpy.context.preferences.addons.get(base_package)
    prefs = addon.preferences if addon is not None else None
    enable = prefs is not None and prefs.settings_storage == "TEXT"
    if enable != bool(_moved):
        _relocate(enable)
    _convert(enable)


def _tag_text_drivers():
    """Update the drivers reading the settings on Texts, which are not in the depsgraph."""
    for id_data in {x for x, _ in _driver_targets(list(bpy.data.armatures))}:
        id_data.update_tag()


@persistent
def _depsgraph_update(scene, depsgraph):
    # Text storage: armatures without their own Text, e.g. new, duplicated or made local
    if _moved:
        texts = [text_of(x) for x in bpy.data.armatures]
        if None in texts or len(set(texts)) < len(texts):
            _convert(True)
        elif depsgraph.id_type_updated("TEXT"):
            _tag_text_drivers()
    # Armature storage: new armatures, e.g. appended with a Text
    elif len(bpy.data.armatures) != _armatures:
        _convert(False)


# Files are saved with Armature storage, readable also without it, e.g. by older versions
@persistent
def _save_pre(*args):
    if _moved:
        _convert(False)


@persistent
def _save_post(*args):
    if _moved:
        _convert(True)


_handlers = (
    (bpy.app.handlers.load_post, apply),
    (bpy.app.handlers.undo_post, apply),
    (bpy.app.handlers.redo_post, apply),
    (bpy.app.handlers.depsgraph_update_post, _depsgraph_update),
    (bpy.app.handlers.save_pre, _save_pre),
    (bpy.app.handlers.save_post, _save_post),
)


def register():
    bpy.types.Armature.MustardUI_data = bpy.props.PointerProperty(type=bpy.types.Text)
    for handlers, func in _handlers:
        handlers.append(func)
    # bpy.data is not available while registering, and the timer survives the startup file load
    bpy.app.timers.register(apply, first_interval=0, persistent=True)


def unregister():
    if bpy.app.timers.is_registered(apply):
        bpy.app.timers.unregister(apply)
    for handlers, func in _handlers:
        if func in handlers:
            handlers.remove(func)
    if _moved:
        _relocate(False)
    del bpy.types.Armature.MustardUI_data
