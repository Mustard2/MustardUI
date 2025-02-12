import bpy
from ..model_selection.active_object import *
from .. import __package__ as base_package


class MustardUI_ToolsCreators_AddClothToHair(bpy.types.Operator):
    bl_idname = "mustardui.tools_creators_add_cloth_to_hair"
    bl_label = "Add cloth physics to selected (Hair)"
    bl_description = "Adds cloth physics with default settings to mesh. Uses active vtx group as 'Pin Group' in object mode. If in edit mode then it creates a new vtx group from selection and uses it instead. Applies to active and selected"
    bl_options = {"REGISTER", "UNDO"}

    quality: bpy.props.IntProperty(name='Quality', description='', default=7, subtype='NONE',
                                   min=1, soft_max=10)
    collision_quality: bpy.props.IntProperty(name='Collision Quality', description='', default=2,
                                             subtype='NONE', min=1, soft_max=10)
    timescale: bpy.props.FloatProperty(name='Timescale', description='', default=1.0,
                                       subtype='NONE', unit='NONE', min=0.0, soft_max=10.0, step=3,
                                       precision=3)
    vertex_mass: bpy.props.FloatProperty(name='Vertex Mass', description='', default=1.0,
                                         subtype='NONE', unit='NONE', min=0.0, soft_max=10.0,
                                         step=3, precision=3)
    shear_stiffness: bpy.props.FloatProperty(name='Shear Stiffness', description='',
                                             default=0.1, subtype='NONE',
                                             unit='NONE', min=0.0, soft_max=10.0, step=3,
                                             precision=3)
    collision: bpy.props.BoolProperty(name='Collision', description='', default=True)
    self_collision: bpy.props.BoolProperty(name='Self Collision', description='', default=False)

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
        col = layout.column(heading='', align=True)
        col.alert = False
        col.enabled = True
        col.active = True
        col.use_property_split = False
        col.use_property_decorate = False
        col.scale_x = 1.0
        col.scale_y = 1.0
        col.alignment = 'Expand'.upper()
        col.operator_context = "INVOKE_DEFAULT" if True else "EXEC_DEFAULT"
        col.separator(factor=1.0)
        col.prop(self, 'quality', text='Quality', icon_value=0, emboss=True)
        col.prop(self, 'collision_quality', text='Collision Quality', icon_value=0, emboss=True)
        col.prop(self, 'timescale', text='Timescale', icon_value=0, emboss=True)
        col.prop(self, 'vertex_mass', text='Vertex Mass', icon_value=0, emboss=True)
        col.prop(self, 'shear_stiffness', text='Shear Stiffness', icon_value=0, emboss=True)
        row = col.row(heading='', align=True)
        row.alert = False
        row.enabled = True
        row.active = True
        row.use_property_split = False
        row.use_property_decorate = False
        row.scale_x = 1.0
        row.scale_y = 1.0
        row.alignment = 'Expand'.upper()
        row.operator_context = "INVOKE_DEFAULT" if True else "EXEC_DEFAULT"
        row.prop(self, 'collision', text='Collision', icon_value=414, emboss=True)
        row.prop(self, 'self_collision', text='Self Collision', icon_value=414, emboss=True)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)


def register():
    bpy.utils.register_class(MustardUI_ToolsCreators_AddClothToHair)


def unregister():
    bpy.utils.unregister_class(MustardUI_ToolsCreators_AddClothToHair)
