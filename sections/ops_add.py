import bpy
from bpy.props import *
from ..model_selection.active_object import *
from ..misc.icons_list import mustardui_icon_list


class MustardUI_Body_AddSection(bpy.types.Operator):
    """Add a new Section"""
    bl_idname = "mustardui.body_addsection"
    bl_label = "Add Section"
    bl_icon = "PREFERENCES"
    bl_options = {'UNDO'}

    name: StringProperty(name='Name',
                         description="Name of the Section",
                         default="Section")
    icon: EnumProperty(name='Icon',
                       items=mustardui_icon_list)
    advanced: BoolProperty(default=False,
                           name="Advanced",
                           description="The section will be shown only when Advances Settings is enabled")
    collapsable: BoolProperty(default=False,
                              name="Collapsable",
                              description="Add a collapse icon to the section.\nNote that this might give bad UI "
                                          "results if combined with an icon")
    description: StringProperty(name='',
                                description="Description of the Section.\nLeave blank to remove description",
                                default="")
    description_icon: EnumProperty(name='Description Icon',
                                   items=mustardui_icon_list)

    @classmethod
    def poll(cls, context):

        res, arm = mustardui_active_object(context, config=1)
        return res

    def execute(self, context):

        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings

        sec_obj = rig_settings.body_custom_properties_sections
        sec_len = len(rig_settings.body_custom_properties_sections)

        if self.name == "":
            self.report({'ERROR'}, 'MustardUI - Cannot create sections with this name.')
            return {'FINISHED'}

        j = -1
        for el in sec_obj:
            j = j + 1
            if el.name == self.name:
                self.report({'WARNING'}, 'MustardUI - Cannot create sections with same name.')
                return {'FINISHED'}

        add_item = sec_obj.add()
        add_item.name = self.name
        add_item.description = self.description
        add_item.description_icon = self.description_icon
        add_item.icon = self.icon
        add_item.advanced = self.advanced
        add_item.collapsable = self.collapsable
        add_item.id = sec_len

        self.report({'INFO'}, 'MustardUI - Section \'' + self.name + '\' created.')

        return {'FINISHED'}

    def invoke(self, context, event):

        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):

        layout = self.layout

        scale = 3.0

        box = layout.box()

        row = box.row()
        row.label(text="Name:")
        row.scale_x = scale
        row.prop(self, "name", text="")

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
    bpy.utils.register_class(MustardUI_Body_AddSection)


def unregister():
    bpy.utils.unregister_class(MustardUI_Body_AddSection)
