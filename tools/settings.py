from bpy.props import *
from ..model_selection.active_object import *
from ..misc.message_box import *


class MustardUI_ToolsSettings(bpy.types.PropertyGroup):
    # Property for collapsing tools properties section
    tools_config_collapse: BoolProperty(default=True,
                                        name="")

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

    # ------------------------------------------------------------------------
    #    Tools - Lips Shrinkwrap
    # ------------------------------------------------------------------------

    def lips_shrinkwrap_bones_corner_list(context, rig_type, armature):

        if rig_type == "arp":
            return ['c_lips_smile.r', 'c_lips_smile.l']
        elif rig_type == "mhx":
            if "LipCorner.l" in [x.name for x in armature.bones]:
                return ['LipCorner.l', 'LipCorner.r']
            else:
                return ['LipCorner.L', 'LipCorner.R']
        else:
            return []

    def lips_shrinkwrap_bones_list(context, rig_type, armature):

        if rig_type == "arp":
            return ['c_lips_smile.r', 'c_lips_top.r', 'c_lips_top_01.r', 'c_lips_top.x', 'c_lips_top.l',
                    'c_lips_top_01.l', 'c_lips_smile.l', 'c_lips_bot.r', 'c_lips_bot_01.r', 'c_lips_bot.x',
                    'c_lips_bot.l', 'c_lips_bot_01.l']
        elif rig_type == "mhx":
            if "LipCorner.l" in [x.name for x in armature.bones]:
                return ['LipCorner.l', 'LipLowerOuter.l', 'LipLowerInner.l', 'LipLowerMiddle', 'LipLowerInner.r',
                        'LipLowerOuter.r', 'LipCorner.r', 'LipUpperMiddle', 'LipUpperOuter.l', 'LipUpperInner.l',
                        'LipUpperInner.r', 'LipUpperOuter.r']
            elif "LipCorner.L" in [x.name for x in armature.bones]:
                return ['LipCorner.L', 'LipLowerOuter.L', 'LipLowerInner.L', 'LipLowerMiddle', 'LipLowerInner.R',
                        'LipLowerOuter.R', 'LipCorner.R', 'LipUpperMiddle', 'LipUpperOuter.L', 'LipUpperInner.L',
                        'LipUpperInner.R', 'LipUpperOuter.R']
            elif "lipCorner.l" in [x.name for x in armature.bones]:
                return ['lipCorner.l', 'lipLowerOuter.l', 'lipLowerInner.l', 'lipLowerMiddle', 'lipLowerInner.r',
                        'lipLowerOuter.r', 'lipCorner.r', 'lipUpperMiddle', 'lipUpperOuter.l', 'lipUpperInner.l',
                        'lipUpperInner.r', 'lipUpperOuter.r']
            elif "lipCorner.L" in [x.name for x in armature.bones]:
                return ['lipCorner.L', 'lipLowerOuter.L', 'lipLowerInner.L', 'lipLowerMiddle', 'lipLowerInner.R',
                        'lipLowerOuter.R', 'lipCorner.R', 'lipUpperMiddle', 'lipUpperOuter.L', 'lipUpperInner.L',
                        'lipUpperInner.R', 'lipUpperOuter.R']
            else:
                return []
        else:
            return []

    def lips_shrinkwrap_update(self, context):

        poll, arm = mustardui_active_object(context, config=0)
        rig_type = arm.MustardUI_RigSettings.model_rig_type

        if self.lips_shrinkwrap_armature_object is not None:
            armature = self.lips_shrinkwrap_armature_object
        else:
            ShowMessageBox("Fatal error", "MustardUI Information", icon="ERROR")

        bones_lips = self.lips_shrinkwrap_bones_list(rig_type, arm)
        if not bones_lips:
            ShowMessageBox("Fatal error", "MustardUI Information", icon="ERROR")

        ob = bpy.context.active_object

        if self.lips_shrinkwrap and self.lips_shrinkwrap_obj:

            for bone in bones_lips:

                constr_check = False

                if not (0 < len([m for m in armature.pose.bones[bone].constraints if m.type == "SHRINKWRAP"])):
                    constr = armature.pose.bones[bone].constraints.new('SHRINKWRAP')
                    constr.name = self.lips_shrink_constr_name
                    constr_check = True

                elif not constr_check:
                    for c in armature.pose.bones[bone].constraints:
                        if c.name == self.lips_shrink_constr_name:
                            constr_check = True
                            break

                if not constr_check:
                    constr = armature.pose.bones[bone].constraints.new('SHRINKWRAP')
                    constr.name = self.lips_shrink_constr_name

                constr = armature.pose.bones[bone].constraints[self.lips_shrink_constr_name]
                constr.target = self.lips_shrinkwrap_obj

                constr.wrap_mode = "OUTSIDE"
                constr.distance = self.lips_shrinkwrap_dist

                if bone in self.lips_shrinkwrap_bones_corner_list(rig_type, arm):
                    constr.distance = constr.distance * self.lips_shrinkwrap_dist_corr

            if self.lips_shrinkwrap_friction and ob == armature:

                for bone in bones_lips:

                    constr_check = False

                    if not (0 < len([m for m in armature.pose.bones[bone].constraints if m.type == "CHILD_OF"])):
                        constr = armature.pose.bones[bone].constraints.new('CHILD_OF')
                        constr.name = self.lips_shrink_constr_name + '_fric'
                        constr_check = True

                    elif not constr_check:
                        for c in armature.pose.bones[bone].constraints:
                            if c.name == self.lips_shrink_constr_name + '_fric':
                                constr_check = True
                                break

                    if not constr_check:
                        constr = armature.pose.bones[bone].constraints.new('CHILD_OF')
                        constr.name = self.lips_shrink_constr_name + '_fric'

                    constr = armature.pose.bones[bone].constraints[self.lips_shrink_constr_name + '_fric']
                    if self.lips_shrinkwrap_obj_fric:
                        constr.target = self.lips_shrinkwrap_obj_fric
                        constr.subtarget = self.lips_shrinkwrap_obj_fric_sec
                    else:
                        constr.target = self.lips_shrinkwrap_obj
                    constr.use_scale_x = False
                    constr.use_scale_y = False
                    constr.use_scale_z = False

                    context_py = bpy.context.copy()
                    context_py["constraint"] = constr

                    org_layers = ob.data.layers[:]
                    for i in range(len(org_layers)):
                        ob.data.layers[i] = True

                    ob.data.bones.active = armature.pose.bones[bone].bone

                    for i in range(len(org_layers)):
                        ob.data.layers[i] = org_layers[i]

                    constr.influence = self.lips_shrinkwrap_friction_infl

            elif self.lips_shrinkwrap and self.lips_shrinkwrap_friction and ob != armature:

                ShowMessageBox("You must select any model armature bone, in Pose mode, to apply the friction.",
                               "MustardUI Information", icon="ERROR")

            else:

                for bone in bones_lips:
                    for c in armature.pose.bones[bone].constraints:
                        if c.name == self.lips_shrink_constr_name + '_fric':
                            to_remove = armature.pose.bones[bone].constraints[self.lips_shrink_constr_name + '_fric']
                            armature.pose.bones[bone].constraints.remove(to_remove)

        elif self.lips_shrinkwrap and not self.lips_shrinkwrap_obj:

            self.lips_shrinkwrap = False
            ShowMessageBox("Select an Object. No modifier has been added", "MustardUI Information")

        else:

            for bone in bones_lips:
                for c in armature.pose.bones[bone].constraints:
                    if self.lips_shrink_constr_name in c.name:
                        to_remove = armature.pose.bones[bone].constraints[c.name]
                        armature.pose.bones[bone].constraints.remove(to_remove)

        return

    def lips_shrinkwrap_distance_update(self, context):

        poll, arm = mustardui_active_object(context, config=0)
        rig_type = arm.MustardUI_RigSettings.model_rig_type

        if self.lips_shrinkwrap_armature_object is not None and arm is not None:
            armature = self.lips_shrinkwrap_armature_object
        else:
            ShowMessageBox("Fatal error", "MustardUI Information", icon="ERROR")

        bones_lips = self.lips_shrinkwrap_bones_list(rig_type, arm)

        if self.lips_shrinkwrap:

            for bone in bones_lips:

                constr = armature.pose.bones[bone].constraints[self.lips_shrink_constr_name]
                constr.distance = self.lips_shrinkwrap_dist

                if bone in self.lips_shrinkwrap_bones_corner_list(rig_type, arm):
                    constr.distance = constr.distance * self.lips_shrinkwrap_dist_corr

        return

    def lips_shrinkwrap_friction_infl_update(self, context):

        poll, arm = mustardui_active_object(context, config=0)
        rig_type = arm.MustardUI_RigSettings.model_rig_type

        if self.lips_shrinkwrap_armature_object is not None and arm is not None:
            armature = self.lips_shrinkwrap_armature_object
        else:
            ShowMessageBox("Fatal error", "MustardUI Information", icon="ERROR")

        bones_lips = self.lips_shrinkwrap_bones_list(rig_type, arm)

        if self.lips_shrinkwrap_friction and self.lips_shrinkwrap:

            for bone in bones_lips:
                constr = armature.pose.bones[bone].constraints[self.lips_shrink_constr_name + '_fric']
                constr.influence = self.lips_shrinkwrap_friction_infl

        return

    def lips_shrinkwrap_obj_sec_poll(self, object):

        if self.lips_shrinkwrap_obj.type == 'MESH':

            return object.type == 'VERTEXGROUP'

        else:

            return object.type == 'EMPTY'

        return

    # Config enable
    lips_shrinkwrap_enable: BoolProperty(default=False,
                                         name="Lips Shrinkwrap",
                                         description="Enable Lips shrinkwrap tool.\nThis can be added only on ARP and "
                                                     "MHX rigs")

    # Poll function for the selection of mesh only in pointer properties
    def poll_armature(self, object):
        return object.type == 'ARMATURE'

    lips_shrink_constr_name: StringProperty(default="MustardUI_lips_shrink_constr")

    lips_shrinkwrap_armature_object: PointerProperty(type=bpy.types.Object,
                                                     name="Armature Object",
                                                     description="Set the armature object.\nThis should be the "
                                                                 "Armature Object of the main model",
                                                     poll=poll_armature)

    lips_shrinkwrap: BoolProperty(default=False,
                                  name="Enable",
                                  description="Enable lips shrinkwrap",
                                  update=lips_shrinkwrap_update)

    lips_shrinkwrap_friction: BoolProperty(default=False,
                                           name="Enable Friction",
                                           description="Enable friction to lips shrinkwrap.",
                                           update=lips_shrinkwrap_update)

    lips_shrinkwrap_dist: FloatProperty(default=0.01,
                                        min=0.0,
                                        name="Distance",
                                        description="Set the distance of the lips bones to the Object",
                                        update=lips_shrinkwrap_distance_update)

    lips_shrinkwrap_dist_corr: FloatProperty(default=1.0,
                                             min=0.0, max=2.0,
                                             name="Outer bones correction",
                                             description="Set the correction of the outer mouth bones to adjust the "
                                                         "result.\nThis value is the fraction of the distance that "
                                                         "will be applied to the outer bones shrinkwrap modifiers",
                                             update=lips_shrinkwrap_distance_update)

    lips_shrinkwrap_friction_infl: FloatProperty(default=0.1,
                                                 min=0.0, max=1.0,
                                                 name="Coefficient",
                                                 description="Set the friction coefficient of the lips "
                                                             "shrinkwrap.\nIf the coefficient is 1, the bone will "
                                                             "follow the Object completely",
                                                 update=lips_shrinkwrap_friction_infl_update)

    lips_shrinkwrap_obj: PointerProperty(type=bpy.types.Object,
                                         name="Object",
                                         description="Select the object where to apply the lips shrinkwrap",
                                         update=lips_shrinkwrap_update)

    lips_shrinkwrap_obj_fric: PointerProperty(type=bpy.types.Object,
                                              name="Object",
                                              description="Select the object to use as a reference for the friction "
                                                          "effect.\nIf no object is selected, the same object "
                                                          "inserted in the main properties will be used",
                                              update=lips_shrinkwrap_update)

    lips_shrinkwrap_obj_fric_sec: StringProperty(name="Sub-target")


def register():
    bpy.utils.register_class(MustardUI_ToolsSettings)
    bpy.types.Armature.MustardUI_ToolsSettings = PointerProperty(type=MustardUI_ToolsSettings)


def unregister():
    bpy.utils.unregister_class(MustardUI_ToolsSettings)
