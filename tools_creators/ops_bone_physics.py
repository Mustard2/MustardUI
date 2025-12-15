import math

import bpy
from ..model_selection.active_object import *


def check_bones_connections(selected_bones):
    is_chain = True

    # Check if the selected bones are parented in a chain
    for i in range(1, len(selected_bones)):
        previous_bone = selected_bones[i - 1]
        current_bone = selected_bones[i]

        # Check if current_bone's parent is the previous_bone
        if current_bone.parent != previous_bone:
            is_chain = False
            break

    return is_chain


def find_bone_chains(selected_bones):
    """Group selected bones into disconnected chains."""
    chains = []
    visited = set()

    for bone in selected_bones:
        if bone in visited:
            continue

        # Start a new chain
        chain = []
        current_bone = bone

        while current_bone and current_bone not in visited and current_bone in selected_bones:
            chain.append(current_bone)
            visited.add(current_bone)
            if len(current_bone.children) == 1:
                current_bone = current_bone.children[0]

        if chain:
            chains.append(chain)

    return chains


class MustardUI_ToolsCreators_BonePhysics(bpy.types.Operator):
    bl_idname = "mustardui.tools_creators_bone_physics"
    bl_label = "Bone Physics"
    bl_description = "Add physics to a set of selected bones in Pose Mode"
    bl_options = {"REGISTER", "UNDO"}

    curve_width: bpy.props.FloatProperty(default=0.01, name="Curve Width",
                                         description="Width of the curve used for physics.\nIncrease this value if the item driven by the curve is larger")
    curve_tilt: bpy.props.FloatProperty(default=0, name="Curve Tilt", subtype="ANGLE",
                                        description="Tilt of the curve mesh.\nIn some cases, a value of 90 degrees might improve results")
    pinned_bones: bpy.props.IntProperty(default=1, name="Pinned Bones",
                                        description="Number of bones to be pinned in the Physics.\nPinned bones will not move, but are included to generate the curve", min=0)
    add_to_panel: bpy.props.BoolProperty(name='Add to Physics Panel',
                                         description='Add the Collision item to Physics Panel', default=True)
    merge_chains: bpy.props.BoolProperty(name='Merge Chains',
                                         description='If several disconnected chains are selected, the results will be merged in one single Object', default=True)

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=1)
        if not res:
            return False

        armature = context.object

        if armature and armature.type == 'ARMATURE' and armature.mode == 'POSE':
            selected_bones = [bone for bone in armature.pose.bones if bone.select]
            return len(selected_bones) >= 2

        return False

    def execute(self, context):

        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings
        physics_settings = obj.MustardUI_PhysicsSettings

        armature = context.object
        bones = [bone for bone in armature.pose.bones if bone.select]

        # Find disconnected bone chains
        bone_chains = find_bone_chains(bones)

        chain_objects =[]
        chain_bone_constraints = []

        for chain_idx, chain in enumerate(bone_chains):

            if self.pinned_bones >= len(chain):
                self.report({'WARNING'},
                            'MustardUI - The number of pinned bones can not be bigger than the number of available bones.')
                return {'FINISHED'}

            # Create a curve to represent the path through the bone tips
            curve_data = bpy.data.curves.new('MustardUI Bone Physics', type='CURVE')
            curve_data.dimensions = '3D'
            spline = curve_data.splines.new(type='POLY')

            # Set the curve points to the bone head/tails
            spline.points.add(count=len(chain))
            spline.points[0].co = (armature.matrix_world @ chain[0].head).to_tuple() + (1,)
            spline.points[0].tilt = self.curve_tilt
            for i, bone in enumerate(chain):
                i += 1
                if i == len(chain):
                    spline.points[i].co = (armature.matrix_world @ bone.tail).to_tuple() + (1,)
                    spline.points[i].tilt = self.curve_tilt
                else:
                    spline.points[i].co = (armature.matrix_world @ bone.tail).to_tuple() + (1,)
                    spline.points[i].tilt = self.curve_tilt

            # Extrude to solidify the curve
            curve_data.extrude = self.curve_width

            bpy.ops.object.mode_set(mode='OBJECT')

            # Create a new object for the curve and link it to the scene
            if rig_settings.model_name != "" and armature.name != "":
                bp_name = f"{rig_settings.model_name} {armature.name.replace(rig_settings.model_name, '')} Bone Physics"
            else:
                bp_name = "Bone Physics"
            curve_obj = bpy.data.objects.new(bp_name, curve_data)
            bpy.context.collection.objects.link(curve_obj)
            curve_obj.MustardUI_tools_creators_is_created = True

            # Select only the new mesh
            bpy.ops.object.select_all(action='DESELECT')
            armature.select_set(False)
            curve_obj.select_set(True)
            bpy.context.view_layer.objects.active = curve_obj

            # Convert the curve to a mesh
            bpy.ops.object.convert(target='MESH')  # Convert the curve to a mesh

            # Create vertex groups and assign weights for each vertex
            curve_obj.vertex_groups.clear()  # Clear any existing vertex groups

            # Create Pin group to populate
            pin_vertex_group = curve_obj.vertex_groups.new(name="Pin")

            # Iterate over each vertex and create a vertex group for it
            idx_vg = 0
            vertex_groups = []
            for idx, vertex in enumerate(curve_obj.data.vertices):

                if vertex.index % 2:
                    continue

                # Create a new vertex group for each vertex
                vertex_group_name = f"V{idx_vg}_C" + str(chain_idx)
                vertex_group = curve_obj.vertex_groups.new(name=vertex_group_name)
                vertex_groups.append(vertex_group)  # Store the created vertex group

                # Assign the weight of 1 to the current vertex in this group
                vertex_group.add([vertex.index], 1.0, 'REPLACE')  # Assign weight 1 to the current vertex
                vertex_group.add([vertex.index + 1], 1.0, 'REPLACE')  # Assign weight 1 to the current vertex

                if idx_vg < self.pinned_bones + 1:
                    pin_vertex_group.add([vertex.index], 1.0, 'REPLACE')  # Assign weight 1 to the current vertex
                    pin_vertex_group.add([vertex.index + 1], 1.0, 'REPLACE')  # Assign weight 1 to the current vertex

                idx_vg += 1

            # Add a Damped Track modifier to each bone (except the first)
            for i, bone in enumerate(chain):

                # Add Damped Track constraint to the bone
                constraint = bone.constraints.new(type='DAMPED_TRACK')
                constraint.name = curve_obj.name
                constraint.target = curve_obj  # The curve object as the target
                constraint.track_axis = 'TRACK_Y'  # Track the Y axis (you can change this if needed)

                # Assign the corresponding vertex group to each bone's constraint (starting from the second group)
                if i - 1 < len(vertex_groups):
                    constraint.subtarget = vertex_groups[i + 1].name  # Set the vertex group from the second onwards

                chain_bone_constraints.append(constraint)

            # Add Cloth modifier to the curve mesh
            cloth_modifier = curve_obj.modifiers.new(name="Cloth", type='CLOTH')

            # Set the vertex group for pinning
            cloth_modifier.settings.vertex_group_mass = "Pin"
            cloth_modifier.settings.pin_stiffness = 1.

            # Configure cloth modifier
            cloth_modifier.settings.quality = 5
            cloth_modifier.settings.mass = 0.15
            cloth_modifier.settings.tension_stiffness = 5.
            cloth_modifier.settings.compression_stiffness = 5.
            cloth_modifier.settings.shear_stiffness = 5.
            cloth_modifier.settings.bending_stiffness = 0.05
            cloth_modifier.settings.tension_damping = 0.05
            cloth_modifier.settings.compression_damping = 0.05
            cloth_modifier.settings.shear_damping = 0.05
            cloth_modifier.settings.bending_damping = 0.05

            cloth_modifier.collision_settings.use_collision = True
            cloth_modifier.collision_settings.distance_min = 0.001

            chain_objects.append(bpy.context.object)

        if self.merge_chains:

            parent_object = chain_objects[0]

            for oc in chain_objects[1:]:
                bpy.ops.object.select_all(action='DESELECT')
                parent_object.select_set(True)
                oc.select_set(True)

                bpy.context.view_layer.objects.active = parent_object
                bpy.ops.object.join()

            chain_objects = [parent_object]

            # Fix missing target in bone constraints
            for constraint in chain_bone_constraints:
                constraint.target = chain_objects[0]

        for co in chain_objects:

            bpy.ops.object.select_all(action='DESELECT')
            co.select_set(True)
            bpy.context.view_layer.objects.active = co

            # Add the object to the Physics Panel
            if self.add_to_panel:
                add_item = physics_settings.items.add()
                add_item.object = co
                add_item.type = 'BONES_DRIVER'

            # Disable shadows for viewport/render
            co.visible_camera = False
            co.visible_shadow = False

            # Set the armature as the parent
            bpy.context.view_layer.objects.active = armature
            bpy.ops.object.parent_set(type='ARMATURE')

        self.report({'INFO'}, 'MustardUI - Bone Physics added.')

        return {"FINISHED"}

    def draw(self, context):

        settings = context.scene.MustardUI_Settings

        layout = self.layout
        layout.prop(self, 'pinned_bones', emboss=True)
        layout.prop(self, 'merge_chains', emboss=True)
        if settings.advanced:
            layout.prop(self, 'curve_width', emboss=True)
            layout.prop(self, 'curve_tilt', emboss=True)

        layout.separator()

        layout.prop(self, 'add_to_panel', emboss=True)

    def invoke(self, context, event):
        self.pinned_bones = 1
        self.curve_width = 0.02
        return context.window_manager.invoke_props_dialog(self, width=300)


