import re

import bpy

from .definitions import mustardui_detect_rig_type


class MustardUI_QuickSetup_SmartCheck(bpy.types.Operator):
    """Scan the scene for the current configuration.\nFill the Model Name and select the Body Object to activate this operator"""  # noqa: E501

    bl_idname = "mustardui.quick_setup_smart_check"
    bl_label = "Smart Check"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    @classmethod
    def poll(cls, context):
        if context.active_object is None:
            return False
        if context.active_object.type != "ARMATURE":
            return False
        arm = context.active_object.data
        if arm.MustardUI_created:
            return False
        rig_settings = arm.MustardUI_RigSettings
        if not rig_settings.model_name:
            return False
        if rig_settings.model_body is None:
            return False
        return True

    def execute(self, context):
        arm_obj = context.active_object
        arm = arm_obj.data
        rig_settings = arm.MustardUI_RigSettings

        # Infer model name from armature object name if not set
        if not rig_settings.model_name:
            name = re.sub(r"(?i)armature", "", arm_obj.name).strip("_. ")
            rig_settings.model_name = name if name else arm_obj.name

        scene_collections = list(context.scene.collection.children_recursive)

        # Auto-detect extras first so it can be excluded from the outfit list
        extras = next(
            (c for c in scene_collections if "extra" in c.name.lower()),
            None,
        )
        if extras is not None:
            rig_settings.extras_collection = extras

        # Build sets of collections and hair objects already claimed by other
        # configured MustardUI models — used to disable them in the UILists
        taken_collections = set()
        taken_hair_objects = set()
        for other_arm in bpy.data.armatures:
            if not other_arm.MustardUI_created:
                continue
            rs = other_arm.MustardUI_RigSettings
            for x in rs.outfits_collections:
                if x.collection:
                    taken_collections.add(x.collection)
            for attr in (
                "hair_collection",
                "extras_collection",
                "hair_extras_collection",
            ):
                coll = getattr(rs, attr, None)
                if coll:
                    taken_collections.add(coll)
            for attr in ("hair_collection", "hair_extras_collection"):
                coll = getattr(rs, attr, None)
                if coll:
                    for obj in coll.objects:
                        taken_hair_objects.add(obj)

        # Populate outfit collection list; pre-check collections whose name suggests
        # they are outfit collections, unless already used by another model
        collections = rig_settings.quick_setup_outfit_collections
        collections.clear()
        for coll in scene_collections:
            item = collections.add()
            item.collection = coll
            if coll in taken_collections:
                item.enabled = False
            else:
                coll_lower = coll.name.lower()
                item.enabled = any(
                    w in coll_lower
                    for w in (
                        "outfit",
                        "dress",
                        "wear",
                        "cloth",
                        "costume",
                        "suit",
                        "attire",
                    )
                )

        # Populate hair object list: any object with "hair" in its name,
        # disabling objects already used by another model
        hair_objs = rig_settings.quick_setup_hair_objects
        hair_objs.clear()
        for obj in bpy.data.objects:
            if "hair" in obj.name.lower():
                item = hair_objs.add()
                item.object = obj
                item.enabled = obj not in taken_hair_objects

        # Detect rig type using the same logic as the configuration operator
        settings = context.scene.MustardUI_Settings
        rig_settings.model_armature_object = arm_obj
        rig_settings.model_rig_type = mustardui_detect_rig_type(arm, arm_obj)

        # Run the armature smart check to autoconfigure bone collections
        # (applies the bone-collection preset for the detected rig type).
        # In Direct Panel Mode, panel_model_selection_armature must point here first.
        if not settings.viewport_model_selection:
            settings.panel_model_selection_armature = arm
        try:
            bpy.ops.mustardui.armature_smartcheck(
                "EXEC_DEFAULT", reset_current_collections=True
            )
        except RuntimeError:
            pass

        self.report(
            {"INFO"},
            f"MustardUI - Found {len(collections)} collection(s), "
            f"{len(hair_objs)} hair object(s).",
        )
        return {"FINISHED"}


