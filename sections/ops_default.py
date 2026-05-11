import bpy

from ..model_selection.active_object import mustardui_active_object


class MustardUI_Section_PropertyDefault(bpy.types.Operator):
    """Revert the section properties to default"""

    bl_idname = "mustardui.section_property_default"
    bl_label = "Reset Properties to Default"
    bl_options = {"UNDO"}

    section_id: bpy.props.IntProperty(default=-1)

    @classmethod
    def poll(cls, context):
        res, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings
        return res and len(rig_settings.body_custom_properties_sections)

    def execute(self, context):

        if self.section_id < 0:
            return {"FINISHED"}

        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings
        custom_props = obj.MustardUI_CustomProperties

        if self.section_id > len(rig_settings.body_custom_properties_sections):
            return {"FINISHED"}

        section = rig_settings.body_custom_properties_sections[self.section_id]

        for prop in custom_props:
            if prop.section == section.name and prop.prop_name in obj.keys():
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
