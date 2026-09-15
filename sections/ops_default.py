import bpy

from ..model_selection.active_object import (
    active_object_operator_poll,
    mustardui_active_object,
)


class MustardUI_Section_PropertyDefault(bpy.types.Operator):
    """Revert the properties of the section to their default value"""

    bl_idname = "mustardui.section_property_default"
    bl_label = "Reset Properties to Default"
    bl_options = {"UNDO"}

    # -1 targets the custom properties with no Section
    section_id: bpy.props.IntProperty(default=-1)

    @classmethod
    def poll(cls, context):
        if not active_object_operator_poll(context, config=0):
            return False

        res, obj = mustardui_active_object(context, config=0)
        return len(obj.MustardUI_CustomProperties) > 0

    def execute(self, context):

        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings
        custom_props = obj.MustardUI_CustomProperties

        sections = rig_settings.body_custom_properties_sections

        if not -1 <= self.section_id < len(sections):
            return {"FINISHED"}

        section_name = "" if self.section_id == -1 else sections[self.section_id].name

        for prop in custom_props:
            if prop.section == section_name and prop.prop_name in obj.keys():
                ui_data = obj.id_properties_ui(prop.prop_name)
                ui_data_dict = ui_data.as_dict()
                obj[prop.prop_name] = ui_data_dict["default"]

        # Force depsgraph re-evaluation and UI redraw so the changes
        # take effect immediately (not just after re-selecting the armature).
        obj.update_tag()
        context.view_layer.update()
        if context.area:
            context.area.tag_redraw()
        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_Section_PropertyDefault)


def unregister():
    bpy.utils.unregister_class(MustardUI_Section_PropertyDefault)
