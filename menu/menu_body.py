import bpy
from . import MainPanel
from ..model_selection.active_object import *
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


class PANEL_PT_MustardUI_Body(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Body"
    bl_label = "Body"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):

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
                            or rig_settings.body_enable_preserve_volume)

            return res and (prop_to_show or len(custom_props) > 0)

        else:
            return res

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
                or rig_settings.body_enable_preserve_volume):

            box = layout.box()
            box.label(text="Global settings", icon="OUTLINER_OB_ARMATURE")

            if (rig_settings.body_enable_preserve_volume
                    or rig_settings.body_enable_solidify
                    or rig_settings.body_enable_smoothcorr):

                col = box.column(align=True)

                if rig_settings.body_enable_preserve_volume:
                    col.prop(rig_settings, "body_preserve_volume")

                if rig_settings.body_enable_smoothcorr:
                    col.prop(rig_settings, "body_smooth_corr")

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

            for i_sec in sorted([x for x in range(0, len(rig_settings.body_custom_properties_sections))],
                                key=lambda x: rig_settings.body_custom_properties_sections[x].id):
                section = rig_settings.body_custom_properties_sections[i_sec]
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
                        not section.advanced or (section.advanced and settings.advanced)):
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


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_Body)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Body)
