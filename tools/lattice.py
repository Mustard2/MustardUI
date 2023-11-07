import bpy
from bpy.props import *
from ..model_selection.active_object import *


class MustardUI_Tools_LatticeSetup(bpy.types.Operator):
    """Setup/Clean Lattice modifiers for all model Objects.\nThis function will create (or delete) Lattice modifiers
    linked with the Lattice object chosen and put it at the top of the modifiers list.\nWhen cleaning, only MustardUI
    Lattice modifiers are deleted"""
    bl_idname = "mustardui.tools_latticesetup"
    bl_label = "Setup Lattice"
    bl_options = {'REGISTER', 'UNDO'}

    mod: IntProperty(name='MOD',
                     description="MOD",
                     default=0
                     )

    @classmethod
    def poll(cls, context):

        res, arm = mustardui_active_object(context, config=1)

        # Check if the lattice object is defined
        if arm is not None:
            lattice_settings = arm.MustardUI_LatticeSettings
            return lattice_settings.lattice_object is not None

        else:
            return False

    def execute(self, context):

        settings = bpy.context.scene.MustardUI_Settings
        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings
        lattice_settings = arm.MustardUI_LatticeSettings

        arm_obj = context.active_object

        mod_name = lattice_settings.lattice_modifiers_name + "Body Lattice"

        if self.mod == 0:

            latt = lattice_settings.lattice_object

            # Body add
            new_mod = True
            obj = rig_settings.model_body
            for modifier in obj.modifiers:
                if modifier.type == "LATTICE" and modifier.name == mod_name:
                    new_mod = False
            if new_mod and obj.type == "MESH":
                mod = obj.modifiers.new(name=mod_name, type='LATTICE')
                obj.modifiers[mod_name].object = latt
                bpy.context.view_layer.objects.active = obj
                while obj.modifiers.find(mod_name) != 0:
                    bpy.ops.object.modifier_move_up(modifier=mod_name)
                bpy.context.view_layer.objects.active = arm_obj

            # Outfits add
            for collection in [x for x in rig_settings.outfits_collections if x.collection != None]:
                items = collection.collection.all_objects if rig_settings.outfit_config_subcollections else collection.collection.objects
                for obj in items:
                    new_mod = True
                    for modifier in obj.modifiers:
                        if modifier.type == "LATTICE" and modifier.name == mod_name:
                            new_mod = False
                    if new_mod and obj.type == "MESH":
                        mod = obj.modifiers.new(name=mod_name, type='LATTICE')
                        obj.modifiers[mod_name].object = latt
                        bpy.context.view_layer.objects.active = obj
                        while obj.modifiers.find(mod_name) != 0:
                            bpy.ops.object.modifier_move_up(modifier=mod_name)
                        bpy.context.view_layer.objects.active = arm_obj

            self.report({'INFO'}, "MustardUI: Lattice Setup complete")

        else:

            # Remove body modifier
            obj = rig_settings.model_body
            if obj.type == "MESH" and obj.modifiers.get(mod_name) is not None:
                obj.modifiers.remove(obj.modifiers.get(mod_name))

            # Remove objects modifiers
            for collection in [x for x in rig_settings.outfits_collections if x.collection is not None]:
                items = collection.collection.all_objects if rig_settings.outfit_config_subcollections else collection.collection.objects
                for obj in items:
                    if obj.type == "MESH" and obj.modifiers.get(mod_name) is not None:
                        obj.modifiers.remove(obj.modifiers.get(mod_name))

            self.report({'INFO'}, "MustardUI: Lattice Uninstallation complete")

        return {'FINISHED'}


class MustardUI_Tools_LatticeModify(bpy.types.Operator):
    """Create a custom Lattice shape key"""
    bl_idname = "mustardui.tools_lattice"
    bl_label = "Custom Lattice"
    bl_options = {'REGISTER'}

    mod: IntProperty(name='MOD',
                     description="MOD",
                     default=0
                     )

    def execute(self, context):

        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings
        lattice_settings = obj.MustardUI_LatticeSettings

        latt = lattice_settings.lattice_object

        # Store armature object to use it as active object at the end
        for object in bpy.data.objects:
            if object.data == obj:
                arm_obj = object

        shape_key_custom_name = lattice_settings.lattice_modifiers_name + "Custom"

        lattice_settings.lattice_mod_status = False

        if self.mod == 0:

            lattice_settings.lattice_mod_status = True

            new_key = True

            bpy.context.view_layer.objects.active = latt

            for key in latt.data.shape_keys.key_blocks:
                key.value = 0.
                if key.name == shape_key_custom_name:
                    new_key = False
                    break

            if new_key:
                shapeKey = latt.shape_key_add(from_mix=False)
                shapeKey.name = shape_key_custom_name

            lattice_settings.lattice_key_value = 1.
            latt.data.shape_keys.key_blocks[shape_key_custom_name].value = 1.
            index = latt.data.shape_keys.key_blocks.find(shape_key_custom_name)
            latt.active_shape_key_index = index
            latt.hide_viewport = False
            try:
                bpy.ops.object.mode_set(mode='EDIT')
            except:
                bpy.context.view_layer.objects.active = arm_obj
                self.report({'ERROR'},
                            "MustardUI: Be sure that " + lattice_settings.lattice_object.name + " is not temporarily disabled in viewport (eye icon)!")
                lattice_settings.lattice_mod_status = False

        elif self.mod == 1:

            bpy.context.view_layer.objects.active = latt
            bpy.ops.object.mode_set(mode='OBJECT')
            latt.hide_viewport = True
            bpy.context.view_layer.objects.active = arm_obj
            lattice_settings.lattice_mod_status = False

        else:

            bpy.context.view_layer.objects.active = latt
            if bpy.context.view_layer.objects.active == latt:
                index = latt.data.shape_keys.key_blocks.find(shape_key_custom_name)
                latt.active_shape_key_index = index

                bpy.ops.object.shape_key_remove()

                shapeKey = latt.shape_key_add(from_mix=False)
                shapeKey.name = shape_key_custom_name

                self.report({'INFO'}, "MustardUI: Custom shape key reset")
            else:
                self.report({'ERROR'}, "MustardUI: Can not select Lattice Object")

            bpy.context.view_layer.objects.active = arm_obj

        return {'FINISHED'}


