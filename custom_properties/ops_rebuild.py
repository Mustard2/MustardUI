import ast
import re

import bpy
from rna_prop_ui import rna_idprop_ui_create

from .. import __package__ as base_package
from ..misc.prop_utils import evaluate_path, evaluate_rna
from ..model_selection.active_object import (
    active_object_operator_poll,
    mustardui_active_object,
)
from .misc import assign_ptr, mustardui_clean_prop, mustardui_cp_path


def replace_id_block(rna_path, id_type, new_name):
    patterns = {
        "OBJECT": r'bpy\.data\.objects\[".*?"\]',
        "SHAPEKEY": r'bpy\.data\.shape_keys\[".*?"\]',
        "ARMATURE": r'bpy\.data\.armatures\[".*?"\]',
        "MATERIAL": r'bpy\.data\.materials\[".*?"\]',
        "COLLECTION": r'bpy\.data\.collections\[".*?"\]',
        "NODE_TREE": r'bpy\.data\.node_groups\[".*?"\]',
    }

    replacements = {
        "OBJECT": f'bpy.data.objects["{new_name}"]',
        "SHAPEKEY": f'bpy.data.shape_keys["{new_name}"]',
        "ARMATURE": f'bpy.data.armatures["{new_name}"]',
        "MATERIAL": f'bpy.data.materials["{new_name}"]',
        "COLLECTION": f'bpy.data.collections["{new_name}"]',
        "NODE_TREE": f'bpy.data.node_groups["{new_name}"]',
    }

    pattern = patterns.get(id_type)
    replacement = replacements.get(id_type)

    if not pattern or not replacement:
        raise Exception("Unsupported type")

    return re.sub(pattern, replacement, rna_path, count=1)


def fix_custom_property_path(obj, uilist, custom_prop, addon_prefs):
    if evaluate_path(custom_prop.rna, custom_prop.path) is not None:
        return "VALID"

    if custom_prop.ptr_type == "None":
        return "NOT_FIXABLE"

    print(
        "MustardUI - Can not find the property "
        + mustardui_cp_path(custom_prop.rna, custom_prop.path)
        + " for custom property "
        + custom_prop.name
        + ". Attempting to fix the path..."
    )

    if custom_prop.ptr_type == "OBJECT" and custom_prop.ptr_object:
        custom_prop.rna = replace_id_block(
            custom_prop.rna, "OBJECT", custom_prop.ptr_object.name
        )
    elif custom_prop.ptr_type == "SHAPEKEY" and custom_prop.ptr_key:
        custom_prop.rna = replace_id_block(
            custom_prop.rna, "SHAPEKEY", custom_prop.ptr_key.name
        )
    elif custom_prop.ptr_type == "ARMATURE" and custom_prop.ptr_armature:
        custom_prop.rna = replace_id_block(
            custom_prop.rna, "ARMATURE", custom_prop.ptr_armature.name
        )
    elif custom_prop.ptr_type == "MATERIAL" and custom_prop.ptr_material:
        custom_prop.rna = replace_id_block(
            custom_prop.rna, "MATERIAL", custom_prop.ptr_material.name
        )
    elif custom_prop.ptr_type == "COLLECTION" and custom_prop.ptr_collection:
        custom_prop.rna = replace_id_block(
            custom_prop.rna,
            "COLLECTION",
            custom_prop.ptr_collection.name,
        )
    elif custom_prop.ptr_type == "NODE_TREE" and custom_prop.ptr_node_tree:
        custom_prop.rna = replace_id_block(
            custom_prop.rna, "NODE_TREE", custom_prop.ptr_node_tree.name
        )
    else:
        print(
            "MustardUI - No valid pointer found for custom property "
            + custom_prop.name
            + "."
        )

    if evaluate_path(custom_prop.rna, custom_prop.path) is None:
        print(
            "MustardUI - Can not fix the path for custom property "
            + custom_prop.name
            + ". This custom property will be removed."
        )

        return "ERROR"

    print(
        "MustardUI - Path fixed for custom property "
        + custom_prop.name
        + ". New path: "
        + custom_prop.rna
    )

    return "FIXED"


