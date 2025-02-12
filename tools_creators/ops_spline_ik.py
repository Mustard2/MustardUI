import bpy
from ..model_selection.active_object import *
from .. import __package__ as base_package


class MustardUI_ToolsCreators_IKSpline(bpy.types.Operator):
    """Create an IK spline on the selected chain.\nSelect the bones, the last one being the tip of the chain.\nThe minimum number of bones is 4"""
    bl_idname = "mustardui.tools_creators_ikspline"
    bl_label = "Create"
    bl_options = {'REGISTER', 'UNDO'}

    ik_spline_number: bpy.props.IntProperty(default=3, min=3, max=20,
                                            name="Controllers",
                                            description="Number of IK spline controllers")
    ik_spline_resolution: bpy.props.IntProperty(default=32, min=1, max=64,
                                                name="Resolution",
                                                description="Resolution of the spline.\nSubdivision performed on each segment of the curve")
    ik_spline_bendy: bpy.props.BoolProperty(name="Bendy Bones",
                                            description="Convert the bones of the chain to bendy bones",
                                            default=False)
    ik_spline_bendy_segments: bpy.props.IntProperty(name="Segments",
                                                    default=2, min=2, max=32,
                                                    description="Number of segments for every bendy bone")

    @classmethod
    def poll(cls, context):

        res, arm = mustardui_active_object(context, config=1)
        if not res:
            return res

        if context.mode != "POSE" or not bpy.context.selected_pose_bones:
            return False
        else:

            chain_bones = bpy.context.selected_pose_bones

            if len(chain_bones) < 3:
                return False
            else:
                abort_aa = False
                for bone in chain_bones:
                    for constraint in bone.constraints:
                        if constraint.type == 'SPLINE_IK':
                            abort_aa = True
                            break
                return not abort_aa

    def execute(self, context):

        addon_prefs = context.preferences.addons[base_package].preferences

        name_prefix = "MustardUI"
        num = self.ik_spline_number

        # Naming convention
        IKSpline_Curve_Name = name_prefix + ".IKSpline.Curve"
        IKSpline_Bone_Name = name_prefix + ".IKSpline.Bone"
        IKSpline_Hook_Modifier_Name = name_prefix + ".IKSpline.Hook"
        IKSpline_Empty_Name = name_prefix + ".IKSpline.Empty"
        IKSpline_Constraint_Name = name_prefix + ".IKSpline"

        # Definitions
        arm = bpy.context.object
        chain_bones = bpy.context.selected_pose_bones
        chain_length = len(chain_bones)
        chain_last_bone = chain_bones[chain_length - 1]

        if self.ik_spline_number > len(chain_bones) - 1:
            self.report({'WARNING'},
                        'MustardUI - The number of bones selected can not be smaller than the number of requested spline bones.')
            return {'FINISHED'}

        # Output a warning if the location has not been applied to the armature
        warning = 0
        if arm.location.x != 0. or arm.location.y != 0. or arm.location.z != 0.:
            self.report({'WARNING'},
                        'MustardUI - The Armature selected seems not to have location applied. This might generate odd results!')
            print("MustardUI IK Spline - Apply the location on the armature with Ctrl+A in Object mode!")
            warning += 1

        if addon_prefs.debug:
            print("MustardUI IK Spline - Armature selected: " + bpy.context.object.name)
            print("MustardUI IK Spline - Chain length: " + str(chain_length))

        # Create the curve in Object mode
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        curveData = bpy.data.curves.new(IKSpline_Curve_Name, type='CURVE')
        curveData.dimensions = '3D'
        curveData.use_path = True

        # Create the path for the curve in Edit mode
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)

        polyline = curveData.splines.new('BEZIER')
        polyline.bezier_points.add(num - 1)

        # Fill the curve with the points, and also create controller bones
        b = []
        b_name = []

        for i in range(0, num - 1):
            # Create the point to insert in the curve, at the head of the bone
            (x, y, z) = (chain_bones[int(chain_length / (num - 1) * i)].head.x,
                         chain_bones[int(chain_length / (num - 1) * i)].head.y,
                         chain_bones[int(chain_length / (num - 1) * i)].head.z)
            polyline.bezier_points[i].co = (x, y, z)
            # Use AUTO to generate handles (should be changed later to ALIGNED to enable rotations)
            polyline.bezier_points[i].handle_right_type = 'AUTO'
            polyline.bezier_points[i].handle_left_type = 'AUTO'

            # Create the controller bone
            b = arm.data.edit_bones.new(IKSpline_Bone_Name)
            b.use_deform = False
            b.head = chain_bones[int(chain_length / (num - 1) * i)].head
            b.tail = chain_bones[int(chain_length / (num - 1) * i)].tail

            # Save the name, as changing context will erase the bone data
            b_name.append(b.name)

        # The same as above, but for the last bone
        i += 1
        (x, y, z) = (chain_bones[chain_length - 1].head.x, chain_bones[chain_length - 1].head.y,
                     chain_bones[chain_length - 1].head.z)
        (x2, y2, z2) = (chain_bones[chain_length - 2].head.x, chain_bones[chain_length - 2].head.y,
                        chain_bones[chain_length - 2].head.z)
        polyline.bezier_points[i].co = (x, y, z)
        polyline.bezier_points[i].handle_right = (x + (x - x2) / 2, y + (y - y2) / 2, z + (z - z2) / 2)
        polyline.bezier_points[i].handle_left = (x2 + (x - x2) / 2, y2 + (y - y2) / 2, z2 + (z - z2) / 2)
        polyline.bezier_points[i].handle_right_type = 'ALIGNED'
        polyline.bezier_points[i].handle_left_type = 'ALIGNED'

        b = arm.data.edit_bones.new(IKSpline_Bone_Name)
        b.use_deform = False
        b.head = chain_bones[chain_length - 1].head
        b.tail = chain_bones[chain_length - 1].tail
        b_name.append(b.name)

        # Enable bendy bones if the option has been selected
        if self.ik_spline_bendy:
            for bone in chain_bones:
                arm.data.edit_bones[bone.name].bbone_segments = self.ik_spline_bendy_segments

            # Switch to B-Bone view for the Armature bones
            arm.data.display_type = "BBONE"

        # GO back to Object mode
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        # Create empties
        e = []
        for i in range(0, num):
            e.append(bpy.data.objects.new(IKSpline_Empty_Name, None))
            e[i].location = curveData.splines[0].bezier_points[i].co
            constraint = e[i].constraints.new('COPY_TRANSFORMS')
            constraint.target = arm
            constraint.subtarget = b_name[i]
            if i == 0:
                e[i].empty_display_type = "SPHERE"
            else:
                e[i].empty_display_type = "CIRCLE"
            bpy.context.collection.objects.link(e[i])
            e[i].hide_render = True
            e[i].hide_viewport = True

        # Set bones custom shape using the Empty default shapes
        bone = arm.pose.bones[b_name[0]]
        bone.custom_shape = e[0]
        bone.use_custom_shape_bone_size = True

        for i in range(1, num):
            bone = arm.pose.bones[b_name[i]]
            bone.custom_shape = e[i]
            bone.use_custom_shape_bone_size = True

        # Create curve object
        curveOB = bpy.data.objects.new(IKSpline_Curve_Name, curveData)

        # Create hook modifiers
        m = []
        for i in range(0, num):
            m.append(curveOB.modifiers.new(IKSpline_Hook_Modifier_Name, 'HOOK'))
            m[i].object = e[i]

        # Link the curve in the scene and use as active object
        bpy.context.collection.objects.link(curveOB)
        context.view_layer.objects.active = curveOB

        # Go in Edit mode
        bpy.ops.object.editmode_toggle()

        # Hook the curve points to the empties
        for i in range(0, num):

            select_index = i
            for j, point in enumerate(curveData.splines[0].bezier_points):
                point.select_left_handle = j == select_index
                point.select_right_handle = j == select_index
                point.select_control_point = j == select_index

            bpy.ops.object.hook_assign(modifier=m[i].name)
            bpy.ops.object.hook_reset(modifier=m[i].name)

            # Change the handle type to ALIGNED to enable rotations
            curveData.splines[0].bezier_points[i].handle_right_type = 'ALIGNED'
            curveData.splines[0].bezier_points[i].handle_left_type = 'ALIGNED'

        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        # Create Spline IK modifier
        IKSplineConstr = chain_last_bone.constraints.new('SPLINE_IK')
        IKSplineConstr.name = IKSpline_Constraint_Name
        IKSplineConstr.target = curveOB
        IKSplineConstr.chain_count = chain_length
        IKSplineConstr.y_scale_mode = "BONE_ORIGINAL"
        IKSplineConstr.xz_scale_mode = "BONE_ORIGINAL"

        # Final settings cleanup
        curveData.resolution_u = self.ik_spline_resolution

        # Go back to pose mode
        context.view_layer.objects.active = arm
        bpy.ops.object.mode_set(mode='POSE')

        # Final messag, if no warning were raised during the execution
        if warning == 0:
            self.report({'INFO'}, 'MustardUI - IK spline rig successfully created.')

        return {'FINISHED'}

    def draw(self, context):

        settings = context.scene.MustardUI_Settings

        layout = self.layout

        box = layout.box()
        box.label(text="Main Settings", icon="CON_SPLINEIK")
        col = box.column()
        col.prop(self, "ik_spline_number")
        if settings.advanced:
            col.prop(self, "ik_spline_resolution")
        col.prop(self, "ik_spline_bendy")
        col = box.column()
        if not self.ik_spline_bendy:
            col.enabled = False
        col.prop(self, "ik_spline_bendy_segments")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)


