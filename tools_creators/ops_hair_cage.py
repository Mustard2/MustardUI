"""
This file is part of MustardUI.

MustardUI is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or (at your option)
any later version.

MustardUI is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with MustardUI.  If not, see <https://www.gnu.org/licenses/>.

The original operator in this file was created by BS_Creative and is
distributed under the terms of the GPL. Modifications have been made by
Mustard, and the modified software is released under the GPL as well,
in compliance with the terms of use of Blender relatively to the scripts
<https://www.blender.org/about/license/>.

Changes made:
- Integrated the code in MustardUI (Physics Panel and UI)
- Updated the implementation with additional functionalities within
the scope of MustardUI
- Fixed several bugs
"""


import bpy
from rna_prop_ui import rna_idprop_ui_create
from ..model_selection.active_object import *
from mathutils import Vector
import bmesh
from .. import __package__ as base_package


def update_voxel_res(self, context):
    updated_prop = self.voxel_res
    voxel_size = updated_prop

    # Define variables for voxel size and decimate ratio
    voxel_size = (0.4 / (voxel_size / 5))
    decimate_ratio = (voxel_size * 5)

    # Ensure an object is selected and active
    if not bpy.context.active_object or not bpy.context.active_object.type == 'MESH':
        return

    active_obj = bpy.context.active_object
    # Loop through all modifiers on the active object
    for mod in active_obj.modifiers:
        # Check if the modifier is a Remesh modifier
        if mod.type == 'REMESH':
            mod.voxel_size = voxel_size
        # Check if the modifier is a Decimate modifier
        elif mod.type == 'DECIMATE':
            if mod.decimate_type == 'COLLAPSE':
                mod.ratio = decimate_ratio


