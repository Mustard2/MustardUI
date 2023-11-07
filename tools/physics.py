import bpy
from bpy.props import *
from ..model_selection.active_object import *


class MustardUI_Tools_Physics_CreateItem(bpy.types.Operator):
    """Create a physics panel using the selected cage object in the UI.\nThis will also create the necessary
    modifiers and clothes settings"""
    bl_idname = "mustardui.tools_physics_createitem"
    bl_label = "Add Physics Item"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):

        res, arm = mustardui_active_object(context, config=1)

        # Check if the lattice object is defined
        if arm is not None:
            physics_settings = arm.MustardUI_PhysicsSettings
            cage_objects = []
            for el in physics_settings.physics_items:
                cage_objects.append(el.cage_object)

            return physics_settings.config_cage_object is not None and physics_settings.config_cage_object_pin_vertex_group != "" and not physics_settings.config_cage_object in cage_objects

        else:
            return False

    def execute(self, context):

        settings = bpy.context.scene.MustardUI_Settings

        res, arm = mustardui_active_object(context, config=1)

        arm_obj = context.active_object

        rig_settings = arm.MustardUI_RigSettings
        physics_settings = arm.MustardUI_PhysicsSettings

        # Show an error if the model body has not been set
        if rig_settings.model_body is None:
            self.report({'ERROR'}, "MustardUI: Can not add the Physics item without a defined Body object")
            return {'FINISHED'}

        # Set the modifier name
        mod_name = physics_settings.physics_modifiers_name + physics_settings.config_cage_object.name + " Cage"

        # Adding the item to the physics items list
        add_item = physics_settings.physics_items.add()
        add_item.cage_object = physics_settings.config_cage_object
        add_item.cage_object_pin_vertex_group = physics_settings.config_cage_object_pin_vertex_group
        add_item.cage_object_bending_stiff_vertex_group = physics_settings.config_cage_object_bending_stiff_vertex_group
        add_item.MustardUI_preset = physics_settings.config_MustardUI_preset

        # Adding modifier to the body
        # Body add
        new_mod = True
        obj = rig_settings.model_body
        for modifier in [x for x in obj.modifiers if x.type == "MESH_DEFORM"]:
            if modifier.object == bpy.data.objects[physics_settings.config_cage_object.name]:
                new_mod = False
        if new_mod and obj.type == "MESH":
            mod = obj.modifiers.new(name=mod_name, type='MESH_DEFORM')
            mod.object = physics_settings.config_cage_object
            mod.use_dynamic_bind = True

            # Move modifier
            arm_mod_id = 0
            for i in range(len(obj.modifiers)):
                if obj.modifiers[i].type == "ARMATURE":
                    arm_mod_id = i
            while obj.modifiers.find(mod_name) > arm_mod_id + 1:
                with context.temp_override(object=obj):
                    bpy.ops.object.modifier_move_up(modifier=mod.name)

            with context.temp_override(object=obj):
                bpy.ops.object.meshdeform_bind(modifier=mod.name)

            mod.show_viewport = physics_settings.physics_enable
            mod.show_render = physics_settings.physics_enable

        # Outfits add
        for collection in [x for x in rig_settings.outfits_collections if x.collection != None]:
            items = collection.collection.all_objects if rig_settings.outfit_config_subcollections else collection.collection.objects
            for obj in items:
                new_mod = True
                for modifier in [x for x in obj.modifiers if x.type == "MESH_DEFORM"]:
                    if modifier.object == bpy.data.objects[physics_settings.config_cage_object.name]:
                        new_mod = False
                if new_mod and obj.type == "MESH":
                    mod = obj.modifiers.new(name=mod_name, type='MESH_DEFORM')
                    mod.object = physics_settings.config_cage_object
                    mod.use_dynamic_bind = True

                    # Move modifier
                    arm_mod_id = 0
                    for i in range(len(obj.modifiers)):
                        if obj.modifiers[i].type == "ARMATURE":
                            arm_mod_id = i
                    while obj.modifiers.find(mod_name) > arm_mod_id + 1:
                        with context.temp_override(object=obj):
                            bpy.ops.object.modifier_move_up(modifier=mod.name)

                    with context.temp_override(object=obj):
                        bpy.ops.object.meshdeform_bind(modifier=mod.name)

                    mod.show_viewport = physics_settings.physics_enable
                    mod.show_render = physics_settings.physics_enable

        # Add cloth modifier to cage and set the settings
        mod_name = physics_settings.physics_modifiers_name + "Cage"

        obj = physics_settings.config_cage_object
        for modifier in obj.modifiers:
            if modifier.type == "CLOTH":
                obj.modifiers.remove(obj.modifiers.get(modifier.name))

        mod = obj.modifiers.new(name=mod_name, type='CLOTH')

        # Quality Steps
        mod.settings.quality = 7
        mod.settings.time_scale = .95
        # Bending model
        mod.settings.bending_model = "ANGULAR"
        # Pin group
        mod.settings.vertex_group_mass = physics_settings.config_cage_object_pin_vertex_group

        # Physics settings
        mod.settings.tension_stiffness = 1.
        mod.settings.compression_stiffness = 0.1
        mod.settings.shear_stiffness = 0.02
        mod.settings.bending_stiffness = 0.02

        mod.settings.tension_damping = 1.
        mod.settings.compression_damping = 0.1
        mod.settings.shear_damping = 0.02
        mod.settings.bending_damping = 0.02

        # Vertex groups
        mod.settings.vertex_group_structural_stiffness = physics_settings.config_cage_object_pin_vertex_group
        mod.settings.vertex_group_shear_stiffness = physics_settings.config_cage_object_pin_vertex_group
        if physics_settings.config_cage_object_bending_stiff_vertex_group != "":
            mod.settings.vertex_group_bending = physics_settings.config_cage_object_bending_stiff_vertex_group
        mod.settings.bending_stiffness_max = 1.

        # Internal springs
        mod.settings.use_internal_springs = True
        mod.settings.internal_spring_max_diversion = 45 / 180 * 3.14  # conversion to radians
        mod.settings.internal_spring_normal_check = True
        mod.settings.internal_tension_stiffness = .1
        mod.settings.internal_compression_stiffness = .1
        mod.settings.internal_tension_stiffness_max = .3
        mod.settings.internal_compression_stiffness_max = .3

        # Pressure
        mod.settings.use_pressure = True
        mod.settings.uniform_pressure_force = .06
        mod.settings.pressure_factor = 1.

        # Gravity factor
        mod.settings.effector_weights.gravity = 0.

        # Collisions
        mod.collision_settings.collision_quality = 5
        mod.collision_settings.use_collision = False

        while obj.modifiers.find(mod.name) > 0:
            with context.temp_override(object=obj):
                bpy.ops.object.modifier_move_up(modifier=mod.name)

        mod.show_viewport = physics_settings.physics_enable
        mod.show_render = physics_settings.physics_enable

        physics_settings.config_cage_object = None
        physics_settings.config_cage_object_pin_vertex_group = ""
        physics_settings.config_cage_object_bending_stiff_vertex_group = ""

        self.report({'INFO'}, "MustardUI: Physics Item added")

        return {'FINISHED'}