class MustardUI_LatticeSettings(bpy.types.PropertyGroup):

    # Poll function for the selection of mesh only in pointer properties
    def poll_lattice(self, object):
        return object.type == 'LATTICE'

    lattice_panel_enable: bpy.props.BoolProperty(default=False,
                                                 name="Lattice",
                                                 description="Enable the Lattice tool.\nThis tool will allow a quick "
                                                             "creation of shapes that affect all outfits")
    lattice_modifiers_name: bpy.props.StringProperty(default="MustardUI - ")

    def lattice_enable_update(self, context):

        for object in bpy.data.objects:
            for modifier in object.modifiers:
                if modifier.type == "LATTICE" and self.lattice_modifiers_name in modifier.name:
                    modifier.show_render = self.lattice_enable
                    modifier.show_viewport = self.lattice_enable
        return

    # Function to create an array of tuples for lattice keys
    def lattice_keys_list(self, context):

        settings = bpy.context.scene.MustardUI_Settings

        latt = self.lattice_object

        items = [("Base", "Base", "Base shape.\nThe body without modifications.")]

        for key in latt.data.shape_keys.key_blocks:
            if hasattr(key, 'name'):
                if self.lattice_modifiers_name in key.name:
                    nname = key.name[len(self.lattice_modifiers_name):]
                    items.append((key.name, nname, key.name))

        return items

    def lattice_shapekey_update(self, context):

        latt = self.lattice_object

        for key in latt.data.shape_keys.key_blocks:
            if "MustardUI" in key.name:
                key.value = 0.

        if self.lattice_keys != "Base":
            self.lattice_key_value = 1.

        return

    def lattice_prop_update(self, context):

        latt = self.lattice_object

        latt.data.interpolation_type_u = self.lattice_interpolation
        latt.data.interpolation_type_v = self.lattice_interpolation
        latt.data.interpolation_type_w = self.lattice_interpolation

        if self.lattice_keys != "Base":
            latt.data.shape_keys.key_blocks[self.lattice_keys].value = self.lattice_key_value

        return

    lattice_object: bpy.props.PointerProperty(name="Lattice Object",
                                              description="The Lattice that will be used for body modifications",
                                              type=bpy.types.Object,
                                              poll=poll_lattice)

    lattice_enable: bpy.props.BoolProperty(default=False,
                                           name="Lattice body modification",
                                           description="Enable lattice body modifications.\nDisable if not used to "
                                                       "increase viewport performance",
                                           update=lattice_enable_update)

    lattice_mod_status: bpy.props.BoolProperty(default=False)

    lattice_keys: bpy.props.EnumProperty(name="",
                                         description="Key selected",
                                         items=lattice_keys_list,
                                         update=lattice_shapekey_update)

    lattice_key_value: bpy.props.FloatProperty(default=0.,
                                               min=0., max=1.,
                                               name="Deformation Intensity",
                                               description="Intensity of lattice deformation",
                                               update=lattice_prop_update)

    lattice_interpolation: bpy.props.EnumProperty(name="",
                                                  description="",
                                                  items=[("KEY_BSPLINE", "BSpline", "BSpline"),
                                                         ("KEY_LINEAR", "Linear", "Linear"),
                                                         ("KEY_CARDINAL", "Cardinal", "Cardinal"),
                                                         ("KEY_CATMULL_ROM", "Catmull-Rom", "Catmull-Rom")],
                                                  update=lattice_prop_update)


def register():
    bpy.utils.register_class(MustardUI_Tools_LatticeSetup)
    bpy.utils.register_class(MustardUI_Tools_LatticeModify)
    bpy.utils.register_class(MustardUI_LatticeSettings)
    bpy.types.Armature.MustardUI_LatticeSettings = bpy.props.PointerProperty(type=MustardUI_LatticeSettings)


def unregister():
    bpy.utils.unregister_class(MustardUI_Tools_LatticeSetup)
    bpy.utils.unregister_class(MustardUI_Tools_LatticeModify)
    bpy.utils.unregister_class(MustardUI_LatticeSettings)
