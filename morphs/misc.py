# Function to add a option to the object, if not already there
def mustardui_add_morph(collection, item, custom_property=True):
    for el in collection:
        if el.name == item[0] and el.path == item[1] and el.custom_property == custom_property:
            return

    add_item = collection.add()
    add_item.name = item[0]
    add_item.path = item[1]
    add_item.custom_property = custom_property
    add_item.shape_key = not custom_property
    return


def mustardui_add_section(collection, item):
    add_item = collection.add()
    add_item.name = item[0]
    return


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