class MustardUI_Tools_Physics_DeleteItem(bpy.types.Operator):
    """Delete a physics panel using the selected cage object in the UI"""
    bl_idname = "mustardui.tools_physics_deleteitem"
    bl_label = "Delete Physics Item"
    bl_options = {'REGISTER', 'UNDO'}

    cage_object_name: StringProperty()

    def execute(self, context):

        settings = bpy.context.scene.MustardUI_Settings

        res, arm = mustardui_active_object(context, config=1)

        arm_obj = context.active_object

        rig_settings = arm.MustardUI_RigSettings
        physics_settings = arm.MustardUI_PhysicsSettings

        if self.cage_object_name == "":

            item_ID = 0
            for item in physics_settings.physics_items:
                if item.cage_object is None:
                    physics_settings.physics_items.remove(item_ID)
                item_ID = item_ID + 1

            self.report({'WARNING'},
                        "MustardUI: Physics Item list cleaned from un-referenced cages. The modifiers could not be "
                        "cleaned.")

            return {'FINISHED'}

        # Remove modifiers from the body
        obj = rig_settings.model_body
        for modifier in [x for x in obj.modifiers if x.type == "MESH_DEFORM"]:
            if modifier.object == bpy.data.objects[self.cage_object_name]:
                obj.modifiers.remove(obj.modifiers.get(modifier.name))

        # Remove objects modifiers
        for collection in [x for x in rig_settings.outfits_collections if x.collection != None]:
            items = collection.collection.all_objects if rig_settings.outfit_config_subcollections else collection.collection.objects
            for obj in items:
                for modifier in [x for x in obj.modifiers if x.type == "MESH_DEFORM"]:
                    if modifier.object == bpy.data.objects[self.cage_object_name]:
                        obj.modifiers.remove(obj.modifiers.get(modifier.name))

        # Remove cloth modifier from the cage
        obj = bpy.data.objects[self.cage_object_name]
        if obj is not None:
            for modifier in obj.modifiers:
                if modifier.type == "CLOTH":
                    obj.modifiers.remove(obj.modifiers.get(modifier.name))

        remove_ID = 0
        for el in physics_settings.physics_items:
            if el.cage_object.name == self.cage_object_name:
                break
            remove_ID = remove_ID + 1

        physics_settings.physics_items.remove(remove_ID)

        self.report({'INFO'}, "MustardUI: Physics Item deleted")

        return {'FINISHED'}


