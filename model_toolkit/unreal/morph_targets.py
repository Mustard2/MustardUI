"""Sources of morph targets, shared by the export operator and the background worker."""

import re

BONE_TRANSFORM = re.compile(
    r'pose\.bones\["[^"]+"\]\.(location|rotation_euler|rotation_quaternion|scale)'
)


def face_controls(rig):
    """Names of the facial controls of the rig which move bones."""
    controls = set()
    for driver in rig.animation_data.drivers if rig.animation_data else ():
        if BONE_TRANSFORM.match(driver.data_path):
            for variable in driver.driver.variables:
                path = variable.targets[0].data_path
                if variable.type == "SINGLE_PROP" and path.startswith('["'):
                    controls.add(path[2:-2].replace("(fin)", ""))
    return sorted(
        name
        for name in controls
        if name.startswith("facs_")
        and name in rig.keys()
        and not re.search("EyeLook|EyeCrossed|EyeResting", name)
    )


def is_baked(key):
    """Active shape keys which are not animation controls are part of the character's shape."""
    return (
        key != key.id_data.reference_key
        and abs(key.value) > 1e-3
        and not key.name.startswith(("facs_", "body_cbs"))
    )


def exported_shape_keys(meshes):
    """Names of the shape keys of the meshes which can become morph targets."""
    return sorted(
        {
            key.name
            for obj in meshes
            if obj.data.shape_keys is not None
            for key in obj.data.shape_keys.key_blocks
            if key != obj.data.shape_keys.reference_key and not is_baked(key)
        }
    )
