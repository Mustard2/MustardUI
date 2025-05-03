import bpy
from .settings_morph import *
from .settings_section import *


morphs_check_items = [("GENERIC", "Generic", "Generic"),
                      ("DIFFEO_GENESIS_8", "Diffeomorphic Genesis 8", "Diffeomorphic Genesis 8"),
                      ("DIFFEO_GENESIS_9", "Diffeomorphic Genesis 9", "Diffeomorphic Genesis 9")]


# Function to update global collection properties
def diffeomorphic_enable_update(self, context):

    if self.diffeomorphic_enable:
        bpy.ops.mustardui.morphs_enabledrivers()
    else:
        self.diffeomorphic_enable_settings = False
        bpy.ops.mustardui.morphs_disabledrivers()


class MustardUI_MorphsSettings(bpy.types.PropertyGroup):
    # CONFIGURATION

    enable_ui: bpy.props.BoolProperty(default=False,
                                      name="Diffeomorphic",
                                      description="Enable Diffeomorphic support.\nIf enabled, standard "
                                                  "morphs from Diffomorphic will be added to the UI")

    type: bpy.props.EnumProperty(items=morphs_check_items,
                                 default="DIFFEO_GENESIS_8",
                                 description="Type of Morphs to add.\nIf Morphs are already available, this setting can not be changed. Clear the Morphs before changing this setting",
                                 name="Morphs Type")

    show_type_icon: bpy.props.BoolProperty(default=False,
                                           name="Show Type Icon",
                                           description="Show Morph type icon in the UI")

    # INTERNAL

    morphs_number: bpy.props.IntProperty(default=0)

    is_diffeomorphic: bpy.props.BoolProperty(default=False)
    diffeomorphic_genesis_version: bpy.props.IntProperty(default=0)

    sections: bpy.props.CollectionProperty(type=MustardUI_Morph_Section)



    # DIFFEOMORPHIC support

    # Switcher for Morphs (drivers, shape keys, etc..) in the Diffeomorphic case
    diffeomorphic_enable: bpy.props.BoolProperty(default=True,
                                                 name="Enable Morphs",
                                                 description="Enabling morphs might affect performance. You can "
                                                             "disable them to increase performance",
                                                 update=diffeomorphic_enable_update)

    # Panel morph search filters
    diffeomorphic_search: bpy.props.StringProperty(name="",
                                                   description="Search for a specific morph",
                                                   default="")
    diffeomorphic_filter_null: bpy.props.BoolProperty(default=False,
                                                      name="Filter morphs",
                                                      description="Filter used morphs.\nOnly non null morphs will be "
                                                                  "shown")

    # Settings panel for switching on/off morphs
    diffeomorphic_enable_settings: bpy.props.BoolProperty(default=False,
                                                          name="Morph Settings",
                                                          description="Show the Morph Settings panel")
    diffeomorphic_enable_shapekeys: bpy.props.BoolProperty(default=True,
                                                           name="Mute Shape Keys",
                                                           description="Shape Keys will also be muted when the Morphs "
                                                                       "are disabled")
    diffeomorphic_enable_facs: bpy.props.BoolProperty(default=True,
                                                      name="Mute Face Controls",
                                                      description="Face Controls will also be muted when the Morphs "
                                                                  "are disabled")
    diffeomorphic_enable_facs_bones: bpy.props.BoolProperty(default=True,
                                                            name="Mute Face Controls Bones",
                                                            description="Bones for Face Controls will also be muted "
                                                                        "when the Morphs are disabled.\nDisabling "
                                                                        "this option, Jaw and Eyes Face controls will "
                                                                        "work correctly, at the price of performance "
                                                                        "decrease.\nNote: if Mute Face Controls is "
                                                                        "enabled, bones will always be disabled")
    diffeomorphic_enable_pJCM: bpy.props.BoolProperty(default=True,
                                                      name="Mute Corrective Morphs",
                                                      description="Corrective Morphs will also be muted when the "
                                                                  "Morphs are disabled")
    diffeomorphic_disable_exceptions: bpy.props.StringProperty(default="",
                                                               name="Exceptions",
                                                               description="Morphs that will not be disabled when "
                                                                           "morphs are disabled.\nAdd strings to add "
                                                                           "morphs (they should map the initial part "
                                                                           "of the name of the morph), separated by "
                                                                           "commas.\nNote: spaces and order are "
                                                                           "considered")

    # Settings to import Diffeomorphic Morphs
    diffeomorphic_emotions: bpy.props.BoolProperty(default=False,
                                                   name="Emotions Morphs",
                                                   description="Search for Diffeomorphic emotions")

    diffeomorphic_emotions_custom: bpy.props.StringProperty(default="",
                                                            name="Custom morphs",
                                                            description="Add strings to add custom morphs (they "
                                                                        "should map the initial part of the name of "
                                                                        "the morph), separated by commas.\nNote: "
                                                                        "spaces and order are considered")

    diffeomorphic_facs_emotions: bpy.props.BoolProperty(default=False,
                                                        name="FACS Emotions Morphs",
                                                        description="Search for Diffeomorphic FACS emotions.\nThese "
                                                                    "morphs will be shown as Advanced Emotions in the"
                                                                    " UI")

    diffeomorphic_emotions_units: bpy.props.BoolProperty(default=False,
                                                         name="Emotions Units Morphs",
                                                         description="Search for Diffeomorphic emotions units")

    diffeomorphic_facs_emotions_units: bpy.props.BoolProperty(default=False,
                                                              name="FACS Emotions Units Morphs",
                                                              description="Search for Diffeomorphic FACS emotions "
                                                                          "units.\nThese morphs will be shown as "
                                                                          "Advanced Emotion Units in the UI")

    diffeomorphic_body_morphs: bpy.props.BoolProperty(default=False,
                                                      name="Body Morphs Morphs",
                                                      description="Search for Diffeomorphic Body morphs")

    diffeomorphic_body_morphs_custom: bpy.props.StringProperty(default="",
                                                               name="Custom morphs",
                                                               description="Add strings to add custom morphs (they "
                                                                           "should map the initial part of the name "
                                                                           "of the morph), separated by "
                                                                           "commas.\nNote: spaces and order are "
                                                                           "considered")


def register():
    bpy.utils.register_class(MustardUI_MorphsSettings)
    bpy.types.Armature.MustardUI_MorphsSettings = bpy.props.PointerProperty(type=MustardUI_MorphsSettings)


def unregister():
    del bpy.types.Armature.MustardUI_MorphsSettings
    bpy.utils.unregister_class(MustardUI_MorphsSettings)
