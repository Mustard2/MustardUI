import math

import bpy

from ..misc.prop_utils import evaluate_path, evaluate_rna

# hard_min/hard_max of an RNA property with no limits: FLT_MAX for Float, INT_MAX for Int
FLOAT_UNBOUNDED = 1e30
INT_UNBOUNDED = 2**31 - 1


# Check if a limit of an RNA property is the sentinel used when the property has no limit
def mustardui_prop_limit_is_unbounded(limit, is_int):
    if is_int:
        return abs(limit) >= INT_UNBOUNDED
    return not math.isfinite(limit) or abs(limit) >= FLOAT_UNBOUNDED


# Minimum and maximum assigned to a Float or Int custom property when it is added
# Unbounded limits make for a property impossible to use in the UI, so, depending on
# the addon preferences, they fall back to 0 and 1
def mustardui_prop_limits(prop, addon_prefs):
    is_int = prop.type == "INT"
    zero, one = (0, 1) if is_int else (0.0, 1.0)

    # Colors are always normalized
    if prop.subtype == "COLOR":
        return zero, one

    limits = addon_prefs.new_property_limits
    if limits == "NORMALIZED":
        return zero, one

    prop_min, prop_max = prop.hard_min, prop.hard_max
    if limits == "PROPERTY":
        return prop_min, prop_max

    if mustardui_prop_limit_is_unbounded(prop_min, is_int):
        prop_min = zero
    if mustardui_prop_limit_is_unbounded(prop_max, is_int):
        prop_max = one

    # Keep the limits usable when only one of the two was unbounded
    if prop_min >= prop_max:
        prop_max = prop_min + one

    return prop_min, prop_max


# Function to check over all custom properties
def mustardui_check_cp(obj, rna, path):
    for cp in obj.MustardUI_CustomProperties:
        if cp.rna == rna and cp.path == path:
            return False

    for cp in obj.MustardUI_CustomPropertiesOutfit:
        if cp.rna == rna and cp.path == path:
            return False

    for cp in obj.MustardUI_CustomPropertiesHair:
        if cp.rna == rna and cp.path == path:
            return False

    return True


# Check if a custom property supports the "Actions on switch"
def mustardui_cp_supports_on_switch(custom_prop):
    if not custom_prop.is_animatable:
        return False
    if custom_prop.array_length > 0 or custom_prop.subtype == "COLOR":
        return False
    if custom_prop.force_type in ["Int", "Bool"]:
        return True
    return custom_prop.type in ["FLOAT", "INT", "BOOLEAN"]


# Name of the field storing the custom value of an "Actions on switch" action
def mustardui_cp_on_switch_custom_field(custom_prop, show):
    prefix = "outfit_enable" if show else "outfit_disable"

    if custom_prop.type == "BOOLEAN" or custom_prop.force_type == "Bool":
        return prefix + "_custom_bool"
    if custom_prop.type == "INT" or custom_prop.force_type == "Int":
        return prefix + "_custom_int"
    return prefix + "_custom_float"


# Value assigned by an "Actions on switch" action, on show (show=True) or on hide
def mustardui_cp_on_switch_value(custom_prop, ui_data, show):
    choice = getattr(custom_prop, "outfit_enable_value" if show else "outfit_disable_value")

    if choice == "MAX":
        return ui_data.get("max", True)
    if choice == "MIN":
        return ui_data.get("min", False)
    if choice == "DEFAULT":
        return ui_data.get("default")

    value = getattr(custom_prop, mustardui_cp_on_switch_custom_field(custom_prop, show))

    # Keep the custom value inside the limits of the property
    if not isinstance(value, bool):
        value = min(max(value, ui_data.get("min", value)), ui_data.get("max", value))

    return value