class MustardUI_Tools_Physics_Clean(bpy.types.Operator):
    """Remove all the physics items"""
    bl_idname = "mustardui.tools_physics_clean"
    bl_label = "Clear Physics Items"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):

        res, arm = mustardui_active_object(context, config=1)

        # Check if the lattice object is defined
        if arm is not None:
            physics_settings = arm.MustardUI_PhysicsSettings
            return len(physics_settings.physics_items) > 0

        else:
            return False

    def execute(self, context):

        settings = bpy.context.scene.MustardUI_Settings

        res, arm = mustardui_active_object(context, config=1)

        arm_obj = context.active_object

        rig_settings = arm.MustardUI_RigSettings
        physics_settings = arm.MustardUI_PhysicsSettings

        for cage in [x.cage_object for x in physics_settings.physics_items]:

            # Remove modifiers from the body
            obj = rig_settings.model_body
            for modifier in [x for x in obj.modifiers if x.type == "MESH_DEFORM"]:
                if modifier.object == cage:
                    obj.modifiers.remove(obj.modifiers.get(modifier.name))

            # Remove objects modifiers
            for collection in [x for x in rig_settings.outfits_collections if x.collection != None]:
                items = collection.collection.all_objects if rig_settings.outfit_config_subcollections else collection.collection.objects
                for obj in items:
                    for modifier in [x for x in obj.modifiers if x.type == "MESH_DEFORM"]:
                        if modifier.object == cage:
                            obj.modifiers.remove(obj.modifiers.get(modifier.name))

            # Remove cloth modifier from the cage
            obj = cage
            if obj != None:
                for modifier in obj.modifiers:
                    if modifier.type == "CLOTH":
                        obj.modifiers.remove(obj.modifiers.get(modifier.name))

        physics_settings.physics_items.clear()

        self.report({'INFO'}, "MustardUI: Physics Items removed")

        return {'FINISHED'}


