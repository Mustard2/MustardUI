import itertools
import re

import bpy

from .. import __package__ as base_package
from ..menu.menu_configure import row_scale
from ..model_selection.active_object import mustardui_active_object
from .misc import get_cp_source, mustardui_add_morph, mustardui_add_section


def rename_morph(self, name, protected_strings=None):
    if protected_strings is None:
        protected_strings = []

    if not self.custom_rename:
        return name

    # 1. Protect substrings using safe non-letter placeholders
    protected = {}
    for i, s in enumerate(protected_strings):
        placeholder = f"<<{i}>>"  # <-- no letters, no digits adjacent to letters
        protected[placeholder] = s
        name = name.replace(s, placeholder)

    # 2. Apply spacing rules (placeholders are safe)
    name = re.sub(r"(?<=[a-z])([A-Z])", r" \1", name)  # lower → upper
    name = re.sub(
        r"(?<=[A-Z])([A-Z][a-z])", r" \1", name
    )  # upper block → capital+lower
    name = re.sub(r"(?<=[a-zA-Z])(\d)", r" \1", name)  # letter → number
    name = re.sub(r"_+", " ", name)  # underscores → spaces

    # 3. Restore protected substrings
    for placeholder, original in protected.items():
        name = name.replace(placeholder, original)

    return name


class MustardUI_Morphs_Clear(bpy.types.Operator):
    """Clear the Morphs UI"""

    bl_idname = "mustardui.morphs_clear"
    bl_label = "Clear Morphs"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=1)
        morphs_settings = arm.MustardUI_MorphsSettings

        return res and morphs_settings.enable_ui and morphs_settings.sections

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings
        morphs_settings = arm.MustardUI_MorphsSettings

        # Remove automatic mute drivers from shape keys
        shape_keys = rig_settings.model_body.data.shape_keys

        if shape_keys and shape_keys.animation_data:
            drivers_to_remove = []
            for driver in shape_keys.animation_data.drivers:
                if driver.data_path.endswith('"].mute'):
                    drv = driver.driver
                    if drv.type == "SCRIPTED" and drv.expression == "abs(var) < 0.001":
                        drivers_to_remove.append(driver.data_path)
            for driver_path in drivers_to_remove:
                try:
                    # Extract shape key name
                    sk_name = driver_path.split('key_blocks["')[1].split('"]')[0]
                    # Unmute before removing driver
                    if sk_name in shape_keys.key_blocks:
                        shape_keys.key_blocks[sk_name].mute = False
                    shape_keys.driver_remove(driver_path)
                except Exception:
                    pass

        morphs_settings.sections.clear()
        morphs_settings.diffeomorphic_genesis_version = -1
        morphs_settings.morphs_number = 0

        # Reset UI List indices
        arm.mustardui_morphs_section_uilist_index = -1

        self.report({"INFO"}, "MustardUI - Morphs cleared.")

        return {"FINISHED"}


