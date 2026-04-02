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

        if arm is None:
            return False

        simplify_settings = arm.MustardUI_SimplifySettings
        if hasattr(simplify_settings, "simplify_main_enable"):
            return res and simplify_settings.simplify_main_enable
        else:
            return False

    def draw_header(self, context):
        poll, arm = mustardui_active_object(context, config=0)
        simplify_settings = arm.MustardUI_SimplifySettings
        self.layout.prop(simplify_settings, "simplify_enable", text="", toggle=False)

    def draw(self, context):

        settings = context.scene.MustardUI_Settings
        poll, obj = mustardui_active_object(context, config=0)

        rig_settings = obj.MustardUI_RigSettings
        morphs_settings = obj.MustardUI_MorphsSettings
        physics_settings = obj.MustardUI_PhysicsSettings
        simplify_settings = obj.MustardUI_SimplifySettings

        layout = self.layout
        layout.enabled = not simplify_settings.simplify_enable


        # Simplify Settings
        box = layout.box()
        box.label(text="Settings", icon="MODIFIER")
        col = box.column(align=True)
        row = col.row()
        row.prop(simplify_settings, "simplify_revert_settings")


        # Blender Simplify
        box = layout.box()
        box.label(text="Blender Simplify", icon="BLENDER")
        col = box.column(align=True)
        row = col.row()
        row.prop(simplify_settings, "simplify_blender")
        row.scale_x = 0.5
        col2 = row.column()
        col2.enabled = simplify_settings.simplify_blender
        col2.prop(context.scene.render, "simplify_subdivision", text="Max Subdiv")
        if rig_settings.outfits_enable_global_subsurface or rig_settings.body_enable_subdiv:
            col.prop(simplify_settings, "simplify_subdiv")


        # General Settings
        box = layout.box()
        box.label(text="General", icon="OUTLINER_OB_ARMATURE")
        col = box.column(align=True)
        row = col.row()

        if rig_settings.outfits_enable_global_subsurface or rig_settings.body_enable_subdiv:
            col.prop(simplify_settings, "simplify_subdiv")
        col.prop(simplify_settings, "simplify_normals_optimize")


        # Morphs
        if morphs_settings.enable_ui and ("DIFFEO_GENESIS" in morphs_settings.type or morphs_settings.enable_freeze_morphs):
            box = layout.box()
            box.label(text="Morphs", icon="SHAPEKEY_DATA")
            col = box.column(align=True)
            if "DIFFEO_GENESIS" in morphs_settings.type:
                col.prop(simplify_settings, "simplify_morphs")
            if morphs_settings.enable_freeze_morphs:
                row = col.column()
                row.enabled = not simplify_settings.simplify_morphs if "DIFFEO_GENESIS" in morphs_settings.type else True
                row.prop(simplify_settings, "simplify_morphs_freeze")


        # Outfits
        box = layout.box()
        box.label(text="Outfits", icon="MOD_CLOTH")
        col = box.column(align=True)

        col.prop(simplify_settings, "simplify_armature_child")

        if rig_settings.outfit_nude:
            col.prop(simplify_settings, "simplify_outfit_switch_nude")
        col.prop(simplify_settings, "simplify_extras")
        col.prop(simplify_settings, "simplify_outfit_global")


        # Hair
        box = layout.box()
        box.label(text="Hair", icon="OUTLINER_OB_CURVES")
        col = box.column(align=True)

        col.prop(simplify_settings, "simplify_hair")
        col.prop(simplify_settings, "simplify_hair_global")
        col.prop(simplify_settings, "simplify_particles")


        # Physics
        if settings.advanced or len(physics_settings.items) > 0:
            box = layout.box()
            box.label(text="Physics", icon="PHYSICS")
            col = box.column(align=True)
            if len(physics_settings.items) > 0:
                col.prop(simplify_settings, "simplify_physics")
            if settings.advanced:
                col.prop(simplify_settings, "simplify_force_no_physics")
                col.prop(simplify_settings, "simplify_force_no_particles")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_Simplify)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Simplify)