class MustardUI_ToolsCreators_HairCage(bpy.types.Operator):
    bl_idname = "mustardui.tools_creators_hair_cage"
    bl_label = "Hair Cage"
    bl_description = "Create a Hair Cage on a Mesh"
    bl_options = {"REGISTER", "UNDO"}

    max_density: bpy.props.BoolProperty(name='Increase Density',
                                        description='Enable Subdivision during the process. Might get better results, but it is slower',
                                        default=False)
    attempt_tight_bind: bpy.props.BoolProperty(name='Attempt Tight Binding',
                                               description='Add a Displace modifier to the cage to attempt a tighter binding',
                                               default=True)
    voxel_res: bpy.props.FloatProperty(name='Cage Resolution', description='', default=100.0,
                                       subtype='NONE', unit='NONE', min=1.0, step=3, precision=3,
                                       update=update_voxel_res)
    add_to_panel: bpy.props.BoolProperty(name='Add to Physics Panel',
                                         description='Add the Collision item to Physics Panel', default=True)

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=1)
        return res and context.active_object and context.active_object.type == 'MESH'

    def cancel(self, context):
        if len(bpy.context.selected_objects) > 1 and bpy.context.active_object:
            # Store the current active object
            active_obj = bpy.context.active_object
            # Deselect the active object (so it can be deleted)
            active_obj.select_set(False)
            # Delete the previously active object
            bpy.data.objects.remove(active_obj)
            # Make the new selected object the active one
            bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]

        return None

    def execute(self, context):

        res, obj = mustardui_active_object(context, config=1)
        physics_settings = obj.MustardUI_PhysicsSettings
        addon_prefs = context.preferences.addons[base_package].preferences

        # Ensure there are at least two selected objects and one active object
        if len(bpy.context.selected_objects) > 1 and bpy.context.active_object:
            # Store the current active object
            active_obj = bpy.context.active_object
            # Deselect the active object (so it can be deleted)
            active_obj.select_set(False)
            # Delete the previously active object
            bpy.data.objects.remove(active_obj)
            # Make the new selected object the active one
            bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
        else:
            print("Make sure there are at least two selected objects and one active object.")

        voxel_size = self.voxel_res
        voxel_size = 0.4 / (voxel_size / 5)
        decimate_ratio = voxel_size * 5

        def create_proxy_mesh(original_obj):
            """Creates a proxy mesh using the method provided."""
            # Duplicate the active object
            bpy.ops.object.duplicate()
            duplicate_obj = bpy.context.active_object

            # Rename the duplicated object
            duplicate_obj.name = f"{original_obj.name} Hair Proxy"

            # Add Displace modifier if attempt_tight_bind is True
            if self.attempt_tight_bind:
                displace_mod = duplicate_obj.modifiers.new(name="Displace", type='DISPLACE')
                displace_mod.strength = -0.9
                displace_mod.mid_level = 0.99

            # Add Solidify modifier
            solidify_mod = duplicate_obj.modifiers.new(name="Solidify", type='SOLIDIFY')
            solidify_mod.thickness = -0.01
            solidify_mod.offset = -1

            # Add Remesh modifier
            remesh_mod = duplicate_obj.modifiers.new(name="Remesh", type='REMESH')
            remesh_mod.voxel_size = voxel_size
            remesh_mod.mode = 'VOXEL'
            remesh_mod.adaptivity = 0

            # Add Decimate modifier
            decimate_mod = duplicate_obj.modifiers.new(name="Decimate", type='DECIMATE')
            decimate_mod.decimate_type = 'COLLAPSE'
            decimate_mod.ratio = decimate_ratio

            # Apply all modifiers
            bpy.ops.object.convert(target='MESH')

            # Enter edit mode
            bpy.ops.object.mode_set(mode='EDIT')

            # Select all geometry
            bpy.ops.mesh.select_all(action='SELECT')

            # Convert triangles to quads
            bpy.ops.mesh.tris_convert_to_quads()

            # Return to object mode
            bpy.ops.object.mode_set(mode='OBJECT')

            # Subdivide mesh if max_density is True
            if self.max_density:
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.mesh.subdivide(number_cuts=1)
                bpy.ops.object.mode_set(mode='OBJECT')

            # Run additional cleanup and selection functions
            select_inward_facing_faces()
            invert_selection_and_delete_vertices()
            select_largest_island_and_delete_other_faces()

            # Set render visibility and display type
            duplicate_obj.display_type = 'WIRE'
            duplicate_obj.hide_render = True

            return duplicate_obj

        def select_inward_facing_faces():
            """Selects inward-facing faces and deletes them, keeping the largest connected region."""
            obj = bpy.context.active_object
            if obj is None or obj.type != 'MESH':
                print("Active object is not a mesh")
                return
            bpy.ops.object.mode_set(mode='EDIT')
            bm = bmesh.from_edit_mesh(obj.data)
            bpy.ops.mesh.select_all(action='DESELECT')
            avg_pos = Vector((0, 0, 0))
            for v in bm.verts:
                avg_pos += v.co
            avg_pos /= len(bm.verts)
            for face in bm.faces:
                face_normal = face.normal
                face_center = face.calc_center_median()
                to_center = (avg_pos - face_center).normalized()
                if face_normal.dot(to_center) > 0:
                    face.select = True
            selected_regions = []
            bm.select_mode = {'FACE'}

            def grow_region_iterative(face):
                """Grow a region iteratively to avoid deep recursion."""
                stack = [face]
                region = set()
                while stack:
                    current_face = stack.pop()
                    if current_face not in region:
                        region.add(current_face)
                        current_face.select = False
                        for edge in current_face.edges:
                            for linked_face in edge.link_faces:
                                if linked_face.select and linked_face not in region:
                                    stack.append(linked_face)
                return region

            for face in bm.faces:
                if face.select:
                    region = grow_region_iterative(face)
                    selected_regions.append(region)
            if selected_regions:
                largest_region = max(selected_regions, key=lambda reg: sum(f.calc_area() for f in reg))
                bpy.ops.mesh.select_all(action='DESELECT')
                for face in largest_region:
                    face.select = True
            bpy.ops.mesh.delete(type='FACE')
            bmesh.update_edit_mesh(obj.data)
            bpy.ops.mesh.select_mode(type="VERT")
            bpy.ops.mesh.select_all(action='DESELECT')
            islands = []
            visited = set()

            def grow_island_iterative(vert, island):
                stack = [vert]
                while stack:
                    v = stack.pop()
                    if v not in visited:
                        visited.add(v)
                        island.append(v)
                        for edge in v.link_edges:
                            linked_vert = edge.other_vert(v)
                            if linked_vert not in visited:
                                stack.append(linked_vert)

            for vert in bm.verts:
                if vert not in visited:
                    island = []
                    grow_island_iterative(vert, island)
                    islands.append(island)
            if islands:
                largest_island = max(islands, key=len)
                bpy.ops.mesh.select_all(action='DESELECT')
                for vert in largest_island:
                    vert.select = True
            bmesh.update_edit_mesh(obj.data)
            bpy.ops.object.mode_set(mode='OBJECT')

        def invert_selection_and_delete_vertices():
            """Inverts the selection and deletes the selected vertices."""
            if bpy.context.object.mode != 'EDIT':
                bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='INVERT')
            bpy.ops.mesh.delete(type='VERT')
            bpy.ops.object.mode_set(mode='OBJECT')

        def select_largest_island_and_delete_other_faces():
            """Selects the largest geometry island and deletes all other faces."""
            if bpy.context.object.mode != 'EDIT':
                bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_mode(type="FACE")
            bpy.ops.mesh.select_all(action='DESELECT')
            bm = bmesh.from_edit_mesh(bpy.context.object.data)
            islands = []
            visited = set()

            def grow_island_iterative(face, island):
                stack = [face]
                while stack:
                    f = stack.pop()
                    if f not in visited:
                        visited.add(f)
                        island.append(f)
                        for edge in f.edges:
                            for linked_face in edge.link_faces:
                                if linked_face not in visited:
                                    stack.append(linked_face)

            for face in bm.faces:
                if not face.hide and not face.select:
                    island = []
                    grow_island_iterative(face, island)
                    islands.append(island)
            if islands:
                largest_island = max(islands, key=len)
                bpy.ops.mesh.select_all(action='DESELECT')
                for face in largest_island:
                    face.select = True
            bpy.ops.mesh.select_all(action='INVERT')
            bpy.ops.mesh.delete(type='FACE')
            bmesh.update_edit_mesh(bpy.context.object.data)
            bpy.ops.object.mode_set(mode='OBJECT')

        def create_gradient_vertex_group(obj, group_name):
            """Creates a vertex group with a gradient weight based on the Z position of vertices."""
            vertex_group = obj.vertex_groups.new(name=group_name)
            bbox_min_z = min([obj.matrix_world @ v.co for v in obj.data.vertices], key=lambda v: v.z).z
            bbox_max_z = max([obj.matrix_world @ v.co for v in obj.data.vertices], key=lambda v: v.z).z
            bbox_height = bbox_max_z - bbox_min_z
            bpy.ops.object.mode_set(mode='EDIT')
            bm = bmesh.from_edit_mesh(obj.data)
            vertex_weights = []
            for v in bm.verts:
                global_co = obj.matrix_world @ v.co
                weight = (global_co.z - bbox_min_z) / bbox_height
                vertex_weights.append((v.index, weight))
            bpy.ops.object.mode_set(mode='OBJECT')
            for index, weight in vertex_weights:
                vertex_group.add([index], weight, 'REPLACE')

        def transfer_armature_modifiers(original_obj, duplicate_obj):
            """Copies all armature modifiers from the original object to the duplicate."""
            for modifier in original_obj.modifiers:
                if modifier.type == 'ARMATURE':
                    arm_mod = duplicate_obj.modifiers.new(name=modifier.name, type='ARMATURE')
                    arm_mod.object = modifier.object
                    arm_mod.use_bone_envelopes = modifier.use_bone_envelopes
                    arm_mod.use_vertex_groups = modifier.use_vertex_groups
                    arm_mod.invert_vertex_group = modifier.invert_vertex_group
                    arm_mod.use_deform_preserve_volume = modifier.use_deform_preserve_volume
                    arm_mod.use_multi_modifier = modifier.use_multi_modifier
                    arm_mod.show_on_cage = modifier.show_on_cage
                    arm_mod.show_in_editmode = modifier.show_in_editmode
                    arm_mod.show_viewport = modifier.show_viewport
                    arm_mod.show_render = modifier.show_render

        def perform_weight_transfer(original_obj, duplicate_obj):
            """Performs vertex group weight transfer from the original object to the duplicate."""
            bpy.ops.object.select_all(action='DESELECT')
            original_obj.select_set(True)
            duplicate_obj.select_set(True)
            bpy.context.view_layer.objects.active = duplicate_obj
            bpy.ops.object.data_transfer(
                use_reverse_transfer=True,
                use_freeze=False,
                data_type='VGROUP_WEIGHTS',
                vert_mapping='POLYINTERP_NEAREST',
                use_auto_transform=False,
                use_object_transform=True,
                use_max_distance=False,
                ray_radius=0.1,
                layers_select_src='NAME',
                layers_select_dst='ALL',
                mix_mode='REPLACE',
                mix_factor=1
            )

        def apply_corrective_smooth_modifier(obj, iterations, smooth_type, rest_source):
            """Applies a corrective smooth modifier with the given settings and binds it."""
            mod = obj.modifiers.new(name="Hair Corrective", type='CORRECTIVE_SMOOTH')
            mod.iterations = iterations
            mod.smooth_type = smooth_type
            mod.rest_source = rest_source
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.correctivesmooth_bind(modifier=mod.name)

        if not bpy.context.active_object.type == 'MESH':
            return {"FINISHED"}

        # Set current frame to start frame
        bpy.context.scene.frame_set(bpy.context.scene.frame_start)

        # Store initial pose state of armature objects
        initial_pose_states = {}
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                for modifier in obj.modifiers:
                    if modifier.type == 'ARMATURE' and modifier.object:
                        armature_obj = modifier.object
                        initial_pose_states[armature_obj.name] = armature_obj.data.pose_position

        # Set all armatures in the scene to rest pose
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                for modifier in obj.modifiers:
                    if modifier.type == 'ARMATURE' and modifier.object:
                        armature_obj = modifier.object
                        armature_obj.data.pose_position = 'REST'

        original_obj = bpy.context.active_object

        # Create the proxy mesh using the new method
        duplicate_obj = create_proxy_mesh(original_obj)

        # Perform weight transfer from the original mesh to the duplicate
        perform_weight_transfer(original_obj, duplicate_obj)

        # Create the vertex group with gradient weight after weight projection
        create_gradient_vertex_group(duplicate_obj, "Hair Pin")

        # Set the original object as active and select the duplicate object for binding
        bpy.context.view_layer.objects.active = original_obj
        original_obj.select_set(True)
        duplicate_obj.select_set(False)

        # Bind the original mesh to the duplicate using Surface Deform
        surface_deform_modifier = original_obj.modifiers.new(name="Hair Deform", type='SURFACE_DEFORM')
        surface_deform_modifier.target = duplicate_obj

        # Bind the last added Surface Deform modifier
        bpy.ops.object.surfacedeform_bind(modifier=surface_deform_modifier.name)

        # After binding, deselect the original object and select the duplicate
        original_obj.select_set(False)
        duplicate_obj.select_set(True)
        bpy.context.view_layer.objects.active = duplicate_obj

        # Transfer all armature modifiers from the original mesh to the duplicate
        transfer_armature_modifiers(original_obj, duplicate_obj)

        # Apply corrective smooth modifier to the duplicate
        apply_corrective_smooth_modifier(duplicate_obj, iterations=10, smooth_type='SIMPLE', rest_source='BIND')

        # Apply corrective smooth modifier to the original mesh
        apply_corrective_smooth_modifier(original_obj, iterations=10, smooth_type='LENGTH_WEIGHTED',
                                         rest_source='BIND')

        # Ensure only the duplicate is selected and active
        original_obj.select_set(False)
        duplicate_obj.select_set(True)
        bpy.context.view_layer.objects.active = duplicate_obj

        # Restore original pose state after operations
        for obj_name, pose_position in initial_pose_states.items():
            armature_obj = bpy.data.objects.get(obj_name)
            if armature_obj:
                armature_obj.data.pose_position = pose_position

        if addon_prefs.debug:
            print("All operations completed: Proxy creation, armature transfer, Surface Deform binding, corrective smooth application, and weight projection with active vertex group 'Hair Pin'.")

        # Get the active object
        active_obj = bpy.context.active_object

        # Check if the active object is valid
        if active_obj is None or active_obj.type != 'MESH':
            print("No active mesh object selected.")
        else:
            # Find the mesh that uses the active object as a target in a Surface Deform modifier
            target_obj = None
            for obj in bpy.data.objects:
                for mod in obj.modifiers:
                    if mod.type == 'SURFACE_DEFORM' and mod.target == active_obj:
                        target_obj = obj
                        break
                if target_obj:
                    break
            # Check if a target mesh is found
            if target_obj is None:
                print("No mesh found using the active mesh as a Surface Deform target.")
            else:
                # Base name for the vertex group
                base_name = "Easy Sim"
                vg_name = base_name
                counter = 1
                # Check if a group with the same name exists and create a unique name
                while vg_name in target_obj.vertex_groups:
                    vg_name = f"{base_name}.{str(counter).zfill(3)}"
                    counter += 1
                # Create the vertex group
                vg = target_obj.vertex_groups.new(name=vg_name)
                # Assign all vertices to the group with weight 1
                verts = [v.index for v in target_obj.data.vertices]
                vg.add(verts, 1.0, 'REPLACE')
                # Find the last Surface Deform and Corrective Smooth modifiers
                surface_deform_modifier = None
                corrective_smooth_modifier = None
                for mod in reversed(target_obj.modifiers):
                    if mod.type == 'SURFACE_DEFORM' and surface_deform_modifier is None:
                        surface_deform_modifier = mod
                    elif mod.type == 'CORRECTIVE_SMOOTH' and corrective_smooth_modifier is None:
                        corrective_smooth_modifier = mod
                # Assign the vertex group to the modifiers
                if surface_deform_modifier:
                    surface_deform_modifier.vertex_group = vg_name
                    if addon_prefs.debug:
                        print(f"Assigned '{vg_name}' to the last Surface Deform modifier of the target object.")
                else:
                    print("No Surface Deform modifier found on the target object.")
                if corrective_smooth_modifier:
                    corrective_smooth_modifier.vertex_group = vg_name
                    if addon_prefs.debug:
                        print(f"Assigned '{vg_name}' to the last Corrective Smooth modifier of the target object.")
                else:
                    print("No Corrective Smooth modifier found on the target object.")

        def add_driver(source, target, prop, data_path, index=-1):
            """Add a driver to a property."""
            if index == -1:
                fcurve = source.driver_add(data_path)
            else:
                fcurve = source.driver_add(data_path, index)
            driver = fcurve.driver
            driver.type = 'AVERAGE'
            var = driver.variables.new()
            var.name = 'var'
            var.type = 'SINGLE_PROP'
            var.targets[0].id = target
            var.targets[0].data_path = prop
            return driver

        obj = bpy.context.active_object
        if obj and obj.type == 'MESH':
            # Clear existing custom property
            if "Inflate" in obj.keys():
                del obj["Inflate"]

            # Add custom property and set its range
            rna_idprop_ui_create(obj, "Inflate",
                                 default=0.,
                                 min=0., soft_min=0.,
                                 max=1., soft_max=0.,
                                 overridable=True)

            # Add a Displace modifier and add the driver to it
            displace_modifier = obj.modifiers.new(name="Displace", type='DISPLACE')
            displace_modifier.mid_level = 0.990
            add_driver(displace_modifier, obj, '["Inflate"]', 'strength')
            if addon_prefs.debug:
                print("Displace modifier with a driver added to the active mesh.")
        else:
            print("No active mesh object found.")

        # Get the active object
        obj = bpy.context.object

        # Check if the object has a Displace modifier
        displace_modifiers = [mod for mod in obj.modifiers if mod.type == 'DISPLACE']

        if not displace_modifiers:
            print("No Displace modifiers found on the active object.")
        else:
            # Get the last Displace modifier
            last_displace = displace_modifiers[-1]
            # Get the active vertex group
            if obj.vertex_groups.active:
                active_vertex_group = obj.vertex_groups.active.name
                # Set the vertex group as the mask for the last Displace modifier
                last_displace.vertex_group = active_vertex_group
                # Invert the vertex group mask
                last_displace.invert_vertex_group = True
                if addon_prefs.debug:
                    print(f"Set '{active_vertex_group}' as the vertex group mask and inverted it.")
            else:
                if addon_prefs.debug:
                    print("No active vertex group found.")

        # Flag the mesh as Cage
        obj.MustardUI_tools_creators_is_created = True

        # Call function to add physics
        bpy.ops.mustardui.tools_creators_add_cloth_to_hair('INVOKE_DEFAULT', )

        # Add the object to the Physics Panel
        if self.add_to_panel:
            add_item = physics_settings.items.add()
            add_item.object = bpy.context.object
            add_item.type = 'CAGE'

        self.report({'INFO'}, 'MustardUI - Hair Cage created.')

        return {"FINISHED"}

    def draw(self, context):

        settings = context.scene.MustardUI_Settings

        layout = self.layout
        layout.prop(self, 'voxel_res')

        if settings.advanced:
            layout.prop(self, 'max_density')
            layout.prop(self, 'attempt_tight_bind')

        layout.separator()

        layout.prop(self, 'add_to_panel')

    def invoke(self, context, event):
        bpy.ops.object.mode_set('INVOKE_DEFAULT', mode='OBJECT')

        # Get all 3D Viewport areas in the current screen
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                # Access the space data of the 3D Viewport
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        # Enable overlays
                        space.overlay.show_overlays = True

        # Ensure that there is an active object and it's a mesh
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

        self.voxel_res = 100.0
        self.max_density = False
        self.attempt_tight_bind = True
        voxel_size = self.voxel_res

        # Define variables for voxel size and decimate ratio
        voxel_size = (0.4 / (voxel_size / 5))
        decimate_ratio = (voxel_size * 5)

        # Store the original active object
        original_obj = bpy.context.active_object

        # Duplicate the active object
        bpy.ops.object.duplicate()
        duplicate_obj = bpy.context.active_object
        duplicate_obj.name = f"{bpy.context.active_object.name} Temp Hair Proxy"

        # Apply scale to the duplicate
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

        # Hide the duplicate in renders
        duplicate_obj.hide_render = True

        # Set the display type to wireframe
        duplicate_obj.display_type = 'WIRE'

        # Add Solidify modifier
        solidify_mod = duplicate_obj.modifiers.new(name="Solidify", type='SOLIDIFY')
        solidify_mod.thickness = -0.01
        solidify_mod.offset = -1

        # Add Remesh modifier
        remesh_mod = duplicate_obj.modifiers.new(name="Remesh", type='REMESH')
        remesh_mod.voxel_size = voxel_size
        remesh_mod.mode = 'VOXEL'
        remesh_mod.adaptivity = 0

        # Add Decimate modifier
        decimate_mod = duplicate_obj.modifiers.new(name="Decimate", type='DECIMATE')
        decimate_mod.decimate_type = 'COLLAPSE'
        decimate_mod.ratio = decimate_ratio

        # Deselect all objects
        bpy.ops.object.select_all(action='DESELECT')

        # Select the original object and make it active
        original_obj.select_set(True)

        # Select the duplicate object (new active object)
        duplicate_obj.select_set(True)

        # Make the duplicate object the active one
        bpy.context.view_layer.objects.active = duplicate_obj

        return context.window_manager.invoke_props_dialog(self, width=300)


def register():
    bpy.utils.register_class(MustardUI_ToolsCreators_HairCage)


def unregister():
    bpy.utils.unregister_class(MustardUI_ToolsCreators_HairCage)
