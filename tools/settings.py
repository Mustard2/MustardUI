import bpy
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)

from ..morphs.settings_morph import cp_source


class MustardUI_ToolsSettings(bpy.types.PropertyGroup):
    # ------------------------------------------------------------------------
    #    Auto - Breath
    # ------------------------------------------------------------------------

    autobreath_enable: BoolProperty(
        default=False,
        name="Auto Breath",
        description="Enable the Auto Breath tool.\nThis tool will allow a quick "
        "creation of a breathing animation",
    )

    autobreath_frequency: FloatProperty(
        default=16.0,
        min=1.0,
        max=200.0,
        name="Frequency",
        description="Breathing frequency in breaths/minute (12-20 at rest)",
    )

    autobreath_amplitude: FloatProperty(
        default=0.05,
        min=0.0,
        max=1.0,
        name="Amplitude",
        description="Peak relative scale/location change at full inhale (resting "
        "breathing is around 0.02-0.05)",
    )

    autobreath_random: FloatProperty(
        default=0.1,
        min=0.0,
        max=1.0,
        name="Random factor",
        description="Breath-to-breath variation of duration and depth",
    )

    autobreath_sampling: IntProperty(
        default=1,
        min=1,
        max=24,
        name="Sampling",
        description="Number of frames between two animations key",
    )

    # ------------------------------------------------------------------------
    #    Auto - Eyelid
    # ------------------------------------------------------------------------

    autoeyelid_enable: BoolProperty(
        default=False,
        name="Auto Blink",
        description="Enable the Auto Blink tool.\nThis tool will allow a quick "
        "creation of eyelid blinking animation",
    )

    autoeyelid_driver_type: EnumProperty(
        default="SHAPE_KEY",
        items=[
            ("SHAPE_KEY", "Shape Key", "Shape Key", "SHAPEKEY_DATA", 0),
            ("MORPH", "Morph", "Morph", "OUTLINER_OB_ARMATURE", 1),
        ],
        name="Driver type",
    )

    autoeyelid_blink_length: FloatProperty(
        default=1.0,
        min=0.1,
        max=20.0,
        name="Blink Length Factor",
        description="Increasing this value, you will proportionally increase the "
        "length of the blink from the common values of 0.1-0.25 ms",
    )

    autoeyelid_blink_rate_per_minute: IntProperty(
        default=26,
        min=1,
        max=104,
        name="Blink Chance",
        description="Number of blinks per minute.\nNote that some "
        "randomization is included in the tool, therefore the "
        "final realization number might be different",
    )

    autoeyelid_eyeL_shapekey: StringProperty(
        name="Key", description="Name of the first shape key to animate (required)"
    )
    autoeyelid_eyeR_shapekey: StringProperty(
        name="Optional",
        description="Name of the second shape key to animate (optional)",
    )
    autoeyelid_morph: StringProperty(
        name="Morph",
        description="The name of the morph should be the name of the custom property "
        "in the Armature object, and not the name of the morph shown in the"
        " UI",
    )

    # ------------------------------------------------------------------------
    #    Lip Sync
    # ------------------------------------------------------------------------

    lipsync_enable: BoolProperty(
        default=False,
        name="Lip Sync",
        description="Enable the Lip Sync tool.\nThis tool will allow a quick creation of "
        "a viseme lip sync animation from text",
    )

    lipsync_driver_type: EnumProperty(
        default="SHAPE_KEY",
        items=[
            ("SHAPE_KEY", "Shape Key", "Visemes are shape keys on the Body", "SHAPEKEY_DATA", 0),
            (
                "MORPH",
                "Morph",
                "Visemes are custom properties, as Morphs",
                "OUTLINER_OB_ARMATURE",
                1,
            ),
        ],
        name="Driver type",
    )

    lipsync_prefix: StringProperty(
        default="facs_ctrl_v",
        name="Prefix",
        description="Prefix of the viseme shape keys/custom properties.\nThe viseme name "
        "is appended to it: AA, EE, EH, ER, F, IH, IY, K, L, M, OW, S, SH, T, TH, UW, W",
    )

    lipsync_source: EnumProperty(
        items=cp_source,
        default="ARMATURE_OBJ",
        name="Source",
        description="Object with the viseme custom properties",
    )

    lipsync_substitutions: StringProperty(
        name="Substitutions",
        description="Drive a viseme with another viseme's shape key/custom property, e.g. "
        "'AA:EH, IY:EE'.\nUseful when a viseme is missing or broken. The replaced viseme "
        "keeps its own strength",
    )

    lipsync_input: EnumProperty(
        default="TEXT",
        items=[
            (
                "TEXT",
                "Text",
                "English text, converted to phonemes with the CMU Pronouncing Dictionary",
                "FONT_DATA",
                0,
            ),
            ("ARPABET", "ARPABET", "ARPABET phonemes separated by spaces", "SORTALPHA", 1),
            (
                "TIMED",
                "Timed",
                "Text datablock with one 'label start end' line per segment (seconds).\n"
                "Label is a viseme or ARPABET phoneme, e.g. from a forced aligner",
                "TIME",
                2,
            ),
        ],
        name="Input",
    )

    lipsync_text: StringProperty(
        default="Hello world, this is a lip sync test.",
        name="Text",
        description="Text to speak",
    )

    lipsync_arpabet: StringProperty(
        default="HH AH L OW W ER L D",
        name="ARPABET",
        description="ARPABET phonemes separated by spaces (stress digits are ignored)",
    )

    lipsync_timed_text: PointerProperty(
        type=bpy.types.Text,
        name="Segments",
        description="Text datablock with one 'label start end' line per segment (seconds)",
    )

    lipsync_speed: FloatProperty(
        default=1.0,
        min=0.1,
        max=5.0,
        name="Speed",
        description="Speech speed.\nNot used with timed segments",
    )

    lipsync_intensity: FloatProperty(
        default=1.0,
        min=0.0,
        soft_max=1.0,
        max=2.0,
        name="Intensity",
        description="Multiplier on the viseme peaks",
    )

    lipsync_smoothing: FloatProperty(
        default=40.0,
        min=0.0,
        max=200.0,
        name="Smoothing",
        description="Smoothing window in ms.\nHigher values give a softer mouth, lower "
        "values crisper consonants. 0 disables smoothing",
    )

    lipsync_interpolation: EnumProperty(
        default="BEZIER",
        items=[
            ("BEZIER", "Bezier", "Smooth interpolation"),
            ("LINEAR", "Linear", "Linear interpolation"),
        ],
        name="Interpolation",
    )

    lipsync_new_action: BoolProperty(
        default=True,
        name="New Action",
        description="Replace the current Action of the target with a new one, named after "
        "the text.\nOther keyframes in the current Action (e.g. Auto Blink) will not "
        "play anymore.\nIf disabled, the viseme keyframes are replaced in the current "
        "Action.\nNot available for Morphs on the Armature Object, whose Action also "
        "holds the body animation",
    )

    # ------------------------------------------------------------------------
    #    Lips Shrinkwrap
    # ------------------------------------------------------------------------

    bone_shrinkwrap_enable: bpy.props.BoolProperty(
        name="Lips Shrinkwrap", description="Enable the Shrinkwrap tool", default=False
    )

    bone_shrinkwrap_target: bpy.props.PointerProperty(
        name="Shrinkwrap Target",
        type=bpy.types.Object,
        description="Object used for shrinkwrap",
    )

    bone_shrinkwrap_target_friction: bpy.props.PointerProperty(
        name="Friction Target",
        type=bpy.types.Object,
        description="Optional separate object for friction",
    )

    bone_shrinkwrap_target_friction_subtarget: bpy.props.StringProperty(
        name="Friction Subtarget",
        description="Bone/vertex group for friction target",
        default="",
    )

    bone_shrinkwrap_enable_friction: bpy.props.BoolProperty(
        name="Enable Friction",
        description="Enable lip sticking/friction",
        default=False,
    )

    bone_shrinkwrap_distance: bpy.props.FloatProperty(
        name="Distance", description="Shrinkwrap distance", default=0.005, min=0.0
    )

    bone_shrinkwrap_corner_correction: bpy.props.FloatProperty(
        name="Corner Correction",
        description="Multiplier for corner bones",
        default=1.0,
        min=0.0,
        max=2.0,
    )

    bone_shrinkwrap_rotation_correction: bpy.props.BoolProperty(
        name="Rotation Correction",
        description="When enabled, rotations are corrected with axis alignment.\nMight"
        " improve the behaviour of the shrinkwrap over lateral movements, "
        "but introduce artifacts in the movement in some rigs or when the "
        "shrinkwrap object is not touching the bones directly",
        default=False,
    )

    bone_shrinkwrap_friction_influence: bpy.props.FloatProperty(
        name="Friction Influence",
        description="How strongly lips stick to target",
        default=0.1,
        min=0.0,
        max=1.0,
    )

    # Internal
    bone_shrinkwrap_constraint_tag: bpy.props.StringProperty(
        name="Constraint Tag",
        default="MUSTARDUI_LIPS",
        description="Internal tag for constraint manager",
    )


def register():
    bpy.utils.register_class(MustardUI_ToolsSettings)
    bpy.types.Armature.MustardUI_ToolsSettings = PointerProperty(type=MustardUI_ToolsSettings)


def unregister():
    del bpy.types.Armature.MustardUI_ToolsSettings
    bpy.utils.unregister_class(MustardUI_ToolsSettings)
