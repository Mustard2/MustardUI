import bpy
from bpy.props import *
from rna_prop_ui import rna_idprop_ui_create
from ..misc.icons_list import mustardui_icon_list
from ..model_selection.active_object import *
from .misc import *
from ..misc.prop_utils import *
from .. import __package__ as base_package


class MustardUI_Property_Settings(bpy.types.Operator):
    """Modify the property settings"""
    bl_idname = "mustardui.property_settings"
    bl_label = "Property Settings"
    bl_icon = "PREFERENCES"
    bl_options = {'UNDO'}

    name: bpy.props.StringProperty(name='Name',
                                   description="Name of the property")
    icon: bpy.props.EnumProperty(name='Icon',
                                 description="Icon of the property",
                                 items=mustardui_icon_list)
    description: bpy.props.StringProperty(name='Description',
                                          description="Description of the property")
    force_type: bpy.props.EnumProperty(name="Force Property Type",
                                       default="None",
                                       description="Force the type of the property to be boolean or integer. If None, "
                                                   "the original type is preserved",
                                       items=(
                                           ("None", "None", "None"),
                                           ("Int", "Int", "Int"),
                                           ("Bool", "Bool", "Bool"))
                                       )
    type: bpy.props.EnumProperty(default="BODY",
                                 items=(("BODY", "Body", ""),
                                        ("OUTFIT", "Outfit", ""),
                                        ("HAIR", "Hair", ""))
                                 )

    max_int: bpy.props.IntProperty(name="Maximum value")
    min_int: bpy.props.IntProperty(name="Minimum value")
    max_float: bpy.props.FloatProperty(name="Maximum value")
    min_float: bpy.props.FloatProperty(name="Minimum value")
    default_int: bpy.props.IntProperty(name="Default value")
    default_bool: bpy.props.BoolProperty(name="Default value")
    default_float: bpy.props.FloatProperty(name="Default value")
    default_array: bpy.props.StringProperty(name="Default array value")

    default_color: bpy.props.FloatVectorProperty(name="Default color value",
                                                 size=4,
                                                 subtype="COLOR",
                                                 min=0., max=1.,
                                                 default=[0., 0., 0., 1.])

    # UI Buttons
    change_rna: bpy.props.BoolProperty(name='Change Path',
                                       default=False,
                                       description="Change path values.\nCareless change of values in this section "
                                                   "might break the custom property.\nChange the values only if you "
                                                   "know what you are doing!")
    change_rna_linked: bpy.props.BoolProperty(name='Change Path',
                                              default=False,
                                              description="Change path values.\nCareless change of values in this "
                                                          "section might break the custom property.\nChange the "
                                                          "values only if you know what you are doing!")

    @classmethod
    def poll(cls, context):
        res, obj = mustardui_active_object(context, config=1)
        return obj is not None

    def execute(self, context):

        res, obj = mustardui_active_object(context, config=1)
        custom_props, index = mustardui_choose_cp(obj, self.type, context.scene)
        custom_prop = custom_props[index]
        addon_prefs = context.preferences.addons[base_package].preferences

        if self.name == "":
            self.report({'ERROR'}, 'MustardUI - Can not rename a property with an empty name.')
            return {'FINISHED'}

        prop_type = custom_prop.type
        if prop_type == "FLOAT" and (
                isinstance(self.max_float, int) or isinstance(self.min_float, int) or isinstance(self.default_float,
                                                                                                 int)):
            self.report({'ERROR'}, 'MustardUI - Can not change type of the custom property.')
            return {'FINISHED'}

        if custom_prop.array_length > 0 and custom_prop.subtype != "COLOR":
            try:
                ast.literal_eval(self.default_array)
            except:
                self.report({'ERROR'}, 'MustardUI - Can not use this default vector.')
                return {'FINISHED'}
            if len(ast.literal_eval(self.default_array)) != custom_prop.array_length:
                self.report({'ERROR'}, 'MustardUI - Can not change default with different vector dimension.')
                return {'FINISHED'}

        custom_prop.name = self.name
        custom_prop.icon = self.icon

        if custom_prop.is_animatable:

            prop_name = custom_prop.prop_name
            prop_array = custom_prop.array_length > 0
            prop_subtype = custom_prop.subtype

            ui_data = obj.id_properties_ui(prop_name)
            ui_data_dict = ui_data.as_dict()

            if prop_type == "FLOAT":
                custom_prop.force_type = self.force_type

            if prop_type == "FLOAT" and self.force_type == "None":

                ui_data.clear()

                rna_idprop_ui_create(obj, prop_name,
                                     default=self.default_float if custom_prop.array_length == 0 else ast.literal_eval(
                                         self.default_array) if prop_subtype != "COLOR" else self.default_color,
                                     min=self.min_float if prop_subtype != "COLOR" else 0.,
                                     max=self.max_float if prop_subtype != "COLOR" else 1.,
                                     description=self.description,
                                     overridable=True,
                                     subtype=custom_prop.subtype if prop_subtype != "FACTOR" else None)

                custom_prop.description = self.description
                custom_prop.min_float = self.min_float
                custom_prop.max_float = self.max_float
                if custom_prop.array_length == 0:
                    custom_prop.default_float = self.default_float
                    obj[prop_name] = float(obj[prop_name])
                else:
                    custom_prop.default_array = self.default_array if prop_subtype != "COLOR" else str(
                        ui_data.as_dict()['default'])
            elif prop_type == "BOOLEAN" or self.force_type == "Bool":

                ui_data.clear()

                rna_idprop_ui_create(obj, prop_name,
                                     default=self.default_bool if custom_prop.array_length == 0 else ast.literal_eval(
                                         self.default_array),
                                     description=self.description,
                                     overridable=True)

                custom_prop.description = self.description
                if custom_prop.array_length == 0:
                    custom_prop.default_bool = self.default_bool
                else:
                    custom_prop.default_array = self.default_array

            elif prop_type == "INT" or self.force_type == "Int":

                ui_data.clear()

                rna_idprop_ui_create(obj, prop_name,
                                     default=self.default_int if custom_prop.array_length == 0 else ast.literal_eval(
                                         self.default_array),
                                     min=self.min_int,
                                     max=self.max_int,
                                     description=self.description,
                                     overridable=True,
                                     subtype=custom_prop.subtype if prop_subtype != "FACTOR" else None)

                custom_prop.description = self.description
                custom_prop.min_int = self.min_int
                custom_prop.max_int = self.max_int
                if custom_prop.array_length == 0:
                    custom_prop.default_int = self.default_int
                    obj[prop_name] = int(obj[prop_name])
                else:
                    custom_prop.default_array = self.default_array
            else:
                ui_data.update(description=custom_prop.description)
                custom_prop.description = self.description

        obj.update_tag()

        return {'FINISHED'}

    def invoke(self, context, event):

        res, obj = mustardui_active_object(context, config=1)
        custom_props, index = mustardui_choose_cp(obj, self.type, context.scene)
        addon_prefs = context.preferences.addons[base_package].preferences

        if len(custom_props) <= index:
            return {'FINISHED'}

        custom_prop = custom_props[index]

        self.name = custom_prop.name
        self.icon = custom_prop.icon
        self.description = custom_prop.description
        self.default_array = "[]"

        self.change_rna = False
        self.change_rna_linked = False

        if custom_prop.is_animatable:

            prop_type = custom_prop.type
            self.force_type = custom_prop.force_type

            try:
                ui_data = obj.id_properties_ui(custom_prop.prop_name)
                ui_data_dict = ui_data.as_dict()
            except:
                self.report({'ERROR'},
                            'MustardUI - An error occurred while retrieving UI data. Try to rebuild properties to '
                            'solve this')
                return {'FINISHED'}

            if prop_type == "INT" or self.force_type == "Int":
                self.max_int = ui_data_dict['max']
                self.min_int = ui_data_dict['min']
                if custom_prop.array_length == 0:
                    self.default_int = ui_data_dict['default']
                else:
                    self.default_array = str(ui_data_dict['default'])

            if prop_type == "BOOLEAN" or self.force_type == "Bool":

                if custom_prop.array_length == 0:
                    self.default_bool = ui_data_dict['default']
                else:
                    self.default_array = str(ui_data_dict['default'])

            elif prop_type == "FLOAT" and self.force_type == "None":
                self.max_float = ui_data_dict['max']
                self.min_float = ui_data_dict['min']
                if self.min_float == self.max_float:
                    self.max_float += 1
                if custom_prop.array_length > 0:
                    if custom_prop.subtype != "COLOR":
                        self.default_array = str(ui_data_dict['default'])
                    else:
                        self.default_color = ui_data_dict['default']
                else:
                    self.default_float = ui_data_dict['default']

        return context.window_manager.invoke_props_dialog(self, width=700 if addon_prefs.debug else 450)

    def draw(self, context):

        res, obj = mustardui_active_object(context, config=1)
        custom_props, index = mustardui_choose_cp(obj, self.type, context.scene)
        custom_prop = custom_props[index]
        prop_type = custom_prop.type
        prop_cp_type = custom_prop.cp_type
        addon_prefs = context.preferences.addons[base_package].preferences

        scale = 3.0

        layout = self.layout

        box = layout.box()

        row = box.row()
        row.label(text="Name:")
        row.scale_x = scale
        row.prop(self, "name", text="")

        row = box.row()
        row.label(text="Icon:")
        row.scale_x = scale
        row.prop(self, "icon", text="")

        row = box.row()
        row.label(text="Visibility:")
        row.scale_x = scale / 2
        row.prop(custom_prop, "hidden", text="Hidden")
        row.prop(custom_prop, "advanced", text="Advanced")

        if prop_cp_type == "OUTFIT":
            row = box.row()
            row.label(text="Outfit:")
            row.scale_x = scale
            row.prop(custom_prop, "outfit", text="")

            row = box.row()
            row.label(text="Outfit piece:")
            row.scale_x = scale
            row.prop(custom_prop, "outfit_piece", text="")

            if prop_type == "FLOAT" and custom_prop.subtype != "COLOR":
                row = box.row()
                row.label(text="Actions on switch:")
                row.scale_x = scale / 2
                row.prop(custom_prop, "outfit_enable_on_switch", text="Enable")
                row.prop(custom_prop, "outfit_disable_on_switch", text="Disable")

        if prop_cp_type == "HAIR":
            row = box.row()
            row.label(text="Hair:")
            row.scale_x = scale
            row.prop(custom_prop, "hair", text="")

        if custom_prop.is_animatable:

            box = layout.box()

            row = box.row()
            row.label(text="Description:")
            row.scale_x = scale
            row.prop(self, "description", text="")

            if prop_type == "FLOAT" and custom_prop.subtype != "COLOR":

                if custom_prop.array_length == 0:
                    row = box.row()
                    row.label(text="Force type:")
                    row.scale_x = scale
                    row.prop(self, "force_type", text="")

                    if self.force_type == "None":
                        row = box.row()
                        row.label(text="Default:")
                        row.scale_x = scale
                        row.prop(self, "default_float", text="")
                else:
                    row = box.row()
                    row.label(text="Default:")
                    row.scale_x = scale
                    row.prop(self, "default_array", text="")

                if self.force_type == "None":
                    row = box.row()
                    row.label(text="Min / Max")
                    row.scale_x = scale
                    row2 = row.row(align=True)
                    row2.prop(self, "min_float", text="")
                    row2.prop(self, "max_float", text="")

            if custom_prop.subtype == "COLOR":
                row = box.row()
                row.label(text="Default:")
                row.scale_x = scale
                row.prop(self, "default_color", text="")

            if prop_type == "INT" or self.force_type == "Int":

                row = box.row()
                row.label(text="Default:")
                row.scale_x = scale
                row.prop(self, "default_int" if custom_prop.array_length == 0 else "default_array", text="")

                row = box.row()
                row.label(text="Min / Max")
                row.scale_x = scale
                row2 = row.row(align=True)
                row2.prop(self, "min_int", text="")
                row2.prop(self, "max_int", text="")

            elif prop_type == "BOOLEAN" or self.force_type == "Bool":

                row = box.row()
                row.label(text="Default:")
                row.prop(self, "default_bool" if custom_prop.array_length == 0 else "default_array", text="")

            if len(custom_prop.linked_properties) > 0:

                row = layout.row()
                row.label(text="Linked Properties", icon="LINK_BLEND")
                if addon_prefs.debug:
                    row.prop(self, "change_rna_linked", text="", icon="GREASEPENCIL")

                box = layout.box()

                for lp in custom_prop.linked_properties:

                    row = box.row()
                    if self.change_rna_linked:
                        row.scale_x = 6
                        row.prop(lp, "rna", icon="RNA", text="")
                        row.scale_x = 0.05
                        row.label(text=".")
                        row.scale_x = 1.2
                        row.prop(lp, "path", text="")
                        row.scale_x = 1
                    else:
                        row.label(text=mustardui_cp_path(lp.rna, lp.path), icon="RNA")
                    op = row.operator('mustardui.property_removelinked', text="", icon="X")
                    op.rna = lp.rna
                    op.path = lp.path
                    op.type = self.type

        if addon_prefs.debug:

            row = layout.row()
            row.label(text="Paths", icon="DECORATE_DRIVER")
            row.prop(self, "change_rna", text="", icon="GREASEPENCIL")

            box = layout.box()

            row = box.row()
            row.label(text="Property name: " + custom_prop.prop_name, icon="PROPERTIES")

            row = box.row()
            if self.change_rna:
                row.scale_x = 6
                row.prop(custom_prop, "rna", icon="RNA", text="")
                row.scale_x = 0.05
                row.label(text=".")
                row.scale_x = 1.5
                row.prop(custom_prop, "path", text="")
            else:
                row.label(text=mustardui_cp_path(custom_prop.rna, custom_prop.path), icon="RNA")

        if self.change_rna or self.change_rna_linked:
            layout.box().label(text="Rebuild properties after modifying path values to apply the changes!",
                               icon="ERROR")


def register():
    bpy.utils.register_class(MustardUI_Property_Settings)


def unregister():
    bpy.utils.unregister_class(MustardUI_Property_Settings)
