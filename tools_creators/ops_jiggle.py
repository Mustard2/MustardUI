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

import bmesh
import bpy
from mathutils import Vector

from .. import __package__ as base_package
from ..model_selection.active_object import mustardui_active_object
from . import physics_presets


def _apply_jiggle_physics(operator):
    """Apply the physics preset selected on 'operator' to every selected mesh.

    Uses the active vertex group as the Pin group in Object Mode; in Edit Mode a
    new group is created from the selected vertices instead.
    """

    # Function to handle vertex group creation and assignment in Edit Mode
    def create_vertex_group(obj, base_name="ClothPinGroup"):
        # Switch to Object Mode temporarily to update the vertex group
        bpy.ops.object.mode_set(mode="OBJECT")

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
        vertex_group.add(selected_verts, 1.0, "ADD")

        # Return to Edit Mode
        bpy.ops.object.mode_set(mode="EDIT")

        return new_name

    engine, preset = physics_presets.selected_preset(operator)

    for obj in [x for x in bpy.context.selected_objects if x.type == "MESH"]:
        # Set the object as active
        bpy.context.view_layer.objects.active = obj

        # Check current mode and handle vertex groups
        current_mode = bpy.context.object.mode
        vertex_group_name = None
        if current_mode == "EDIT":
            vertex_group_name = create_vertex_group(obj)
        elif current_mode == "OBJECT" and obj.vertex_groups.active:
            vertex_group_name = obj.vertex_groups.active.name

        # The settings are not written here: every Creator Tool goes through the
        # same presets, so that they are defined in a single place
        if (
            physics_presets.apply_physics(
                obj,
                engine=engine,
                preset=preset,
                pin_group_name=vertex_group_name or "",
            )
            is None
        ):
            operator.report(
                {"WARNING"},
                "MustardUI - The Cloth Dynamics physics could not be added: the "
                "Cloth modifier was used instead.",
            )
            physics_presets.apply_physics(
                obj,
                engine="CLOTH",
                preset=operator.cloth_preset,
                pin_group_name=vertex_group_name or "",
            )

    # Toggle Edit Mode
    if bpy.context.active_object and bpy.context.active_object.type == "MESH":
        # Store the current mode
        current_mode = bpy.context.object.mode

        # Switch to Edit Mode
        bpy.ops.object.mode_set(mode="EDIT")

        # Switch back to the previous mode (typically Object Mode)
        bpy.ops.object.mode_set(mode=current_mode)


