import bpy

from ..misc.geometry_nodes import (
    draw_geometry_nodes_modifier_inputs,
    geometry_nodes_modifier_inputs,
)
from ..model_selection.active_object import mustardui_active_object
from ..warnings.can_draw_ui import can_draw_ui
from . import MainPanel


class PANEL_PT_MustardUI_Body(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Body"
    bl_label = "Body"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):

        if can_draw_ui():
            return False

        res, arm = mustardui_active_object(context, config=0)

        if arm is None:
            return False

        rig_settings = arm.MustardUI_RigSettings

        # Check if there is any property to show
        prop_to_show = (
            rig_settings.body_enable_subdiv
            or rig_settings.body_enable_smoothcorr
            or rig_settings.body_enable_solidify
            or rig_settings.body_enable_material_normal_nodes
            or rig_settings.body_enable_preserve_volume
            or rig_settings.body_enable_geometry_nodes
        )

        # Check if geometry nodes support is active and there are geometry nodes
        # on the body object
        geometry_nodes_support = False
        if rig_settings.model_body is not None and rig_settings.body_enable_geometry_nodes_support:
            geometry_nodes_support = (
                len([x for x in rig_settings.model_body.modifiers if x.type == "NODES"]) > 0
            )

        return res and (prop_to_show or geometry_nodes_support)

    def draw(self, context):

        settings = bpy.context.scene.MustardUI_Settings

        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings

        layout = self.layout

        if (
            rig_settings.body_enable_smoothcorr
            or rig_settings.body_enable_solidify
            or rig_settings.body_enable_material_normal_nodes
            or rig_settings.body_enable_preserve_volume
            or rig_settings.body_enable_geometry_nodes
        ):
            box = layout.box()
            box.label(text="Global settings", icon="OUTLINER_OB_ARMATURE")

            if (
                rig_settings.body_enable_preserve_volume
                or rig_settings.body_enable_geometry_nodes
                or rig_settings.body_enable_solidify
                or rig_settings.body_enable_smoothcorr
            ):
                col = box.column(align=True)

                if rig_settings.body_enable_preserve_volume:
                    col.prop(rig_settings, "body_preserve_volume")

                if rig_settings.body_enable_smoothcorr:
                    col.prop(rig_settings, "body_smooth_corr")

                if rig_settings.body_enable_geometry_nodes:
                    col.prop(rig_settings, "body_geometry_nodes")

                if rig_settings.body_enable_solidify:
                    col.prop(rig_settings, "body_solidify")

            if rig_settings.body_enable_material_normal_nodes:
                col = box.column(align=True)

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

        # Geometry nodes as sections
        if rig_settings.model_body is None:
            return

        gnm = [x for x in rig_settings.model_body.modifiers if x.type == "NODES"]

        if len(gnm) > 0 and rig_settings.body_enable_geometry_nodes_support:
            for m in gnm:
                if m.node_group is None:
                    continue

                gndi = m.node_group.interface.items_tree
                if gndi is None:
                    continue

                if len(gndi.keys()):
                    row = layout.row()
                    arrow = row.column(align=True)
                    arrow.prop(
                        m.node_group,
                        "MustardUI_collapse",
                        icon=(
                            "DOWNARROW_HLT" if not m.node_group.MustardUI_collapse else "RIGHTARROW"
                        ),
                        icon_only=True,
                        emboss=False,
                    )
                    row.label(text=m.node_group.name)
                    row.label(icon="GEOMETRY_NODES")

                    row2 = row.row(align=True)
                    row2.prop(m, "show_viewport", text="")
                    row2.prop(m, "show_render", text="")

                    drawable = geometry_nodes_modifier_inputs(m)
                    arrow.enabled = bool(drawable)
                    if not m.node_group.MustardUI_collapse:
                        if drawable:
                            box = layout.box()
                            draw_geometry_nodes_modifier_inputs(box, drawable)


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_Body)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Body)
