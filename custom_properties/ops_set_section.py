import bpy
from bpy.props import EnumProperty, IntProperty

from ..model_selection.active_object import (
    active_object_operator_poll,
    mustardui_active_object,
)

# Identifier used for the entry that removes the property from every section
SECTION_NONE = "MUSTARDUI_SECTION_NONE"

# Blender does not keep a reference to the strings returned by an EnumProperty items
# callback, therefore they are stored here to avoid them being garbage collected
sections_enum_items = []


def sections_enum(self, context):
    sections_enum_items.clear()
    sections_enum_items.append(
        (SECTION_NONE, "No Section", "Remove the property from any section", "RECORD_OFF", 0)
    )

    res, arm = mustardui_active_object(context, config=1)
    if res:
        rig_settings = arm.MustardUI_RigSettings
        for i, section in enumerate(rig_settings.body_custom_properties_sections):
            sections_enum_items.append(
                (
                    section.name,
                    section.name,
                    "Add the property to this section",
                    section.icon if section.icon not in {"NONE", ""} else "DOT",
                    i + 1,
                )
            )

    return sections_enum_items


class MustardUI_Property_SetSection(bpy.types.Operator):
    """Change the section of the property"""

    bl_idname = "mustardui.property_set_section"
    bl_label = "Section"
    bl_options = {"UNDO", "INTERNAL"}

    index: IntProperty(default=-1, options={"HIDDEN"})
    section: EnumProperty(name="Section", items=sections_enum)

    @classmethod
    def poll(cls, context):
        return active_object_operator_poll(context, config=1)

    def execute(self, context):
        res, arm = mustardui_active_object(context, config=1)
        custom_props = arm.MustardUI_CustomProperties

        if not 0 <= self.index < len(custom_props):
            self.report({"ERROR"}, "MustardUI - Can not find the property to modify")
            return {"CANCELLED"}

        custom_props[self.index].section = "" if self.section == SECTION_NONE else self.section

        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_Property_SetSection)


def unregister():
    bpy.utils.unregister_class(MustardUI_Property_SetSection)