class MustardUI_ToolsCreators_BonePhysics_Clean(bpy.types.Operator):
    bl_idname = "mustardui.tools_creators_bone_physics_clean"
    bl_label = "Remove Bone Physics"
    bl_description = "Clean the bone physics of the selected mesh"
    bl_options = {"REGISTER", "UNDO"}

    curve_width: bpy.props.FloatProperty(default=0.01, name="Curve Width", description="")
    pinned_bones: bpy.props.IntProperty(default=1, name="Pinned Bones", description="")
    add_to_panel: bpy.props.BoolProperty(name='Add to Physics Panel',
                                         description='Add the Collision item to Physics Panel', default=True)

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=1)
        if not res:
            return False

        obj = context.object

        if obj and obj.type == 'MESH' and obj.mode == 'OBJECT':
            return obj.MustardUI_tools_creators_is_created

        return False

    def execute(self, context):

        res, obj = mustardui_active_object(context, config=1)
        physics_settings = obj.MustardUI_PhysicsSettings

        curve_obj = context.object

        # Remove all Damped Track constraints from the bones of the armature
        armature = curve_obj.parent  # Assuming the armature is the active object
        if armature.type != 'ARMATURE':
            self.report({'WARNING'}, 'MustardUI - Removal was not possible: the mesh is not parented to any Armature.')
            return {"FINISHED"}

        # Loop through all pose bones and remove the specific Damped Track constraints
        for bone in armature.pose.bones:
            for constraint in bone.constraints:
                if constraint.type == 'DAMPED_TRACK' and constraint.target == curve_obj:
                    bone.constraints.remove(constraint)

        # Remove the item from the list if available
        for i, pi in enumerate(physics_settings.items):
            if pi.object == curve_obj:
                physics_settings.items.remove(i)

        # Delete the curve object
        if curve_obj and curve_obj.name in bpy.data.objects:
            bpy.data.objects.remove(curve_obj, do_unlink=True)

        self.report({'INFO'}, 'MustardUI - Bone Physics removed.')

        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_ToolsCreators_BonePhysics)
    bpy.utils.register_class(MustardUI_ToolsCreators_BonePhysics_Clean)


def unregister():
    bpy.utils.unregister_class(MustardUI_ToolsCreators_BonePhysics_Clean)
    bpy.utils.unregister_class(MustardUI_ToolsCreators_BonePhysics)
