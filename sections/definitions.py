import bpy
from bpy.props import BoolProperty, EnumProperty, StringProperty

from ..misc.icons import mustardui_icon_list


# Section for body properties
class MustardUI_SectionItem(bpy.types.PropertyGroup):
    # Name of the section

    # Fix for #148 - https://github.com/Mustard2/MustardUI/issues/148
    # Custom properties store their Section as a name, so renaming a Section would leave
    # them dangling. The name lives in the "name" ID property: inside the setter that
    # still holds the previous name, which is the one to move the custom properties from
    def name_get(self):
        return self.get("name", "")

    def name_set(self, value):
        old_name = self.get("name", "")

        if old_name and old_name != value:
            for cp in self.id_data.MustardUI_CustomProperties:
                if cp.section == old_name:
                    cp.section = value

        self["name"] = value

    name: StringProperty(name="Section name", get=name_get, set=name_set)

    # Section icon
    icon: EnumProperty(name="Section Icon", items=mustardui_icon_list)

    # Advanced settings
    advanced: BoolProperty(
        default=False,
        name="Advanced",
        description="The section will be shown only when Advances Settings is enabled",
    )

    # Collapsable
    collapsable: BoolProperty(
        default=True,
        name="Collapsable",
        description="Add a collapse icon to the section.\nNote that this might give "
        "bad UI results if combined with an icon",
    )
    collapsed: BoolProperty(name="", default=False)

    # Description
    description: StringProperty(name="Description")

    description_icon: EnumProperty(name="Description Icon", items=mustardui_icon_list)

    # Subsection
    is_subsection: BoolProperty(
        name="Sub-section",
        description="Consider this Section as a sub-section of the first section above "
        "not flagged as sub-section.\nSubsections are shown in the parent section",
        default=False,
    )


def register():
    bpy.utils.register_class(MustardUI_SectionItem)


def unregister():
    bpy.utils.unregister_class(MustardUI_SectionItem)
