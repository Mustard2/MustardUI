# Function to add a option to the object, if not already there
def mustardui_add_morph(collection, item, custom_property=True, custom_property_source="ARMATURE"):
    for el in collection:
        if el.path == item[1] and el.custom_property == custom_property:
            return

    add_item = collection.add()
    add_item.name = item[0]
    add_item.path = item[1]
    add_item.custom_property = custom_property
    add_item.shape_key = not custom_property
    if custom_property:
        add_item.custom_property_source = custom_property_source
    return


def mustardui_add_section(collection, item, is_internal=False, diffeomorphic=-1):
    if is_internal:
        for el in collection:
            if el.is_internal and el.diffeomorphic_id == diffeomorphic:
                return

    add_item = collection.add()
    add_item.name = item[0]
    add_item.is_internal = is_internal
    add_item.diffeomorphic_id = diffeomorphic
    return


def get_cp_source(custom_property_source, rig_settings):
    if custom_property_source == "ARMATURE_OBJ":
        return rig_settings.model_armature_object
    elif custom_property_source == "ARMATURE_DATA":
        return rig_settings.model_armature_object.data
    elif custom_property_source == "BODY_OBJ":
        return rig_settings.model_body
    elif custom_property_source == "BODY_DATA":
        return rig_settings.model_body.data
    return None


def get_section_by_diffeomorphic_id(morphs_settings, did):
    secs = [x for x in morphs_settings.sections if x.diffeomorphic_id == did]
    if len(secs):
        return secs[0]
    return None


diffeomorphic_facs_bones_rot = ['lowerJaw', 'EyelidOuter', 'EyelidInner', 'EyelidUpperInner', 'EyelidUpper',
                                'EyelidUpperOuter',
                                'EyelidLowerOuter', 'EyelidLower', 'EyelidLowerInner']
diffeomorphic_facs_bones_loc = ['lowerJaw', 'NasolabialLower', 'NasolabialMouthCorner', 'LipCorner',
                                'LipLowerOuter',
                                'LipLowerInner', 'LipLowerMiddle', 'CheekLower', 'LipNasolabialCrease',
                                'LipUpperMiddle', 'LipUpperOuter', 'LipUpperInner', 'LipBelow', 'NasolabialMiddle']


def muteDazFcurves_exceptionscheck(muteexceptions, string, exceptions):
    check_final = False
    for s in [x for x in exceptions.split(',') if x != '']:
        check_final = check_final or s in string
    return not check_final or muteexceptions


def muteDazFcurves_facscheck(mutefacs, string, check_bones_rot, check_bones_loc):
    check_final = False

    # Rotation check
    for s in check_bones_rot:
        if check_final:
            break
        check_single = s + ":Rot" in string or (s in string and "rotation" in string)
        check_final = check_final or check_single
    for s in check_bones_loc:
        if check_final:
            break
        check_single = s + ":Loc" in string or (s in string and "location" in string)
        check_final = check_final or check_single

    return (not "facs" in string and not check_final) or mutefacs


def pJCMcheck(string, mutepJCM):
    return not ("pJCM" in string) or mutepJCM


def isDazFcurve(path):
    for string in ["(fin)", "(rst)", ":Loc:", ":Rot:", ":Sca:", ":Hdo:", ":Tlo"]:
        if string in path:
            return True
    return False


# Function to mute daz drivers
def muteDazFcurves(rig, mute, useLocation=True, useRotation=True, useScale=True, muteSK=True, mutepJCM=False,
                   mutefacs=False, check_bones_rot=[], check_bones_loc=[], muteexceptions=False, exceptions=[]):

    if rig and rig.data.animation_data:
        for fcu in rig.data.animation_data.drivers:
            if isDazFcurve(fcu.data_path) and pJCMcheck(fcu.data_path, mutepJCM):
                if muteDazFcurves_facscheck(mutefacs, fcu.data_path, check_bones_rot,
                                            check_bones_loc) and muteDazFcurves_exceptionscheck(muteexceptions,
                                                                                                fcu.data_path,
                                                                                                exceptions):
                    fcu.mute = mute
                else:
                    fcu.mute = False

    if rig and rig.animation_data:
        for fcu in rig.animation_data.drivers:
            words = fcu.data_path.split('"')
            if words[0] == "pose.bones[":
                channel = words[-1].rsplit(".", 1)[-1]
                if ((channel in ["rotation_euler", "rotation_quaternion"] and useRotation) or
                    (channel == "location" and useLocation) or
                    (channel == "scale" and useScale) or
                    channel in ["HdOffset", "TlOffset"]) and muteDazFcurves_facscheck(mutefacs, fcu.data_path,
                                                                                      check_bones_rot, check_bones_loc):
                    fcu.mute = mute

    for ob in rig.children:
        if ob.type == 'MESH':
            skeys = ob.data.shape_keys
            if skeys and skeys.animation_data:
                for fcu in skeys.animation_data.drivers:
                    words = fcu.data_path.split('"')
                    if words[0] == "key_blocks[":
                        if muteDazFcurves_facscheck(mutefacs, fcu.data_path, check_bones_rot,
                                                    check_bones_loc) and muteDazFcurves_exceptionscheck(muteexceptions,
                                                                                                        fcu.data_path,
                                                                                                        exceptions):
                            fcu.mute = mute
                        else:
                            fcu.mute = False
                        sname = words[1]
                        if sname in skeys.key_blocks.keys() and muteSK:
                            if not "MustardUINotDisable" in sname and pJCMcheck(sname, mutepJCM) and muteDazFcurves_facscheck(
                                    mutefacs, sname, check_bones_rot, check_bones_loc):
                                skey = skeys.key_blocks[sname]
                                if muteDazFcurves_exceptionscheck(muteexceptions, sname, exceptions):
                                    skey.mute = mute
                                else:
                                    skey.mute = False