# Apply the "Actions on switch" of the given custom properties
def mustardui_cp_apply_on_switch(arm, custom_props, shown, value_shown=None):
    ui_data_cache = {}

    for cp in custom_props:
        if not (cp.outfit_enable_on_switch or cp.outfit_disable_on_switch):
            continue
        if not mustardui_cp_supports_on_switch(cp):
            continue

        is_shown = shown(cp)
        if is_shown is None:
            continue

        # The action of the switch direction should be enabled
        if not (cp.outfit_enable_on_switch if is_shown else cp.outfit_disable_on_switch):
            continue

        prop = cp.prop_name
        if prop not in arm.keys():
            continue

        ui_data = ui_data_cache.get(prop)
        if ui_data is None:
            ui_data = arm.id_properties_ui(prop).as_dict()
            ui_data_cache[prop] = ui_data

        desired = mustardui_cp_on_switch_value(
            cp, ui_data, is_shown if value_shown is None else value_shown(cp)
        )

        if desired is not None and arm[prop] != desired:
            arm[prop] = desired


# Restore the value of a custom property after it has been re-created
def mustardui_cp_restore_value(obj, prop_name, value, cast, prop_min=None, prop_max=None):
    if value is None:
        return

    def convert(single_value):
        single_value = cast(single_value)
        if prop_min is not None and prop_max is not None:
            single_value = min(max(single_value, prop_min), prop_max)
        return single_value

    try:
        obj[prop_name] = [convert(x) for x in value] if isinstance(value, list) else convert(value)
    except Exception:
        print(f"MustardUI - Could not restore the value of the custom property {prop_name}")


# Function to choose correct custom properties list
def mustardui_choose_cp(obj, type, scene):
    if type == "BODY":
        return obj.MustardUI_CustomProperties, scene.mustardui_property_uilist_index
    elif type == "OUTFIT":
        return (
            obj.MustardUI_CustomPropertiesOutfit,
            scene.mustardui_property_uilist_outfits_index,
        )
    else:
        return (
            obj.MustardUI_CustomPropertiesHair,
            scene.mustardui_property_uilist_hair_index,
        )


def mustardui_update_index_cp(type, scene, index):
    if type == "BODY":
        scene.mustardui_property_uilist_index = index
    elif type == "OUTFIT":
        scene.mustardui_property_uilist_outfits_index = index
    else:
        scene.mustardui_property_uilist_hair_index = index


# Add the driver that links the property at rna.path to the custom property prop_name of
# the Armature. array_length is the number of elements of the driven property, and it is
# evaluated from the property itself when it is not provided
def mustardui_add_driver(obj, rna, path, prop_name, array_length=None):
    driver_object = evaluate_rna(rna)
    driver_object.driver_remove(path)
    driver = driver_object.driver_add(path)

    if array_length is None:
        try:
            array_length = len(evaluate_path(rna, path))
        except Exception:
            array_length = 0

    # The name should be escaped, or a name containing quotes breaks the driver
    data_path = f'["{bpy.utils.escape_identifier(prop_name)}"]'

    def add_variable(fcurve, target_path):
        fcurve.driver.type = "AVERAGE"
        var = fcurve.driver.variables.new()
        var.name = "mustardui_var"
        var.targets[0].id_type = "ARMATURE"
        var.targets[0].id = obj
        var.targets[0].data_path = target_path

    # No array property
    if array_length == 0:
        add_variable(driver, data_path)

    # Array property
    else:
        for i in range(0, array_length):
            add_variable(driver[i], f"{data_path}[{i}]")


def mustardui_reassign_default(obj, uilist, index, addon_prefs):
    if not 0 <= index < len(uilist):
        return

    # Assign default before removing the associated drivers
    try:
        prop = uilist[index]
        if prop.type == "FLOAT" and prop.force_type == "None":
            obj[prop.prop_name] = prop.default_float
        elif prop.type == "INT" or (prop.type == "FLOAT" and prop.force_type == "Int"):
            obj[prop.prop_name] = prop.default_int
        elif prop.type == "BOOLEAN" or (prop.type == "FLOAT" and prop.force_type == "Bool"):
            obj[prop.prop_name] = prop.default_bool
    except Exception:
        if addon_prefs.debug:
            print("MustardUI - Could not reassign default value. Skipping for this custom property")

    return


