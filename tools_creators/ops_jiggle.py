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
import bmesh
from mathutils import Vector
from ..model_selection.active_object import *
from .. import __package__ as base_package


class MustardUI_ToolsCreators_CreateJiggle_Preset(bpy.types.Operator):
    bl_idname = "mustardui.tools_creators_create_jiggle_preset"
    bl_label = "Jiggle Preset"
    bl_description = "Adds cloth jiggle physics with Wildeer settings to mesh. Uses active vtx group as 'Pin Group' in object mode. If in edit mode then it creates a new vtx group from selection and uses it instead. Applies to active and selected"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=1)
        return res

    def execute(self, context):

        # Set the playback sync mode to 'NONE' (Play Every Frame)
        bpy.context.scene.sync_mode = 'NONE'

        # Remove cloth modifiers
        for obj in bpy.context.selected_objects:
            # Ensure the object is a mesh
            if obj.type == 'MESH':
                # List to hold the names of the cloth modifiers to be removed
                cloth_modifiers = [mod.name for mod in obj.modifiers if mod.type == 'CLOTH']
                # Remove each cloth modifier
                for mod_name in cloth_modifiers:
                    obj.modifiers.remove(obj.modifiers[mod_name])

        # Ensure that the context is correct for adding modifiers
        bpy.context.view_layer.update()

        # Function to handle vertex group creation and assignment in Edit Mode
        def create_vertex_group(obj, base_name="ClothPinGroup"):
            # Switch to Object Mode temporarily to update the vertex group
            bpy.ops.object.mode_set(mode='OBJECT')

            # Create a unique vertex group name
            i = 1
            new_name = base_name
            while new_name in obj.vertex_groups:
                new_name = f"{base_name}_{i}"
                i += 1

            # Create a new vertex group
            vertex_group = obj.vertex_groups.new(name=new_name)

            # Get the selected vertices
            selected_verts = [v.index for v in obj.data.vertices if v.select]

            # Add selected vertices to the vertex group with weight 1.0
            vertex_group.add(selected_verts, 1.0, 'ADD')

            # Return to Edit Mode
            bpy.ops.object.mode_set(mode='EDIT')

            return new_name

        for obj in [x for x in bpy.context.selected_objects if x.type == "MESH"]:
            # Set the object as active
            bpy.context.view_layer.objects.active = obj

            # Add or get the existing Cloth modifier
            cloth_modifier = obj.modifiers.get("Cloth")
            if not cloth_modifier:
                cloth_modifier = obj.modifiers.new(name="Cloth", type='CLOTH')

            # Check current mode and handle vertex groups
            current_mode = bpy.context.object.mode
            vertex_group_name = None
            if current_mode == 'EDIT':
                if obj.vertex_groups:
                    if cloth_modifier.settings.vertex_group_mass:
                        # Replace the existing vertex group
                        vertex_group_name = create_vertex_group(obj)
                    else:
                        vertex_group_name = create_vertex_group(obj)
                else:
                    vertex_group_name = create_vertex_group(obj)
            elif current_mode == 'OBJECT' and obj.vertex_groups.active:
                vertex_group_name = obj.vertex_groups.active.name

            # Modify specific cloth settings with the new values
            cloth_modifier.settings.quality = 7
            cloth_modifier.settings.time_scale = 0.240
            cloth_modifier.settings.mass = 0.3
            cloth_modifier.settings.air_damping = 1
            cloth_modifier.settings.bending_model = 'ANGULAR'
            cloth_modifier.settings.tension_stiffness = 1
            cloth_modifier.settings.compression_stiffness = 0.1
            cloth_modifier.settings.shear_stiffness = 0.02
            cloth_modifier.settings.bending_stiffness = 0.02
            cloth_modifier.settings.tension_damping = 1
            cloth_modifier.settings.compression_damping = 0.1
            cloth_modifier.settings.shear_damping = 0.02
            cloth_modifier.settings.bending_damping = 0.02
            cloth_modifier.settings.use_internal_springs = True
            cloth_modifier.settings.use_pressure = True
            cloth_modifier.settings.internal_spring_max_length = 0
            cloth_modifier.settings.internal_spring_max_diversion = 0.785398
            cloth_modifier.settings.internal_spring_normal_check = True
            cloth_modifier.settings.internal_tension_stiffness = 0.1
            cloth_modifier.settings.internal_compression_stiffness = 0.1
            cloth_modifier.settings.internal_tension_stiffness_max = 0.3
            cloth_modifier.settings.internal_compression_stiffness_max = 0.3
            cloth_modifier.settings.uniform_pressure_force = 0.06
            cloth_modifier.settings.use_pressure_volume = False
            cloth_modifier.settings.target_volume = 0
            cloth_modifier.settings.pressure_factor = 1
            cloth_modifier.settings.fluid_density = 0
            cloth_modifier.settings.pin_stiffness = 1
            cloth_modifier.settings.use_sewing_springs = False
            cloth_modifier.settings.sewing_force_max = 0
            cloth_modifier.settings.shrink_min = 0
            cloth_modifier.settings.use_dynamic_mesh = False
            cloth_modifier.collision_settings.collision_quality = 2
            cloth_modifier.collision_settings.use_collision = False
            cloth_modifier.collision_settings.distance_min = 0.015
            cloth_modifier.collision_settings.impulse_clamp = 0
            cloth_modifier.collision_settings.use_self_collision = False
            cloth_modifier.collision_settings.self_friction = 5
            cloth_modifier.collision_settings.self_distance_min = 0.015
            cloth_modifier.collision_settings.self_impulse_clamp = 0
            cloth_modifier.settings.tension_stiffness_max = 15
            cloth_modifier.settings.compression_stiffness_max = 15
            cloth_modifier.settings.shear_stiffness_max = 5
            cloth_modifier.settings.bending_stiffness_max = 0.5
            cloth_modifier.settings.shrink_max = 0

            # Set the vertex group as the pin group if applicable
            if vertex_group_name:
                cloth_modifier.settings.vertex_group_mass = vertex_group_name

            # Set simulation start and end to the same start and end frame values of the scene
            cloth_modifier.point_cache.frame_start = bpy.context.scene.frame_start
            cloth_modifier.point_cache.frame_end = bpy.context.scene.frame_end

        # Toggle Edit Mode
        if bpy.context.active_object and bpy.context.active_object.type == 'MESH':
            # Store the current mode
            current_mode = bpy.context.object.mode

            # Switch to Edit Mode
            bpy.ops.object.mode_set(mode='EDIT')

            # Switch back to the previous mode (typically Object Mode)
            bpy.ops.object.mode_set(mode=current_mode)

        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class MustardUI_ToolsCreators_CreateJiggle(bpy.types.Operator):
    bl_idname = "mustardui.tools_creators_create_jiggle"
    bl_label = "Create Jiggle"
    bl_description = "Needs to select vertices in Edit Mode.\nCreates a jiggle cage using the selected regions in Edit Mode and attaches it to the active mesh"
    bl_options = {"REGISTER", "UNDO"}

    merge_proxies: bpy.props.BoolProperty(name='Merge Cages',
                                          description='Merge the cages if the belong to disconnected vertex selections in Edit Mode.\nOtherwise different Objects will be created for each disconnected vertex island',
                                          default=True)
    proxy_subdivisions: bpy.props.IntProperty(name='Cage Resolution',
                                              description='Resolution of the cage.\nThis is the number of subdivisions in the resulting cage',
                                              default=1, subtype='NONE', min=1, max=4)
    add_to_panel: bpy.props.BoolProperty(name='Add to Physics Panel',
                                         description='Add the Collision item to Physics Panel', default=True)

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=1)
        return res and context.active_object and context.active_object.type == 'MESH' and bpy.context.mode == 'EDIT_MESH'

    def execute(self, context):

        res, obj = mustardui_active_object(context, config=1)
        physics_settings = obj.MustardUI_PhysicsSettings
        addon_prefs = context.preferences.addons[base_package].preferences

        # Store Armature Pose states
        stored_pose_states = {}
        for obj in bpy.context.scene.objects:
            if obj.type == 'ARMATURE':
                stored_pose_states[obj.name] = obj.data.pose_position  # Store the pose position ('REST' or 'POSE')

        for obj in [x for x in bpy.context.scene.objects if x.type == "ARMATURE"]:
            # Set the armature to rest position
            obj.data.pose_position = 'REST'

        # Update the scene to reflect the changes
        bpy.context.view_layer.update()

        def generate_unique_name(base_name):
            # Generate a unique name by appending a number if necessary
            name = base_name
            count = 1
            while bpy.data.objects.get(name) is not None:
                name = f"{base_name}.{str(count).zfill(3)}"
                count += 1
            return name

        def add_subdivided_cube(location, bbox_dimensions):
            # Deselect all objects
            bpy.ops.object.select_all(action='DESELECT')
            # Add a cube at the given location
            bpy.ops.mesh.primitive_cube_add(location=location)
            # Get the cube object
            cube = bpy.context.object
            # Generate a unique name for the cube
            base_name = "Physics_Proxy"
            unique_name = generate_unique_name(base_name)
            # Rename the cube
            cube.name = unique_name
            cube.data.name = unique_name
            # Scale the cube to match the bounding box dimensions
            cube.scale = bbox_dimensions / 2  # Scale uses half of the bounding box
            # Apply the scale
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            # Enter edit mode
            bpy.ops.object.mode_set(mode='EDIT')
            # Deselect all vertices
            bpy.ops.mesh.select_all(action='DESELECT')
            # Select all vertices again
            bpy.ops.mesh.select_all(action='SELECT')
            # Subdivide
            bpy.ops.mesh.subdivide(number_cuts=self.proxy_subdivisions, smoothness=0.5)
            # Exit edit mode
            bpy.ops.object.mode_set(mode='OBJECT')
            # Set smooth shading
            bpy.ops.object.shade_flat()
            # Set display settings to wireframe and in front
            cube.display_type = 'WIRE'
            cube.show_in_front = True
            # Disable the cube in renders
            cube.hide_render = True
            return cube  # Return the created cube object for selection later

        def create_vertex_group(obj, group_name, vertices):
            # Create a new vertex group on the object
            vg = obj.vertex_groups.new(name=group_name)
            for vert in vertices:
                vg.add([vert.index], 1.0, 'ADD')  # Add vertex with full weight
            return vg

        def add_surface_deform_modifier(obj, target, group_name, modifier_name):
            # Add a Surface Deform modifier to the object
            mod = obj.modifiers.new(name=modifier_name, type='SURFACE_DEFORM')
            mod.target = target
            mod.vertex_group = group_name
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.surfacedeform_bind(modifier=mod.name)  # Bind the modifier
            return mod

        def add_corrective_smooth_modifier(obj, group_name=None, name="", iterations=20, smooth_type='SIMPLE'):
            # Add a Corrective Smooth modifier with specified settings
            mod = obj.modifiers.new(name="Jiggle Corrective" if name == "" else name, type='CORRECTIVE_SMOOTH')
            mod.iterations = iterations
            mod.smooth_type = smooth_type
            mod.rest_source = 'BIND'
            if group_name:
                mod.vertex_group = group_name
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.correctivesmooth_bind(modifier=mod.name)  # Bind the modifier
            return mod

        # Create Physics Proxies from Selected Islands
        # Get the active mesh object and its mesh data
        obj = bpy.context.object
        me = obj.data

        # Switch to object mode temporarily to access the bmesh
        bpy.ops.object.mode_set(mode='OBJECT')
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.verts.ensure_lookup_table()

        # Find all connected vertex islands (selected vertices)
        islands = []
        visited = set()
        for vert in bm.verts:
            if vert.select and vert not in visited:
                island = set()
                stack = [vert]
                while stack:
                    current_vert = stack.pop()
                    if current_vert not in visited:
                        visited.add(current_vert)
                        island.add(current_vert)
                        for edge in current_vert.link_edges:
                            neighbor = edge.other_vert(current_vert)
                            if neighbor.select and neighbor not in visited:
                                stack.append(neighbor)
                islands.append(island)

        # List to store created proxy objects
        created_proxies = []

        # Create a combined vertex group for all regions
        combined_group_verts = set()

        # Store dynamically created vertex groups for each region
        region_vertex_groups = []

        # For each island, calculate the center and bounding box, and add a physics proxy mesh
        for idx, island in enumerate(islands):
            island_coords = [v.co for v in island]
            # Calculate the bounding box (min and max coordinates)
            min_coords = Vector((min([v.x for v in island_coords]),
                                 min([v.y for v in island_coords]),
                                 min([v.z for v in island_coords])))
            max_coords = Vector((max([v.x for v in island_coords]),
                                 max([v.y for v in island_coords]),
                                 max([v.z for v in island_coords])))
            # Bounding box dimensions
            bbox_dimensions = max_coords - min_coords
            # Center of the bounding box
            center = (min_coords + max_coords) / 2
            # Create a physics proxy cube with dimensions matching the bounding box
            proxy = add_subdivided_cube(location=obj.matrix_world @ center, bbox_dimensions=bbox_dimensions)
            # Add the proxy object to the list of created proxies
            created_proxies.append(proxy)
            # Create a vertex group for this region
            group_name = f"Jiggle Region {idx + 1}"
            region_vertex_group = create_vertex_group(obj, group_name, island)
            region_vertex_groups.append(region_vertex_group.name)  # Store the group name
            # Add vertices from this island to the combined group
            combined_group_verts.update(island)

        # Create the combined vertex group for all regions
        combined_group_name = "Combined Jiggle Groups"
        combined_vertex_group = create_vertex_group(obj, combined_group_name, combined_group_verts)

        # Clean up the bmesh
        bm.free()

        # Switch back to object mode
        bpy.ops.object.mode_set(mode='OBJECT')

        # Add Surface Deform modifiers
        if self.merge_proxies:
            # Merge the proxies if merge_proxies is True
            bpy.ops.object.select_all(action='DESELECT')
            for proxy in created_proxies:
                proxy.select_set(True)
            bpy.context.view_layer.objects.active = created_proxies[0]
            bpy.ops.object.join()
            merged_proxy = bpy.context.object
            # Add a single Surface Deform modifier targeting the merged proxy
            add_surface_deform_modifier(obj, merged_proxy, combined_vertex_group.name, "Jiggle Deform")
            # Select the merged proxy
            bpy.ops.object.select_all(action='DESELECT')
            merged_proxy.select_set(True)
        else:
            # Add a Surface Deform modifier for each individual proxy using the correct vertex group for each
            for idx, proxy in enumerate(created_proxies):
                group_name = region_vertex_groups[idx]  # Use the dynamically created vertex group
                add_surface_deform_modifier(obj, proxy, group_name, f"Jiggle Deform {idx + 1}")
            # Select all proxies
            bpy.ops.object.select_all(action='DESELECT')
            for proxy in created_proxies:
                proxy.select_set(True)

        # Add Corrective Smooth modifier to the source mesh
        name = ""
        for n in [x.name for x in bpy.context.selected_objects]:
            name = name + n
        add_corrective_smooth_modifier(obj, combined_vertex_group.name, name)

        # Now, apply a corrective smooth modifier to the selected proxies/meshes
        for selected_obj in bpy.context.selected_objects:
            add_corrective_smooth_modifier(selected_obj)

        # Ensure the original object remains active
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

        def copy_armature_modifier(source, targets):
            # Find the armature modifier in the source object
            armature_modifier = next((mod for mod in source.modifiers if mod.type == 'ARMATURE'), None)
            if not armature_modifier:
                print("No armature modifier found in the active object.")
                return
            # Copy the armature modifier to each target object
            for target in targets:
                if target != source and target.type == 'MESH':
                    # Remove existing armature modifiers
                    for mod in target.modifiers:
                        if mod.type == 'ARMATURE':
                            target.modifiers.remove(mod)
                    # Add a new armature modifier to the target object
                    new_modifier = target.modifiers.new(name=armature_modifier.name, type='ARMATURE')
                    new_modifier.object = armature_modifier.object
                    new_modifier.use_vertex_groups = armature_modifier.use_vertex_groups
                    new_modifier.use_bone_envelopes = armature_modifier.use_bone_envelopes
                    new_modifier.use_deform_preserve_volume = armature_modifier.use_deform_preserve_volume
                    new_modifier.use_multi_modifier = armature_modifier.use_multi_modifier
                    # Move the new modifier to the top of the stack
                    bpy.context.view_layer.objects.active = target
                    for _ in range(len(target.modifiers)):
                        bpy.ops.object.modifier_move_up(modifier=new_modifier.name)

        # Store the initial active object and selection
        context = bpy.context
        initial_active_obj = context.active_object
        initial_selection = context.selected_objects[:]

        if initial_active_obj and initial_selection:
            copy_armature_modifier(initial_active_obj, initial_selection)

        # Restore the initial active object and selection
        context.view_layer.objects.active = initial_active_obj
        for obj in context.view_layer.objects:
            obj.select_set(obj in initial_selection)

        bpy.ops.object.data_transfer('INVOKE_DEFAULT', use_freeze=False, data_type='VGROUP_WEIGHTS',
                                     use_create=True, vert_mapping='POLYINTERP_NEAREST', use_auto_transform=False,
                                     use_object_transform=True, use_max_distance=False, ray_radius=0.1,
                                     layers_select_src='ALL', layers_select_dst='NAME', mix_mode='REPLACE',
                                     mix_factor=1.0)

        def create_unique_vertex_group_name(obj, base_name):
            """Create a unique vertex group name by appending a number if necessary."""
            existing_groups = {group.name for group in obj.vertex_groups}
            if base_name not in existing_groups:
                return base_name
            # If base_name exists, append .001, .002, etc.
            index = 1
            while True:
                new_name = f"{base_name}.{str(index).zfill(3)}"
                if new_name not in existing_groups:
                    return new_name
                index += 1

        def create_gradient_vertex_group(obj, group_name, all_islands):
            """Creates a vertex group with a gradient weight based on the Y position of vertices for all islands."""
            # Create a unique name for the vertex group if needed
            unique_group_name = create_unique_vertex_group_name(obj, group_name)
            # Create the vertex group
            vertex_group = obj.vertex_groups.new(name=unique_group_name)
            # Collect all vertex weights for all islands before switching modes
            all_vertex_weights = []
            for island_verts in all_islands:
                # Collect world coordinates and vertex indices for the current island
                world_coords = [(v.index, obj.matrix_world @ v.co) for v in island_verts]
                # Calculate min and max Y coordinates in world space for this island
                bbox_min_y = min(world_coords, key=lambda vc: vc[1].y)[1].y
                bbox_max_y = max(world_coords, key=lambda vc: vc[1].y)[1].y
                bbox_depth = bbox_max_y - bbox_min_y if bbox_max_y != bbox_min_y else 1  # Avoid division by zero
                # Collect vertex weights for this island
                vertex_weights = [(v_idx, (world_co.y - bbox_min_y) / bbox_depth) for v_idx, world_co in world_coords]
                all_vertex_weights.extend(vertex_weights)
            # Apply weights to the vertex group in object mode
            bpy.ops.object.mode_set(mode='OBJECT')
            for index, weight in all_vertex_weights:
                vertex_group.add([index], weight, 'REPLACE')

        def get_geometry_islands(bm):
            """Get geometry islands as separate groups of vertices."""
            islands = []
            visited = set()
            # Iterate over all verts, creating islands
            for v in bm.verts:
                if v.index not in visited:
                    island = []
                    stack = [v]
                    # Depth-first search to find all connected vertices (an island)
                    while stack:
                        vert = stack.pop()
                        if vert.index not in visited:
                            visited.add(vert.index)
                            island.append(vert)
                            for edge in vert.link_edges:
                                other_vert = edge.other_vert(vert)
                                if other_vert.index not in visited:
                                    stack.append(other_vert)
                    islands.append(island)
            return islands

        def restore_selection_and_mode(mode, selected_objects, active_object):
            """Restore the original selection and mode."""
            bpy.ops.object.select_all(action='DESELECT')
            for obj in selected_objects:
                obj.select_set(True)
            bpy.context.view_layer.objects.active = active_object
            bpy.ops.object.mode_set(mode=mode)

        # Store the current selection and mode
        initial_mode = bpy.context.object.mode
        initial_selected_objects = bpy.context.selected_objects
        initial_active_object = bpy.context.view_layer.objects.active

        selected_objects = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
        active_object = bpy.context.view_layer.objects.active

        if selected_objects:
            for obj in selected_objects:
                if obj != active_object:  # Exclude the active mesh
                    bpy.context.view_layer.objects.active = obj
                    bpy.ops.object.mode_set(mode='EDIT')
                    bm = bmesh.from_edit_mesh(obj.data)
                    islands = get_geometry_islands(bm)

                    # Pass all islands at once to the vertex group creation function
                    create_gradient_vertex_group(obj, "Jiggle Pin", islands)
                    if addon_prefs.debug:
                        print(f"Gradient vertex group 'Jiggle Pin' (or numbered version) applied to geometry islands in {obj.name}.")

        # Restore the original selection and mode
        restore_selection_and_mode(initial_mode, initial_selected_objects, initial_active_object)

        # Restore Armature Pose States
        for obj in bpy.context.scene.objects:
            if obj.type == 'ARMATURE' and obj.name in stored_pose_states:
                # Restore the saved pose position ('REST' or 'POSE')
                obj.data.pose_position = stored_pose_states[obj.name]

        # Force the scene to update
        bpy.context.view_layer.update()

        # Deselect Active Mesh
        active_obj = bpy.context.active_object

        if active_obj and active_obj.type == 'MESH':
            # Deselect the active mesh
            active_obj.select_set(False)
            # Update the scene (optional, depending on the Blender version)
            bpy.context.view_layer.update()

        # Set the gain value as a variable, which can be adjusted later
        gain_value = 1.5

        for obj in [x for x in bpy.context.selected_objects if x.type == "MESH"]:
            # Make the object active
            bpy.context.view_layer.objects.active = obj
            # Perform the vertex group levels operation with the specified gain
            bpy.ops.object.vertex_group_levels(gain=gain_value)

        # Apply Default Preset
        bpy.ops.mustardui.tools_creators_create_jiggle_preset('INVOKE_DEFAULT', )

        def move_cloth_above_corrective_smooth(obj):
            cloth_modifier = None
            last_corrective_smooth = None
            # Find the Cloth modifier and the last Corrective Smooth modifier
            for mod in obj.modifiers:
                if mod.type == 'CLOTH':
                    cloth_modifier = mod
                elif mod.type == 'CORRECTIVE_SMOOTH':
                    last_corrective_smooth = mod
            if cloth_modifier and last_corrective_smooth:
                # Move the Cloth modifier above the last Corrective Smooth modifier
                while obj.modifiers.find(cloth_modifier.name) > obj.modifiers.find(last_corrective_smooth.name):
                    bpy.context.view_layer.objects.active = obj
                    bpy.ops.object.modifier_move_up(modifier=cloth_modifier.name)
                if addon_prefs.debug:
                    print(f"Moved Cloth modifier above the last Corrective Smooth modifier for {obj.name}.")
            else:
                if addon_prefs.debug:
                    print(f"Cloth or Corrective Smooth modifier not found for {obj.name}.")

        # Move Cloth for selected Objects
        selected_objects = bpy.context.selected_objects
        for obj in selected_objects:
            if obj.type == 'MESH':
                move_cloth_above_corrective_smooth(obj)
            else:
                if addon_prefs.debug:
                    print(f"Skipped {obj.name}, not a mesh object.")

        # Toggle Edit Mode
        if bpy.context.active_object and bpy.context.active_object.type == 'MESH':
            # Store the current mode
            current_mode = bpy.context.object.mode
            # Switch to Edit Mode
            bpy.ops.object.mode_set(mode='EDIT')
            # Switch back to the previous mode (typically Object Mode)
            bpy.ops.object.mode_set(mode=current_mode)

        # Add the object to the Physics Panel
        if self.add_to_panel:
            for obj in bpy.context.selected_objects:
                add_item = physics_settings.items.add()
                add_item.object = obj
                add_item.type = 'CAGE'

        self.report({'INFO'}, 'MustardUI - Jiggle Cage created.')

        return {"FINISHED"}

    def draw(self, context):

        settings = context.scene.MustardUI_Settings

        layout = self.layout
        layout.prop(self, 'proxy_subdivisions', emboss=True)
        if settings.advanced:
            layout.prop(self, 'merge_proxies', emboss=True)

        layout.separator()
        box = layout.box()
        box.label(text="UI", icon="MENU_PANEL")
        box.prop(self, 'add_to_panel', emboss=True)

    def invoke(self, context, event):
        self.merge_proxies = True
        self.proxy_subdivisions = 1
        return context.window_manager.invoke_props_dialog(self, width=300)


def register():
    bpy.utils.register_class(MustardUI_ToolsCreators_CreateJiggle_Preset)
    bpy.utils.register_class(MustardUI_ToolsCreators_CreateJiggle)


def unregister():
    bpy.utils.unregister_class(MustardUI_ToolsCreators_CreateJiggle)
    bpy.utils.unregister_class(MustardUI_ToolsCreators_CreateJiggle_Preset)
