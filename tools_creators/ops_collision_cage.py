import bpy
from rna_prop_ui import rna_idprop_ui_create
from ..model_selection.active_object import *
from .. import __package__ as base_package


class MustardUI_ToolsCreators_CreateCollisionCage(bpy.types.Operator):
    """Create a collision cage by duplicating the current mesh and masking it based on the selection in Edit Mode. If nothing is selected or if the mesh is in Object Mode, the entire mesh is used.\nThe inflation value of the cage can be adjusted via the object's 'Inflate' custom property.\nThe operation applies to both the active object and any selected objects."""
    bl_idname = "mustardui.tools_creators_create_collision_cage"
    bl_label = "Create collision cage"
    bl_options = {"REGISTER", "UNDO"}

    decimate_proxy: bpy.props.BoolProperty(name='Decimate Cage',
                                           description='Decrease the density of the cage mesh.\nThis considerably improve performance, and it usually lead to similar results to un-decimated cages',
                                           default=True)
    add_to_panel: bpy.props.BoolProperty(name='Add to Physics Panel',
                                         description='Add the Collision item to Physics Panel', default=True)

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=1)
        return res and bpy.context.selected_objects

    def execute(self, context):

        res, obj = mustardui_active_object(context, config=1)
        physics_settings = obj.MustardUI_PhysicsSettings

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

        def remove_drivers_from_visibility(obj):
            """Remove drivers from 'Disable in Viewport' and 'Disable in Renders' properties."""
            if obj.animation_data:
                for prop in ['hide_viewport', 'hide_render']:
                    try:
                        fcurve = obj.animation_data.drivers.find(f'{prop}')
                        if fcurve:
                            obj.driver_remove(f'{prop}')
                    except AttributeError:
                        pass

        def create_vertex_group_from_selection(obj):
            """Create a vertex group from the current selection."""
            group = obj.vertex_groups.new(name="MaskGroup")
            selected_vertices = [v for v in obj.data.vertices if v.select]
            for v in selected_vertices:
                group.add([v.index], 1.0, 'ADD')
            return group.name

        def remove_subdiv_and_multires_modifiers(obj):
            """Remove all Subdivision Surface and Multiresolution modifiers from the object."""
            for modifier in obj.modifiers:
                if modifier.type in {'SUBSURF', 'MULTIRES'}:
                    obj.modifiers.remove(modifier)

        def create_proxy_for_object(obj, vertex_selection_required):
            """Create a proxy object for the given object with specified modifiers and drivers."""
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.duplicate(linked=True)
            duplicate_obj = bpy.context.active_object
            duplicate_obj.name = f"{obj.name} Proxy"

            # Clear existing custom property
            if "Inflate" in obj.keys():
                del obj["Inflate"]

            # Add custom property and set its range
            rna_idprop_ui_create(obj, "Inflate",
                                 default=0.,
                                 min=0., soft_min=0.,
                                 max=1., soft_max=0.,
                                 overridable=True)

            duplicate_obj.display_type = 'WIRE'
            remove_subdiv_and_multires_modifiers(duplicate_obj)
            if vertex_selection_required:
                create_vertex_group_from_selection(obj)  # Keep creating the vertex group without adding a mask modifier
                print(f"Vertex group created for {obj.name} but mask modifier not added.")

            displace_modifier = duplicate_obj.modifiers.new(name="Displace", type='DISPLACE')
            displace_modifier.mid_level = 0.990

            add_driver(displace_modifier, duplicate_obj, '["Inflate"]', 'strength')
            remove_drivers_from_visibility(duplicate_obj)

            # Disable in renders
            duplicate_obj.hide_render = True
            print(f"Duplicate proxy created for {obj.name} with materials unlinked and link set to 'OBJECT'.")

            return duplicate_obj

        def process_proxy(proxy, edit_mode_with_selection):
            """Process each proxy individually with different operations based on edit mode and selection state."""
            bpy.context.view_layer.objects.active = proxy
            proxy.select_set(True)
            bpy.ops.object.mode_set(mode='EDIT')

            # Ensure there is a valid selection before deleting to avoid disappearing geometry
            if edit_mode_with_selection:
                # Operations when in edit mode with a selection
                bpy.ops.mesh.split()
                bpy.ops.mesh.select_all(action='INVERT')
                bpy.ops.mesh.reveal()
                if any(v.select for v in proxy.data.vertices):
                    bpy.ops.mesh.delete(type='VERT')
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.mesh.fill_holes()
                bpy.context.scene.tool_settings.mesh_select_mode = (False, False, True)  # Face select mode
                bpy.ops.mesh.fill_holes(sides=0)
                bpy.ops.mesh.select_all(action='DESELECT')
                bpy.ops.mesh.select_face_by_sides(number=4, type='GREATER')
                bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')
            else:
                # Operations when in object mode or edit mode without selection
                bpy.ops.mesh.reveal()
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.mesh.fill_holes()
                bpy.context.scene.tool_settings.mesh_select_mode = (False, False, True)  # Face select mode
                bpy.ops.mesh.fill_holes(sides=0)
                bpy.ops.mesh.select_all(action='DESELECT')
                bpy.ops.mesh.select_face_by_sides(number=4, type='GREATER')
                bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')

            bpy.ops.object.mode_set(mode='OBJECT')

        selected_objs = bpy.context.selected_objects
        active_obj = bpy.context.active_object
        vertex_selection_required = False
        edit_mode_with_selection = False
        proxy_map = {}  # To store the mapping of original objects and their proxies

        # Determine if we have vertex selections in Edit mode for each object individually
        for obj in selected_objs:
            if obj.type == 'MESH' and obj.mode == 'EDIT':
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.mode_set(mode='OBJECT')
                if any(v.select for v in obj.data.vertices):
                    vertex_selection_required = True
                    edit_mode_with_selection = True
                bpy.ops.object.mode_set(mode='EDIT')

        # Process each selected mesh individually
        if selected_objs:
            # Switch to Object mode for processing
            bpy.ops.object.mode_set(mode='OBJECT')
            for obj in selected_objs:
                if obj.type == 'MESH':
                    # Create a proxy for each selected mesh individually
                    proxy = create_proxy_for_object(obj, vertex_selection_required)
                    # Make the proxy's mesh data single user.
                    proxy.data = proxy.data.copy()
                    # Store the mapping of original object and proxy
                    proxy_map[obj] = proxy
                    # Process each proxy based on the context of the original object
                    process_proxy(proxy, edit_mode_with_selection)
            # Restore selection: Deselect all first
            bpy.ops.object.select_all(action='DESELECT')
            # Restore the selection for proxies based on original selection
            for original, proxy in proxy_map.items():
                proxy.select_set(True)
                # Set the active object to the proxy if the original was active
                if original == active_obj:
                    bpy.context.view_layer.objects.active = proxy
            print("Proxies created, processed, and selection restored for all selected meshes.")
        else:
            print("No selected meshes to process.")

        # Function to add a collision modifier with specific settings to an object
        def add_collision_modifier(obj):
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.modifier_add(type='COLLISION')
            collision = obj.collision
            collision.absorption = 0
            collision.permeability = 0
            collision.stickiness = 0
            collision.use_particle_kill = False
            collision.damping_factor = 0
            collision.damping_random = 0
            collision.friction_factor = 0
            collision.friction_random = 0
            collision.damping = 0.1
            collision.thickness_outer = 0.001
            collision.thickness_inner = 0.001
            collision.cloth_friction = 5
            collision.use_culling = True
            collision.use_normal = False

        # Store the initial selection state
        initial_selection = [obj for obj in bpy.context.selected_objects]
        initial_active = bpy.context.view_layer.objects.active

        # Main script to apply the collision modifier to all selected objects
        for obj in initial_selection:
            if obj.type == 'MESH':
                add_collision_modifier(obj)

        # Restore the initial selection state
        for obj in initial_selection:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = initial_active
        print("Collision modifier applied to all selected meshes, and selection state restored.")

        # Iterate over all selected objects
        for obj in bpy.context.selected_objects:
            # Check if the object is a mesh
            if obj.type == 'MESH':
                # Clear all material slots for this object
                obj.data.materials.clear()

        # Print a message to confirm completion
        print("All materials removed from selected objects.")

        if self.decimate_proxy:
            # Set the decimation ratio as a variable
            decimation_ratio = 0.25  # You can change this value later
            # Enter edit mode
            bpy.ops.object.editmode_toggle()
            # Select all mesh elements
            bpy.ops.mesh.select_all(action='SELECT')
            # Apply the decimate modifier
            bpy.ops.mesh.decimate(ratio=decimation_ratio)
            # Exit edit mode
            bpy.ops.object.editmode_toggle()

        # Add the object to the Physics Panel
        if self.add_to_panel:
            add_item = physics_settings.items.add()
            add_item.object = bpy.context.object
            add_item.type = 'COLLISION'

        self.report({'INFO'}, 'MustardUI - Collision Cage created.')

        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'decimate_proxy', text='Decimate Proxy', icon_value=0, emboss=True)

        layout.separator()
        layout.label(text="UI", icon="MENU_PANEL")
        layout.prop(self, 'add_to_panel', icon_value=0, emboss=True)

    def invoke(self, context, event):
        self.decimate_proxy = True
        return context.window_manager.invoke_props_dialog(self, width=300)


def register():
    bpy.utils.register_class(MustardUI_ToolsCreators_CreateCollisionCage)


def unregister():
    bpy.utils.unregister_class(MustardUI_ToolsCreators_CreateCollisionCage)
