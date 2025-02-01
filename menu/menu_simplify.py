import bpy
from . import MainPanel
from ..model_selection.active_object import *
from ..warnings.ops_fix_old_UI import check_old_UI
from ..settings.rig import *


class PANEL_PT_MustardUI_Simplify(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Simplify"
    bl_label = "Simplify"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):

        if check_old_UI():
            return False

        res, arm = mustardui_active_object(context, config=0)

        if arm is not None:
            rig_settings = arm.MustardUI_RigSettings
            if hasattr(rig_settings, "simplify_main_enable"):
                return res and rig_settings.simplify_main_enable
            else:
                return False

        return res

    def draw_header(self, context):

        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings

        self.layout.prop(rig_settings, "simplify_enable", text="", toggle=False)

    def draw(self, context):

        settings = bpy.context.scene.MustardUI_Settings
        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings
        physics_settings = obj.MustardUI_PhysicsSettings

        layout = self.layout
        layout.enabled = not rig_settings.simplify_enable

        box = layout.box()
        box.label(text="General", icon="OPTIONS")
        col = box.column(align=True)
        row = col.row()
        row.prop(rig_settings, "simplify_blender")
        row.scale_x = 0.5
        col2 = row.column()
        col2.enabled = rig_settings.simplify_blender
        col2.prop(context.scene.render, "simplify_subdivision", text="Max Subdiv")
        if rig_settings.outfits_enable_global_subsurface or rig_settings.body_enable_subdiv:
            col.prop(rig_settings, "simplify_subdiv")
        if rig_settings.outfits_enable_global_normalautosmooth or rig_settings.body_enable_norm_autosmooth:
            col.prop(rig_settings, "simplify_normals_autosmooth")
        col.prop(rig_settings, "simplify_normals_optimize")

        box = layout.box()
        box.label(text="Objects", icon="OUTLINER_OB_ARMATURE")
        col = box.column(align=True)
        if rig_settings.diffeomorphic_support:
            col.prop(rig_settings, "simplify_diffeomorphic")
        if rig_settings.outfit_nude:
            col.prop(rig_settings, "simplify_outfit_switch_nude")
        col.prop(rig_settings, "simplify_outfit_global")
        col.prop(rig_settings, "simplify_extras")
        col.prop(rig_settings, "simplify_armature_child")
        col.separator()
        col.prop(rig_settings, "simplify_hair")
        col.prop(rig_settings, "simplify_hair_global")
        col.prop(rig_settings, "simplify_particles")

        if len(physics_settings.items) > 0:
            col.separator()
            col.prop(rig_settings, "simplify_physics")

        if settings.advanced:
            box = layout.box()
            box.label(text="Global Disable", icon="WORLD")
            col = box.column(align=True)
            col.prop(rig_settings, "simplify_force_no_physics")
            col.prop(rig_settings, "simplify_force_no_particles")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_Simplify)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Simplify)
