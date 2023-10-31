import bpy
from bpy.props import *
from rna_prop_ui import rna_idprop_ui_create
from ..model_selection.active_object import *
from .misc import *


class MustardUI_Property_MenuAdd(bpy.types.Operator):
    """Add the property to the menu"""
    bl_idname = "mustardui.property_menuadd"
    bl_label = "Add to MustardUI (Un-sorted)"
    bl_options = {'UNDO'}

    section: StringProperty(default="")
    outfit: StringProperty(default="")
    outfit_piece: StringProperty(default="")
    hair: StringProperty(default="")

    @classmethod
    def poll(cls, context):

        res, arm = mustardui_active_object(context, config=1)
        return res

    def execute(self, context):

        res, obj = mustardui_active_object(context, config=1)
        if self.outfit != "":
            custom_props = obj.MustardUI_CustomPropertiesOutfit
        elif self.hair != "":
            custom_props = obj.MustardUI_CustomPropertiesHair
        else:
            custom_props = obj.MustardUI_CustomProperties

        if not hasattr(context, 'button_prop'):
            self.report({'ERROR'}, 'MustardUI - Can not create custom property from this property.')
            return {'FINISHED'}

        prop = context.button_prop

        # dump(prop, 'button_prop')

        # Copy the path of the selected property
        try:
            bpy.ops.ui.copy_data_path_button(full_path=True)
        except:
            self.report({'ERROR'}, 'MustardUI - Invalid selection.')
            return {'FINISHED'}

        # Adjust the property path to be exported
        clipboard = context.window_manager.clipboard
        blender_custom_property = '][' in clipboard
        if not blender_custom_property:
            rna, path = clipboard.rsplit('.', 1)
        else:
            path = clipboard
            rna = ""

        if blender_custom_property:
            path, rem = path.rsplit('[', 1)
            rna = path
            path = '[' + rem
        elif '[' in path:
            path, rem = path.rsplit('[', 1)

        # Check if the property was already added
        if not mustardui_check_cp(obj, rna, path):
            self.report({'ERROR'}, 'MustardUI - This property was already added.')
            return {'FINISHED'}

        # Try to find a better name than default_value for material nodes
        if "node_tree.nodes" in rna:
            rna_node = rna.rsplit(".", 1)

            # Check for .type existance
            try:
                if eval(rna_node[0] + ".type") in ["VALUE", "RGB"]:
                    prop_name_ui = eval(rna_node[0] + ".name")
                else:
                    prop_name_ui = eval(rna + ".name")
            except:
                prop_name_ui = prop.name

        # Try to find a better name than default_value for shape keys
        elif "shape_keys" in rna and "key_block" in rna:
            prop_name_ui = eval(rna + ".name")
        else:
            prop_name_ui = prop.name

        # Add custom property to the object
        prop_name = prop_name_ui
        if prop.is_animatable or blender_custom_property:

            add_string_num = 1
            while prop_name in obj.keys():
                add_string_num += 1
                prop_name = prop_name_ui + ' ' + str(add_string_num)

            if prop.type == "ENUM":
                pass

            # Change custom properties settings
            elif prop.type == "BOOLEAN" and prop.array_length < 1:
                rna_idprop_ui_create(obj, prop_name, default=eval(mustardui_cp_path(rna, path)),
                                     description=prop.description,
                                     overridable=True)

            elif (hasattr(prop, 'hard_min') and hasattr(prop, 'hard_max') and hasattr(prop, 'default')
                  and hasattr(prop, 'description') and hasattr(prop, 'subtype')):
                description = prop.description if (not "node_tree.nodes" in rna and not "shape_keys" in rna) else ""
                rna_idprop_ui_create(obj, prop_name, default=eval(mustardui_cp_path(rna, path)),
                                     min=prop.hard_min if prop.subtype != "COLOR" else 0.,
                                     max=prop.hard_max if prop.subtype != "COLOR" else 1.,
                                     description=description,
                                     overridable=True,
                                     subtype=prop.subtype if prop.subtype != "FACTOR" else None)
            elif hasattr(prop, 'description'):
                rna_idprop_ui_create(obj, prop_name, default=eval(mustardui_cp_path(rna, path)),
                                     description=prop.description)

        # Add driver
        force_non_animatable = False
        try:
            if (prop.is_animatable or blender_custom_property) and not prop.type == "ENUM":
                mustardui_add_driver(obj, rna, path, prop, prop_name)
            else:
                force_non_animatable = True
        except:
            force_non_animatable = True

        # Add property to the collection of properties
        if not (rna, path) in [(x.rna, x.path) for x in custom_props]:

            cp = custom_props.add()
            cp.rna = rna
            cp.path = path
            cp.name = prop_name_ui
            cp.prop_name = prop_name
            cp.type = prop.type
            if hasattr(prop, 'array_length'):
                cp.array_length = prop.array_length
            cp.subtype = prop.subtype

            # Try to find icon
            if "materials" in rna:
                cp.icon = "MATERIAL"
            elif "key_blocks" in rna:
                cp.icon = "SHAPEKEY_DATA"

            cp.is_animatable = (prop.is_animatable if not force_non_animatable else False) or blender_custom_property

            cp.section = self.section

            # Assign type
            if self.outfit != "":
                cp.cp_type = "OUTFIT"
            elif self.hair != "":
                cp.cp_type = "HAIR"
            else:
                cp.cp_type = "BODY"

            # Outfit and hair properties
            if self.outfit != "":
                cp.outfit = bpy.data.collections[self.outfit]
                if self.outfit_piece != "":
                    cp.outfit_piece = bpy.data.objects[self.outfit_piece]
            elif self.hair != "":
                cp.hair = bpy.data.objects[self.hair]

            if cp.is_animatable:

                ui_data_dict = obj.id_properties_ui(prop_name).as_dict()

                if hasattr(prop, 'description'):
                    cp.description = ui_data_dict['description']
                if hasattr(prop, 'default'):
                    if prop.array_length == 0:
                        if prop.type == "FLOAT":
                            cp.default_float = prop.default
                        elif prop.type == "INT" or prop.type == "BOOLEAN":
                            cp.default_int = prop.default
                    else:
                        cp.default_array = str(ui_data_dict['default'])

                if hasattr(prop, 'hard_min') and prop.type != "BOOLEAN":
                    if prop.type == "FLOAT":
                        cp.min_float = prop.hard_min
                    elif prop.type == "INT":
                        cp.min_int = prop.hard_min
                if hasattr(prop, 'hard_max') and prop.type != "BOOLEAN":
                    if prop.type == "FLOAT":
                        cp.max_float = prop.hard_max
                    elif prop.type == "INT":
                        cp.max_int = prop.hard_max
        else:
            self.report({'ERROR'},
                        'MustardUI - An error occurred while adding the property to the custom properties list.')
            return {'FINISHED'}

        # Update the drivers
        obj.update_tag()

        self.report({'INFO'}, 'MustardUI - Property added.')

        return {'FINISHED'}


