import bpy


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
    driver_object = eval(rna)
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
        var.targets[0].data_path = '["' + prop_name + '"]'

    # Array property
    else:
        for i in range(0, prop.array_length):
            driver[i] = driver[i].driver
            driver[i].type = "AVERAGE"

            var = driver[i].variables.new()
            var.name = 'mustardui_var'
            var.targets[0].id_type = "ARMATURE"
            var.targets[0].id = obj
            var.targets[0].data_path = '["' + prop_name + '"]' + '[' + str(i) + ']'

    return


def mustardui_clean_prop(obj, uilist, index, addon_prefs):
    # Delete custom property and drivers
    try:
        ui_data = obj.id_properties_ui(uilist[index].prop_name)
        ui_data.clear()
    except:
        if addon_prefs.debug:
            print('MustardUI - Could not clear UI properties. Skipping for this custom property')

    # Delete custom property
    try:
        del obj[uilist[index].prop_name]
    except:
        if addon_prefs.debug:
            print('MustardUI - Properties not found. Skipping custom properties deletion')

    # Remove linked properties drivers
    for lp in uilist[index].linked_properties:
        try:
            driver_object = eval(lp.rna)
            driver_object.driver_remove(lp.path)
        except:
            print("MustardUI - Could not delete driver with path: " + lp.rna)

    # Remove driver
    try:
        driver_object = eval(uilist[index].rna)
        driver_object.driver_remove(uilist[index].path)
    except:
        print("MustardUI - Could not delete driver with path: " + uilist[index].rna)

    return


def mustardui_cp_path(rna, path):
    return rna + "." + path if not all(["[" in path, "]" in path]) else rna + path