class MustardUI_Tools_Physics_ReBind(bpy.types.Operator):
    """Re-bind mesh deform cages to the Body mesh.\nUse this tool if the mesh is deformed after the cage has been
    modified"""
    bl_idname = "mustardui.tools_physics_rebind"
    bl_label = "Re-bind Cages"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        return arm is not None

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=0)

        rig_settings = arm.MustardUI_RigSettings
        physics_settings = arm.MustardUI_PhysicsSettings

        for cage in [x for x in physics_settings.physics_items]:

            for collection in [x for x in rig_settings.outfits_collections if x.collection is not None]:
                items = collection.collection.all_objects if rig_settings.outfit_config_subcollections else collection.collection.objects
                for obj in items:
                    for modifier in obj.modifiers:
                        if modifier.type == 'MESH_DEFORM':
                            if cage.cage_object == modifier.object:
                                with context.temp_override(object=obj):
                                    bpy.ops.object.meshdeform_bind(modifier=modifier.name)
                                if not modifier.is_bound:
                                    with context.temp_override(object=obj):
                                        bpy.ops.object.meshdeform_bind(modifier=modifier.name)

            obj = rig_settings.model_body
            for modifier in rig_settings.model_body.modifiers:
                if modifier.type == 'MESH_DEFORM':
                    if cage.cage_object == modifier.object:
                        with context.temp_override(object=obj):
                            bpy.ops.object.meshdeform_bind(modifier=modifier.name)
                        if not modifier.is_bound:
                            with context.temp_override(object=obj):
                                bpy.ops.object.meshdeform_bind(modifier=modifier.name)

        return {'FINISHED'}


class MustardUI_Tools_Physics_SimulateObject(bpy.types.Operator):
    """Bake the physics for the selected object only"""
    bl_idname = "mustardui.tools_physics_simulateobject"
    bl_label = "Bake Item Physics"
    bl_options = {'REGISTER'}

    cage_object_name: StringProperty()

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=0)

        if arm is None:
            self.report({'ERROR'}, "MustardUI: Uncorrect selected object")
            return {'FINISHED'}

        physics_settings = arm.MustardUI_PhysicsSettings

        try:
            cage = bpy.data.objects[self.cage_object_name]
            for modifier in cage.modifiers:
                if modifier.type == "CLOTH":
                    cage_cache = modifier.point_cache

            override = {'active_object': cage, 'point_cache': cage_cache}
            if not cage_cache.is_baked:
                bpy.ops.ptcache.bake(override, bake=True)
            else:
                bpy.ops.ptcache.free_bake(override)

            self.report({'INFO'}, "MustardUI: Bake procedure complete")
        except:
            self.report({'ERROR'}, "MustardUI: An error occurred while baking physics")

        return {'FINISHED'}


# Function for global and single physics item visbility
def mustardui_physics_enable_update(self, context):
    res, arm = mustardui_active_object(context, config=1)

    if arm == None:
        return

    rig_settings = arm.MustardUI_RigSettings
    physics_settings = arm.MustardUI_PhysicsSettings

    for cage in [x for x in physics_settings.physics_items]:

        for modifier in cage.cage_object.modifiers:
            if modifier.type == 'CLOTH':
                modifier.show_viewport = physics_settings.physics_enable and cage.physics_enable
                modifier.show_render = physics_settings.physics_enable and cage.physics_enable

        for collection in [x for x in rig_settings.outfits_collections if x.collection != None]:
            items = collection.collection.all_objects if rig_settings.outfit_config_subcollections else collection.collection.objects
            for obj in items:
                for modifier in obj.modifiers:
                    if modifier.type == 'MESH_DEFORM':
                        if cage.cage_object == modifier.object:
                            modifier.show_viewport = physics_settings.physics_enable and cage.physics_enable
                            modifier.show_render = physics_settings.physics_enable and cage.physics_enable

        for modifier in rig_settings.model_body.modifiers:
            if modifier.type == 'MESH_DEFORM':
                if cage.cage_object == modifier.object:
                    modifier.show_viewport = physics_settings.physics_enable and cage.physics_enable
                    modifier.show_render = physics_settings.physics_enable and cage.physics_enable

    return