class MustardUI_QuickSetup(bpy.types.Operator):
    """Quickly set up MustardUI with essential Outfits and Hair support"""

    bl_idname = "mustardui.quick_setup"
    bl_label = "Quick Setup"
    bl_description = (
        "Set up MustardUI for this character with minimal configuration.\n"
        "Outfits and Hair can be added with the optional fields"
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if context.active_object is None:
            return False
        if context.active_object.type != "ARMATURE":
            return False
        arm = context.active_object.data
        if arm.MustardUI_created:
            return False
        rig_settings = arm.MustardUI_RigSettings
        if not rig_settings.model_name:
            return False
        if rig_settings.model_body is None:
            return False
        return True

    def execute(self, context):
        settings = context.scene.MustardUI_Settings

        arm_obj = context.active_object
        arm = arm_obj.data
        rig_settings = arm.MustardUI_RigSettings

        if rig_settings.model_body is None:
            self.report(
                {"ERROR"},
                "MustardUI - No body mesh found. Select one in the Body field and "
                "try again.",
            )
            return {"FINISHED"}

        def find_layer_collection(layer_coll, collection):
            if layer_coll.collection == collection:
                return layer_coll
            for child in layer_coll.children:
                result = find_layer_collection(child, collection)
                if result:
                    return result
            return None

        # Add outfit collections that the user toggled on.
        # Extras, hair and hair extras collections take precedence — skip them.
        reserved = {
            rig_settings.extras_collection,
            rig_settings.hair_collection,
            rig_settings.hair_extras_collection,
        }
        reserved.discard(None)

        existing = [x.collection for x in rig_settings.outfits_collections]
        for item in rig_settings.quick_setup_outfit_collections:
            if not item.enabled or item.collection is None:
                continue
            if item.collection in reserved:
                continue
            if item.collection not in existing:
                entry = rig_settings.outfits_collections.add()
                entry.collection = item.collection
                existing.append(item.collection)

            lc = find_layer_collection(
                context.view_layer.layer_collection, item.collection
            )
            if lc and lc.exclude:
                lc.exclude = False

        if len(rig_settings.outfits_collections) > 0:
            rig_settings.outfits_list = "Nude"

        # Build hair collection from objects the user toggled on in the UIList
        if rig_settings.hair_collection is None:
            selected_hair = [
                item.object
                for item in rig_settings.quick_setup_hair_objects
                if item.enabled and item.object is not None
            ]
            if selected_hair:
                hair_coll_name = rig_settings.model_name + " Hair"
                if hair_coll_name in bpy.data.collections:
                    hair_coll = bpy.data.collections[hair_coll_name]
                else:
                    hair_coll = bpy.data.collections.new(hair_coll_name)
                    context.scene.collection.children.link(hair_coll)
                for obj in selected_hair:
                    if obj.name not in hair_coll.objects:
                        hair_coll.objects.link(obj)

                rig_settings.hair_collection = hair_coll
                lc = find_layer_collection(
                    context.view_layer.layer_collection, hair_coll
                )
                if lc and lc.exclude:
                    lc.exclude = False

        if rig_settings.extras_collection is not None:
            lc = find_layer_collection(
                context.view_layer.layer_collection, rig_settings.extras_collection
            )
            if lc and lc.exclude:
                lc.exclude = False

        # Disable MustardUI naming convention — quick setup users have arbitrary names
        rig_settings.model_MustardUI_naming_convention = False

        # Clean up temporary quick setup data
        rig_settings.quick_setup_outfit_collections.clear()
        rig_settings.quick_setup_outfit_index = 0
        rig_settings.quick_setup_hair_objects.clear()
        rig_settings.quick_setup_hair_index = 0

        # When the rig is not a recognized type ("other"), set up the IK/FK Snapper
        # automatically: detect its chains and enable it. If detection finds no
        # usable chain (missing the vital IK/FK bones), keep it disabled so it does
        # not show up in the final configuration.
        from ..armature.ik_fk_snapper import (
            ikfk_has_complete_chains,
            populate_ikfk_chains,
        )

        armature_settings = arm.MustardUI_ArmatureSettings
        if mustardui_detect_rig_type(arm, arm_obj) == "other":
            populate_ikfk_chains(arm, arm_obj)
            armature_settings.ikfk_snapper_enable = ikfk_has_complete_chains(arm)
        else:
            armature_settings.ikfk_snapper_enable = False

        # In Direct Panel Mode, point the selection at this armature so the
        # main configuration operator can find it
        if not settings.viewport_model_selection:
            settings.panel_model_selection_armature = arm

        return bpy.ops.mustardui.configuration()


def register():
    bpy.utils.register_class(MustardUI_QuickSetup_SmartCheck)
    bpy.utils.register_class(MustardUI_QuickSetup)


def unregister():
    bpy.utils.unregister_class(MustardUI_QuickSetup)
    bpy.utils.unregister_class(MustardUI_QuickSetup_SmartCheck)
