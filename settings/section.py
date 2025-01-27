import bpy
from bpy.props import *

from ..model_selection.active_object import mustardui_active_object
from ..misc.icons_list import mustardui_icon_list


# Section for body properties
class MustardUI_SectionItem(bpy.types.PropertyGroup):
    # Name of the section

    # Fix for #148 - https://github.com/Mustard2/MustardUI/issues/148
    # The update function is to avoid dangling section strings on custom properties,
    # storing the old name to check if the section name in the cp should be changed
    old_name: StringProperty(default="")

    def name_update(self, context):
        res, arm = mustardui_active_object(context, config=1)
        custom_props = arm.MustardUI_CustomProperties

        for cp in custom_props:
            if cp.section == self.old_name:
                cp.section = self.name

        self.old_name = self.name

    name: StringProperty(name="Section name",
                         update=name_update)

    # Section icon
    icon: EnumProperty(name='Section Icon',
                       items=mustardui_icon_list)

    # Advanced settings
    advanced: BoolProperty(default=False,
                           name="Advanced",
                           description="The section will be shown only when Advances Settings is enabled")

    # Collapsable
    collapsable: BoolProperty(default=True,
                              name="Collapsable",
                              description="Add a collapse icon to the section.\nNote that this might give bad UI "
                                          "results if combined with an icon")
    collapsed: BoolProperty(name="",
                            default=False)

    # Description
    description: StringProperty(name="Description")

    description_icon: EnumProperty(name='Description Icon',
                                   items=mustardui_icon_list)

    # Subsection
    is_subsection: BoolProperty(name="Sub-section",
                                description="Consider this Section as a sub-section of the first section above not flagged as sub-section.\nSubsections are shown in the parent section",
                                default=False)


def register():
    bpy.utils.register_class(MustardUI_SectionItem)


def unregister():
    bpy.utils.unregister_class(MustardUI_SectionItem)
