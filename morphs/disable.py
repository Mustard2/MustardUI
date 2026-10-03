import bpy

from .. import __package__ as base_package
from ..misc.outfits import outfits_get_collection_items
from ..misc.set_bool import set_bool
from .misc import (
    diffeomorphic_facs_bones_loc,
    diffeomorphic_facs_bones_rot,
    get_cp_source,
    muteDazFcurves,
    muteDazFcurves_exceptionscheck,
)


# Values driven by the seeds through chains of drivers, and the indices of these drivers.
# With all_inputs, only the drivers whose inputs are all driven by the seeds are followed
def driven_values(drivers, seeds, all_inputs):
    values = set(seeds)
    driven = set()
    check = all if all_inputs else any
    changed = bool(values)
    while changed:
        changed = False
        for i, (_, output, inputs) in enumerate(drivers):
            if i not in driven and inputs and check(x in values for x in inputs):
                driven.add(i)
                values.add(output)
                changed = True
    return values, driven


def morphs_enable_update(self, context):
    arm = self.id_data
    rig_settings = arm.MustardUI_RigSettings
    rig = rig_settings.model_armature_object
    body = rig_settings.model_body
    enable = self.diffeomorphic_enable
    mute_used_sk = self.mute_shape_keys == "ALL"

    if not enable:
        self.diffeomorphic_enable_settings = False

    outfits = [
        obj
        for x in rig_settings.outfits_collections
        if x.collection
        for obj in outfits_get_collection_items(rig_settings, x.collection)
        if obj.type == "MESH"
    ]
    meshes = {body, *outfits, *(x for x in rig.children if x.type == "MESH")}
    keys = {x.data.shape_keys for x in meshes} - {None}

    # Drivers with their output and inputs (None for inputs that are not properties)
    drivers = [
        (
            fcurve,
            (fcurve.id_data, fcurve.data_path),
            [
                (v.targets[0].id, v.targets[0].data_path) if v.type == "SINGLE_PROP" else None
                for v in fcurve.driver.variables
            ],
        )
        for x in {rig, arm, *meshes, *(x.data for x in meshes), *keys}
        if x.animation_data
        for fcurve in x.animation_data.drivers
    ]
    key_blocks = {
        (key, f'key_blocks["{bpy.utils.escape_identifier(kb.name)}"].value'): kb
        for key in keys
        for kb in key.key_blocks
    }

    def morph_values(sections):
        values = set()
        for section in sections:
            for morph in section.morphs:
                name = bpy.utils.escape_identifier(morph.path)
                if morph.custom_property:
                    source = get_cp_source(morph.custom_property_source, rig_settings)
                    path = f'["{name}"]'
                else:
                    source = body.data.shape_keys
                    path = f'key_blocks["{name}"].value'
                if source is not None:
                    values.add((source, path))
        return values

    # Morphs that can not be disabled stay active, with all the drivers they affect
    kept_values, kept = driven_values(
        drivers, morph_values(x for x in self.sections if not x.can_disable), all_inputs=False
    )
    # Drivers depending only on disabled morphs can be muted, as their values can not change.
    # Diffeomorphic sections are disabled with the Diffeomorphic rules below
    disabled_values, disabled = driven_values(
        drivers,
        morph_values(x for x in self.sections if x.can_disable and not x.is_internal) - kept_values,
        all_inputs=True,
    )

    if self.type != "GENERIC":
        mutepJCM = self.diffeomorphic_enable_pJCM
        mutefacs = self.diffeomorphic_enable_facs
        mutefacs_bones = mutefacs or self.diffeomorphic_enable_facs_bones
        exceptions = self.diffeomorphic_disable_exceptions

        try:
            muteDazFcurves(
                rig,
                not enable,
                mute_used_sk=mute_used_sk,
                mutepJCM=mutepJCM,
                mutefacs=mutefacs,
                check_bones_rot=[] if mutefacs_bones else diffeomorphic_facs_bones_rot,
                check_bones_loc=[] if mutefacs_bones else diffeomorphic_facs_bones_loc,
                exceptions=exceptions,
            )
            if hasattr(rig, "DazDriversDisabled"):
                rig.DazDriversDisabled = not enable
        except Exception:
            if context.preferences.addons[base_package].preferences.debug:
                print("MustardUI - Error occurred while switching Daz drivers.")

        # Drivers of the custom properties are not disabled ("\n" is never in a data path)
        cp_paths = "\n".join(
            cp.rna + "." + cp.path
            for cp in [
                *arm.MustardUI_CustomProperties,
                *arm.MustardUI_CustomPropertiesOutfit,
                *arm.MustardUI_CustomPropertiesHair,
            ]
        )

        for obj in [body, *outfits]:
            shape_keys = obj.data.shape_keys
            if shape_keys is None or shape_keys.animation_data is None:
                continue
            for fcurve in shape_keys.animation_data.drivers:
                path = fcurve.data_path
                if (
                    ("pJCM" not in path or mutepJCM)
                    and ("facs" not in path or mutefacs)
                    and muteDazFcurves_exceptionscheck(False, path, exceptions)
                    and "MustardUINotDisable" not in path
                ):
                    set_bool(fcurve, "mute", not enable and path not in cp_paths)
                # Drivers excluded from disabling are kept active
                elif not enable:
                    set_bool(fcurve, "mute", False)

        if rig.animation_data is not None:
            for fcurve in rig.animation_data.drivers:
                expression = fcurve.driver.expression
                if "evalMorphs" in expression or (enable and expression in ("0.0", "-0.0")):
                    set_bool(fcurve, "mute", not enable and fcurve.data_path not in cp_paths)

        # Restore what the morphs that can not be disabled need
        if not enable:
            for i in kept:
                set_bool(drivers[i][0], "mute", False)
            for value in kept_values:
                if value in key_blocks:
                    set_bool(key_blocks[value], "mute", False)

    for i in disabled - kept:
        set_bool(drivers[i][0], "mute", not enable)
    for value in disabled_values - kept_values:
        kb = key_blocks.get(value)
        if kb is not None:
            set_bool(kb, "mute", not enable and (mute_used_sk or abs(kb.value) < 0.001))
