import bpy
from ..misc.prop_utils import *


# Function to check keys of custom properties (only for debug)
def dump(obj, text):
    print('-' * 40, text, '-' * 40)
    for attr in dir(obj):
        if hasattr(obj, attr):
            print("obj.%s = %s" % (attr, getattr(obj, attr)))


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


# Function to choose correct custom properties list
def mustardui_choose_cp(obj, type, scene):
    if type == "BODY":
        return obj.MustardUI_CustomProperties, scene.mustardui_property_uilist_index
    elif type == "OUTFIT":
        return obj.MustardUI_CustomPropertiesOutfit, scene.mustardui_property_uilist_outfits_index
    else:
        return obj.MustardUI_CustomPropertiesHair, scene.mustardui_property_uilist_hair_index


def mustardui_update_index_cp(type, scene, index):
    if type == "BODY":
        scene.mustardui_property_uilist_index = index
    elif type == "OUTFIT":
        scene.mustardui_property_uilist_outfits_index = index
    else:
        scene.mustardui_property_uilist_hair_index = index


def mustardui_add_driver(obj, rna, path, prop, prop_name):
    driver_object = evaluate_rna(rna)
    driver_object.driver_remove(path)
    driver = driver_object.driver_add(path)

    # No array property
    if prop.array_length == 0:
        driver = driver.driver
        driver.type = "AVERAGE"
        var = driver.variables.new()
        var.name = 'mustardui_var'
        var.targets[0].id_type = "ARMATURE"
        var.targets[0].id = obj
        var.targets[0].data_path = f'["{prop_name}"]'

    # Array property
    else:
        for i in range(0, prop.array_length):
            driver[i] = driver[i].driver
            driver[i].type = "AVERAGE"

            var = driver[i].variables.new()
            var.name = 'mustardui_var'
            var.targets[0].id_type = "ARMATURE"
            var.targets[0].id = obj
            var.targets[0].data_path = f'["{prop_name}"][{str(i)}]'

    return


def mustardui_reassign_default(obj, uilist, index, addon_prefs):
    # Assign default before removing the associated drivers
    try:
        prop = uilist[index]
        if prop.type == "FLOAT" and prop.force_type == "None":
            obj[prop.prop_name] = prop.default_float
        elif prop.type == "INT" or (prop.type == "FLOAT" and prop.force_type == "Int"):
            obj[prop.prop_name] = prop.default_int
    except:
        if addon_prefs.debug:
            print('MustardUI - Could not reassign default value. Skipping for this custom property')

    return


def mustardui_clean_prop(obj, uilist, index, addon_prefs):
    # Delete custom property and drivers
    try:
        ui_data = obj.id_properties_ui(uilist[index].prop_name)
        ui_data.clear()
    except:
        if addon_prefs.debug:
            print('MustardUI - Could not clean UI property. Skipping for this custom property')

    # Delete custom property
    try:
        del obj[uilist[index].prop_name]
    except:
        if addon_prefs.debug:
            print('MustardUI - Properties not found. Skipping custom properties deletion')

    # Remove linked properties drivers
    for lp in uilist[index].linked_properties:
        try:
            driver_object = evaluate_rna(lp.rna)
            driver_object.driver_remove(lp.path)
        except:
            print("MustardUI - Could not delete driver with path: " + lp.rna)

    # Remove driver
    try:
        driver_object = evaluate_rna(uilist[index].rna)
        driver_object.driver_remove(uilist[index].path)
    except:
        print("MustardUI - Could not delete driver with path: " + uilist[index].rna)


    '''
    Delete Drivers Associated with the outfit's CP

    For the current custom prop, we get the rna and go through the shapekeys with drivers, if we get
    a match that a shape key is driven by this cp path, we remove it!
    '''

    if not obj.MustardUI_RigSettings.model_body.data.shape_keys or not obj.MustardUI_RigSettings.model_body.data.shape_keys.animation_data:
        return

    drivers = obj.MustardUI_RigSettings.model_body.data.shape_keys.animation_data.drivers

    if drivers:
        # set here, because list adds duplicates and causes error removing an already removed driver
        drivers_to_remove = set()

        for drv in drivers:
            for var in drv.driver.variables:
                for target in var.targets:
                    if target.data_path == uilist[index].rna.partition('.key_blocks')[2]:
                        drivers_to_remove.add(drv)
                        break

        for drv in drivers_to_remove:
            drivers.remove(drv)


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