def mustardui_clean_prop(obj, uilist, index, addon_prefs):
    if not 0 <= index < len(uilist):
        return

    # Delete custom property and drivers
    try:
        ui_data = obj.id_properties_ui(uilist[index].prop_name)
        ui_data.clear()
    except Exception:
        if addon_prefs.debug:
            print("MustardUI - Could not clean UI property. Skipping for this custom property")

    # Delete custom property
    try:
        del obj[uilist[index].prop_name]
    except Exception:
        if addon_prefs.debug:
            print("MustardUI - Properties not found. Skipping custom properties deletion")

    # Remove linked properties drivers
    for lp in uilist[index].linked_properties:
        try:
            driver_object = evaluate_rna(lp.rna)
            driver_object.driver_remove(lp.path)
        except Exception:
            print("MustardUI - Could not delete driver with path: " + lp.rna)

    # Remove driver
    try:
        driver_object = evaluate_rna(uilist[index].rna)
        driver_object.driver_remove(uilist[index].path)
    except Exception:
        print("MustardUI - Could not delete driver with path: " + uilist[index].rna)

    return


def mustardui_delete_all_custom_properties(arm, uilist, addon_prefs, rig_settings):
    to_remove = []

    # Firstly set the custom property to their default value
    for i, cp in enumerate(uilist):
        mustardui_reassign_default(arm, uilist, i, addon_prefs)

    # Update everything
    if rig_settings.model_armature_object:
        rig_settings.model_armature_object.update_tag()
    bpy.context.view_layer.update()

    # And then delete data
    for i, cp in enumerate(uilist):
        mustardui_clean_prop(arm, uilist, i, addon_prefs)
        to_remove.append(i)
    for i in reversed(to_remove):
        uilist.remove(i)

    return len(to_remove)


def mustardui_cp_path(rna, path):
    return rna + "." + path if not all(["[" in path, "]" in path]) else rna + path


def assign_ptr(custom_prop, rna, addon_prefs):
    # Skip assignment if already assigned
    # This is to avoid to overwrite the custom property type to "None"
    if custom_prop.ptr_type != "None" and (
        custom_prop.ptr_armature is not None
        or custom_prop.ptr_object is not None
        or custom_prop.ptr_key is not None
        or custom_prop.ptr_material is not None
        or custom_prop.ptr_collection is not None
        or custom_prop.ptr_node_tree is not None
    ):
        return

    # Get the type and assign the pointer
    try:
        if "bpy.data.armatures" in rna and custom_prop.ptr_armature is None:
            custom_prop.ptr_armature = bpy.data.armatures[rna.split('"')[1]]
            custom_prop.ptr_type = "ARMATURE"
        elif "bpy.data.objects" in rna and custom_prop.ptr_object is None:
            custom_prop.ptr_object = bpy.data.objects[rna.split('"')[1]]
            custom_prop.ptr_type = "OBJECT"
        elif "bpy.data.shape_keys" in rna and custom_prop.ptr_key is None:
            custom_prop.ptr_key = bpy.data.shape_keys[rna.split('"')[1]]
            custom_prop.ptr_type = "SHAPEKEY"
        elif "bpy.data.materials" in rna and custom_prop.ptr_material is None:
            custom_prop.ptr_material = bpy.data.materials[rna.split('"')[1]]
            custom_prop.ptr_type = "MATERIAL"
        elif "bpy.data.collections" in rna and custom_prop.ptr_collection is None:
            custom_prop.ptr_collection = bpy.data.collections[rna.split('"')[1]]
            custom_prop.ptr_type = "COLLECTION"
        elif "bpy.data.node_groups" in rna and custom_prop.ptr_node_tree is None:
            custom_prop.ptr_node_tree = bpy.data.node_groups[rna.split('"')[1]]
            custom_prop.ptr_type = "NODE_TREE"
        else:
            custom_prop.ptr_type = "None"
    except Exception as e:
        if addon_prefs.debug:
            print(f"MustardUI - Error while assigning Custom Property pointer: {e}")
        custom_prop.ptr_type = "None"


def assign_pointers(custom_properties, addon_prefs):
    pointers_errors = 0
    for custom_prop in custom_properties:
        try:
            assign_ptr(custom_prop, custom_prop.rna, addon_prefs)
        except Exception as e:
            if addon_prefs.debug:
                print(
                    f"MustardUI - Error while assigning Custom Property pointer for "
                    f"RNA {custom_prop.rna}: {e}"
                )
            pointers_errors += 1

    return pointers_errors
