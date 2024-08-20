import bpy
from bpy.props import *
from rna_prop_ui import rna_idprop_ui_create
from ..model_selection.active_object import *
from .misc import *
from ..misc.prop_utils import *
from .. import __package__ as base_package


class MustardUI_Property_SmartCheck(bpy.types.Operator):
    """Check if some properties respect the MustardUI Int/Float/Bool convention, and automatically add them as additional properties"""
    bl_idname = "mustardui.property_smartcheck"
    bl_label = "Properties Smart Check"
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
            var.targets[0].data_path = f'["{bpy.utils.escape_identifier(prop_name)}"]'

        # Array property
        else:
            for i in range(0, array_length):
                driver[i] = driver[i].driver
                driver[i].type = "AVERAGE"

                var = driver[i].variables.new()
                var.name = 'mustardui_var'
                var.targets[0].id_type = "ARMATURE"
                var.targets[0].id = obj
                var.targets[0].data_path = f'["{bpy.utils.escape_identifier(prop_name)}"][{str(i)}]'

        return

    def link_property(self, obj, rna, path, parent_prop, custom_props):

        for check_prop in custom_props:
            to_remove = []
            for i in range(0, len(check_prop.linked_properties)):
                if check_prop.linked_properties[i].rna == rna and check_prop.linked_properties[i].path == path:
                    to_remove.append(i)
            to_remove.reverse()
            for i in to_remove:
                check_prop.linked_properties.remove(i)

        # Add driver
        try:
            self.add_driver(obj, rna, path, parent_prop.prop_name)
        except:
            print("MustardUI - Could not link property to " + parent_prop.prop_name)

        # Add linked property to list
        if not rna in [x.rna for x in parent_prop.linked_properties] or not path in [x.path for x in
                                                                                     parent_prop.linked_properties]:
            lp = parent_prop.linked_properties.add()
            lp.rna = rna
            lp.path = path

        return

    def add_custom_property(self, obj, rna, path, name, type, custom_props, sections_to_recover):

        # Check if the property was already added. If yes, link it to the one already added
        for cp in custom_props:
            if cp.rna == rna and cp.path == path:
                if cp.prop_name in obj.keys():
                    return
            if cp.name == name:
                self.link_property(obj, rna, path, cp, custom_props)
                return

        # Add custom property to the object
        prop_name = name

        add_string_num = 1
        while prop_name in obj.keys():
            add_string_num += 1
            prop_name = name + ' ' + str(add_string_num)

        obj[prop_name] = evaluate_path(rna, path)

        # Change custom properties settings
        if type == "BOOLEAN":
            rna_idprop_ui_create(obj, prop_name,
                                 default=bool(evaluate_path(rna, path)),
                                 overridable=True)
        else:
            rna_idprop_ui_create(obj, prop_name,
                                 default=int(evaluate_path(rna, path)) if type == "INT" else evaluate_path(rna, path),
                                 min=0 if type == "INT" else 0.,
                                 max=1 if type == "INT" else 1.,
                                 overridable=True,
                                 subtype="COLOR" if type == "COLOR" else None)

        # Add driver
        try:
            self.add_driver(obj, rna, path, prop_name)
        except:
            print("MustardUI - Could not add a driver for " + prop_name)
            del obj[prop_name]
            return

        # Add property to the collection of properties
        if not (rna, path) in [(x.rna, x.path) for x in custom_props]:

            ui_data = obj.id_properties_ui(prop_name)
            ui_data_dict = ui_data.as_dict()

            cp = custom_props.add()
            cp.rna = rna
            cp.path = path
            cp.prop_name = prop_name
            cp.type = "FLOAT" if type == "COLOR" else type
            cp.subtype = "COLOR" if type == "COLOR" else "NONE"
            cp.array_length = 4 if type == "COLOR" else 0
            cp.name = name

            cp.is_animatable = True
            for cptr in sections_to_recover:
                if cptr[0] == rna and cptr[1] == path:
                    cp.section = cptr[2]
                    break

            if 'description' in ui_data_dict.keys():
                cp.description = ui_data_dict['description']
            if 'default' in ui_data_dict.keys() and type != "BOOLEAN":
                if type == "FLOAT":
                    cp.default_float = ui_data_dict['default']
                elif type == "INT":
                    cp.default_int = ui_data_dict['default']
                else:
                    cp.default_array = str(ui_data_dict['default'])
            if 'min' in ui_data_dict.keys() and type != "BOOLEAN":
                if type == "FLOAT":
                    cp.min_float = ui_data_dict['min']
                elif type == "INT":
                    cp.min_int = ui_data_dict['min']
            if 'max' in ui_data_dict.keys() and type != "BOOLEAN":
                if type == "FLOAT":
                    cp.max_float = ui_data_dict['max']
                elif type == "INT":
                    cp.max_int = ui_data_dict['max']

        obj.property_overridable_library_set(f'["{prop_name}"]', True)

        return

    @classmethod
    def poll(cls, context):

        res, arm = mustardui_active_object(context, config=1)
        return res

    def execute(self, context):

        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings
        custom_props = obj.MustardUI_CustomProperties
        addon_prefs = context.preferences.addons[base_package].preferences

        k = 0

        index_to_remove = []
        sections_to_recover = []
        for i in range(0, len(custom_props)):
            if ("MustardUI Float - " in custom_props[i].rna or "MustardUI Int - " in custom_props[i].rna
                    or "MustardUI Bool - " in custom_props[i].rna or "MustardUI - " in custom_props[i].rna):
                if custom_props[i].section != "":
                    sections_to_recover.append([custom_props[i].rna, custom_props[i].path, custom_props[i].section])
                index_to_remove.append(i)

        for i in reversed(index_to_remove):
            mustardui_clean_prop(obj, custom_props, i, addon_prefs)
            custom_props.remove(i)

        for mat in [x for x in rig_settings.model_body.data.materials if x is not None]:
            for j in range(len(mat.node_tree.nodes)):
                if "MustardUI Float" in mat.node_tree.nodes[j].name and mat.node_tree.nodes[j].type == "VALUE":
                    self.add_custom_property(obj,
                                             f'bpy.data.materials["{bpy.utils.escape_identifier(mat.name)}"].node_tree.nodes["{bpy.utils.escape_identifier(mat.node_tree.nodes[j].name)}"].outputs[0]',
                                             'default_value', mat.node_tree.nodes[j].name[len("MustardUI Float - "):],
                                             "FLOAT", custom_props, sections_to_recover)
                    k = k + 1
                elif "MustardUI Bool" in mat.node_tree.nodes[j].name and mat.node_tree.nodes[j].type == "VALUE":
                    self.add_custom_property(obj,
                                             f'bpy.data.materials["{bpy.utils.escape_identifier(mat.name)}"].node_tree.nodes["{bpy.utils.escape_identifier(mat.node_tree.nodes[j].name)}"].outputs[0]',
                                             'default_value', mat.node_tree.nodes[j].name[len("MustardUI Bool - "):],
                                             "BOOLEAN", custom_props, sections_to_recover)
                    k = k + 1
                elif "MustardUI Int" in mat.node_tree.nodes[j].name and mat.node_tree.nodes[j].type == "VALUE":
                    self.add_custom_property(obj,
                                             f'bpy.data.materials["{bpy.utils.escape_identifier(mat.name)}"].node_tree.nodes["{bpy.utils.escape_identifier(mat.node_tree.nodes[j].name)}"].outputs[0]',
                                             'default_value', mat.node_tree.nodes[j].name[len("MustardUI Int - "):],
                                             "INT", custom_props, sections_to_recover)
                    k = k + 1
                elif "MustardUI" in mat.node_tree.nodes[j].name and mat.node_tree.nodes[j].type == "RGB":
                    self.add_custom_property(obj,
                                             f'bpy.data.materials["{bpy.utils.escape_identifier(mat.name)}"].node_tree.nodes["{bpy.utils.escape_identifier(mat.node_tree.nodes[j].name)}"].outputs[0]',
                                             'default_value', mat.node_tree.nodes[j].name[len("MustardUI - "):],
                                             "COLOR", custom_props, sections_to_recover)
                    k = k + 1

        if rig_settings.model_body.data.shape_keys is not None:
            for shape_key in rig_settings.model_body.data.shape_keys.key_blocks:
                if "MustardUI Float" in shape_key.name:
                    self.add_custom_property(obj,
                                             f'bpy.data.objects["{bpy.utils.escape_identifier(rig_settings.model_body.name)}"].data.shape_keys.key_blocks["{bpy.utils.escape_identifier(shape_key.name)}"]',
                                             'value', shape_key.name[len("MustardUI Float - "):], "FLOAT", custom_props,
                                             sections_to_recover)
                    k = k + 1
                elif "MustardUI Bool" in shape_key.name:
                    self.add_custom_property(obj,
                                             f'bpy.data.objects["{bpy.utils.escape_identifier(rig_settings.model_body.name)}"].data.shape_keys.key_blocks["{bpy.utils.escape_identifier(shape_key.name)}"]',
                                             'value', shape_key.name[len("MustardUI Bool - "):], "BOOL", custom_props,
                                             sections_to_recover)
                    k = k + 1

        # Update the drivers
        obj.update_tag()

        self.report({'INFO'}, 'MustardUI - Smart Check found ' + str(k) + ' properties.')

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_Property_SmartCheck)


def unregister():
    bpy.utils.unregister_class(MustardUI_Property_SmartCheck)
