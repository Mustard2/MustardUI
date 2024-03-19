import bpy
from bpy.props import *
from rna_prop_ui import rna_idprop_ui_create
from ..model_selection.active_object import *
from .misc import *


class MustardUI_Property_MenuLink(bpy.types.Operator):
    """Link the property to an existing one"""
    bl_idname = "mustardui.property_menulink"
    bl_label = "Link Property"
    bl_options = {'UNDO'}

    parent_rna: StringProperty()
    parent_path: StringProperty()
    type: EnumProperty(default="BODY",
                       items=(
                           ("BODY", "Body", ""),
                           ("OUTFIT", "Outfit", ""),
                           ("HAIR", "Hair", ""))
                       )

    @classmethod
    def poll(cls, context):

        res, arm = mustardui_active_object(context, config=1)
        return res

    def execute(self, context):

        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config=1)
        custom_props, nu = mustardui_choose_cp(obj, self.type, context.scene)

        prop = context.button_prop

        if not hasattr(context, 'button_prop') or not hasattr(prop, 'array_length'):
            self.report({'ERROR'}, 'MustardUI - Can not link this property to anything.')
            return {'FINISHED'}

        if not prop.is_animatable:
            self.report({'ERROR'}, 'MustardUI - Can not link a \'non animatable\' property.')
            return {'FINISHED'}

        found = False
        for parent_prop in custom_props:
            if parent_prop.rna == self.parent_rna and parent_prop.path == self.parent_path:
                found = True
                break
        if not found:
            self.report({'ERROR'}, 'MustardUI - An error occurred while searching for parent property.')
            return {'FINISHED'}

        try:
            parent_prop_length = len(eval(mustardui_cp_path(parent_prop.rna, parent_prop.path)))
        except:
            parent_prop_length = 0

        if prop.array_length != parent_prop_length:
            self.report({'ERROR'}, 'MustardUI - Can not link properties with different array length.')
            return {'FINISHED'}

        if parent_prop.type != prop.type:
            self.report({'ERROR'}, 'MustardUI - Can not link properties with different type.')
            return {'FINISHED'}

        # dump(prop, 'button_prop')

        # Copy the path of the selected property
        try:
            bpy.ops.ui.copy_data_path_button(full_path=True)
        except:
            self.report({'ERROR'}, 'MustardUI - Invalid selection.')
            return {'FINISHED'}

        # Adjust the property path to be exported
        rna, path = context.window_manager.clipboard.rsplit('.', 1)
        if '][' in path:
            path, rem = path.rsplit('[', 1)
            rna = rna + '.' + path
            path = '[' + rem
        elif '[' in path:
            path, rem = path.rsplit('[', 1)

        if parent_prop.rna == rna and parent_prop.path == path:
            self.report({'ERROR'}, 'MustardUI - Can not link a property with itself.')
            return {'FINISHED'}

        if not mustardui_check_cp(obj, rna, path):
            self.report({'ERROR'}, 'MustardUI - Can not link a property already added.')
            return {'FINISHED'}

        switched_warning = False
        for check_prop in custom_props:
            for i in range(0, len(check_prop.linked_properties)):
                if check_prop.linked_properties[i].rna == rna and check_prop.linked_properties[i].path == path:
                    switched_warning = True
                    check_prop.linked_properties.remove(i)

        # Add driver
        if prop.is_animatable:
            mustardui_add_driver(obj, rna, path, prop, parent_prop.prop_name)

        # Add linked property to list
        if not (rna, path) in [(x.rna, x.path) for x in parent_prop.linked_properties]:
            lp = parent_prop.linked_properties.add()
            lp.rna = rna
            lp.path = path
        else:
            self.report({'ERROR'}, 'MustardUI - An error occurred while linking the property.')
            return {'FINISHED'}

        obj.update_tag()

        if switched_warning:
            self.report({'WARNING'}, 'MustardUI - Switched linked property.')
        else:
            self.report({'INFO'}, 'MustardUI - Property linked.')

        return {'FINISHED'}


class MustardUI_Property_RemoveLinked(bpy.types.Operator):
    """Remove the linked property from the list"""
    bl_idname = "mustardui.property_removelinked"
    bl_label = "Remove Linked Property"
    bl_options = {'UNDO'}

    rna: bpy.props.StringProperty()
    path: bpy.props.StringProperty()

    type: bpy.props.EnumProperty(default="BODY",
                                 items=(
                                     ("BODY", "Body", ""),
                                     ("OUTFIT", "Outfit", ""),
                                     ("HAIR", "Hair", ""))
                                 )

    def clean_prop(self, obj, uilist, index):

        # Remove linked property driver
        try:
            driver_object = eval(self.rna)
            driver_object.driver_remove(self.path)
            return True
        except:
            return False

    @classmethod
    def poll(cls, context):

        res, obj = mustardui_active_object(context, config=1)
        return obj is not None

    def execute(self, context):

        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config=1)
        uilist, index = mustardui_choose_cp(obj, self.type, context.scene)

        # Remove custom property and driver
        driver_removed = self.clean_prop(obj, uilist, index)

        # Find the linked property index to remove it from the list
        i = -1
        for lp in uilist[index].linked_properties:
            i += 1
            if lp.rna == self.rna and lp.path == self.path:
                break

        if i != -1:
            uilist[index].linked_properties.remove(i)

        obj.update_tag()

        if not driver_removed:
            self.report({'WARNING'},
                        'MustardUI - The linked property was removed from the UI, but the associated driver was not '
                        'found: you might need to remove it manually.')

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_Property_MenuLink)
    bpy.utils.register_class(MustardUI_Property_RemoveLinked)


def unregister():
    bpy.utils.unregister_class(MustardUI_Property_RemoveLinked)
    bpy.utils.unregister_class(MustardUI_Property_MenuLink)