class MustardUI_Property_Remove(bpy.types.Operator):
    """Remove the selected property from the list.\nType"""
    bl_idname = "mustardui.property_remove"
    bl_label = "Remove Property"
    bl_options = {'UNDO'}

    type: bpy.props.EnumProperty(default="BODY",
                                 items=(
                                     ("BODY", "Body", ""),
                                     ("OUTFIT", "Outfit", ""),
                                     ("HAIR", "Hair", ""))
                                 )

    @classmethod
    def poll(cls, context):
        res, obj = mustardui_active_object(context, config=1)
        return obj != None

    def execute(self, context):
        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config=1)
        uilist, index = mustardui_choose_cp(obj, self.type, context.scene)

        if len(uilist) <= index:
            return {'FINISHED'}

        # Remove custom property and driver
        mustardui_clean_prop(obj, uilist, index, settings)

        uilist.remove(index)
        index = min(max(0, index - 1), len(uilist) - 1)
        mustardui_update_index_cp(self.type, context.scene, index)

        obj.update_tag()

        return {'FINISHED'}


class MustardUI_Property_Switch(bpy.types.Operator):
    """Move the selected property in the list.\nType"""

    bl_idname = "mustardui.property_switch"
    bl_label = "Move property"

    type: bpy.props.EnumProperty(default="BODY",
                                 items=(
                                     ("BODY", "Body", ""),
                                     ("OUTFIT", "Outfit", ""),
                                     ("HAIR", "Hair", ""))
                                 )
    direction: bpy.props.EnumProperty(items=(('UP', 'Up', ""),
                                             ('DOWN', 'Down', ""),))

    @classmethod
    def poll(cls, context):
        res, obj = mustardui_active_object(context, config=1)
        return obj is not None

    def move_index(self, uilist, index):
        """ Move index of an item render queue while clamping it. """

        list_length = len(uilist) - 1  # (index starts at 0)
        new_index = index + (-1 if self.direction == 'UP' else 1)

        return max(0, min(new_index, list_length))

    def execute(self, context):
        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config=1)
        uilist, index = mustardui_choose_cp(obj, self.type, context.scene)

        if len(uilist) <= index:
            return {'FINISHED'}

        neighbour = index + (-1 if self.direction == 'UP' else 1)
        uilist.move(neighbour, index)
        index = self.move_index(uilist, index)
        mustardui_update_index_cp(self.type, context.scene, index)

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_Property_MenuAdd)
    bpy.utils.register_class(MustardUI_Property_Remove)
    bpy.utils.register_class(MustardUI_Property_Switch)


def unregister():
    bpy.utils.unregister_class(MustardUI_Property_MenuAdd)
    bpy.utils.unregister_class(MustardUI_Property_Remove)
    bpy.utils.unregister_class(MustardUI_Property_Switch)
