import bpy
from . import MainPanel
from ..model_selection.active_object import *
from ..warnings.ops_fix_old_UI import check_old_UI
from ..settings.rig import *
import textwrap


def _label_multiline(context, text, parent, icon):
    chars = int(context.region.width / 7)  # 7 pix on 1 character
    wrapper = textwrap.TextWrapper(width=chars)
    text_lines = wrapper.wrap(text=text)
    if icon in ["", "NONE"]:
        for i, text_line in enumerate(text_lines):
            parent.label(text=text_line)
    else:

        for i, text_line in enumerate(text_lines):
            if not i:
                parent.label(text=text_line, icon=icon)
            else:
                parent.label(text=text_line, icon="BLANK1")


def draw_section(context, layout, obj, settings, rig_settings, custom_props, section, draw_sub = True):
    if rig_settings.body_custom_properties_name_order:
        custom_properties_section = sorted([x for x in custom_props if
                                            x.section == section.name and not x.hidden and (
                                                not x.advanced if not settings.advanced else True)],
                                           key=lambda x: x.name)
    else:
        custom_properties_section = [x for x in custom_props if
                                     x.section == section.name and not x.hidden and (
                                         not x.advanced if not settings.advanced else True)]
    if len(custom_properties_section) > 0 and (
            not section.advanced or (section.advanced and settings.advanced)) and draw_sub:
        box = layout.box()
        row = box.row(align=False)
        if section.collapsable:
            row.prop(section, "collapsed",
                     icon="TRIA_DOWN" if not section.collapsed else "TRIA_RIGHT",
                     icon_only=True,
                     emboss=False)
        if section.icon != "" and section.icon != "NONE":
            row.label(text=section.name, icon=section.icon)
        else:
            row.label(text=section.name)
        if not section.collapsed:
            if section.description != "":
                box2 = box.box()
                _label_multiline(context=context, text=section.description, parent=box2,
                                 icon=section.description_icon)
            for prop in custom_properties_section:
                row = box.row()
                if rig_settings.body_custom_properties_icons:
                    row.label(text=prop.name, icon=prop.icon if prop.icon != "NONE" else "DOT")
                else:
                    row.label(text=prop.name)
                if not prop.is_animatable:
                    try:
                        row.prop(eval(prop.rna), prop.path, text="")
                    except:
                        row.prop(settings, 'custom_properties_error_nonanimatable', icon="ERROR", text="",
                                 icon_only=True, emboss=False)
                else:
                    if prop.prop_name in obj.keys():
                        row.prop(obj, '["' + prop.prop_name + '"]', text="")
                    else:
                        row.prop(settings, 'custom_properties_error', icon="ERROR", text="", icon_only=True,
                                 emboss=False)

        return box, not section.collapsed

    return layout, False