# Physics item informations
# Class to store physics item informations
class MustardUI_PhysicsItem(bpy.types.PropertyGroup):
    # Property for collapsing rig properties section
    config_collapse: bpy.props.BoolProperty(default=True,
                                            name="")

    # Body object
    # Poll function for the selection of mesh only in pointer properties
    def poll_mesh(self, object):

        res, obj = mustardui_active_object(context, config=1)
        physics_settings = obj.MustardUI_PhysicsSettings

        cage_objects = []
        for el in physics_settings:
            cage_objects.append(el.cage_object)

        return object.type == 'MESH' and not object in cage_objects

    cage_object: bpy.props.PointerProperty(type=bpy.types.Object,
                                           poll=poll_mesh,
                                           name="Cage",
                                           description="Select the object to use as a cage")

    cage_object_pin_vertex_group: bpy.props.StringProperty(name="Pin Vertex Group")
    cage_object_bending_stiff_vertex_group: bpy.props.StringProperty(name="Bending Stiffness Vertex Group")

    MustardUI_preset: bpy.props.BoolProperty(default=True,
                                             name="Compact Definitions",
                                             description="Enable compact definitions of physical settings.\nEnable this to substitute tension, compression, shear and bending with more 'human readable' settings")

    physics_enable: bpy.props.BoolProperty(default=True,
                                           name="Enable Physics",
                                           description="Enable Physics simulation for this item",
                                           update=mustardui_physics_enable_update)

    # Physics settings

    def physics_settings_update(self, context):

        res, arm = mustardui_active_object(context, config=0)

        if arm == None:
            return

        physics_settings = arm.MustardUI_PhysicsSettings

        mod = None
        for modifier in self.cage_object.modifiers:
            if modifier.type == "CLOTH":
                mod = modifier
        if mod == None:
            print("MustardUI - Error in finding the \'CLOTH\' modifier.")
            return

        # Inertia effect
        mod.settings.mass = 0.3 * self.inertia ** .5

        # Stiffness effect
        mod.settings.uniform_pressure_force = .06 * self.stiffness ** 1.6
        mod.settings.compression_damping = 0.1 * self.stiffness ** .2
        mod.settings.compression_stiffness = .1 * self.stiffness ** .2
        mod.settings.bending_stiffness_max = 1. * self.stiffness ** 1.

        # Bounciness effect
        mod.settings.internal_compression_stiffness = 0.1 / self.bounciness
        mod.settings.internal_compression_stiffness_max = mod.settings.internal_compression_stiffness * 3.

        return

    bounciness: bpy.props.FloatProperty(default=1.,
                                        min=0.01,
                                        name="Bounciness",
                                        update=physics_settings_update)
    stiffness: bpy.props.FloatProperty(default=1.,
                                       min=0.01,
                                       name="Stiffness",
                                       update=physics_settings_update)
    inertia: bpy.props.FloatProperty(default=1.,
                                     min=0.01,
                                     name="Inertia",
                                     update=physics_settings_update)