class MustardUI_Property_FixPath(bpy.types.Operator):
    """Attempt to fix an invalid path"""

    bl_idname = "mustardui.property_fix_path"
    bl_label = "Fix Custom Property Path"
    bl_options = {"UNDO"}

    remove_invalid_properties: bpy.props.BoolProperty(
        name="Remove Invalid Properties",
        default=True,
        description="Remove custom properties that can not be rebuilt because their "
        "path can not be found.",
    )
    assign_pointers: bpy.props.BoolProperty(
        name="Assign Pointers",
        default=False,
        description="Try to assign pointers to custom properties to be able to fix"
                    " their path.\nThis only affects future custom properties rebuild, "
                    "not the current",
    )

    @classmethod
    def poll(cls, context):
        return active_object_operator_poll(context, config=-1)

    def execute(self, context):

        res, obj = mustardui_active_object(context, config=-1)
        addon_prefs = context.preferences.addons[base_package].preferences

        invalid = 0
        not_fixable = 0
        fixed = 0
        errors = 0

        custom_properties_types = [
            ("MustardUI_CustomProperties", obj.MustardUI_CustomProperties),
            ("MustardUI_CustomPropertiesOutfit", obj.MustardUI_CustomPropertiesOutfit),
            ("MustardUI_CustomPropertiesHair", obj.MustardUI_CustomPropertiesHair),
        ]

        # Try to assign pointers to custom properties to be able to fix their path
        pointers_errors = 0
        if self.assign_pointers:
            for custom_properties in custom_properties_types:
                for custom_prop in custom_properties:
                    try:
                        assign_ptr(custom_prop, custom_prop.rna, addon_prefs)
                    except Exception:
                        pointers_errors += 1

        to_remove = []

        for prop_type_name, custom_properties in custom_properties_types:
            for i, custom_prop in enumerate(custom_properties):
                res = fix_custom_property_path(
                    obj, custom_properties, custom_prop, addon_prefs
                )
                if res != "VALID":
                    invalid += 1
                elif res == "NOT_FIXABLE":
                    not_fixable += 1
                elif res == "FIXED":
                    fixed += 1
                elif res == "ERROR":
                    errors += 1
                    to_remove.append((i, custom_properties))

        if self.remove_invalid_properties:
            for i, uilist in reversed(to_remove):
                mustardui_clean_prop(
                    obj,
                    uilist,
                    i,
                    addon_prefs,
                )
                uilist.remove(i)

        total = (
            len(obj.MustardUI_CustomProperties)
            + len(obj.MustardUI_CustomPropertiesOutfit)
            + len(obj.MustardUI_CustomPropertiesHair)
        )

        if invalid == 0:
            self.report(
                {"INFO"}, f"MustardUI - All {total} custom properties are valid."
            )
        else:
            msg_parts = [f"{invalid} invalid"]

            if fixed > 0:
                msg_parts.append(f"{fixed} fixed")

            if errors > 0:
                msg_parts.append(f"{errors} removed")

            if not_fixable > 0:
                msg_parts.append(f"{not_fixable} not fixable")

            summary = ", ".join(msg_parts)

            level = {"INFO"} if errors == 0 else {"WARNING"}

            self.report(
                level,
                f"MustardUI - {summary} custom properties. Check console for details.",
            )

        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=450)

    def draw(self, context):

        addon_prefs = context.preferences.addons[base_package].preferences

        layout = self.layout

        box = layout.box()
        col = box.column(align=True)
        col.label(
            text="This will attempt to recover CP paths.",
            icon="INFO",
        )

        box = layout.box()
        col = box.column(align=True)
        col.prop(self, "remove_invalid_properties")

        if addon_prefs.debug:
            col.separator()
            col.prop(self, "assign_pointers")


