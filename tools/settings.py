from bpy.props import *
from ..model_selection.active_object import *


class MustardUI_ToolsSettings(bpy.types.PropertyGroup):
    # ------------------------------------------------------------------------
    #    Auto - Breath
    # ------------------------------------------------------------------------

    autobreath_enable: BoolProperty(default=False,
                                    name="Auto Breath",
                                    description="Enable the Auto Breath tool.\nThis tool will allow a quick creation "
                                                "of a breathing animation")

    autobreath_frequency: FloatProperty(default=16.0,
                                        min=1.0, max=200.0,
                                        name="Frequency",
                                        description="Breathing frequency in breath/minute")

    autobreath_amplitude: FloatProperty(default=1.0,
                                        min=0.0, max=1.0,
                                        name="Amplitude",
                                        description="Amplitude of the breathing animation")

    autobreath_random: FloatProperty(default=0.01,
                                     min=0.0, max=1.0,
                                     name="Random factor",
                                     description="Randomization of breathing")

    autobreath_sampling: IntProperty(default=1,
                                     min=1, max=24,
                                     name="Sampling",
                                     description="Number of frames beetween two animations key")

    # ------------------------------------------------------------------------
    #    Auto - Eyelid
    # ------------------------------------------------------------------------

    autoeyelid_enable: BoolProperty(default=False,
                                    name="Auto Blink",
                                    description="Enable the Auto Blink tool.\nThis tool will allow a quick creation of eyelid blinking animation")

    autoeyelid_driver_type: EnumProperty(default="SHAPE_KEY",
                                         items=[("SHAPE_KEY", "Shape Key", "Shape Key", "SHAPEKEY_DATA", 0),
                                                ("MORPH", "Morph", "Morph", "OUTLINER_OB_ARMATURE", 1)],
                                         name="Driver type")

    autoeyelid_blink_length: FloatProperty(default=1.,
                                           min=0.1, max=20.0,
                                           name="Blink Length Factor",
                                           description="Increasing this value, you will proportionally increase the "
                                                       "length of the blink from the common values of 0.1-0.25 ms")

    autoeyelid_blink_rate_per_minute: IntProperty(default=26,
                                                  min=1, max=104,
                                                  name="Blink Chance",
                                                  description="Number of blinks per minute.\nNote that some "
                                                              "randomization is included in the tool, therefore the "
                                                              "final realization number might be different")

    autoeyelid_eyeL_shapekey: StringProperty(name="Key",
                                             description="Name of the first shape key to animate (required)")
    autoeyelid_eyeR_shapekey: StringProperty(name="Optional",
                                             description="Name of the second shape key to animate (optional)")
    autoeyelid_morph: StringProperty(name="Morph",
                                     description="The name of the morph should be the name of the custom property in "
                                                 "the Armature object, and not the name of the morph shown in the UI")

    # ------------------------------------------------------------------------
    #    Lips Shrinkwrap
    # ------------------------------------------------------------------------

    bone_shrinkwrap_enable: bpy.props.BoolProperty(name="Lips Shrinkwrap",
                                                   default=False)

    bone_shrinkwrap_target: bpy.props.PointerProperty(
        name="Shrinkwrap Target",
        type=bpy.types.Object,
        description="Object used for shrinkwrap"
    )

    bone_shrinkwrap_target_friction: bpy.props.PointerProperty(
        name="Friction Target",
        type=bpy.types.Object,
        description="Optional separate object for friction"
    )

    bone_shrinkwrap_target_friction_subtarget: bpy.props.StringProperty(
        name="Friction Subtarget",
        description="Bone/vertex group for friction target",
        default=""
    )

    bone_shrinkwrap_enable: bpy.props.BoolProperty(
        name="Enable Lips Shrinkwrap",
        description="Toggle shrinkwrap effect (non-destructive)",
        default=False
    )

    bone_shrinkwrap_enable_friction: bpy.props.BoolProperty(
        name="Enable Friction",
        description="Enable lip sticking/friction",
        default=False
    )

    bone_shrinkwrap_distance: bpy.props.FloatProperty(
        name="Distance",
        description="Shrinkwrap distance",
        default=0.005,
        min=0.0
    )

    bone_shrinkwrap_corner_correction: bpy.props.FloatProperty(
        name="Corner Correction",
        description="Multiplier for corner bones",
        default=1.0,
        min=0.0,
        max=2.0
    )

    bone_shrinkwrap_friction_influence: bpy.props.FloatProperty(
        name="Friction Influence",
        description="How strongly lips stick to target",
        default=0.1,
        min=0.0,
        max=1.0
    )

    # Internal
    bone_shrinkwrap_constraint_tag: bpy.props.StringProperty(
        name="Constraint Tag",
        default="MUSTARDUI_LIPS",
        description="Internal tag for constraint manager"
    )


def register():
    bpy.utils.register_class(MustardUI_ToolsSettings)
    bpy.types.Armature.MustardUI_ToolsSettings = PointerProperty(type=MustardUI_ToolsSettings)


def unregister():
    del bpy.types.Armature.MustardUI_ToolsSettings
    bpy.utils.unregister_class(MustardUI_ToolsSettings)