class MustardUI_PhysicsSettings(bpy.types.PropertyGroup):
    # Property for collapsing rig properties section
    config_collapse: bpy.props.BoolProperty(default=True,
                                            name="")

    # Modifiers name convention
    physics_modifiers_name: bpy.props.StringProperty(default="MustardUI ")

    physics_enable: bpy.props.BoolProperty(default=False,
                                           name="Enable Physics",
                                           description="Enable/disable physics simulation.\nThis can greatly affect the performance in viewport, therefore enable it only for renderings or checks.\nNote that the baked physics will be deleted if you disable physics",
                                           update=mustardui_physics_enable_update)

    # Body object
    # Poll function for the selection of mesh only in pointer properties
    def poll_mesh(self, object):

        cage_objects = []
        for el in self.physics_items:
            cage_objects.append(el.cage_object)

        return object.type == 'MESH' and not object in cage_objects

    config_cage_object: bpy.props.PointerProperty(type=bpy.types.Object,
                                                  poll=poll_mesh,
                                                  name="Cage",
                                                  description="Select the object to use as a cage")

    config_cage_object_pin_vertex_group: bpy.props.StringProperty(name="Pin Vertex Group")
    config_cage_object_bending_stiff_vertex_group: bpy.props.StringProperty(name="Bending Stiffness Vertex Group")

    config_MustardUI_preset: bpy.props.BoolProperty(default=True,
                                                    name="Compact Definitions",
                                                    description="Enable compact definitions of physical settings.\nEnable this to substitute tension, compression, shear and bending with more 'human readable' settings")

    # Function to create an array of tuples for Outfit enum collections
    def physics_items_list_make(self, context):

        res, arm = mustardui_active_object(context, config=1)

        if arm == None:
            return

        rig_settings = arm.MustardUI_RigSettings
        naming_conv = rig_settings.model_MustardUI_naming_convention

        items = []

        for cage in self.physics_items:
            if cage.cage_object != None:
                if naming_conv:
                    nname = cage.cage_object.name[len(rig_settings.model_name + ' Physics - '):]
                else:
                    nname = cage.cage_object.name
                items.append((cage.cage_object.name, nname, cage.cage_object.name))

        items = sorted(items)

        return items

    def simulation_update(self, context):

        mod_name = self.physics_modifiers_name + "Cage"

        for cage in [x.cage_object for x in self.physics_items if x.cage_object != None]:
            mod = None
            for modifier in cage.modifiers:
                if modifier.type == "CLOTH":
                    mod = modifier

                if mod == None:
                    print("MustardUI - Error in finding the \'CLOTH\' modifier: " + mod_name)
                    return

                mod.settings.quality = self.simulation_quality
                mod.collision_settings.collision_quality = self.simulation_quality_collision

                mod.point_cache.frame_start = self.simulation_start
                mod.point_cache.frame_end = self.simulation_end

        for object in bpy.data.objects:

            for modifier in object.modifiers:

                if modifier.type == "CLOTH":
                    mod = modifier

                    mod.settings.quality = self.simulation_quality
                    mod.collision_settings.collision_quality = self.simulation_quality_collision

                    mod.point_cache.frame_start = self.simulation_start
                    mod.point_cache.frame_end = self.simulation_end

        return

    physics_items: bpy.props.CollectionProperty(type=MustardUI_PhysicsItem)

    physics_items_list: bpy.props.EnumProperty(name="Physics Items",
                                               items=physics_items_list_make)

    # Simulation properties
    simulation_start: bpy.props.IntProperty(default=1,
                                            name="Simulation Start",
                                            description="Frame on which the simulation starts",
                                            update=simulation_update)

    simulation_end: bpy.props.IntProperty(default=250,
                                          name="Simulation End",
                                          description="Frame on which the simulation stops",
                                          update=simulation_update)

    simulation_quality: bpy.props.IntProperty(default=5,
                                              name="Quality",
                                              description="Quality of the simulation in steps per frame (higher is better quality but slower)",
                                              update=simulation_update)

    simulation_quality_collision: bpy.props.IntProperty(default=2,
                                                        name="Collision Quality",
                                                        update=simulation_update)


def register():
    bpy.utils.register_class(MustardUI_Tools_Physics_CreateItem)
    bpy.utils.register_class(MustardUI_Tools_Physics_SimulateObject)
    bpy.utils.register_class(MustardUI_Tools_Physics_Clean)
    bpy.utils.register_class(MustardUI_Tools_Physics_ReBind)
    bpy.utils.register_class(MustardUI_Tools_Physics_DeleteItem)
    bpy.utils.register_class(MustardUI_PhysicsItem)
    bpy.utils.register_class(MustardUI_PhysicsSettings)
    bpy.types.Armature.MustardUI_PhysicsSettings = bpy.props.PointerProperty(type=MustardUI_PhysicsSettings)


def unregister():
    bpy.utils.unregister_class(MustardUI_Tools_Physics_CreateItem)
    bpy.utils.unregister_class(MustardUI_Tools_Physics_SimulateObject)
    bpy.utils.unregister_class(MustardUI_Tools_Physics_Clean)
    bpy.utils.unregister_class(MustardUI_Tools_Physics_ReBind)
    bpy.utils.unregister_class(MustardUI_Tools_Physics_DeleteItem)
    bpy.utils.unregister_class(MustardUI_PhysicsItem)
    bpy.utils.unregister_class(MustardUI_PhysicsSettings)