class PANEL_PT_MustardUI_Body(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Body"
    bl_label = "Body"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):

        if check_old_UI():
            return False

        res, arm = mustardui_active_object(context, config=0)

        if arm is not None:
            rig_settings = arm.MustardUI_RigSettings
            custom_props = arm.MustardUI_CustomProperties

            # Check if there is any property to show
            prop_to_show = (rig_settings.body_enable_subdiv
                            or rig_settings.body_enable_smoothcorr
                            or rig_settings.body_enable_solidify
                            or rig_settings.body_enable_norm_autosmooth
                            or rig_settings.body_enable_material_normal_nodes
                            or rig_settings.body_enable_preserve_volume
                            or rig_settings.body_enable_geometry_nodes)

            # Check if geometry nodes support is active and there are geometry nodes on the body object
            geometry_nodes_support = False
            if rig_settings.model_body is not None and rig_settings.body_enable_geometry_nodes_support:
                geometry_nodes_support = len([x for x in rig_settings.model_body.modifiers if x.type == "NODES"]) > 0

            return res and (prop_to_show or len(custom_props) > 0 or geometry_nodes_support)

        return False

    def draw(self, context):

        settings = bpy.context.scene.MustardUI_Settings

        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings
        custom_props = obj.MustardUI_CustomProperties

        layout = self.layout

        if (rig_settings.body_enable_smoothcorr
            or rig_settings.body_enable_solidify
            or rig_settings.body_enable_norm_autosmooth
            or rig_settings.body_enable_material_normal_nodes
            or rig_settings.body_enable_preserve_volume
            or rig_settings.body_enable_geometry_nodes):

            box = layout.box()
            box.label(text="Global settings", icon="OUTLINER_OB_ARMATURE")

            if (rig_settings.body_enable_preserve_volume
                or rig_settings.body_enable_geometry_nodes
                or rig_settings.body_enable_solidify
                or rig_settings.body_enable_smoothcorr):

                col = box.column(align=True)

                if rig_settings.body_enable_preserve_volume:
                    col.prop(rig_settings, "body_preserve_volume")

                if rig_settings.body_enable_smoothcorr:
                    col.prop(rig_settings, "body_smooth_corr")

                if rig_settings.body_enable_geometry_nodes:
                    col.prop(rig_settings, "body_geometry_nodes")

                if rig_settings.body_enable_solidify:
                    col.prop(rig_settings, "body_solidify")

            if rig_settings.body_enable_norm_autosmooth or rig_settings.body_enable_material_normal_nodes:
                col = box.column(align=True)

                if rig_settings.body_enable_norm_autosmooth:
                    col.prop(rig_settings, "body_norm_autosmooth")

                if rig_settings.body_enable_material_normal_nodes:
                    row = col.row(align=True)
                    row.scale_x = 0.94
                    if context.scene.render.engine == "CYCLES" and settings.material_normal_nodes:
                        row.alert = True
                    row.prop(settings, "material_normal_nodes", text="")
                    row.label(text="Eevee Optimized Normals")

        if rig_settings.body_enable_subdiv:
            box = layout.box()

            box.label(text="Subdivision surface", icon="MOD_SUBSURF")

            col = box.column(align=True)

            row = col.row(align=True)
            row.prop(rig_settings, "body_subdiv_view", text="Viewport")
            row.scale_x = 0.7
            row.prop(rig_settings, "body_subdiv_view_lv")

            row = col.row(align=True)
            row.prop(rig_settings, "body_subdiv_rend", text="Render")
            row.scale_x = 0.7
            row.prop(rig_settings, "body_subdiv_rend_lv")

        if len(custom_props) > 0:

            unsorted_props = [x for x in custom_props if x.section == ""]
            if len(unsorted_props) > 0:
                box = layout.box()
                box.label(text="Un-sorted properties", icon="LIBRARY_DATA_BROKEN")
                for prop in [x for x in custom_props if
                             x.section == "" and not x.hidden and (not x.advanced if not settings.advanced else True)]:
                    row = box.row()
                    if rig_settings.body_custom_properties_icons:
                        row.label(text=prop.name, icon=prop.icon if prop.icon != "NONE" else "DOT")
                    else:
                        row.label(text=prop.name)
                    if not prop.is_animatable:
                        try:
                            row.prop(eval(prop.rna), prop.path, text="")
                        except:
                            row.prop(settings, 'custom_properties_error_nonanimatable', icon="ERROR", text="",
                                     icon_only=True, emboss=False)
                    else:
                        if prop.prop_name in obj.keys():
                            row.prop(obj, '["' + prop.prop_name + '"]', text="")
                        else:
                            row.prop(settings, 'custom_properties_error', icon="ERROR", text="", icon_only=True,
                                     emboss=False)

            sec_num = len(rig_settings.body_custom_properties_sections)
            id = 0
            for section in rig_settings.body_custom_properties_sections:

                # Subsections are drawn inside standard sections
                if section.is_subsection:
                    continue

                # Draw main section
                sublayout, subcollapse = draw_section(context, layout, obj, settings, rig_settings, custom_props, section)

                # Draw subsections if available
                id = id + 1
                if id >= sec_num:
                    break

                subsec = rig_settings.body_custom_properties_sections[id]
                while subsec.is_subsection:
                    draw_section(context, sublayout, obj, settings, rig_settings, custom_props, subsec, subcollapse)
                    id = id + 1
                    if id >= sec_num:
                        break
                    subsec = rig_settings.body_custom_properties_sections[id]

        # Geometry nodes as sections
        gnm = [x for x in rig_settings.model_body.modifiers if x.type == "NODES"]

        if len(gnm) > 0 and rig_settings.body_enable_geometry_nodes_support:
            for m in gnm:
                gndi = m.node_group.interface.items_tree
                if gndi is None:
                    continue

                if len(gndi.keys()):
                    box = layout.box()
                    row = box.row()
                    row.prop(m.node_group, "MustardUI_collapse",
                             icon="TRIA_DOWN" if not m.node_group.MustardUI_collapse else "TRIA_RIGHT",
                             icon_only=True,
                             emboss=False)
                    row.label(text=m.node_group.name)
                    row.label(icon="GEOMETRY_NODES")
                    row2 = row.row(align=True)
                    row2.prop(m, "show_viewport", text="")
                    row2.prop(m, "show_render", text="")
                    if not m.node_group.MustardUI_collapse:
                        for i in [x for x in gndi.items() if hasattr(gndi[x[0]], 'identifier')]:
                            if i[1].identifier in m.keys():
                                box.prop(m, '["' + i[1].identifier + '"]', text=i[0])


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_Body)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Body)
