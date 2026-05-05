import bpy
from mathutils import Vector

from ..model_selection.active_object import mustardui_active_object


def physics_preset_poll(arm, physics_settings, type="CREATE"):
    if arm.mustardui_physics_items_uilist_index < 0 or len(physics_settings.items) < 1:
        return "ERROR", "MustardUI - Invalid Preset selected"

    obj = physics_settings.items[arm.mustardui_physics_items_uilist_index].object

    if obj is None or obj.type != "MESH":
        return "ERROR", "MustardUI - Invalid Object to apply Preset"

    if type == "CREATE":
        modifiers = obj.modifiers
        if len(modifiers) < 1:
            return "ERROR", "MustardUI - No data/modifier to create a Preset from found"

    return "", ""


def get_physics_modifiers(obj):
    cloth = next((m for m in obj.modifiers if m.type == "CLOTH"), None)
    soft_body = next((m for m in obj.modifiers if m.type == "SOFT_BODY"), None)
    collision = next((m for m in obj.modifiers if m.type == "COLLISION"), None)

    return cloth, soft_body, collision


def physics_to_json(obj):
    cloth, soft_body, collision = get_physics_modifiers(obj)

    if not cloth and not soft_body and not collision:
        return None

    def dump_rna_block(rna):
        data = {}
        for prop in rna.bl_rna.properties:
            if prop.is_readonly:
                continue
            try:
                val = getattr(rna, prop.identifier)
                if hasattr(val, "__iter__") and not isinstance(val, (str, bytes)):
                    val = list(val)
                data[prop.identifier] = val
            except Exception:
                pass
        return data

    preset_data = {
        "cloth": {},
        "cloth_collision": {},
        "object_collision": {},
        "soft_body": {},
        "has_cloth": cloth is not None,
        "has_soft_body": soft_body is not None,
        "has_collision": obj.collision is not None and collision is not None,
    }

    if cloth:
        preset_data["cloth"] = dump_rna_block(cloth.settings)

        if cloth.collision_settings:
            preset_data["cloth_collision"] = dump_rna_block(cloth.collision_settings)

    if collision and obj.collision:
        preset_data["object_collision"] = dump_rna_block(obj.collision)

    if soft_body:
        preset_data["soft_body"] = dump_rna_block(soft_body.settings)

    return preset_data


def restore_value(current_value, loaded_value):
    if isinstance(current_value, Vector) and isinstance(loaded_value, list):
        return Vector(loaded_value)
    return loaded_value


def apply_settings(target, data, errors, debug):
    if not target or not data:
        return errors

    props = target.bl_rna.properties.keys()

    for key, value in data.items():
        if key not in props:
            errors += 1
            continue

        try:
            current = getattr(target, key)
            value = restore_value(current, value)
            setattr(target, key, value)
        except TypeError as e:
            msg = str(e)
            # Ignore Blender collection assignment mismatch
            if "expected a Collection type" in msg:
                continue
            errors += 1
        except Exception as e:
            if debug:
                print(f"MustardUI - Preset Apply Error - {key}: {e}")
            errors += 1

    return errors


def apply_physics_preset(context, arm, settings, data, force=False):
    obj = settings.items[arm.mustardui_physics_items_uilist_index].object
    errors = 0

    if not obj:
        return 1

    cloth = next((m for m in obj.modifiers if m.type == "CLOTH"), None)
    soft_body = next((m for m in obj.modifiers if m.type == "SOFT_BODY"), None)
    collision = next((m for m in obj.modifiers if m.type == "COLLISION"), None)

    if cloth:
        errors = apply_settings(cloth.settings, data.get("cloth"), errors, False)

        if cloth.collision_settings:
            errors = apply_settings(
                cloth.collision_settings,
                data.get("cloth_collision"),
                errors,
                False,
            )

    if obj.collision and collision:
        errors = apply_settings(
            obj.collision, data.get("object_collision"), errors, False
        )

    if soft_body:
        errors = apply_settings(
            soft_body.settings, data.get("soft_body"), errors, False
        )

    return errors


def warning_physics_preset(obj):
    cloth, soft_body, collision = get_physics_modifiers(obj)

    if cloth is None and soft_body is None and collision is None:
        return "WARNING", "No data to save in the preset."

    return "", ""


def set_physics_preset(obj, preset):
    cloth, soft_body, collision = get_physics_modifiers(obj)

    preset.has_cloth = cloth is not None
    preset.has_soft_body = soft_body is not None
    preset.has_collision = obj.collision is not None and collision is not None


def physics_post_import(preset, preset_json):
    # Physics additional flags
    if hasattr(preset, "has_cloth"):
        preset.has_cloth = bool(preset_json.get("cloth"))
    if hasattr(preset, "has_soft_body"):
        preset.has_soft_body = bool(preset_json.get("soft_body"))
    if hasattr(preset, "has_collision"):
        preset.has_collision = bool(preset_json.get("object_collision"))


class MustardUI_Physics_Preset(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Name")

    # Preset data in Json format
    data: bpy.props.StringProperty()

    has_cloth: bpy.props.BoolProperty()
    has_soft_body: bpy.props.BoolProperty()
    has_collision: bpy.props.BoolProperty()


class MUSTARDUI_UL_Physics_Presets_UIList(bpy.types.UIList):
    """UIList for Physics Presets"""

    def poll(cls, context):
        res, obj = mustardui_active_object(context, config=0)
        return res if obj is not None else False

    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname, index
    ):
        row = layout.row(align=True)
        row2 = row.row()
        if item.has_cloth:
            row2.label(text="", icon="MOD_CLOTH")
        if item.has_soft_body:
            row2.label(text="", icon="MOD_SOFT")
        if item.has_collision:
            row2.label(text="", icon="MOD_PHYSICS")
        row2.prop(
            item,
            "name",
            text="",
            emboss=False,
            translate=False,
        )


def register():
    bpy.utils.register_class(MustardUI_Physics_Preset)
    bpy.utils.register_class(MUSTARDUI_UL_Physics_Presets_UIList)

    bpy.types.Armature.mustardui_physics_preset_uilist_index = bpy.props.IntProperty(
        name="", default=0
    )


def unregister():
    del bpy.types.Armature.mustardui_physics_preset_uilist_index

    bpy.utils.unregister_class(MUSTARDUI_UL_Physics_Presets_UIList)
    bpy.utils.unregister_class(MustardUI_Physics_Preset)