class MustardUI_ToolsCreators_IKSpline_Clean(bpy.types.Operator):
    """This tool will remove the IK spline.\nSelect a bone with an IK constraint to enable the tool.\nA confirmation box will appear"""
    bl_idname = "mustardui.tools_creators_ikspline_clean"
    bl_label = "Clean"
    bl_options = {'REGISTER', 'UNDO'}

    delete_bones: bpy.props.BoolProperty(name='Delete bones',
                                         description="Delete controller and pole bones",
                                         default=True)
    reset_bendy: bpy.props.BoolProperty(name='Reset Bendy Bones',
                                        description="Reset bendy bones to standard bones",
                                        default=True)

    @classmethod
    def poll(cls, context):
        if context.mode != "POSE" or not bpy.context.selected_pose_bones:
            return False
        else:

            chain_bones = bpy.context.selected_pose_bones

            if len(chain_bones) < 1:
                return False
            else:
                abort_aa = True
                for bone in chain_bones:
                    for constraint in bone.constraints:
                        if constraint.type == 'SPLINE_IK':
                            abort_aa = False
                            break
                return not abort_aa

    def execute(self, context):

        addon_prefs = context.preferences.addons[base_package].preferences

        arm = bpy.context.object
        chain_bones = bpy.context.selected_pose_bones

        e = []

        removed_constr = 0
        removed_bones = 0

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)

        if self.reset_bendy:
            for bone in chain_bones:
                arm.data.edit_bones[bone.name].bbone_segments = 1
            arm.data.display_type = "OCTAHEDRAL"
            if addon_prefs.debug:
                print("MustardUI IK Spline - Bendy bones resetted")

        bpy.ops.object.mode_set(mode='POSE', toggle=False)

        for bone in chain_bones:
            for constraint in bone.constraints:
                if constraint.type == 'SPLINE_IK':

                    bpy.ops.object.mode_set(mode='EDIT', toggle=False)

                    if constraint.target:
                        IKCurve = constraint.target
                        for hook_mod in IKCurve.modifiers:
                            if hook_mod.object:

                                IKEmpty = hook_mod.object
                                e.append(IKEmpty.name)

                                if self.delete_bones:
                                    for e_constraint in IKEmpty.constraints:
                                        if e_constraint.type == "COPY_TRANSFORMS":
                                            if e_constraint.target and e_constraint.subtarget and e_constraint.subtarget != "":
                                                IKArm = e_constraint.target
                                                IKBone = IKArm.data.edit_bones[e_constraint.subtarget]
                                                IKBone_name = IKBone.name
                                                IKArm.data.edit_bones.remove(IKBone)
                                                if addon_prefs.debug:
                                                    print(
                                                        "MustardUI IK Spline - Bone " + IKBone_name + " removed from Armature " + IKArm.name)
                                                removed_bones = removed_bones + 1

                    bpy.ops.object.mode_set(mode='OBJECT')
                    bpy.ops.object.select_all(action='DESELECT')
                    for empty_name in e:
                        empty = bpy.data.objects[empty_name]
                        bpy.context.collection.objects.unlink(empty)
                        bpy.data.objects.remove(empty)

                    bpy.ops.object.select_all(action='DESELECT')
                    IKCurve = constraint.target
                    IKCurve_name = IKCurve.name
                    bpy.context.collection.objects.unlink(IKCurve)
                    bpy.data.objects.remove(IKCurve)
                    if addon_prefs.debug:
                        print("MustardUI IK Spline - Curve " + IKCurve_name + " removed.")

                    bpy.ops.object.mode_set(mode='POSE')

                    IKConstr_name = constraint.name
                    bone.constraints.remove(constraint)
                    removed_constr = removed_constr + 1
                    if addon_prefs.debug:
                        print(
                            "MustardUI IK Spline - Constraint " + IKConstr_name + " removed from " + bone.name + ".")

        if self.delete_bones:
            self.report({'INFO'}, 'MustardUI - ' + str(removed_constr) + ' IK constraints and ' + str(
                removed_bones) + ' Bones successfully removed.')
        else:
            self.report({'INFO'}, 'MustardUI - ' + str(removed_constr) + ' IK constraints successfully removed.')

        return {'FINISHED'}

    def invoke(self, context, event):

        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):

        layout = self.layout

        chain_bones = bpy.context.selected_pose_bones

        IK_num = 0
        IK_num_nMUI = 0
        for bone in chain_bones:
            for constraint in bone.constraints:
                if constraint.type == 'SPLINE_IK':
                    IK_num = IK_num + 1
                    if "MustardUI" not in constraint.name:
                        IK_num_nMUI = IK_num_nMUI + 1

        box = layout.box()
        box.prop(self, "delete_bones")
        box.prop(self, "reset_bendy")
        box = layout.box()
        box.label(text="Will be removed:", icon="ERROR")
        box.label(text="        - " + str(IK_num) + " Spline IK constraints.")
        box.label(text="        - " + str(IK_num_nMUI) + " of which are not Mustard Tools generated.")


def register():
    bpy.utils.register_class(MustardUI_ToolsCreators_IKSpline)
    bpy.utils.register_class(MustardUI_ToolsCreators_IKSpline_Clean)


def unregister():
    bpy.utils.unregister_class(MustardUI_ToolsCreators_IKSpline_Clean)
    bpy.utils.unregister_class(MustardUI_ToolsCreators_IKSpline)
