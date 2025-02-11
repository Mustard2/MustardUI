import bpy
from . import MainPanel
from ..model_selection.active_object import *
from ..warnings.ops_fix_old_UI import check_old_UI
from .. import __package__ as base_package


class PANEL_PT_MustardUI_ToolsCreators(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_ToolsCreators"
    bl_label = "Creator Tools"

    @classmethod
    def poll(cls, context):
        if check_old_UI():
            return False

        res, arm = mustardui_active_object(context, config=1)
        addon_prefs = context.preferences.addons[base_package].preferences
        return res and addon_prefs.developer

    def draw(self, context):

        layout = self.layout

        box = layout.box()
        box.label(text="Physics", icon="PHYSICS")
        row = box.row(align=True)
        row.operator('mustardui.tools_creators_create_jiggle', text="Add Jiggle Cage", icon="MESH_UVSPHERE")
        row = box.row(align=True)
        row.operator('mustardui.tools_creators_create_collision_cage', text="Create Collision Cage", icon="MESH_UVSPHERE")
        row = box.row(align=True)
        row.operator('mustardui.tools_creators_hair_cage', text="Create Hair Cage", icon="OUTLINER_OB_CURVES")
        row.operator('mustardui.tools_creators_add_cloth_to_hair', text="", icon="MOD_CLOTH")

        box = layout.box()
        box.label(text="Rig", icon="OUTLINER_DATA_ARMATURE")
        row = box.row(align=True)
        row.operator('mustardui.tools_creators_ikspline', text="Create IK Spline", icon="CON_SPLINEIK")
        row.operator('mustardui.tools_creators_ikspline_clean', text="", icon="X")
        row = box.row(align=True)
        row.operator('mustardui.tools_creators_affect_transform', text="Affect Transform on Bone Constraints", icon="CONSTRAINT_BONE").enable = True
        row.operator('mustardui.tools_creators_affect_transform', text="", icon="X").enable = False


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_ToolsCreators)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ToolsCreators)
