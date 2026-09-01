import bpy

from ..misc.prop_utils import evaluate_rna
from ..misc.ui_multiline import label_multiline
from ..model_selection.active_object import mustardui_active_object
from ..warnings.can_draw_ui import can_draw_ui
from . import MainPanel


def visible_custom_properties(settings, custom_props):
    return [
        x
        for x in custom_props
        if not x.hidden and (not x.advanced if not settings.advanced else True)
    ]


def draw_property(layout, obj, settings, rig_settings, prop):
    row = layout.row()

    if rig_settings.body_custom_properties_icons:
        row.label(text=prop.name, icon=prop.icon if prop.icon != "NONE" else "DOT")
    else:
        row.label(text=prop.name)

    if not prop.is_animatable:
        try:
            row.prop(evaluate_rna(prop.rna), prop.path, text="")
        except Exception:
            row.prop(
                settings,
                "custom_properties_error_nonanimatable",
                icon="ERROR",
                text="",
                icon_only=True,
                emboss=False,
            )
    elif prop.prop_name in obj.keys():
        row.prop(obj, f'["{prop.prop_name}"]', text="")
    else:
        row.prop(
            settings,
            "custom_properties_error",
            icon="ERROR",
            text="",
            icon_only=True,
            emboss=False,
        )


def draw_section(
    context,
    layout,
    obj,
    settings,
    rig_settings,
    custom_props,
    section,
    section_id,
    draw_sub=True,
):
    custom_properties_section = [
        x for x in visible_custom_properties(settings, custom_props) if x.section == section.name
    ]

    if rig_settings.body_custom_properties_name_order:
        custom_properties_section = sorted(custom_properties_section, key=lambda x: x.name)

    if (
        len(custom_properties_section) > 0
        and (not section.advanced or (section.advanced and settings.advanced))
        and draw_sub
    ):
        box = layout

        # Header
        row = layout.row(align=False)
        if section.collapsable:
            row.prop(
                section,
                "collapsed",
                icon="DOWNARROW_HLT" if not section.collapsed else "RIGHTARROW",
                icon_only=True,
                emboss=False,
            )
        if section.icon != "" and section.icon != "NONE":
            row.label(text=section.name, icon=section.icon)
        else:
            row.label(text=section.name)
        row.operator(
            "mustardui.section_property_default", text="", icon="LOOP_BACK"
        ).section_id = section_id

        # Properties
        if not section.collapsed:
            box = layout.box()
            if section.description != "":
                box2 = box.box()
                label_multiline(
                    context=context,
                    text=section.description,
                    parent=box2,
                    icon=section.description_icon,
                )
            for prop in custom_properties_section:
                draw_property(box, obj, settings, rig_settings, prop)

        return box, not section.collapsed

    return layout, False


class PANEL_PT_MustardUI_Properties(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Properties"
    bl_label = "Properties"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):

        if can_draw_ui():
            return False

        settings = bpy.context.scene.MustardUI_Settings

        res, arm = mustardui_active_object(context, config=0)

        if arm is not None:
            custom_props = visible_custom_properties(settings, arm.MustardUI_CustomProperties)
            return res and len(custom_props) > 0

        return False

    def draw(self, context):

        settings = bpy.context.scene.MustardUI_Settings

        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings
        custom_props = obj.MustardUI_CustomProperties

        layout = self.layout

        unsorted_props = [
            x for x in visible_custom_properties(settings, custom_props) if x.section == ""
        ]
        if len(unsorted_props) > 0:
            box = layout.box()
            box.label(text="Un-sorted properties", icon="LIBRARY_DATA_BROKEN")
            for prop in unsorted_props:
                draw_property(box, obj, settings, rig_settings, prop)

        sec_num = len(rig_settings.body_custom_properties_sections)
        id = 0
        for section_id, section in enumerate(rig_settings.body_custom_properties_sections):
            # Subsections are drawn inside standard sections
            if section.is_subsection:
                continue

            # Draw main section
            sublayout, subcollapse = draw_section(
                context,
                layout,
                obj,
                settings,
                rig_settings,
                custom_props,
                section,
                section_id,
            )

            # Draw subsections if available
            id = id + 1
            if id >= sec_num:
                break

            subsec = rig_settings.body_custom_properties_sections[id]
            while subsec.is_subsection:
                draw_section(
                    context,
                    sublayout,
                    obj,
                    settings,
                    rig_settings,
                    custom_props,
                    subsec,
                    section_id,
                    subcollapse,
                )
                id = id + 1
                if id >= sec_num:
                    break
                subsec = rig_settings.body_custom_properties_sections[id]


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_Properties)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Properties)
