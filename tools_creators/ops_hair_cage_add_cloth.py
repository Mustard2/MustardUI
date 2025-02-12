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
from ..model_selection.active_object import *
from .. import __package__ as base_package


class MustardUI_ToolsCreators_AddClothToHair(bpy.types.Operator):
    """This function adds cloth physics with default settings to the mesh.\nIn Object Mode, it uses the active vertex group as the 'Pin Group'. If called in Edit Mode, the pin group is assigned to the selected vertices.\nThe operation applies to both the active object and any selected objects."""
    bl_idname = "mustardui.tools_creators_add_cloth_to_hair"
    bl_label = "Add Cloth Physics to Hair Cage"
    bl_options = {"REGISTER", "UNDO"}

    quality: bpy.props.IntProperty(name='Simulation Steps', description='Sets the quality of the Physics simulation', default=7,
                                   min=1, soft_max=10)
    collision_quality: bpy.props.IntProperty(name='Collision Steps', description='Sets the quality of collisions evaluation during the simulation', default=2,
                                             min=1, soft_max=10)
    timescale: bpy.props.FloatProperty(name='Speed Multiplier', description='Lower value will slow the simulation (more dragged effect)', default=1.0,
                                       min=0.0, soft_max=10.0, step=3,
                                       precision=3)
    vertex_mass: bpy.props.FloatProperty(name='Vertex Mass', description='Mass of each vertex for gravity and inertia evaluations', default=1.0,
                                         min=0.0, soft_max=10.0,
                                         step=3, precision=3)
    shear_stiffness: bpy.props.FloatProperty(name='Shear Stiffness', description='',
                                             default=0.1, min=0.0, soft_max=10.0, step=3,
                                             precision=3)
    collision: bpy.props.BoolProperty(name='Collision', description='Enables collisions', default=True)
    self_collision: bpy.props.BoolProperty(name='Self Collision', description='Enables collisions between parts of the cage', default=False)

    @classmethod
    def poll(cls, context):

        res, arm = mustardui_active_object(context, config=1)
        if not res:
            return False

        if len(bpy.context.selected_objects) > 1:
            return False

        if bpy.context.active_object and bpy.context.active_object.type == 'MESH':
            return bpy.context.active_object.MustardUI_tools_creators_is_created

        return False

    def execute(self, context):

        if not bpy.context.active_object:
            return {"FINISHED"}

        obj = bpy.context.active_object
        if not obj.type == 'MESH' or not obj.MustardUI_tools_creators_is_created:
            return {"FINISHED"}

        # Set the playback sync mode to 'NONE' (Play Every Frame)
        bpy.context.scene.sync_mode = 'NONE'

        # Remove Cloth Modifiers
        if obj.type == 'MESH':
            # List to hold the names of the cloth modifiers to be removed
            cloth_modifiers = [mod.name for mod in obj.modifiers if mod.type == 'CLOTH']
            # Remove each cloth modifier
            for mod_name in cloth_modifiers:
                obj.modifiers.remove(obj.modifiers[mod_name])

        timescale_multiplier = self.timescale
        mass_value = self.vertex_mass
        shear_stiffness_value = self.shear_stiffness
        collision_quality_value = self.collision_quality
        quality = self.quality
        collision = self.collision
        self_collision = self.self_collision

        # Define the variables for base FPS and timescale multiplier
        base_fps = 24

        # Get the playback FPS from the scene's current FPS
        playback_fps = bpy.context.scene.render.fps

        # Calculate the time scale using the formula: (base_fps / playback_fps) * timescale_multiplier
        time_scale_value = (base_fps / playback_fps) * timescale_multiplier

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

        # Set the object as active
        bpy.context.view_layer.objects.active = obj
        # Add or get the existing Cloth modifier
        cloth_modifier = obj.modifiers.get("Cloth")
        if not cloth_modifier:
            cloth_modifier = obj.modifiers.new(name="Cloth", type='CLOTH')
        # Set Cloth modifier settings
        cloth_modifier.settings.quality = quality  # Use the quality variable here
        cloth_modifier.settings.time_scale = time_scale_value
        cloth_modifier.settings.mass = mass_value
        cloth_modifier.settings.shear_stiffness = shear_stiffness_value
        cloth_modifier.settings.bending_stiffness = 1
        cloth_modifier.collision_settings.collision_quality = collision_quality_value
        cloth_modifier.collision_settings.use_collision = collision
        cloth_modifier.collision_settings.distance_min = 0.001
        cloth_modifier.collision_settings.use_self_collision = self_collision
        cloth_modifier.collision_settings.self_distance_min = 0.001
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
        # Set the vertex group as the pin group if applicable
        if vertex_group_name:
            cloth_modifier.settings.vertex_group_mass = vertex_group_name
        # Set simulation start and end to the same start and end frame values of the scene
        cloth_modifier.point_cache.frame_start = bpy.context.scene.frame_start
        cloth_modifier.point_cache.frame_end = bpy.context.scene.frame_end

        # Print a completion message
        print("Cloth modifiers added, configured, and collisions enabled for selected mesh objects.")

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
            print(f"Moved Cloth modifier above the last Corrective Smooth modifier for {obj.name}.")
        else:
            print(f"Cloth or Corrective Smooth modifier not found for {obj.name}.")

        # Store the current mode
        current_mode = bpy.context.object.mode
        # Switch to Edit Mode
        bpy.ops.object.mode_set(mode='EDIT')
        # Switch back to the previous mode (typically Object Mode)
        bpy.ops.object.mode_set(mode=current_mode)

        return {"FINISHED"}

    def draw(self, context):

        layout = self.layout

        col = layout.column(align=True)
        col.operator_context = "INVOKE_DEFAULT" if True else "EXEC_DEFAULT"
        col.prop(self, 'quality')
        col.prop(self, 'collision_quality')
        col.prop(self, 'timescale')
        col.prop(self, 'vertex_mass')
        col.prop(self, 'shear_stiffness')

        row = col.row(align=True)
        row.operator_context = "INVOKE_DEFAULT" if True else "EXEC_DEFAULT"
        row.prop(self, 'collision', icon_value=414, emboss=True)
        row.prop(self, 'self_collision', icon_value=414, emboss=True)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)


def register():
    bpy.utils.register_class(MustardUI_ToolsCreators_AddClothToHair)


def unregister():
    bpy.utils.unregister_class(MustardUI_ToolsCreators_AddClothToHair)
