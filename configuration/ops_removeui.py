import bpy
from bpy.props import BoolProperty

from .. import __package__ as base_package
from ..custom_properties.misc import mustardui_delete_all_custom_properties
from ..model_selection.active_object import (
    active_object_operator_poll,
    mustardui_active_object,
)
from ..physics.definitions_nodes import CLOTH_DYNAMICS_NODE_GROUP, CLOTH_DYNAMICS_SOCKETS


class MustardUI_RemoveUI(bpy.types.Operator):
    """Remove and clean the model and the UI"""

    bl_idname = "mustardui.remove"
    bl_label = "Remove UI and Model"
    bl_options = {"PRESET", "UNDO"}

    delete_settings: BoolProperty(
        default=False,
        name="Delete Settings",
        description="All Settings of the UI will be removed.\nA clean Configuration is "
        "necessary after using this option",
    )
    delete_objects: BoolProperty(
        default=False,
        name="Delete Objects",
        description="All Objects are deleted from the file, including the main Armature",
    )

    delete_shared: BoolProperty(
        default=False,
        name="Delete Shared Data",
        description="Also delete Collections and Objects that might be shared with other models "
        "(Collision collections, bones custom shapes)",
    )
    delete_model_collections: BoolProperty(
        default=False,
        name="Delete Model Collections",
        description="Also delete the Collections containing the Armature, the bones custom "
        "shapes and the Physics Items, with their parent Collections, all their Objects and "
        "sub-collections.\nCollections containing Objects of other MustardUI models are kept.\n"
        "Warning: this might delete Objects not related to the model (e.g. Objects not "
        "registered in MustardUI)",
    )

    def remove_data_col(self, context, col, remove_subcoll=False):
        # Copy the objects, as removing them while iterating the collection skips some of them
        items = list(col.all_objects if remove_subcoll else col.objects)
        self.remove_data_list(context, items)

        bpy.data.collections.remove(col)
        return

    def remove_data_list(self, context, ll):
        for obj in ll:
            data = obj.data
            obj_type = obj.type
            bpy.data.objects.remove(obj)

            # Remove the data only if not shared with other objects
            if data is None or data.users > 0:
                continue
            if obj_type == "MESH":
                bpy.data.meshes.remove(data)
            elif obj_type == "ARMATURE":
                bpy.data.armatures.remove(data)
        return

    def remove_property(self, obj, name):
        try:
            del obj[name]
        except Exception:
            pass

    def other_models_objects(self, arm):
        # List the Objects belonging to the other MustardUI models in the file
        other_arms = [x for x in bpy.data.armatures if x != arm and x.MustardUI_created]
        if not other_arms:
            return set()

        objects = set()
        for obj in bpy.data.objects:
            if obj.type == "ARMATURE" and obj.data in other_arms:
                objects.add(obj)
                objects.update(x.custom_shape for x in obj.pose.bones if x.custom_shape is not None)
            elif (
                obj.parent is not None
                and obj.parent.type == "ARMATURE"
                and obj.parent.data in other_arms
            ):
                objects.add(obj)
            elif any(
                m.type == "ARMATURE" and m.object is not None and m.object.data in other_arms
                for m in obj.modifiers
            ):
                objects.add(obj)
            elif any(
                c.type == "CHILD_OF" and c.target is not None and c.target.data in other_arms
                for c in obj.constraints
            ):
                objects.add(obj)

        for other_arm in other_arms:
            other_rig_settings = other_arm.MustardUI_RigSettings
            collections = [x.collection for x in other_rig_settings.outfits_collections]
            collections += [
                other_rig_settings.hair_collection,
                other_rig_settings.hair_extras_collection,
                other_rig_settings.extras_collection,
            ]
            for col in collections:
                if col is not None:
                    objects.update(col.all_objects)

        return objects

    @classmethod
    def poll(cls, context):
        return active_object_operator_poll(context, config=0)

    def execute(self, context):

        settings = bpy.context.scene.MustardUI_Settings
        res, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings
        arm_obj = rig_settings.model_armature_object
        addon_prefs = context.preferences.addons[base_package].preferences
        physics_settings = arm.MustardUI_PhysicsSettings

        # Store the leftover collections
        model_collections = set()
        if self.delete_objects and self.delete_model_collections:
            objects = [arm_obj]
            objects += [x.custom_shape for x in arm_obj.pose.bones if x.custom_shape is not None]
            objects += [x.object for x in physics_settings.items if x.object is not None]
            other_objects = self.other_models_objects(arm)

            parent_collections = {}
            for col in bpy.data.collections:
                for child in col.children:
                    parent_collections.setdefault(child.name, []).append(col)

            to_check = [col for obj in objects for col in obj.users_collection]
            checked_collections = set()
            skipped_collections = set()
            while to_check:
                col = to_check.pop()
                # Skip scene master collections and linked collections (can not be deleted)
                if bpy.data.collections.get(col.name) != col or col.library is not None:
                    continue
                if col.name in checked_collections:
                    continue
                checked_collections.add(col.name)
                # Skip collections containing Objects of other MustardUI models
                if any(x in other_objects for x in col.all_objects):
                    skipped_collections.add(col.name)
                    continue
                model_collections.add(col.name)
                to_check += parent_collections.get(col.name, [])

            if skipped_collections:
                self.report(
                    {"WARNING"},
                    "MustardUI - Collections shared with other models were not deleted: "
                    + ", ".join(sorted(skipped_collections)),
                )

        # Store the collision collections set in the physics items
        collision_collections = set()
        if self.delete_objects and self.delete_shared:
            for item in physics_settings.items:
                if item.object is None:
                    continue
                for mod in item.object.modifiers:
                    col = None
                    if mod.type == "CLOTH":
                        col = mod.collision_settings.collection
                    elif mod.type == "SOFT_BODY":
                        col = mod.settings.collision_collection
                    elif (
                        mod.type == "NODES"
                        and mod.node_group
                        and mod.node_group.name.startswith(CLOTH_DYNAMICS_NODE_GROUP)
                        and hasattr(mod, "properties")
                    ):
                        entry = getattr(
                            mod.properties.inputs,
                            CLOTH_DYNAMICS_SOCKETS["effectors_collection"],
                            None,
                        )
                        col = entry.value if entry is not None else None
                    if isinstance(col, bpy.types.Collection):
                        collision_collections.add(col.name)

        # Remove or delete physics items
        for i in reversed(range(len(physics_settings.items))):
            arm.mustardui_physics_items_uilist_index = i
            if self.delete_objects and physics_settings.items[i].object is not None:
                bpy.ops.mustardui.physics_item_delete()
            elif self.delete_objects or self.delete_settings:
                bpy.ops.mustardui.physics_item_remove()

        # Remove Objects and Collections settings
        if self.delete_settings and not self.delete_objects:
            collections = [x.collection for x in rig_settings.outfits_collections]
            collections += [
                rig_settings.hair_collection,
                rig_settings.hair_extras_collection,
                rig_settings.extras_collection,
            ]
            collections = [x for x in collections if x is not None]
            for col in list(collections):
                collections += list(col.children_recursive)

            objects = {obj for col in collections for obj in col.all_objects}
            for obj in objects:
                self.remove_property(obj, "MustardUI_OutfitSettings")
                self.remove_property(obj, "MustardUI_outfit_visibility")
                self.remove_property(obj, "MustardUI_outfit_lock")
            for col in set(collections):
                self.remove_property(col, "MustardUI_extras_collapse")
                self.remove_property(col, "MustardUI_extras_show")

        # Remove or delete outfits
        for i in reversed(range(len(rig_settings.outfits_collections))):
            context.scene.mustardui_outfits_uilist_index = i
            if self.delete_objects:
                bpy.ops.mustardui.delete_outfit(is_config=True, delete_cp=True)
            elif self.delete_settings:
                bpy.ops.mustardui.remove_outfit(is_config=True, delete_cp=True)

        # Remove hair and extras
        if self.delete_objects:
            if rig_settings.hair_collection is not None:
                self.remove_data_col(context, rig_settings.hair_collection)
            if rig_settings.hair_extras_collection is not None:
                self.remove_data_col(context, rig_settings.hair_extras_collection)
            if rig_settings.extras_collection is not None:
                self.remove_data_col(
                    context,
                    rig_settings.extras_collection,
                    rig_settings.extras_config_subcollections,
                )
            if self.delete_shared:
                for col_name in collision_collections:
                    col = bpy.data.collections.get(col_name)
                    if col is not None:
                        self.remove_data_col(context, col)

        # Remove settings
        if self.delete_settings or self.delete_objects:
            # Remove custom properties
            mustardui_delete_all_custom_properties(
                arm, arm.MustardUI_CustomProperties, addon_prefs, rig_settings
            )
            mustardui_delete_all_custom_properties(
                arm, arm.MustardUI_CustomPropertiesOutfit, addon_prefs, rig_settings
            )
            mustardui_delete_all_custom_properties(
                arm, arm.MustardUI_CustomPropertiesHair, addon_prefs, rig_settings
            )

            # Clear all settings
            self.remove_property(arm, "MustardUI_ToolsSettings")
            self.remove_property(arm, "MustardUI_MorphsSettings")
            self.remove_property(arm, "MustardUI_PhysicsSettings")
            self.remove_property(arm, "MustardUI_ArmatureSettings")
            self.remove_property(arm, "MustardUI_CustomProperties")
            self.remove_property(arm, "MustardUI_CustomPropertiesHair")
            self.remove_property(arm, "MustardUI_CustomPropertiesOutfit")
            self.remove_property(arm, "MustardUI_RigSettings")
            self.remove_property(arm, "MustardUI_SimplifySettings")
            self.remove_property(arm, "MustardUI_IKFKSnapperSettings")
            self.remove_property(arm, "MustardUI_Links")

            # Clear UI lists indices and filters
            self.remove_property(arm, "mustardui_morphs_uilist_index")
            self.remove_property(arm, "mustardui_morphs_uilist_menu_index")
            self.remove_property(arm, "mustardui_morphs_preset_uilist_index")
            self.remove_property(arm, "mustardui_morphs_section_uilist_index")
            self.remove_property(arm, "mustardui_physics_items_uilist_index")
            self.remove_property(arm, "mustardui_physics_items_outfits_uilist_index")
            self.remove_property(arm, "mustardui_physics_preset_uilist_index")
            self.remove_property(arm, "mustardui_property_uilist_outfits_filter_outfit")
            self.remove_property(arm, "mustardui_property_uilist_outfits_filter_piece")
            self.remove_property(arm, "mustardui_property_uilist_hair_filter_object")

        # Remove Armature and its children objects
        if self.delete_objects:
            # Remove Armature Children
            self.remove_data_list(context, arm_obj.children)

            # Remove bones custom shapes
            if self.delete_shared:
                csb = []
                for bone in arm_obj.pose.bones:
                    if bone.custom_shape is not None and bone.custom_shape not in csb:
                        csb.append(bone.custom_shape)
                self.remove_data_list(context, csb)

            # Remove Armature
            self.remove_data_list(context, [arm_obj])

            # Remove the leftover collections (including their parent collections) containing
            # - model Armature
            # - bones custom shapes
            # - physics items
            if self.delete_model_collections:
                for col_name in model_collections:
                    col = bpy.data.collections.get(col_name)
                    if col is None:
                        continue
                    children = [x.name for x in col.children_recursive]
                    self.remove_data_col(context, col, remove_subcoll=True)
                    for child_name in children:
                        child = bpy.data.collections.get(child_name)
                        if child is not None:
                            bpy.data.collections.remove(child)

            # Purge the data left without users
            bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

        else:
            arm.MustardUI_enable = not arm.MustardUI_enable
            arm.MustardUI_created = False

        settings.viewport_model_selection = True

        self.report(
            {"INFO"},
            "MustardUI - MustardUI deletion complete. Switched to Viewport Model Selection",
        )

        return {"FINISHED"}

    def invoke(self, context, event):

        addon_prefs = context.preferences.addons[base_package].preferences

        return context.window_manager.invoke_props_dialog(
            self, width=550 if addon_prefs.debug else 450
        )

    def draw(self, context):

        layout = self.layout

        box = layout.box()
        col = box.column(align=True)
        col.label(
            text="This is a highly destructive operation! Use it at your own risk!",
            icon="ERROR",
        )
        col.label(
            text="Move your cursor over a button to display its description.",
            icon="BLANK1",
        )

        box = layout.box()
        col = box.column(align=True)
        col.prop(self, "delete_settings")
        col.prop(self, "delete_objects")

        col.separator()

        col = col.column(align=True)
        col.enabled = self.delete_objects
        col.prop(self, "delete_shared")
        col.prop(self, "delete_model_collections")


def register():
    bpy.utils.register_class(MustardUI_RemoveUI)


def unregister():
    bpy.utils.unregister_class(MustardUI_RemoveUI)
