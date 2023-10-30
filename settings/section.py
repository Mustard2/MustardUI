import bpy
from bpy.props import *


# Section for body properties
class MustardUI_SectionItem(bpy.types.PropertyGroup):
    # Name of the section
    name: StringProperty(name="Section name")

    # Section ID
    id: IntProperty(name="Section ID")

    # Section icon
    icon: StringProperty(name="Section Icon",
                         default="NONE")

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
    description_icon: StringProperty(name="Description Icon",
                                     default="NONE")


def register():
    bpy.utils.register_class(MustardUI_SectionItem)


def unregister():
    bpy.utils.unregister_class(MustardUI_SectionItem)
