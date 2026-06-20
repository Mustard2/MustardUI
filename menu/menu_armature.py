import bpy

from ..armature.ik_fk_snapper import ikfk_snapper_available
from ..misc.mirror import check_mirror
from ..model_selection.active_object import mustardui_active_object
from ..warnings.can_draw_ui import can_draw_ui
from . import MainPanel


def draw_armature_button(bcoll, bcoll_settings, bcolls, armature_settings, layout, is_solo_enabled):

    def draw_with_icon(layout, prop, prop_name, name, icon, enabled=True):

        row = layout.row(align=True)
        row.enabled = enabled
        if prop.children:
            show_children = prop.MustardUI_ArmatureBoneCollection.show_children
            row.prop(
                prop.MustardUI_ArmatureBoneCollection,
                "show_children",
                toggle=True,
                icon="TRIA_DOWN" if show_children else "TRIA_RIGHT",
            )

        if icon != "NONE":
            row.prop(prop, prop_name, text=name, toggle=True, icon=icon)
        else:
            row.prop(prop, prop_name, text=name, toggle=True)

    def draw_children(layout, bcoll):
        if bcoll.children and bcoll.MustardUI_ArmatureBoneCollection.show_children:
            for c in bcoll.children:
                row = layout.row(align=True)
                row.label(icon="BLANK1")
                draw_with_icon(
                    row,
                    c,
                    "is_visible",
                    c.name,
                    c.MustardUI_ArmatureBoneCollection.icon,
                )

    if not armature_settings.mirror:
        row = layout.row()
        draw_with_icon(row, bcoll, "is_visible", bcoll.name, bcoll_settings.icon)
        draw_children(layout, bcoll)
        return

    for b in bcolls:
        if check_mirror(bcoll.name, b.name, left=True):
            col = layout.column()
            row = col.row(align=True)
            draw_with_icon(
                row,
                bcoll,
                "is_visible",
                bcoll.name,
                bcoll_settings.icon,
                is_solo_enabled,
            )
            draw_with_icon(row, bcoll, "is_solo", "", "SOLO_ON" if bcoll.is_solo else "SOLO_OFF")

            row.separator()

            r_icon = b.MustardUI_ArmatureBoneCollection.icon
            draw_with_icon(row, b, "is_visible", b.name, r_icon, is_solo_enabled)
            draw_with_icon(row, b, "is_solo", "", "SOLO_ON" if b.is_solo else "SOLO_OFF")
            return
        elif check_mirror(bcoll.name, b.name, left=False):
            return

    row = layout.row(align=True)
    draw_with_icon(row, bcoll, "is_visible", bcoll.name, bcoll_settings.icon, is_solo_enabled)
    draw_with_icon(row, bcoll, "is_solo", "", "SOLO_ON" if bcoll.is_solo else "SOLO_OFF")

    draw_children(layout, bcoll)