class MustardUI_ToolsCreators_CreateJiggle(bpy.types.Operator):
    bl_idname = "mustardui.tools_creators_create_jiggle"
    bl_label = "Create Jiggle Cage (Low-resolution)"
    bl_description = "Needs to select vertices in Edit Mode.\nCreates a jiggle cage using the selected regions in Edit Mode and attaches it to the active mesh"  # noqa: E501
    bl_options = {"REGISTER", "UNDO", "PRESET"}

    merge_proxies: bpy.props.BoolProperty(
        name="Merge Cages",
        description="Merge the cages if the belong to disconnected vertex selections "
        "in Edit Mode.\nOtherwise different Objects will be created for each "
        "disconnected vertex island",
        default=True,
    )
    proxy_subdivisions: bpy.props.IntProperty(
        name="Cage Resolution",
        description="Resolution of the cage.\nThis is the number of subdivisions in "
        "the resulting cage",
        default=1,
        subtype="NONE",
        min=1,
        max=8,
    )
    object_direction: bpy.props.EnumProperty(
        name="Pin Direction",
        description="Direction where to create the Pin group weights.\nThe direction "
        "in global coordinates is the direction in which the weights decreases",
        items=[
            (
                "AUTO",
                "Automatic",
                "Infer the direction from the border of the selection",
            ),
            ("+X", "+X", "+X"),
            ("-X", "-X", "-X"),
            ("+Y", "+Y", "+Y"),
            ("-Y", "-Y", "-Y"),
            ("+Z", "+Z", "+Z"),
            ("-Z", "-Z", "-Z"),
        ],
        default="AUTO",
    )
    parent_to_model: bpy.props.BoolProperty(
        name="Parent to Model",
        description="Parent the cage to the Model Armature",
        default=False,
    )
    add_to_panel: bpy.props.BoolProperty(
        name="Add to Physics Panel",
        description="Add the Collision item to Physics Panel",
        default=True,
    )
    name: bpy.props.StringProperty(
        name="Cage Name",
        description="Assign a name to the Cage and the associated modifiers",
        default="",
    )
    physics_engine: physics_presets.physics_engine_property()
    cloth_preset: physics_presets.cloth_preset_property(default="JIGGLE")
    nodes_preset: physics_presets.nodes_preset_property(default="JIGGLE")

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=1)
        return (
            res
            and context.active_object
            and context.active_object.type == "MESH"
            and bpy.context.mode == "EDIT_MESH"
        )

    def execute(self, context):

        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings
        physics_settings = obj.MustardUI_PhysicsSettings
        addon_prefs = context.preferences.addons[base_package].preferences

        # Store Armature Pose states
        stored_pose_states = {}
        for obj in bpy.context.scene.objects:
            if obj.type == "ARMATURE":
                stored_pose_states[obj.name] = (
                    obj.data.pose_position
                )  # Store the pose position ('REST' or 'POSE')

        for obj in [x for x in bpy.context.scene.objects if x.type == "ARMATURE"]:
            # Set the armature to rest position
            obj.data.pose_position = "REST"

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

        # Assign names
        base_name = generate_unique_name(self.name) if self.name != "" else "Physics_Proxy"
        corrective_name = base_name
        surfdef_name = base_name + " Deform"

        def add_subdivided_cube(location, bbox_dimensions):
            # Deselect all objects
            bpy.ops.object.select_all(action="DESELECT")
            # Add a cube at the given location
            bpy.ops.mesh.primitive_cube_add(location=location)
            # Get the cube object
            cube = bpy.context.object
            # Generate a unique name for the cube
            unique_name = generate_unique_name(base_name)
            # Rename the cube
            cube.name = unique_name
            cube.data.name = unique_name
            # Scale the cube to match the bounding box dimensions
            cube.scale = bbox_dimensions / 2  # Scale uses half of the bounding box
            # Apply the scale
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            # Enter edit mode
            bpy.ops.object.mode_set(mode="EDIT")
            # Deselect all vertices
            bpy.ops.mesh.select_all(action="DESELECT")
            # Select all vertices again
            bpy.ops.mesh.select_all(action="SELECT")
            # Subdivide
            bpy.ops.mesh.subdivide(number_cuts=self.proxy_subdivisions, smoothness=0.5)
            # Exit edit mode
            bpy.ops.object.mode_set(mode="OBJECT")
            # Set smooth shading
            bpy.ops.object.shade_flat()
            # Set display settings to wireframe and in front
            cube.display_type = "WIRE"
            cube.show_in_front = True
            # Disable the cube in renders
            cube.hide_render = True
            return cube  # Return the created cube object for selection later

        def create_vertex_group(obj, group_name, vertices):
            # Create a new vertex group on the object
            vg = obj.vertex_groups.new(name=group_name)
            for vert in vertices:
                vg.add([vert.index], 1.0, "ADD")  # Add vertex with full weight
            return vg

        def add_surface_deform_modifier(obj, target, group_name, modifier_name):
            # Add a Surface Deform modifier to the object
            mod = obj.modifiers.new(name=modifier_name, type="SURFACE_DEFORM")
            mod.target = target
            mod.vertex_group = group_name
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.surfacedeform_bind(modifier=mod.name)  # Bind the modifier
            return mod

        def add_corrective_smooth_modifier(
            obj, group_name=None, name="", iterations=20, smooth_type="SIMPLE"
        ):
            # Add a Corrective Smooth modifier with specified settings
            mod = obj.modifiers.new(
                name=corrective_name if name == "" else name, type="CORRECTIVE_SMOOTH"
            )
            mod.iterations = iterations
            mod.smooth_type = smooth_type
            mod.rest_source = "BIND"
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
        bpy.ops.object.mode_set(mode="OBJECT")
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

        def island_pin_direction(island):
            """The direction the Pin weights of a region of the model decrease along."""
            border = [v for v in island if any(not e.other_vert(v).select for e in v.link_edges)]
            if not border:
                return None

            island_center = sum((v.co for v in island), Vector()) / len(island)
            border_center = sum((v.co for v in border), Vector()) / len(border)

            # The direction is used against the world coordinates of the cage
            direction = obj.matrix_world.to_3x3() @ (island_center - border_center)

            # A region centred on its own border (a belt, a ring) has no side to
            # hang from, as much as one which is attached all around
            if direction.length < 1e-6:
                return None

            return direction.normalized()

        # List to store created proxy objects
        created_proxies = []

        # Pin direction of each region, and where the region is, to match the cages
        # back to the region they were built on when Automatic is used
        island_directions = []
        island_centers = []

        # Create a combined vertex group for all regions
        combined_group_verts = set()

        # Store dynamically created vertex groups for each region
        region_vertex_groups = []

        # For each island, calculate the center and bounding box, and add a physics
        # proxy mesh
        for idx, island in enumerate(islands):
            island_coords = [v.co for v in island]
            # Calculate the bounding box (min and max coordinates)
            min_coords = Vector(
                (
                    min([v.x for v in island_coords]),
                    min([v.y for v in island_coords]),
                    min([v.z for v in island_coords]),
                )
            )
            max_coords = Vector(
                (
                    max([v.x for v in island_coords]),
                    max([v.y for v in island_coords]),
                    max([v.z for v in island_coords]),
                )
            )
            # Bounding box dimensions
            bbox_dimensions = max_coords - min_coords
            # Center of the bounding box
            center = (min_coords + max_coords) / 2
            # Create a physics proxy cube with dimensions matching the bounding box
            proxy = add_subdivided_cube(
                location=obj.matrix_world @ center, bbox_dimensions=bbox_dimensions
            )
            # Add the proxy object to the list of created proxies
            created_proxies.append(proxy)
            # Store the direction the Pin group of this region hangs from
            island_directions.append(island_pin_direction(island))
            island_centers.append(obj.matrix_world @ center)
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
        bpy.ops.object.mode_set(mode="OBJECT")

        # Add Surface Deform modifiers
        if self.merge_proxies:
            # Merge the proxies if merge_proxies is True
            bpy.ops.object.select_all(action="DESELECT")
            for proxy in created_proxies:
                proxy.select_set(True)
            bpy.context.view_layer.objects.active = created_proxies[0]
            bpy.ops.object.join()
            merged_proxy = bpy.context.object
            # Add a single Surface Deform modifier targeting the merged proxy
            add_surface_deform_modifier(obj, merged_proxy, combined_vertex_group.name, surfdef_name)
            # Select the merged proxy
            bpy.ops.object.select_all(action="DESELECT")
            merged_proxy.select_set(True)
        else:
            # Add a Surface Deform modifier for each individual proxy using the
            # correct vertex group for each
            for idx, proxy in enumerate(created_proxies):
                group_name = region_vertex_groups[idx]  # Use the dynamically created vertex group
                add_surface_deform_modifier(obj, proxy, group_name, f"{surfdef_name} {idx + 1}")
            # Select all proxies
            bpy.ops.object.select_all(action="DESELECT")
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
            armature_modifier = next(
                (mod for mod in source.modifiers if mod.type == "ARMATURE"), None
            )
            if not armature_modifier:
                print("No armature modifier found in the active object.")
                return
            # Copy the armature modifier to each target object
            for target in targets:
                if target != source and target.type == "MESH":
                    # Remove existing armature modifiers
                    for mod in target.modifiers:
                        if mod.type == "ARMATURE":
                            target.modifiers.remove(mod)
                    # Add a new armature modifier to the target object
                    new_modifier = target.modifiers.new(
                        name=armature_modifier.name, type="ARMATURE"
                    )
                    new_modifier.object = armature_modifier.object
                    new_modifier.use_vertex_groups = armature_modifier.use_vertex_groups
                    new_modifier.use_bone_envelopes = armature_modifier.use_bone_envelopes
                    new_modifier.use_deform_preserve_volume = (
                        armature_modifier.use_deform_preserve_volume
                    )
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

        bpy.ops.object.data_transfer(
            "INVOKE_DEFAULT",
            use_freeze=False,
            data_type="VGROUP_WEIGHTS",
            use_create=True,
            vert_mapping="POLYINTERP_NEAREST",
            use_auto_transform=False,
            use_object_transform=True,
            use_max_distance=False,
            ray_radius=0.1,
            layers_select_src="ALL",
            layers_select_dst="NAME",
            mix_mode="REPLACE",
            mix_factor=1.0,
        )

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

        # Regions whose Pin direction could not be inferred, reported once at the end
        auto_fallback = []

        PIN_AXIS_FALLBACK = "+Y"

        def pin_direction(world_coords):
            """The direction the weights of a single cage island decrease along."""

            PIN_AXES = {
                "+X": Vector((1.0, 0.0, 0.0)),
                "-X": Vector((-1.0, 0.0, 0.0)),
                "+Y": Vector((0.0, 1.0, 0.0)),
                "-Y": Vector((0.0, -1.0, 0.0)),
                "+Z": Vector((0.0, 0.0, 1.0)),
                "-Z": Vector((0.0, 0.0, -1.0)),
            }

            if self.object_direction != "AUTO":
                return PIN_AXES[self.object_direction]

            center = sum((co for _, co in world_coords), Vector()) / len(world_coords)
            nearest = min(
                range(len(island_centers)),
                key=lambda i: (island_centers[i] - center).length_squared,
            )

            direction = island_directions[nearest]
            if direction is None:
                auto_fallback.append(nearest)
                return PIN_AXES[PIN_AXIS_FALLBACK]

            return direction

        def create_gradient_vertex_group(obj, group_name, all_islands):
            """Creates a vertex group with a gradient weight along the Pin direction for all islands."""  # noqa: E501
            # Create a unique name for the vertex group if needed
            unique_group_name = create_unique_vertex_group_name(obj, group_name)
            # Create the vertex group
            vertex_group = obj.vertex_groups.new(name=unique_group_name)
            # Collect all vertex weights for all islands before switching modes
            all_vertex_weights = []
            for island_verts in all_islands:
                # Collect world coordinates and vertex indices for the current island
                world_coords = [(v.index, obj.matrix_world @ v.co) for v in island_verts]
                # Where each vertex stands along the direction the weights decrease
                # along: a signed axis is the direction itself, so the same
                # projection covers the manual directions and the inferred ones
                direction = pin_direction(world_coords)
                projections = [(v_idx, world_co.dot(direction)) for v_idx, world_co in world_coords]
                bbox_min = min(projection for _, projection in projections)
                bbox_max = max(projection for _, projection in projections)
                bbox_depth = (
                    bbox_max - bbox_min if bbox_max != bbox_min else 1
                )  # Avoid division by zero
                # Collect vertex weights for this island: 1 at the start of the
                # direction, 0 at its end
                all_vertex_weights.extend(
                    (v_idx, 1 - (projection - bbox_min) / bbox_depth)
                    for v_idx, projection in projections
                )
            # Apply weights to the vertex group in object mode
            bpy.ops.object.mode_set(mode="OBJECT")
            for index, weight in all_vertex_weights:
                vertex_group.add([index], weight, "REPLACE")

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
            bpy.ops.object.select_all(action="DESELECT")
            for obj in selected_objects:
                obj.select_set(True)
            bpy.context.view_layer.objects.active = active_object
            bpy.ops.object.mode_set(mode=mode)

        # Store the current selection and mode
        initial_mode = bpy.context.object.mode
        initial_selected_objects = bpy.context.selected_objects
        initial_active_object = bpy.context.view_layer.objects.active

        selected_objects = [obj for obj in bpy.context.selected_objects if obj.type == "MESH"]
        active_object = bpy.context.view_layer.objects.active

        if selected_objects:
            for obj in selected_objects:
                if obj != active_object:  # Exclude the active mesh
                    bpy.context.view_layer.objects.active = obj
                    bpy.ops.object.mode_set(mode="EDIT")
                    bm = bmesh.from_edit_mesh(obj.data)
                    islands = get_geometry_islands(bm)

                    # Pass all islands at once to the vertex group creation function
                    create_gradient_vertex_group(obj, "Jiggle Pin", islands)
                    if addon_prefs.debug:
                        print(
                            f"Gradient vertex group 'Jiggle Pin' (or numbered version) "
                            f"applied to geometry islands in {obj.name}."
                        )

        # Restore the original selection and mode
        restore_selection_and_mode(initial_mode, initial_selected_objects, initial_active_object)

        if auto_fallback:
            self.report(
                {"WARNING"},
                f"MustardUI - The Pin direction of {len(set(auto_fallback))} regions could "
                f"not be inferred: {PIN_AXIS_FALLBACK} was used for them.",
            )

        # Restore Armature Pose States
        for obj in bpy.context.scene.objects:
            if obj.type == "ARMATURE" and obj.name in stored_pose_states:
                # Restore the saved pose position ('REST' or 'POSE')
                obj.data.pose_position = stored_pose_states[obj.name]

        # Force the scene to update
        bpy.context.view_layer.update()

        # Deselect Active Mesh
        active_obj = bpy.context.active_object

        if active_obj and active_obj.type == "MESH":
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

        # Apply the selected Preset
        _apply_jiggle_physics(self)

        def move_cloth_above_corrective_smooth(obj):
            cloth_modifier = None
            last_corrective_smooth = None
            # Find the Cloth modifier and the last Corrective Smooth modifier
            for mod in obj.modifiers:
                if mod.type == "CLOTH":
                    cloth_modifier = mod
                elif mod.type == "CORRECTIVE_SMOOTH":
                    last_corrective_smooth = mod
            if cloth_modifier and last_corrective_smooth:
                # Move the Cloth modifier above the last Corrective Smooth modifier
                while obj.modifiers.find(cloth_modifier.name) > obj.modifiers.find(
                    last_corrective_smooth.name
                ):
                    bpy.context.view_layer.objects.active = obj
                    bpy.ops.object.modifier_move_up(modifier=cloth_modifier.name)
                if addon_prefs.debug:
                    print(
                        f"Moved Cloth modifier above the last Corrective Smooth "
                        f"modifier for {obj.name}."
                    )
            else:
                if addon_prefs.debug:
                    print(f"Cloth or Corrective Smooth modifier not found for {obj.name}.")

        # Move Cloth for selected Objects
        selected_objects = bpy.context.selected_objects
        for obj in selected_objects:
            if obj.type == "MESH":
                move_cloth_above_corrective_smooth(obj)
            else:
                if addon_prefs.debug:
                    print(f"Skipped {obj.name}, not a mesh object.")

        # Toggle Edit Mode
        if bpy.context.active_object and bpy.context.active_object.type == "MESH":
            # Store the current mode
            current_mode = bpy.context.object.mode
            # Switch to Edit Mode
            bpy.ops.object.mode_set(mode="EDIT")
            # Switch back to the previous mode (typically Object Mode)
            bpy.ops.object.mode_set(mode=current_mode)

        # Add the object to the Physics Panel
        if self.add_to_panel:
            for obj in bpy.context.selected_objects:
                add_item = physics_settings.items.add()
                add_item.object = obj
                add_item.type = "CAGE"
                if self.parent_to_model and rig_settings.model_armature_object is not None:
                    parent = rig_settings.model_armature_object
                    obj.parent = parent
                    obj.matrix_parent_inverse = parent.matrix_world.inverted()

        # Disable shadows for viewport/render
        for obj in bpy.context.selected_objects:
            obj.visible_camera = False
            obj.visible_shadow = False
            obj.visible_diffuse = False
            obj.visible_glossy = False
            obj.visible_transmission = False
            obj.visible_volume_scatter = False

        self.report({"INFO"}, "MustardUI - Jiggle Cage created.")

        return {"FINISHED"}

    def draw(self, context):

        layout = self.layout

        layout.separator()

        box = layout.box()
        box.label(text="Cage Generation Settings", icon="SPHERE")
        box.prop(self, "proxy_subdivisions")
        box.prop(self, "object_direction")
        box.prop(self, "merge_proxies", text="Merge Cages (Disconnected Vertex Islands)")

        layout.separator()

        box = layout.box()
        box.label(text="Physics Settings", icon="PHYSICS")
        physics_presets.draw_physics_presets(box, self)

        layout.separator()

        layout.prop(self, "name")

        col = layout.column(align=True)
        col.prop(self, "parent_to_model")
        col.prop(self, "add_to_panel")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)


def register():
    bpy.utils.register_class(MustardUI_ToolsCreators_CreateJiggle)


def unregister():
    bpy.utils.unregister_class(MustardUI_ToolsCreators_CreateJiggle)
