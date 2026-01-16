import bpy
from .. import __package__ as base_package


class MustardUI_ToolsCreators_LinkShapeKeysToActive(bpy.types.Operator):
    bl_idname = "mustardui.tools_creators_link_shape_keys"
    bl_label = "Link Shape Keys to Active"
    bl_description = "Link matching Shape Keys on selected objects to the active object using Drivers"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):

        addon_prefs = context.preferences.addons[base_package].preferences
        debug = addon_prefs.debug

        active_obj = context.active_object
        selected_objs = context.selected_objects

        if not active_obj or not active_obj.data.shape_keys:
            self.report({'ERROR'}, "Active object has no shape keys")
            return {'CANCELLED'}

        errors = 0

        active_keys = active_obj.data.shape_keys.key_blocks

        for obj in selected_objs:
            if obj == active_obj:
                continue

            if not obj.data.shape_keys:
                continue

            obj_keys = obj.data.shape_keys.key_blocks

            for key in obj_keys:
                if key.name in active_keys and key.name != "Basis":
                    # Remove existing driver if any
                    try:
                        key.driver_remove("value")
                    except TypeError:
                        pass

                    try:
                        driver = key.driver_add("value").driver
                        driver.type = 'SCRIPTED'

                        var = driver.variables.new()
                        var.name = "val"
                        var.type = 'SINGLE_PROP'

                        target = var.targets[0]
                        target.id = active_obj
                        target.data_path = (
                            f'data.shape_keys.key_blocks["{key.name}"].value'
                        )

                        driver.expression = "val"

                        if debug:
                            print(f'MustardUI - Linked: Shape Key "{key.name}" in Object "{obj.name}"')

                    except TypeError:
                        print(f'MustardUI - Can not link Shape Key "{key.name}" to Object "{obj.name}"')
                        errors += 1

        if errors == 0:
            self.report({'INFO'}, f'MustardUI - Shape key linked to "{active_obj.name}".')
        else:
            self.report({'WARNING'}, f'MustardUI - Some shape keys could not be linked to "{active_obj.name}".')

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_ToolsCreators_LinkShapeKeysToActive)


def unregister():
    bpy.utils.unregister_class(MustardUI_ToolsCreators_LinkShapeKeysToActive)
