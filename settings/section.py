import bpy
from bpy.props import *
from ..misc.icons_list import mustardui_icon_list


# Section for body properties
class MustardUI_SectionItem(bpy.types.PropertyGroup):
    # Name of the section
    name: StringProperty(name="Section name")

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
                                default=False)


def register():
    bpy.utils.register_class(MustardUI_SectionItem)


def unregister():
    bpy.utils.unregister_class(MustardUI_SectionItem)
