import bpy

from .. import __package__ as base_package
from ..armature.ik_fk_snapper import ikfk_snapper_available
from ..model_selection.active_object import mustardui_active_object
from ..warnings.can_draw_ui import can_draw_ui
from . import MainPanel


class PANEL_PT_MustardUI_InitPanel_Armature(MainPanel, bpy.types.Panel):
    bl_label = "Armature"
    bl_parent_id = "PANEL_PT_MustardUI_InitPanel"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        if can_draw_ui():
            return False

        res, arm = mustardui_active_object(context, config=1)
        addon_prefs = context.preferences.addons[base_package].preferences
        return res and addon_prefs.developer

    def draw_header(self, context):
        layout = self.layout
        layout.label(text="", icon="ARMATURE_DATA")

    def draw(self, context):

        layout = self.layout

        res, arm = mustardui_active_object(context, config=1)
        armature_settings = arm.MustardUI_ArmatureSettings
        rig_settings = arm.MustardUI_RigSettings

        box = layout.box()
        box.label(text="General Settings", icon="MODIFIER")
        box.prop(armature_settings, "mirror")

        col = box.column()
        # IK/FK Snapper: only for a configured generic ("Other") rig.
        row = col.row()
        row.enabled = ikfk_snapper_available(arm)
        row.prop(armature_settings, "ikfk_snapper_enable")

        # Supported rigs: MHX
        row = col.row()
        row.enabled = rig_settings.model_rig_type == "mhx"
        row.prop(armature_settings, "rig_specific_panel")

        box = layout.box()
        row = box.row()
        row.label(text="Bone Collections", icon="BONE_DATA")
        row.operator("Mustardui.armature_smartcheck", text="", icon="SHADERFX")

        active_bcoll = arm.collections.active

        rows = 1
        if active_bcoll:
            rows = 4

        row = box.row()

        row.template_list(
            "MUSTARDUI_UL_Armature_UIList",
            "collections",
            arm,
            "collections",
            arm.collections,
            "active_index",
            rows=rows,
        )

        col = row.column(align=True)
        if active_bcoll:
            col.separator()
            col.operator(
                "armature.collection_move", icon="TRIA_UP", text=""
            ).direction = "UP"
            col.operator(
                "armature.collection_move", icon="TRIA_DOWN", text=""
            ).direction = "DOWN"
            col.separator()

        if arm.collections.active_index > -1:
            collections = arm.collections_all
            bcoll = collections[arm.collections.active_index]
            bcoll_settings = bcoll.MustardUI_ArmatureBoneCollection

            col = box.column(align=True)
            row = col.row()
            row.enabled = not bcoll_settings.outfit_switcher_enable
            row.prop(bcoll_settings, "icon")
            row = col.row()
            row.enabled = not bcoll_settings.outfit_switcher_enable
            row.prop(bcoll_settings, "advanced")
            row = col.row()
            row.enabled = not bcoll_settings.outfit_switcher_enable
            row.prop(bcoll_settings, "default")

            col = box.column(align=True)
            col.prop(bcoll_settings, "outfit_switcher_enable")
            if bcoll_settings.outfit_switcher_enable:
                col.prop(
                    bcoll_settings, "outfit_switcher_collection", text="Collection"
                )
                if bcoll_settings.outfit_switcher_collection is not None:
                    col.prop(bcoll_settings, "outfit_switcher_object", text="Object")

            if bcoll.children:
                box = layout.box()
                box.label(text="Children", icon="CON_CHILDOF")

                box.template_list(
                    "MUSTARDUI_UL_Armature_UIList_Children",
                    "collections_all",
                    bcoll,
                    "children",
                    context.scene,
                    "mustardui_armature_uilist_index",
                    rows=rows,
                )

                child = bcoll.children[context.scene.mustardui_armature_uilist_index]
                cbcoll_settings = child.MustardUI_ArmatureBoneCollection

                col = box.column(align=True)
                row = col.row()
                row.enabled = not cbcoll_settings.outfit_switcher_enable
                row.prop(cbcoll_settings, "icon")
                row = col.row()
                row.enabled = not cbcoll_settings.outfit_switcher_enable
                row.prop(cbcoll_settings, "advanced")
                row = col.row()
                row.enabled = not cbcoll_settings.outfit_switcher_enable
                row.prop(cbcoll_settings, "default")

                col = box.column(align=True)
                col.prop(cbcoll_settings, "outfit_switcher_enable")
                if cbcoll_settings.outfit_switcher_enable:
                    col.prop(
                        cbcoll_settings, "outfit_switcher_collection", text="Collection"
                    )
                    if cbcoll_settings.outfit_switcher_collection is not None:
                        col.prop(
                            cbcoll_settings, "outfit_switcher_object", text="Object"
                        )

        if armature_settings.ikfk_snapper_enable and ikfk_snapper_available(arm):
            self._draw_ikfk_config(layout, arm)

    def _draw_ikfk_config(self, layout, arm):
        snapper = arm.MustardUI_IKFKSnapperSettings
        chains = snapper.ikfk_chains

        box = layout.box()
        box.label(text="IK/FK Chains", icon="CONSTRAINT_BONE")
        box.operator(
            "mustardui.ikfk_detect", text="Auto-Detect from Rig", icon="FILE_REFRESH"
        )

        row = box.row()
        row.template_list(
            "MUSTARDUI_UL_IKFKChain_UIList",
            "",
            snapper,
            "ikfk_chains",
            snapper,
            "ikfk_chains_index",
            rows=3,
        )
        col = row.column(align=True)
        col.operator("mustardui.ikfk_chain_add", icon="ADD", text="")
        col.operator("mustardui.ikfk_chain_remove", icon="REMOVE", text="")

        if not chains or snapper.ikfk_chains_index >= len(chains):
            return

        chain = chains[snapper.ikfk_chains_index]

        b = box.box()
        b.label(text="IK Bones (comma-separated, root→end)", icon="BONE_DATA")
        b.prop(chain, "ik_bones", text="")

        b = box.box()
        b.label(text="FK Bones (same order as IK bones)", icon="BONE_DATA")
        b.prop(chain, "fk_bones", text="")

        b = box.box()
        b.label(text="IK Controls", icon="CONSTRAINT_BONE")
        col = b.column(align=True)
        col.prop_search(chain, "ik_ctrl", arm, "bones", text="IK Ctrl")
        col.prop_search(chain, "pole_ctrl", arm, "bones", text="Pole")
        col.prop(chain, "pole_distance")

        b = box.box()
        b.label(text="Bone Collections (shown per mode)", icon="GROUP_BONE")
        col = b.column(align=True)
        col.prop_search(chain, "ik_collection", arm, "collections_all", text="IK Layer")
        col.prop_search(chain, "fk_collection", arm, "collections_all", text="FK Layer")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_InitPanel_Armature)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_InitPanel_Armature)
