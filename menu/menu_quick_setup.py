import bpy

from .. import __package__ as base_package
from ..model_selection.active_object import mustardui_active_object
from ..warnings.can_draw_ui import can_draw_ui
from . import MainPanel


class MUSTARDUI_UL_QuickSetup_Outfits(bpy.types.UIList):
    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname, index
    ):
        if item.collection:
            row = layout.row(align=True)
            row.prop(item, "enabled", text="")
            row.label(text=item.collection.name, icon="OUTLINER_COLLECTION")
        else:
            layout.label(text="Collection not found", icon="ERROR")


class MUSTARDUI_UL_QuickSetup_Hair(bpy.types.UIList):
    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname, index
    ):
        if item.object:
            obj_icon = (
                "OUTLINER_OB_CURVES"
                if item.object.type == "CURVES"
                else "OUTLINER_OB_MESH"
            )
            row = layout.row(align=True)
            row.prop(item, "enabled", text="")
            row.label(text=item.object.name, icon=obj_icon)
        else:
            layout.label(text="Object not found", icon="ERROR")

class PANEL_PT_MustardUI_QuickSetup(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_QuickSetup"
    bl_label = "Quick Setup"

    @classmethod
    def poll(cls, context):
        if can_draw_ui():
            return False
        res, arm = mustardui_active_object(context, config=2)
        addon_prefs = context.preferences.addons[base_package].preferences
        return res and not addon_prefs.developer

    def draw(self, context):
        layout = self.layout

        res, arm = mustardui_active_object(context, config=2)
        rig_settings = arm.MustardUI_RigSettings
        scanned = rig_settings.model_armature_object is not None

        # --- General ---
        box = layout.box()
        box.label(text="Model Details", icon="MODIFIER")
        col = box.column()
        col.prop(rig_settings, "model_name", text="Model Name")
        col.prop(rig_settings, "model_body", text="Body Object")

        if not scanned:
            layout.operator(
                "mustardui.quick_setup_smart_check",
                text="Scan for Other Settings",
                icon="FILE_REFRESH",
            )
            return

        # --- Outfits (shown after scan) ---
        box = layout.box()
        box.label(text="Outfits", icon="MOD_CLOTH")

        collections = rig_settings.quick_setup_outfit_collections
        if len(collections):
            col = box.box().column(align=True)
            col.label(text="Check the Collections containing Outfits.", icon="INFO")
            col.label(
                text="Each Collection is an entry in the Outfits list.", icon="BLANK1"
            )

            box.template_list(
                "MUSTARDUI_UL_QuickSetup_Outfits",
                "",
                rig_settings,
                "quick_setup_outfit_collections",
                rig_settings,
                "quick_setup_outfit_index",
                rows=4,
            )
        else:
            box.box().label(text="No collections found in the scene.", icon="INFO")

        row = box.row(align=True)
        row.label(text="Extras", icon="PLUS")
        row.prop(rig_settings, "extras_collection", text="")

        # --- Hair (shown after scan) ---
        box = layout.box()
        box.label(text="Hair", icon="OUTLINER_OB_CURVES")

        hair_objs = rig_settings.quick_setup_hair_objects
        if len(hair_objs):
            col = box.box().column(align=True)
            col.label(text="Check the Hair to be added to the List.", icon="INFO")
            col.label(
                text="Objects should contain the string 'Hair' to be", icon="BLANK1"
            )
            col.label(text="added in this list during the Scan.", icon="BLANK1")

            box.template_list(
                "MUSTARDUI_UL_QuickSetup_Hair",
                "",
                rig_settings,
                "quick_setup_hair_objects",
                rig_settings,
                "quick_setup_hair_index",
                rows=4,
            )
        else:
            box.box().label(text="No hair objects found.", icon="INFO")

        # --- Armature (shown after scan) ---
        rig_labels = {
            "arp": ("Auto-Rig Pro", "ARMATURE_DATA"),
            "rigify": ("Rigify", "ARMATURE_DATA"),
            "mhx": ("MHX", "ARMATURE_DATA"),
            "other": ("Unrecognized", "QUESTION"),
        }
        rig_label, rig_icon = rig_labels.get(
            rig_settings.model_rig_type, ("Unrecognized", "QUESTION")
        )

        box = layout.box()
        row = box.row()
        row.label(text=f"Armature: {rig_label}", icon="ARMATURE_DATA")

        if rig_settings.model_rig_type == "other":
            col = box.box().column(align=True)
            col.label(text="Unrecognized Armature Type!", icon="ERROR")
            col.label(text="Manually select the Bone Collections to add", icon="BLANK1")
            col.label(text="to the Armature panel", icon="BLANK1")

            active_bcoll = arm.collections.active
            row = box.row()
            row.template_list(
                "MUSTARDUI_UL_Armature_UIList",
                "collections",
                arm,
                "collections",
                arm.collections,
                "active_index",
                rows=4,
            )
            col = row.column(align=True)
            col.separator()
            sub = col.column(align=True)
            sub.enabled = active_bcoll is not None
            sub.operator(
                "armature.collection_move", icon="TRIA_UP", text=""
            ).direction = "UP"
            sub.operator(
                "armature.collection_move", icon="TRIA_DOWN", text=""
            ).direction = "DOWN"
            col.separator()

            # Add a warning if the bone collesion visibility is driven by a driver
            arm_obj = rig_settings.model_armature_object
            _selected_names = {
                c.name
                for c in arm.collections_all
                if c.MustardUI_ArmatureBoneCollection.is_in_UI
            }
            _anim_sources = [arm.animation_data]
            if arm_obj is not None:
                _anim_sources.append(arm_obj.animation_data)
            has_driven_colls = any(
                any(name in fc.data_path for name in _selected_names)
                and "is_visible" in fc.data_path
                for src in _anim_sources
                if src is not None
                for fc in src.drivers
            )
            if has_driven_colls:
                col = box.box().column(align=True)
                col.label(text="Some layers may appear purple (driven).", icon="ERROR")
                col.label(
                    text="Right-click on those and select Delete Driver", icon="BLANK1"
                )
                col.label(text="to make them functional in MustardUI.", icon="BLANK1")

        # --- Info ---
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Additional features can be configured in Developer", icon="INFO")
        col.label(text="mode (enable it in Blender's Add-on Preferences).", icon="BLANK1")
        col.separator()
        col.label(text="For more information check the Documentation.", icon="BLANK1")
        col.separator()
        col.operator(
            "wm.url_open",
            text="MustardUI Wiki",
            icon="URL",
        ).url = "https://github.com/Mustard2/MustardUI/wiki/Configuration"

        layout.operator(
            "mustardui.quick_setup_smart_check",
            text="Re-scan",
            icon="FILE_REFRESH",
        )

        row = layout.row()
        row.scale_y = 1.4
        row.operator("mustardui.quick_setup", text="Quick Setup", icon="PLAY")


def register():
    bpy.utils.register_class(MUSTARDUI_UL_QuickSetup_Outfits)
    bpy.utils.register_class(MUSTARDUI_UL_QuickSetup_Hair)
    bpy.utils.register_class(PANEL_PT_MustardUI_QuickSetup)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_QuickSetup)
    bpy.utils.unregister_class(MUSTARDUI_UL_QuickSetup_Hair)
    bpy.utils.unregister_class(MUSTARDUI_UL_QuickSetup_Outfits)
