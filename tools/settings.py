from bpy.props import *
from ..model_selection.active_object import *


class MustardUI_ToolsSettings(bpy.types.PropertyGroup):
    # ------------------------------------------------------------------------
    #    Child Of
    # ------------------------------------------------------------------------

    childof_enable: BoolProperty(default=False,
                                 name="Child Of",
                                 description="Enable the Child Of tool.\nThis tool will allow a quick creation of "
                                             "Child Of modifiers between two selected bones")

    childof_influence: FloatProperty(default=1.0,
                                     min=0.0, max=1.0,
                                     name="Influence",
                                     description="Set the influence the parent Bone will have on the Child one")

    # Name of the modifiers created by the tool
    childof_constr_name: StringProperty(default='MustardUI_ChildOf')

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


def register():
    bpy.utils.register_class(MustardUI_ToolsSettings)
    bpy.types.Armature.MustardUI_ToolsSettings = PointerProperty(type=MustardUI_ToolsSettings)


def unregister():
    del bpy.types.Armature.MustardUI_ToolsSettings
    bpy.utils.unregister_class(MustardUI_ToolsSettings)
