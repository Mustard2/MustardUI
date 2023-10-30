import bpy
from bpy.props import *
from ..model_selection.active_object import *
from ..misc.icons_list import mustardui_icon_list


class MustardUI_Body_SettingsSection(bpy.types.Operator):
    """Modify the section settings."""
    bl_idname = "mustardui.body_settingssection"
    bl_label = "Section Settings"
    bl_icon = "PREFERENCES"
    bl_options = {'UNDO'}

    name: StringProperty(name='Name',
                         description="Choose the name of the section")
    icon: EnumProperty(name='Icon',
                       items=mustardui_icon_list)
    advanced: BoolProperty(default=False,
                           name="Advanced",
                           description="The section will be shown only when Advances Settings is enabled")
    collapsable: BoolProperty(default=False,
                              name="Collapsable",
                              description="Add a collapse icon to the section.\nNote that this might give bad UI "
                                          "results if combined with an icon")

    name_edit: StringProperty(name='Name',
                              description="Name of the section")

    description: StringProperty(name='Description',
                                description="Description of the section")
    description_icon: EnumProperty(name='Icon',
                                   items=mustardui_icon_list)

    ID: IntProperty()

    def find_index_section(self, collection, item):
        i = -1
        for el in collection:
            i = i + 1
            if el.name == item:
                break
        return i

    @classmethod
    def poll(cls, context):

        res, arm = mustardui_active_object(context, config=1)
        return res

    def execute(self, context):

        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings
        sec_obj = rig_settings.body_custom_properties_sections

        if self.name_edit == "":
            self.report({'WARNING'}, 'MustardUI - Can not rename a Section with an empty name.')
            return {'FINISHED'}

        i = self.find_index_section(sec_obj, self.name)

        for prop in obj.MustardUI_CustomProperties:
            if prop.section == sec_obj[i].name:
                prop.section = self.name_edit

        if i >= 0:
            sec_obj[i].name = self.name_edit
            sec_obj[i].icon = self.icon
            sec_obj[i].advanced = self.advanced
            sec_obj[i].collapsable = self.collapsable
            sec_obj[i].description = self.description
            sec_obj[i].description_icon = self.description_icon

        return {'FINISHED'}

    def invoke(self, context, event):

        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings
        sec_obj = rig_settings.body_custom_properties_sections

        self.name_edit = self.name
        self.ID = self.find_index_section(sec_obj, self.name)
        self.icon = sec_obj[self.ID].icon
        self.advanced = sec_obj[self.ID].advanced
        self.collapsable = sec_obj[self.ID].collapsable
        self.description = sec_obj[self.ID].description
        self.description_icon = sec_obj[self.ID].description_icon

        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):

        scale = 3.0

        layout = self.layout

        box = layout.box()

        row = box.row()
        row.label(text="Name:")
        row.scale_x = scale
        row.prop(self, "name_edit", text="")

        row = box.row()
        row.label(text="Icon:")
        row.scale_x = scale
        row.prop(self, "icon", text="")

        col = box.column()

        row = col.row()
        row.label(text="Advanced:")
        row.prop(self, "advanced", text="")

        row = col.row()
        row.label(text="Collapsable:")
        row.prop(self, "collapsable", text="")

        box = layout.box()

        row = box.row()
        row.label(text="Description:")
        row.scale_x = scale
        row.prop(self, "description", text="")

        row = box.row()
        row.enabled = self.description != ""
        row.label(text="Icon:")
        row.scale_x = scale
        row.prop(self, "description_icon", text="")


def register():
    bpy.utils.register_class(MustardUI_Body_SettingsSection)


def unregister():
    bpy.utils.unregister_class(MustardUI_Body_SettingsSection)