class MustardUI_Morphs_Check(bpy.types.Operator):
    """Search for morphs to display in the UI External Morphs panel"""

    bl_idname = "mustardui.morphs_check"
    bl_label = "Check Morphs"
    bl_options = {"UNDO"}

    custom_rename: bpy.props.BoolProperty(
        default=False,
        name="Attempt Renaming",
        description="Apply a predefined set of rules to attempt a better renaming of "
        "the Morphs",
    )
    clear_existing_morphs: bpy.props.BoolProperty(
        default=False,
        name="Clear Existing Morphs",
        description="Remove existing Morphs from the sections before re-adding them",
    )
    add_shape_key_mute_driver: bpy.props.BoolProperty(
        default=False,
        name="Automatically Mute null Shape Keys",
        description="Add a driver on the Mute property of the Shape Keys, which are "
        "automatically disabled when their value is 0.\nNote: Freezable option for "
        "custom sections will be disabled as incompatible with drivers on the Mute "
        "properties",
    )

    @classmethod
    def poll(cls, context):

        res, arm = mustardui_active_object(context, config=1)
        morphs_settings = arm.MustardUI_MorphsSettings

        if morphs_settings.type == "GENERIC":
            return res and morphs_settings.enable_ui and morphs_settings.sections
        return res and morphs_settings.enable_ui

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings
        morphs_settings = arm.MustardUI_MorphsSettings
        addon_prefs = context.preferences.addons[base_package].preferences

        # Try to assign the rig object
        if not arm.MustardUI_created:
            if (
                context.active_object is not None
                and context.active_object.type == "ARMATURE"
            ):
                rig_settings.model_armature_object = context.active_object
            else:
                self.report(
                    {"ERROR"},
                    "MustardUI - You need to complete the first configuration before "
                    "being able to add Morphs to the UI.",
                )
                return {"FINISHED"}

        # Clean the existing morph settings
        if self.clear_existing_morphs:
            for section in morphs_settings.sections:
                section.morphs.clear()

        properties_number = 0

        if (
            morphs_settings.type == "DIFFEO_GENESIS_8"
            or morphs_settings.type == "DIFFEO_GENESIS_9"
        ):
            # TYPE: 0: Emotion Units, 1: Emotions, 2: FACS Emotion Units,
            # 3: FACS Emotions, 4: Body Morphs

            # Default lists
            facs_emotions_default_list = [
                "facs_ctrl_Afraid",
                "facs_ctrl_Angry",
                "facs_ctrl_Flirting",
                "facs_ctrl_Frown",
                "facs_ctrl_Shock",
                "facs_ctrl_SmileFullFace",
                "facs_ctrl_SmileOpenFullFace",
                "facs_ctrl_Surprised",
            ]

            # Emotions Units
            mustardui_add_section(
                morphs_settings.sections,
                ["Emotion Units"],
                is_internal=True,
                diffeomorphic=0,
            )
            if (
                morphs_settings.diffeomorphic_emotions_units
                and morphs_settings.type == "DIFFEO_GENESIS_8"
            ):
                emotions_units = [
                    x
                    for x in rig_settings.model_armature_object.keys()
                    if ("eCTRL" in x or "ECTRL" in x)
                    and "HD" not in x
                    and "eCTRLSmile" not in x
                    and "eCTRLv" not in x
                    and sum(1 for c in x if c.isupper()) >= 6
                ]

                for emotion in emotions_units:
                    name = emotion[len("eCTRL")] + "".join(
                        [
                            c if not c.isupper() else " " + c
                            for c in emotion[len("eCTRL") + 1 :]
                        ]
                    )
                    mustardui_add_morph(
                        morphs_settings.sections[0].morphs, [name, emotion]
                    )

                morphs_settings.sections[0].freezable = False

            # Emotions
            mustardui_add_section(
                morphs_settings.sections,
                ["Emotions"],
                is_internal=True,
                diffeomorphic=1,
            )
            if (
                morphs_settings.diffeomorphic_emotions
                and morphs_settings.type == "DIFFEO_GENESIS_8"
            ):
                emotions = [
                    x
                    for x in rig_settings.model_armature_object.keys()
                    if "eCTRL" in x
                    and "HD" not in x
                    and "eCTRLv" not in x
                    and (sum(1 for c in x if c.isupper()) < 6 or "eCTRLSmile" in x)
                ]

                # Custom Diffeomorphic emotions
                emotions_custom = []
                emotions_custom_strings = [
                    x
                    for x in morphs_settings.diffeomorphic_emotions_custom.split(",")
                    if x != ""
                ]
                for string in emotions_custom_strings:
                    for x in [
                        x
                        for x in rig_settings.model_armature_object.keys()
                        if "Adjust Custom" not in x
                    ]:
                        if string in x:
                            emotions_custom.append(x)

                for emotion in emotions:
                    name = emotion[len("eCTRL")] + "".join(
                        [
                            c if not c.isupper() else " " + c
                            for c in emotion[len("eCTRL") + 1 :]
                        ]
                    )
                    mustardui_add_morph(
                        morphs_settings.sections[1].morphs, [name, emotion]
                    )
                for emotion in emotions_custom:
                    mustardui_add_morph(
                        morphs_settings.sections[1].morphs,
                        [rename_morph(self, emotion, emotions_custom_strings), emotion],
                    )

            # FACS Emotions Units
            sec = (
                "Advanced Emotion Units"
                if morphs_settings.type == "DIFFEO_GENESIS_8"
                else "Emotion Units"
            )
            mustardui_add_section(
                morphs_settings.sections, [sec], is_internal=True, diffeomorphic=2
            )
            if morphs_settings.diffeomorphic_facs_emotions_units:
                facs_emotions_units = []
                facs_emotions_units.append(
                    [
                        x
                        for x in rig_settings.model_armature_object.keys()
                        if "facs_ctrl_" in x and x not in facs_emotions_default_list
                    ]
                )
                facs_emotions_units.append(
                    [
                        x
                        for x in rig_settings.model_armature_object.keys()
                        if "facs_bs_" in x and sum(1 for c in x if c.isupper()) >= 2
                    ]
                )
                facs_emotions_units.append(
                    [
                        x
                        for x in rig_settings.model_armature_object.keys()
                        if "facs_jnt_" in x and sum(1 for c in x if c.isupper()) >= 2
                    ]
                )
                facs_emotions_units = itertools.chain.from_iterable(facs_emotions_units)

                for emotion in facs_emotions_units:
                    name = emotion[emotion.rfind("_", 0, 12) + 1] + "".join(
                        [
                            c if not c.isupper() else " " + c
                            for c in emotion[emotion.rfind("_", 0, 12) + 2 :]
                        ]
                    )
                    name = name.removesuffix("_div2")
                    mustardui_add_morph(
                        morphs_settings.sections[2].morphs, [name, emotion]
                    )

                morphs_settings.sections[2].freezable = False

            # FACS Emotions
            sec = (
                "Advanced Emotions"
                if morphs_settings.type == "DIFFEO_GENESIS_8"
                else "Emotions"
            )
            mustardui_add_section(
                morphs_settings.sections, [sec], is_internal=True, diffeomorphic=3
            )
            if morphs_settings.diffeomorphic_facs_emotions:
                facs_emotions = [
                    x
                    for x in rig_settings.model_armature_object.keys()
                    if x in facs_emotions_default_list
                ]

                # For Genesis 9, add also custom emotions to the panel
                emotions_custom = []
                emotions_custom_strings = [
                    x
                    for x in morphs_settings.diffeomorphic_emotions_custom.split(",")
                    if x != ""
                ]
                if morphs_settings.type == "DIFFEO_GENESIS_9":
                    emotions_custom = []
                    for string in emotions_custom_strings:
                        for x in [
                            x
                            for x in rig_settings.model_armature_object.keys()
                            if "Adjust Custom" not in x
                        ]:
                            if string in x:
                                emotions_custom.append(x)

                for emotion in facs_emotions:
                    name = emotion[len("facs_ctrl_")] + "".join(
                        [
                            c if not c.isupper() else " " + c
                            for c in emotion[len("facs_ctrl_") + 1 :]
                        ]
                    )
                    mustardui_add_morph(
                        morphs_settings.sections[3].morphs, [name, emotion]
                    )

                for emotion in emotions_custom:
                    mustardui_add_morph(
                        morphs_settings.sections[3].morphs,
                        [rename_morph(self, emotion, emotions_custom_strings), emotion],
                    )

            # Body Morphs for Genesis 8
            mustardui_add_section(
                morphs_settings.sections, ["Body"], is_internal=True, diffeomorphic=4
            )
            if morphs_settings.diffeomorphic_body_morphs:
                body_morphs_FBM = [
                    x
                    for x in rig_settings.model_armature_object.keys()
                    if x.startswith("FBM")
                    and sum(1 for c in x if c.isdigit()) < 1
                    and sum(1 for c in x if c.isupper()) < 6
                ]
                body_morphs_bs = [
                    x
                    for x in rig_settings.model_armature_object.keys()
                    if x.startswith("body_bs_")
                    and sum(1 for c in x if c.isdigit()) < 1
                    and sum(1 for c in x if c.isupper()) < 6
                ]
                body_morphs_CTRLB = [
                    x
                    for x in rig_settings.model_armature_object.keys()
                    if "CTRLBreasts" in x
                    and "pCTRLBreasts" not in x
                    and sum(1 for c in x if c.isupper()) < 10
                ]
                body_morphs_ctrl = [
                    x
                    for x in rig_settings.model_armature_object.keys()
                    if x.startswith("body_ctrl_")
                    and sum(1 for c in x if c.isdigit()) < 1
                    and sum(1 for c in x if c.isupper()) < 6
                ]
                body_morphs_PBM = [
                    x
                    for x in rig_settings.model_armature_object.keys()
                    if "PBMBreasts" in x and sum(1 for c in x if c.isupper()) < 10
                ]

                # Custom Diffeomorphic emotions
                body_morphs_custom = []
                body_morphs_custom_strings = [
                    x
                    for x in morphs_settings.diffeomorphic_body_morphs_custom.split(",")
                    if x != ""
                ]
                for string in body_morphs_custom_strings:
                    for x in [
                        x
                        for x in rig_settings.model_armature_object.keys()
                        if "Adjust Custom" not in x
                    ]:
                        if string in x:  # and sum(1 for c in x if c.isupper()) < 6:
                            body_morphs_custom.append(x)

                for morph in body_morphs_FBM:
                    name = morph[len("FBM")] + "".join(
                        [
                            c if not c.isupper() else " " + c
                            for c in morph[len("FBM") + 1 :]
                        ]
                    )
                    mustardui_add_morph(
                        morphs_settings.sections[4].morphs, [name, morph]
                    )
                for morph in body_morphs_bs:
                    name = morph[len("body_bs_")] + "".join(
                        [
                            c if not c.isupper() else " " + c
                            for c in morph[len("body_bs_") + 1 :]
                        ]
                    )
                    mustardui_add_morph(
                        morphs_settings.sections[4].morphs, [name, morph]
                    )
                for morph in body_morphs_CTRLB:
                    name = morph[len("CTRL")] + "".join(
                        [
                            c if not c.isupper() else " " + c
                            for c in morph[len("CTRL") + 1 :]
                        ]
                    )
                    mustardui_add_morph(
                        morphs_settings.sections[4].morphs, [name, morph]
                    )
                for morph in body_morphs_ctrl:
                    name = morph[len("body_ctrl_")] + "".join(
                        [
                            c if not c.isupper() else " " + c
                            for c in morph[len("body_ctrl_") + 1 :]
                        ]
                    )
                    mustardui_add_morph(
                        morphs_settings.sections[4].morphs, [name, morph]
                    )
                for morph in body_morphs_PBM:
                    name = morph[len("PBM")] + "".join(
                        [
                            c if not c.isupper() else " " + c
                            for c in morph[len("PBM") + 1 :]
                        ]
                    )
                    mustardui_add_morph(
                        morphs_settings.sections[4].morphs, [name, morph]
                    )
                for morph in body_morphs_custom:
                    morph_name = morph
                    if self.custom_rename:
                        morph_name = re.sub(r"_body_bs_", " ", morph_name)
                        morph_name = re.sub(r"_body_cbs_", " ", morph_name)
                    morph_name = rename_morph(
                        self, morph_name, body_morphs_custom_strings
                    )
                    mustardui_add_morph(
                        morphs_settings.sections[4].morphs, [morph_name, morph]
                    )

            # Set the Genesis version
            morphs_settings.diffeomorphic_genesis_version = (
                8 if morphs_settings.type == "DIFFEO_GENESIS_8" else 9
            )

        for i, section in enumerate(morphs_settings.sections):
            shape_keys = section.shape_keys
            custom_properties = section.custom_properties
            custom_properties_source = section.custom_properties_source
            string = section.string

            strings = string.split(",")

            if custom_properties:
                cp_source = get_cp_source(custom_properties_source, rig_settings)
                if cp_source is None:
                    continue
                custom_props = [
                    x for x in cp_source.keys() if any(s in x for s in strings)
                ]
                for morph in custom_props:
                    mustardui_add_morph(
                        morphs_settings.sections[i].morphs,
                        [rename_morph(self, morph), morph],
                        custom_property=True,
                        custom_property_source=custom_properties_source,
                    )

            body_sks = rig_settings.model_body.data.shape_keys
            if shape_keys and body_sks is not None:
                sks = [
                    x for x in body_sks.key_blocks if any(s in x.name for s in strings)
                ]

                # Disable the freezable setting as it would work on the Mute
                # button which is now blocked by the driver
                # Note: Enable Freeze Morphs might still be enabled for Diffeomorphic
                # Morphs
                if not section.is_internal:
                    section.freezable = False

                for sk in sks:
                    morph = sk.name
                    mustardui_add_morph(
                        morphs_settings.sections[i].morphs,
                        [rename_morph(self, morph), morph],
                        custom_property=False,
                    )

                    # Add automatic mute driver
                    if self.add_shape_key_mute_driver:
                        # Remove existing driver if present
                        try:
                            sk.driver_remove("mute")
                        except Exception:
                            pass

                        fcurve = sk.driver_add("mute")
                        driver = fcurve.driver
                        driver.type = "SCRIPTED"
                        var = driver.variables.new()
                        var.name = "var"
                        target = var.targets[0]
                        target.id_type = "KEY"
                        target.id = body_sks
                        target.data_path = f'key_blocks["{morph}"].value'
                        driver.expression = "abs(var) < 0.001"
                    # Otherwise remove the mute driver
                    else:
                        try:
                            driver_path = f'key_blocks["{sk.name}"].mute'
                            fcurve = body_sks.animation_data.drivers.find(driver_path)
                            if fcurve:
                                drv = fcurve.driver
                                if (
                                    drv.type == "SCRIPTED"
                                    and drv.expression == "abs(var) < 0.001"
                                ):
                                    body_sks.driver_remove(driver_path)
                            # Unmute if muted
                            body_sks.key_blocks[sk.name].mute = False
                        except Exception:
                            pass

        # Save the status of the mute drivers on Shape Keys
        morphs_settings.use_shape_key_mute_drivers = self.add_shape_key_mute_driver

        morphs_settings.diffeomorphic_genesis_version = (
            -1
            if morphs_settings.type == "GENERIC"
            else morphs_settings.diffeomorphic_genesis_version
        )

        if addon_prefs.debug:
            print("\nMustardUI - Morphs found\n")

        # Print the options
        for section in morphs_settings.sections:
            for morph in section.morphs:
                if addon_prefs.debug:
                    print(
                        f"  {repr(morph.name)} in section: {repr(section.name)} "
                        f"(name: {repr(morph.path)})"
                    )
                properties_number = properties_number + 1

        morphs_settings.morphs_number = properties_number

        if properties_number:
            self.report({"INFO"}, "MustardUI - Morphs check completed.")
        else:
            self.report({"WARNING"}, "MustardUI - No Morph found.")

        return {"FINISHED"}

    def invoke(self, context, event):
        res, arm = mustardui_active_object(context, config=1)
        morphs_settings = arm.MustardUI_MorphsSettings

        if morphs_settings.diffeomorphic_genesis_version == 8:
            morphs_settings.type = "DIFFEO_GENESIS_8"
        elif morphs_settings.diffeomorphic_genesis_version == 9:
            morphs_settings.type = "DIFFEO_GENESIS_9"

        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):

        res, arm = mustardui_active_object(context, config=1)
        morphs_settings = arm.MustardUI_MorphsSettings

        layout = self.layout

        box = layout.box()
        col = box.column()
        col.label(text="Settings", icon="MODIFIER")

        col.prop(self, "custom_rename")
        col.prop(self, "clear_existing_morphs")

        row = col.row()
        row.enabled = any(section.shape_keys for section in morphs_settings.sections)
        row.prop(self, "add_shape_key_mute_driver")

        if morphs_settings.type in ["DIFFEO_GENESIS_8", "DIFFEO_GENESIS_9"]:
            box = layout.box()
            col = box.column()
            col.label(text="Diffeomorphic Morphs", icon="SHAPEKEY_DATA")

            if morphs_settings.type == "DIFFEO_GENESIS_8":
                col.prop(morphs_settings, "diffeomorphic_emotions_units")
                col.prop(morphs_settings, "diffeomorphic_emotions")

                row = col.row(align=True)
                row.enabled = morphs_settings.diffeomorphic_emotions
                row.label(text="Custom morphs")
                row.scale_x = row_scale
                row.prop(morphs_settings, "diffeomorphic_emotions_custom", text="")

            if morphs_settings.type == "DIFFEO_GENESIS_8":
                col.prop(morphs_settings, "diffeomorphic_facs_emotions_units")
                col.prop(morphs_settings, "diffeomorphic_facs_emotions")
            else:
                col.prop(
                    morphs_settings,
                    "diffeomorphic_facs_emotions_units",
                    text="Emotions Units Morphs",
                )
                col.prop(
                    morphs_settings,
                    "diffeomorphic_facs_emotions",
                    text="Emotions Morphs",
                )

                row = col.row(align=True)
                row.enabled = morphs_settings.diffeomorphic_facs_emotions
                row.label(text="Custom morphs")
                row.scale_x = row_scale
                row.prop(morphs_settings, "diffeomorphic_emotions_custom", text="")

            col.prop(morphs_settings, "diffeomorphic_body_morphs")

            row = col.row(align=True)
            row.enabled = morphs_settings.diffeomorphic_body_morphs
            row.label(text="Custom morphs")
            row.scale_x = row_scale
            row.prop(morphs_settings, "diffeomorphic_body_morphs_custom", text="")


def register():
    bpy.utils.register_class(MustardUI_Morphs_Check)
    bpy.utils.register_class(MustardUI_Morphs_Clear)


def unregister():
    bpy.utils.unregister_class(MustardUI_Morphs_Clear)
    bpy.utils.unregister_class(MustardUI_Morphs_Check)
