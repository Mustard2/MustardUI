import bpy

from ..misc.prop_utils import evaluate_rna
from ..misc.ui_multiline import label_multiline
from ..model_selection.active_object import active_object_operator_poll, mustardui_active_object
from ..warnings.can_draw_ui import can_draw_ui
from . import MainPanel


# Visible custom properties grouped by section name, "" for the ones with no section
def custom_properties_by_section(settings, custom_props):
    advanced = settings.advanced
    by_section = {}
    for prop in custom_props:
        if not prop.hidden and (advanced or not prop.advanced):
            by_section.setdefault(prop.section, []).append(prop)
    return by_section


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
    elif prop.prop_name in obj:
        row.prop(obj, f'["{bpy.utils.escape_identifier(prop.prop_name)}"]', text="")
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
    props_by_section,
    section,
    section_id,
    draw_sub=True,
):
    custom_properties_section = props_by_section.get(section.name, [])

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


class PANEL_PT_MustardUI_Model(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Model"
    bl_label = "Model"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        if can_draw_ui():
            return False

        return active_object_operator_poll(context, config=0)

    def draw(self, context):

        settings = bpy.context.scene.MustardUI_Settings

        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings
        props_by_section = custom_properties_by_section(settings, obj.MustardUI_CustomProperties)

        layout = self.layout

        box = layout.box()
        box.label(text="Global Settings", icon="MODIFIER_ON")

        col = box.column(align=True)

        row = col.row(align=True)
        row.scale_x = 0.94
        if context.scene.render.engine == "CYCLES" and settings.material_normal_nodes:
            row.alert = True
        row.prop(settings, "material_normal_nodes", text="")
        row.label(text="Eevee Optimized Normals")

        if rig_settings.body_enable_preserve_volume:
            col = box.column(align=True)
            col.prop(rig_settings, "body_preserve_volume")

        unsorted_props = props_by_section.get("", [])
        if len(unsorted_props) > 0:
            box = layout.box()

            row = box.row(align=False)
            row.label(text="Properties", icon="PROPERTIES")
            row.operator(
                "mustardui.section_property_default", text="", icon="LOOP_BACK"
            ).section_id = -1

            col = box.column(align=True)
            for prop in unsorted_props:
                draw_property(col, obj, settings, rig_settings, prop)

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
                props_by_section,
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
                    props_by_section,
                    subsec,
                    section_id,
                    subcollapse,
                )
                id = id + 1
                if id >= sec_num:
                    break
                subsec = rig_settings.body_custom_properties_sections[id]


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_Model)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Model)