class MustardUI_Property_Rebuild(bpy.types.Operator):
    """Rebuild all drivers and custom properties. This can be used if the properties aren't working or if the properties max/min/default/descriptions are broken"""  # noqa: E501

    bl_idname = "mustardui.property_rebuild"
    bl_label = "Rebuild Custom Properties"
    bl_options = {"UNDO"}

    attempt_fix_paths: bpy.props.BoolProperty(
        name="Attempt to Fix Paths",
        default=True,
        description="Attempt to fix the paths of custom properties"
        " that can not be rebuilt because their path can not be found. "
        "This will try to find the new path of the property if it "
        "was moved to another object or if it was renamed.",
    )
    remove_invalid_properties: bpy.props.BoolProperty(
        name="Remove Invalid Properties",
        default=True,
        description="Remove custom properties that can not be rebuilt because their "
        "path can not be found.",
    )
    assign_pointers: bpy.props.BoolProperty(
        name="Assign Pointers",
        default=False,
        description="Try to assign pointers to custom properties to be able to fix"
        " their path.\nThis only affects future custom properties rebuild, "
        "not the current",
    )

    def add_driver(self, obj, rna, path, prop_name):

        driver_object = evaluate_rna(rna)
        driver_object.driver_remove(path)
        driver = driver_object.driver_add(path)

        try:
            array_length = len(evaluate_path(rna, path))
        except Exception:
            array_length = 0

        # No array property
        if array_length == 0:
            driver = driver.driver
            driver.type = "AVERAGE"
            var = driver.variables.new()
            var.name = "mustardui_var"
            var.targets[0].id_type = "ARMATURE"
            var.targets[0].id = obj
            var.targets[0].data_path = f'["{prop_name}"]'

        # Array property
        else:
            for i in range(0, array_length):
                driver[i] = driver[i].driver
                driver[i].type = "AVERAGE"

                var = driver[i].variables.new()
                var.name = "mustardui_var"
                var.targets[0].id_type = "ARMATURE"
                var.targets[0].id = obj
                var.targets[0].data_path = f'["{prop_name}"][{str(i)}]'

        return

    @classmethod
    def poll(cls, context):
        return active_object_operator_poll(context, config=0)

    def execute(self, context):

        res, obj = mustardui_active_object(context, config=0)
        addon_prefs = context.preferences.addons[base_package].preferences

        # Rebuild all custom properties
        custom_properties_types = [
            obj.MustardUI_CustomProperties,
            obj.MustardUI_CustomPropertiesOutfit,
            obj.MustardUI_CustomPropertiesHair,
        ]

        errors = 0

        if self.attempt_fix_paths:
            bpy.ops.mustardui.property_fix_path(
                remove_invalid_properties=self.remove_invalid_properties,
                assign_pointers=self.assign_pointers,
            )

        # Rebuilding custom properties and their linked properties drivers
        for custom_properties in custom_properties_types:
            to_remove = []

            for i, custom_prop in enumerate(custom_properties):
                try:
                    if evaluate_path(custom_prop.rna, custom_prop.path) is None:
                        raise Exception(
                            "Property not rebuildable because path is not valid"
                        )

                    if not custom_prop.is_animatable:
                        continue

                    prop_name = custom_prop.prop_name

                    if prop_name in obj.keys():
                        del obj[prop_name]

                    if (
                        custom_prop.type == "BOOLEAN"
                        or custom_prop.force_type == "Bool"
                    ):
                        try:
                            default_bool = bool(
                                evaluate_path(custom_prop.rna, custom_prop.path)
                            )
                        except Exception:
                            print(
                                "MustardUI - Can not find the property "
                                + mustardui_cp_path(custom_prop.rna, custom_prop.path)
                            )
                            default_bool = True
                        rna_idprop_ui_create(
                            obj,
                            prop_name,
                            default=default_bool,
                            description=custom_prop.description,
                            overridable=True,
                        )

                    elif (
                        custom_prop.type == "FLOAT" and custom_prop.force_type == "None"
                    ):
                        rna_idprop_ui_create(
                            obj,
                            prop_name,
                            default=float(custom_prop.default_float)
                            if custom_prop.array_length == 0
                            else ast.literal_eval(custom_prop.default_array),
                            min=float(custom_prop.min_float)
                            if custom_prop.subtype != "COLOR"
                            else 0.0,
                            max=float(custom_prop.max_float)
                            if custom_prop.subtype != "COLOR"
                            else 1.0,
                            step=float(custom_prop.step_float),
                            description=custom_prop.description,
                            overridable=True,
                            subtype=custom_prop.subtype,
                        )

                    elif custom_prop.type == "INT" or custom_prop.force_type == "Int":
                        rna_idprop_ui_create(
                            obj,
                            prop_name,
                            default=int(custom_prop.default_int)
                            if custom_prop.array_length == 0
                            else ast.literal_eval(custom_prop.default_array),
                            min=custom_prop.min_int,
                            max=custom_prop.max_int,
                            description=custom_prop.description,
                            overridable=True,
                            subtype=custom_prop.subtype
                            if custom_prop.subtype != "FACTOR"
                            else None,
                        )

                    else:
                        rna_idprop_ui_create(
                            obj,
                            prop_name,
                            default=evaluate_path(custom_prop.rna, custom_prop.path),
                            description=custom_prop.description,
                            overridable=True,
                        )

                        self.add_driver(
                            obj,
                            custom_prop.rna,
                            custom_prop.path,
                            custom_prop.prop_name,
                        )
                        for linked_custom_prop in custom_prop.linked_properties:
                            self.add_driver(
                                obj,
                                linked_custom_prop.rna,
                                linked_custom_prop.path,
                                custom_prop.prop_name,
                            )
                    if evaluate_path(custom_prop.rna, custom_prop.path) is None:
                        raise Exception("Property not found after rebuilding")
                except Exception:
                    errors += 1

                    if "[" in custom_prop.path and "]" in custom_prop.path:
                        print(
                            "MustardUI - Something went wrong when trying to restore "
                            + custom_prop.name
                            + " at "
                            + repr(custom_prop.rna + custom_prop.path)
                            + ". This custom property will be removed."
                        )
                    else:
                        print(
                            "MustardUI - Something went wrong when trying to restore "
                            + custom_prop.name
                            + " at "
                            + repr(custom_prop.rna + "." + custom_prop.path)
                            + ". This custom property will be removed."
                        )

                    to_remove.append(i)

            if self.remove_invalid_properties:
                for i in reversed(to_remove):
                    mustardui_clean_prop(obj, custom_properties, i, addon_prefs)
                    custom_properties.remove(i)

        obj.update_tag()

        if errors > 0:
            if self.remove_invalid_properties:
                self.report(
                    {"WARNING"},
                    "MustardUI - "
                    + str(errors)
                    + " custom properties were invalid and deleted. Check the "
                    "console for more infos.",
                )
            else:
                self.report(
                    {"WARNING"},
                    "MustardUI - "
                    + str(errors)
                    + " custom properties seems invalid. Check the console for more "
                    "infos.",
                )
        else:
            self.report({"INFO"}, "MustardUI - Custom Properties rebuilt.")

        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=450)

    def draw(self, context):

        addon_prefs = context.preferences.addons[base_package].preferences

        layout = self.layout

        box = layout.box()
        col = box.column(align=True)
        col.label(
            text="This will attempt to rebuild all the drivers and custom properties.",
            icon="ERROR",
        )
        col.label(
            text="This can fix most issues with custom properties but it can also "
            "cause issues ",
            icon="BLANK1",
        )
        col.label(
            text="if the paths of the custom properties are not valid anymore.",
            icon="BLANK1",
        )

        box = layout.box()
        col = box.column(align=True)
        col.prop(self, "attempt_fix_paths")
        col.prop(self, "remove_invalid_properties")

        if addon_prefs.debug:
            col.separator()
            col.prop(self, "assign_pointers")


def register():
    bpy.utils.register_class(MustardUI_Property_FixPath)
    bpy.utils.register_class(MustardUI_Property_Rebuild)


def unregister():
    bpy.utils.unregister_class(MustardUI_Property_Rebuild)
    bpy.utils.unregister_class(MustardUI_Property_FixPath)