class PANEL_PT_MustardUI_Armature(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Armature"
    bl_label = "Armature"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):

        if can_draw_ui():
            return False

        res, obj = mustardui_active_object(context, config=0)

        if obj is None:
            return res

        rig_settings = obj.MustardUI_RigSettings
        armature_settings = obj.MustardUI_ArmatureSettings
        bcolls = obj.collections_all

        if len(bcolls) < 1:
            return False

        enabled_colls = [x for x in bcolls if x.MustardUI_ArmatureBoneCollection.is_in_UI]

        if rig_settings.hair_collection is not None:
            return res and (
                len(enabled_colls) > 0
                or (
                    len([x for x in rig_settings.hair_collection.objects if x.type == "ARMATURE"])
                    > 1
                    and armature_settings.enable_automatic_hair
                )
            )
        else:
            return res and len(enabled_colls) > 0

    def draw_header(self, context):
        poll, obj = mustardui_active_object(context, config=0)
        armature_settings = obj.MustardUI_ArmatureSettings

        self.layout.prop(armature_settings, "show_viewport", text="", toggle=False)

    def draw(self, context):

        settings = bpy.context.scene.MustardUI_Settings
        poll, obj = mustardui_active_object(context, config=0)
        armature_settings = obj.MustardUI_ArmatureSettings
        rig_settings = obj.MustardUI_RigSettings

        bcolls = obj.collections

        enabled_colls = [x for x in bcolls if x.MustardUI_ArmatureBoneCollection.is_in_UI]
        is_solo_enabled = not any([x.is_solo for x in bcolls])

        layout = self.layout

        col = layout.column()
        col.enabled = is_solo_enabled
        draw_separator = False
        if rig_settings.hair_collection is not None and armature_settings.enable_automatic_hair:
            if len([x for x in rig_settings.hair_collection.objects if x.type == "ARMATURE"]) > 0:
                col.prop(armature_settings, "hair", toggle=True, icon="CURVES")
                draw_separator = True

        if len(rig_settings.outfits_list) > 0:
            if len(
                [x for x in bcolls if x.MustardUI_ArmatureBoneCollection.outfit_switcher_enable]
            ):
                col.prop(armature_settings, "outfits", toggle=True, icon="MOD_CLOTH")
                draw_separator = True

        if draw_separator:
            layout.separator()

        layout.use_property_split = False
        layout.use_property_decorate = True

        for bcoll in enabled_colls:
            bcoll_settings = bcoll.MustardUI_ArmatureBoneCollection
            if (bcoll_settings.advanced and settings.advanced) or not bcoll_settings.advanced:
                draw_armature_button(
                    bcoll,
                    bcoll_settings,
                    enabled_colls,
                    armature_settings,
                    layout,
                    is_solo_enabled,
                )

        layout.separator()
        layout.operator(
            "mustardui.armature_reset_bcoll",
            icon="LOOP_BACK",
            text="Reset Layers Visibility",
        )
        layout.operator(
            "mustardui.armature_clearpose",
            icon="OUTLINER_OB_ARMATURE",
            text="Reset Pose",
        )
        layout.operator("mustardui.armature_transfer_animation", icon="RENDER_ANIMATION")


class PANEL_PT_MustardUI_Armature_IKFKPanel(MainPanel, bpy.types.Panel):
    bl_parent_id = "PANEL_PT_MustardUI_Armature"
    bl_idname = "PANEL_PT_MustardUI_Armature_IKFKPanel"
    bl_label = "IK/FK Settings"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        if not arm:
            return False
        return (
            res
            and arm.MustardUI_ArmatureSettings.ikfk_snapper_enable
            and ikfk_snapper_available(arm)
        )

    def draw(self, context):
        res, arm = mustardui_active_object(context, config=0)
        snapper = arm.MustardUI_IKFKSnapperSettings
        chains = snapper.ikfk_chains
        layout = self.layout

        if not chains:
            layout.label(text="No chains found yet.", icon="INFO")
            return

        for i, chain in enumerate(chains):
            box = layout.box()
            icon = "CURVE_PATH" if chain.auto_detected else "ARMATURE_DATA"
            box.label(text=chain.name, icon=icon)

            fk_list = [n.strip() for n in chain.fk_bones.split(",") if n.strip()]
            has_fk = bool(fk_list and any(fk_list))

            # Snap row (moves bones then switches)
            row = box.row(align=True)
            row.label(text="", icon="SNAP_ON")
            row.separator()
            op = row.operator("mustardui.ikfk_snap", text="Snap  IK")
            op.chain_index = i
            op.direction = "FK_TO_IK"
            op.switch = True
            sub = row.row(align=True)
            sub.enabled = has_fk
            op = sub.operator("mustardui.ikfk_snap", text="Snap FK")
            op.chain_index = i
            op.direction = "IK_TO_FK"
            op.switch = True

            # Switch row (mode only, no position snap)
            row = box.row(align=True)
            row.label(text="", icon="ARROW_LEFTRIGHT")
            row.separator()
            op = row.operator("mustardui.ikfk_switch", text="Switch IK")
            op.chain_index = i
            op.direction = "TO_IK"
            op = row.operator("mustardui.ikfk_switch", text="Switch FK")
            op.chain_index = i
            op.direction = "TO_FK"


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_Armature)
    bpy.utils.register_class(PANEL_PT_MustardUI_Armature_IKFKPanel)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Armature_IKFKPanel)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Armature)
