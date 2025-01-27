import bpy
from bpy.props import *
from rna_prop_ui import rna_idprop_ui_create
from ..model_selection.active_object import *
from .misc import *
from ..misc.prop_utils import *
from .. import __package__ as base_package


class MustardUI_Property_Rebuild(bpy.types.Operator):
    """Rebuild all drivers and custom properties. This can be used if the properties aren't working or if the properties max/min/default/descriptions are broken"""
    bl_idname = "mustardui.property_rebuild"
    bl_label = "Rebuild Custom Properties"
    bl_options = {'UNDO'}

    def add_driver(self, obj, rna, path, prop_name):

        driver_object = evaluate_rna(rna)
        driver_object.driver_remove(path)
        driver = driver_object.driver_add(path)

        try:
            array_length = len(evaluate_path(rna, path))
        except:
            array_length = 0

        # No array property
        if array_length == 0:
            driver = driver.driver
            driver.type = "AVERAGE"
            var = driver.variables.new()
            var.name = 'mustardui_var'
            var.targets[0].id_type = "ARMATURE"
            var.targets[0].id = obj
            var.targets[0].data_path = f'["{prop_name}"]'

        # Array property
        else:
            for i in range(0, array_length):
                driver[i] = driver[i].driver
                driver[i].type = "AVERAGE"

                var = driver[i].variables.new()
                var.name = 'mustardui_var'
                var.targets[0].id_type = "ARMATURE"
                var.targets[0].id = obj
                var.targets[0].data_path = f'["{prop_name}"][{str(i)}]'

        return

    @classmethod
    def poll(cls, context):

        res, arm = mustardui_active_object(context, config=0)
        return res

    def execute(self, context):

        res, obj = mustardui_active_object(context, config=0)
        addon_prefs = context.preferences.addons[base_package].preferences

        # Rebuild all custom properties
        custom_props = [(x, 0) for x in obj.MustardUI_CustomProperties]
        for x in obj.MustardUI_CustomPropertiesOutfit:
            custom_props.append((x, 1))
        for x in obj.MustardUI_CustomPropertiesHair:
            custom_props.append((x, 2))

        errors = 0

        to_remove = []

        for custom_prop, prop_type in [x for x in custom_props if x[0].is_animatable]:

            prop_name = custom_prop.prop_name

            if prop_name in obj.keys():
                del obj[prop_name]

            if custom_prop.type == "BOOLEAN" or custom_prop.force_type == "Bool":
                try:
                    default_bool = int(evaluate_path(custom_prop.rna, custom_prop.path))
                except:
                    print(
                        "MustardUI - Can not find the property " + mustardui_cp_path(custom_prop.rna, custom_prop.path))
                    default_bool = True
                rna_idprop_ui_create(obj, prop_name, default=default_bool,
                                     min=0,
                                     max=1,
                                     description=custom_prop.description,
                                     overridable=True)

            elif custom_prop.type == "FLOAT" and custom_prop.force_type == "None":
                import numpy as np
                rna_idprop_ui_create(obj, prop_name,
                                     default=custom_prop.default_float if custom_prop.array_length == 0 else ast.literal_eval(custom_prop.default_array),
                                     min=custom_prop.min_float if custom_prop.subtype != "COLOR" else 0.,
                                     max=custom_prop.max_float if custom_prop.subtype != "COLOR" else 1.,
                                     description=custom_prop.description,
                                     overridable=True,
                                     subtype=custom_prop.subtype if custom_prop.subtype != "FACTOR" else None)

            elif custom_prop.type == "INT" or custom_prop.force_type == "Int":
                rna_idprop_ui_create(obj, prop_name,
                                     default=int(custom_prop.default_int) if custom_prop.array_length == 0 else ast.literal_eval(custom_prop.default_array),
                                     min=custom_prop.min_int,
                                     max=custom_prop.max_int,
                                     description=custom_prop.description,
                                     overridable=True,
                                     subtype=custom_prop.subtype if custom_prop.subtype != "FACTOR" else None)

            else:
                rna_idprop_ui_create(obj, prop_name,
                                     default=evaluate_path(custom_prop.rna, custom_prop.path),
                                     description=custom_prop.description,
                                     overridable=True)

            # Rebuilding custom properties and their linked properties drivers
            try:
                self.add_driver(obj, custom_prop.rna, custom_prop.path, custom_prop.prop_name)
                for linked_custom_prop in custom_prop.linked_properties:
                    self.add_driver(obj, linked_custom_prop.rna, linked_custom_prop.path, custom_prop.prop_name)
            except:
                errors += 1

                if "[" in custom_prop.path and "]" in custom_prop.path:
                    print(
                        'MustardUI - Something went wrong when trying to restore ' + custom_prop.name + ' at ' + repr(custom_prop.rna + custom_prop.path) + '. This custom property will be removed.')
                else:
                    print(
                        'MustardUI - Something went wrong when trying to restore ' + custom_prop.name + ' at ' + repr(custom_prop.rna + '.' + custom_prop.path) + '. This custom property will be removed.')

                if prop_type == 0:
                    uilist = obj.MustardUI_CustomProperties
                elif prop_type == 1:
                    uilist = obj.MustardUI_CustomPropertiesOutfit
                else:
                    uilist = obj.MustardUI_CustomPropertiesHair

                for i in range(0, len(uilist)):
                    if uilist[i].rna == custom_prop.rna and uilist[i].path == custom_prop.path:
                        break

                mustardui_clean_prop(obj, uilist, i, addon_prefs)
                to_remove.append((i, prop_type))

        for i, prop_type in reversed(to_remove):

            if prop_type == 0:
                uilist = obj.MustardUI_CustomProperties
            elif prop_type == 1:
                uilist = obj.MustardUI_CustomPropertiesOutfit
            else:
                uilist = obj.MustardUI_CustomPropertiesHair

            uilist.remove(i)

        obj.update_tag()

        if errors > 0:
            if errors > 1:
                self.report({'WARNING'}, 'MustardUI - ' + str(
                    errors) + ' custom properties were corrupted and deleted. Check the console for more infos.')
            else:
                self.report({'WARNING'},
                            'MustardUI - A custom property was corrupted and deleted. Check the console for more infos.')
        else:
            self.report({'INFO'}, 'MustardUI - All the drivers and custom properties rebuilt.')

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_Property_Rebuild)


def unregister():
    bpy.utils.unregister_class(MustardUI_Property_Rebuild)
