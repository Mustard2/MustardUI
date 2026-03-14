import bpy
from bpy.props import BoolProperty

from .. import __package__ as base_package
from ..custom_properties.misc import (
    mustardui_cleanup_dangling_drivers,
    mustardui_delete_all_custom_properties,
    mustardui_reassign_default,
    mustardui_resync_drivers,
)
from ..model_selection.active_object import mustardui_active_object
from ..morphs.misc import isDazFcurve


def remove_diffeomorphic_data_result(obj, attr):
    try:
        del obj[attr]
        return 1
    except:
        return 0


class MustardUI_CleanModel(bpy.types.Operator):
    """Clean the model to get better performance, at the cost of deleting some features/shape keys/morphs/outfits"""

    bl_idname = "mustardui.cleanmodel"
    bl_label = "Clean Model"
    bl_options = {"UNDO"}

    remove_body_cp: BoolProperty(default=False, name="Remove Body Custom Properties")
    remove_outfit_cp: BoolProperty(
        default=False, name="Remove Outfit Custom Properties"
    )
    remove_hair_cp: BoolProperty(default=False, name="Remove Hair Custom Properties")

    remove_unselected_outfits: BoolProperty(
        default=False,
        name="Delete Unselected Outfits",
        description="Remove all the outfits that are not selected in the UI ("
        "Outfits list)",
    )
    remove_unselected_extras: BoolProperty(
        default=False,
        name="Delete Unselected Extras",
        description="Remove all the Extras objects that are not selected in the UI",
    )
    remove_unselected_hair: BoolProperty(
        default=False,
        name="Delete Unselected Hair",
        description="Remove all the Hair that are not currently in use",
    )

    remove_nulldrivers: BoolProperty(
        default=False,
        name="Remove Null Drivers",
        description="Remove drivers whose equations are '0.0' or '-0.0'",
    )

    remove_morphs: BoolProperty(
        default=False,
        name="Remove Morphs",
        description="Remove all morphs (except JCMs and FACS if not enabled below)",
    )
    remove_morphs_shapekeys: BoolProperty(
        default=False,
        name="Remove Shape Keys",
        description="Remove selected morphs shape keys",
    )
    remove_morphs_jcms: BoolProperty(
        default=False, name="Remove JCMs", description="Remove JCMs"
    )
    remove_morphs_facs: BoolProperty(
        default=False, name="Remove FACS", description="Remove FACS (Advanced Emotions)"
    )
    remove_diffeomorphic_data: BoolProperty(
        default=False,
        name="Remove Diffeomorphic Data",
        description="Remove Diffeomorphic data.\nAfter this operation, Morph "
        "settings in the DAZ Importer (Diffeomorphic) tool might not "
        "work",
    )

    def remove_props_from_group(self, obj, group, props_removed):
        if hasattr(obj, group):
            props = getattr(obj, group)
            if props:
                idx = []
                for n, prop in enumerate(props):
                    if "pJCM" not in prop.name or self.remove_morphs_jcms:
                        idx.append(n)
                        props_removed.append(prop.name)

                for i in reversed(idx):
                    props.remove(i)

        return props_removed

    def remove_props_from_cat_group(self, obj, group, props_removed):
        if hasattr(obj, group):
            categories = getattr(obj, group)
            if categories:
                for cat in categories:
                    props = cat["morphs"]
                    idx = []
                    for n, prop in enumerate(props):
                        if "name" in prop:
                            prop_name = prop["name"]
                            if "pJCM" not in prop_name or self.remove_morphs_jcms:
                                idx.append(n)
                                props_removed.append(prop_name)
                        else:
                            idx.append(n)

                    for i in reversed(idx):
                        del props[i]

        return props_removed

    def check_removal(self, string, string_cmp):
        check_eCTRL = "eCTRL" in string_cmp
        check_eJCM = "eJCM" in string_cmp
        check_pJCM = "pJCM" not in string_cmp or self.remove_morphs_jcms
        check_facs = "facs" not in string_cmp or self.remove_morphs_facs

        return (
            (string == string_cmp or check_eCTRL or check_eJCM)
            and check_pJCM
            and check_facs
        )

    def locked_outfits_collections(self, rig_settings):
        locked_objects = set()
        for coll in [
            x for x in rig_settings.outfits_collections if x.collection is not None
        ]:
            items = (
                coll.collection.all_objects
                if rig_settings.outfit_config_subcollections
                else coll.collection.objects
            )
            for obj in items:
                if obj.MustardUI_outfit_lock:
                    locked_objects.add(coll)
        return list(locked_objects)

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        return res

    def execute(self, context):
        res, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings
        morphs_settings = arm.MustardUI_MorphsSettings
        physics_settings = arm.MustardUI_PhysicsSettings
        addon_prefs = context.preferences.addons[base_package].preferences

        options = (
            self.remove_nulldrivers
            or self.remove_morphs
            or self.remove_diffeomorphic_data
            or self.remove_unselected_outfits
            or self.remove_unselected_extras
            or self.remove_unselected_hair
            or self.remove_body_cp
            or self.remove_outfit_cp
            or self.remove_hair_cp
        )

        if not options:
            return {"FINISHED"}

        if addon_prefs.debug:
            print("MustardUI Clean model statistics")

        null_drivers_removed = 0
        morphs_props_removed = 0
        morphs_drivers_removed = 0
        morphs_shapekeys_removed = 0
        diffeomorphic_data_deleted = 0
        outfits_deleted = 0
        extras_deleted = 0
        hair_deleted = 0
        outfits_cp_deleted = 0
        body_cp_removed = 0
        outfit_cp_removed = 0
        hair_cp_removed = 0

        # Remove null drivers
        if self.remove_nulldrivers:
            for obj in [x for x in context.scene.objects if x.type == "MESH"]:
                if obj.animation_data is not None:
                    drivers = obj.animation_data.drivers
                    for driver in drivers:
                        if (
                            driver.driver.expression == "0.0"
                            or driver.driver.expression == "-0.0"
                        ):
                            drivers.remove(driver)
                            null_drivers_removed = null_drivers_removed + 1
                if obj.data.shape_keys is not None:
                    if obj.data.shape_keys.animation_data is not None:
                        drivers = obj.data.shape_keys.animation_data.drivers
                        for driver in drivers:
                            if (
                                driver.driver.expression == "0.0"
                                or driver.driver.expression == "-0.0"
                            ):
                                drivers.remove(driver)
                                morphs_drivers_removed = morphs_drivers_removed + 1

            if addon_prefs.debug:
                print("  Null drivers removed: " + str(null_drivers_removed))

        # Check diffeomorphic custom morphs existence and delete all of them (except JCMs)
        if self.remove_morphs:
            props_removed = []

            # Add props to the removed list from the armature
            if self.remove_morphs_jcms:
                props_removed = self.remove_props_from_group(
                    rig_settings.model_armature_object, "DazStandardjcms", props_removed
                )
                props_removed.append("pJCM")
            if self.remove_morphs_facs:
                props_removed = self.remove_props_from_group(
                    rig_settings.model_armature_object, "DazFacs", props_removed
                )
                props_removed.append("facs")
            props_removed = self.remove_props_from_group(
                rig_settings.model_armature_object, "DazUnits", props_removed
            )
            props_removed = self.remove_props_from_group(
                rig_settings.model_armature_object, "DazExpressions", props_removed
            )
            props_removed = self.remove_props_from_group(
                rig_settings.model_armature_object, "DazBody", props_removed
            )
            props_removed = self.remove_props_from_group(
                rig_settings.model_armature_object, "DazCustom", props_removed
            )
            props_removed = self.remove_props_from_group(
                rig_settings.model_armature_object, "DazCustom", props_removed
            )
            props_removed = self.remove_props_from_cat_group(
                rig_settings.model_armature_object, "DazMorphCats", props_removed
            )

            # Add props to the removed list from the body
            if self.remove_morphs_jcms:
                props_removed = self.remove_props_from_group(
                    rig_settings.model_body, "DazStandardjcms", props_removed
                )
            if self.remove_morphs_facs:
                props_removed = self.remove_props_from_group(
                    rig_settings.model_body, "DazFacs", props_removed
                )
            props_removed = self.remove_props_from_group(
                rig_settings.model_body, "DazUnits", props_removed
            )
            props_removed = self.remove_props_from_group(
                rig_settings.model_body, "DazExpressions", props_removed
            )
            props_removed = self.remove_props_from_group(
                rig_settings.model_body, "DazBody", props_removed
            )
            props_removed = self.remove_props_from_group(
                rig_settings.model_body, "DazCustom", props_removed
            )
            props_removed = self.remove_props_from_cat_group(
                rig_settings.model_body, "DazMorphCats", props_removed
            )

            # Remove unused drivers and shape keys
            aobj = context.active_object
            context.view_layer.objects.active = rig_settings.model_armature_object

            # Find objects where to remove drivers and shape keys
            objects = [rig_settings.model_body]

            for collection in [
                x
                for x in [
                    y
                    for y in rig_settings.outfits_collections
                    if y.collection is not None
                ]
                if x.collection is not None
            ]:
                items = (
                    collection.collection.all_objects
                    if rig_settings.outfit_config_subcollections
                    else collection.collection.objects
                )
                for obj in items:
                    if obj.type == "MESH":
                        objects.append(obj)
            if rig_settings.extras_collection is not None:
                items = (
                    rig_settings.extras_collection.all_objects
                    if rig_settings.outfit_config_subcollections
                    else rig_settings.extras_collection.objects
                )
                for obj in items:
                    if obj.type == "MESH":
                        objects.append(obj)
            for obj in context.scene.objects:
                if (
                    obj.find_armature() == rig_settings.model_armature_object
                    and obj.type == "MESH"
                ):
                    objects.append(obj)

            # Add Children to Objects
            for c in [
                x
                for x in rig_settings.model_armature_object.children
                if x != rig_settings.model_body and x not in objects
            ]:
                objects.append(c)

            # Remove shape keys and their drivers
            for obj in objects:
                if obj.data.shape_keys is not None:
                    if obj.data.shape_keys.animation_data is not None:
                        drivers = obj.data.shape_keys.animation_data.drivers
                        for driver in drivers:
                            words = driver.data_path.split('"')
                            for cp in props_removed:
                                if words[0] == "key_blocks[" and self.check_removal(
                                    cp, words[1]
                                ):
                                    drivers.remove(driver)
                                    morphs_drivers_removed = morphs_drivers_removed + 1
                                    break
                    if self.remove_morphs_shapekeys:
                        for sk in obj.data.shape_keys.key_blocks:
                            for cp in props_removed:
                                if self.check_removal(cp, sk.name):
                                    obj.shape_key_remove(sk)
                                    morphs_shapekeys_removed = (
                                        morphs_shapekeys_removed + 1
                                    )
                                    break

                obj.update_tag()

            # Remove drivers from objects
            objects.append(arm)
            for obj in objects:
                if obj.animation_data:
                    if obj.animation_data.drivers:
                        drivers = obj.animation_data.drivers

                        for driver in drivers:
                            ddelete = (
                                "evalMorphs" in driver.driver.expression
                                or driver.driver.expression == "0.0"
                                or driver.driver.expression == "-0.0"
                            )
                            for cp in props_removed:
                                ddelete = ddelete or (
                                    self.check_removal(cp, driver.data_path)
                                    or isDazFcurve(driver.data_path)
                                )
                                for v in driver.driver.variables:
                                    ddelete = ddelete or cp in v.targets[0].data_path
                            if ddelete:
                                drivers.remove(driver)
                                morphs_drivers_removed = morphs_drivers_removed + 1

                        obj.update_tag()

            # Remove drivers from bones
            for bone in [
                x
                for x in rig_settings.model_armature_object.pose.bones
                if "(drv)" in x.name
            ]:
                bone.driver_remove("location")
                bone.driver_remove("rotation_euler")
                bone.driver_remove("scale")

            context.view_layer.objects.active = aobj

            # Remove custom properties from armature
            for cp in props_removed:
                for kp in [x for x in rig_settings.model_armature_object.keys()]:
                    if self.check_removal(cp, kp) or isDazFcurve(kp):
                        del rig_settings.model_armature_object[kp]
                        morphs_props_removed = morphs_props_removed + 1
                for kp in [x for x in arm.keys()]:
                    if self.check_removal(cp, kp) or isDazFcurve(kp):
                        del arm[kp]
                        morphs_props_removed = morphs_props_removed + 1

            # Remove diffeomorphic support from the UI to avoid errors in the UI, or restore it if FACS are asked
            if not self.remove_morphs_facs:
                morphs_settings.sections.clear()
                morphs_settings.diffeomorphic_body_morphs = False
                morphs_settings.diffeomorphic_emotions = False
                morphs_settings.diffeomorphic_emotions_units = False
                bpy.ops.mustardui.configuration()
                bpy.ops.mustardui.morphs_check()
                bpy.ops.mustardui.configuration()
            else:
                morphs_settings.sections.clear()
                morphs_settings.enable_ui = False

            if addon_prefs.debug:
                print("  Morph properties removed: " + str(morphs_props_removed))
                print("  Morph drivers removed: " + str(morphs_drivers_removed))
                print("  Morph shape keys removed: " + str(morphs_shapekeys_removed))

        if self.remove_diffeomorphic_data:
            objects = [rig_settings.model_body, rig_settings.model_body.data]

            dd_colls = [
                x.collection
                for x in rig_settings.outfits_collections
                if x.collection is not None
            ]
            if rig_settings.extras_collection is not None:
                dd_colls.append(rig_settings.extras_collection)
            if rig_settings.hair_collection is not None:
                dd_colls.append(rig_settings.hair_collection)

            for col in dd_colls:
                items = (
                    col.all_objects
                    if rig_settings.outfit_config_subcollections
                    else col.objects
                )
                for obj in [x for x in items if x is not None]:
                    objects.append(obj)
                    if obj.data is not None:
                        objects.append(obj.data)

            for obj in objects:
                items_to_remove = []
                for k, v in obj.items():
                    if "Daz" in k:
                        items_to_remove.append(k)
                for k in items_to_remove:
                    diffeomorphic_data_deleted = (
                        diffeomorphic_data_deleted
                        + remove_diffeomorphic_data_result(obj, k)
                    )
                obj.update_tag()

            if addon_prefs.debug:
                print(
                    "  Diffeomorphic Data Blocks removed: "
                    + str(diffeomorphic_data_deleted)
                )

        # Remove unselected outfits
        if self.remove_unselected_outfits:
            current_outfit = rig_settings.outfits_list

            to_remove = [
                x.collection
                for x in [
                    y
                    for y in rig_settings.outfits_collections
                    if y.collection is not None
                    and y not in self.locked_outfits_collections(rig_settings)
                ]
                if x.collection.name != current_outfit
            ]

            # Remove dangling Physics Items first
            items_to_remove = []
            for pi_id, item in enumerate(physics_settings.items):
                if (
                    item.outfit_enable
                    and item.outfit_collection in to_remove
                    and item.object is not None
                ):
                    pi_obj = item.object
                    obj_name = pi_obj.name
                    try:
                        data = pi_obj.data
                        bpy.data.objects.remove(pi_obj)
                        bpy.data.meshes.remove(data)
                        if addon_prefs.debug:
                            print("  Physics item deleted: " + obj_name)
                    except:
                        if addon_prefs.debug:
                            print(
                                "  Physics item not deleted (error occurred): "
                                + obj_name
                            )
                        continue
                    items_to_remove.append(pi_id)
            for pi_id in reversed(items_to_remove):
                physics_settings.items.remove(pi_id)

            for col in to_remove:
                # Find the index of the collection to remove
                i = 0
                for v in rig_settings.outfits_collections:
                    if v.collection == col:
                        break
                    i += 1

                context.scene.mustardui_outfits_uilist_index = i
                bpy.ops.mustardui.delete_outfit(is_config=True)
                outfits_deleted = outfits_deleted + 1

            rig_settings.outfits_list = current_outfit

            if addon_prefs.debug:
                print("  Outfits deleted: " + str(outfits_deleted))

        # Remove unselected extras
        if rig_settings.extras_collection is not None and self.remove_unselected_extras:
            items = (
                rig_settings.extras_collection.all_objects
                if rig_settings.outfit_config_subcollections
                else rig_settings.extras_collection.objects
            )
            objs = [x for x in items if x.hide_viewport]

            # Remove dangling Physics Items first
            items_to_remove = []
            for pi_id, item in enumerate(physics_settings.items):
                if (
                    item.outfit_enable
                    and item.outfit_collection == rig_settings.extras_collection
                    and item.outfit_object in objs
                    and item.object is not None
                ):
                    pi_obj = item.object
                    obj_name = pi_obj.name
                    try:
                        data = pi_obj.data
                        bpy.data.objects.remove(pi_obj)
                        bpy.data.meshes.remove(data)
                        if addon_prefs.debug:
                            print("  Physics item deleted: " + obj_name)
                    except:
                        if addon_prefs.debug:
                            print(
                                "  Physics item not deleted (error occurred): "
                                + obj_name
                            )
                        continue
                    items_to_remove.append(pi_id)
            for pi_id in reversed(items_to_remove):
                physics_settings.items.remove(pi_id)

            outfit_cp = arm.MustardUI_CustomPropertiesOutfit

            # Firstly set the custom property to their default value
            for i, cp in enumerate(outfit_cp):
                if (
                    cp.outfit == rig_settings.extras_collection
                    and cp.outfit_piece in objs
                ):
                    mustardui_reassign_default(arm, outfit_cp, i, addon_prefs)

            # Update everything
            if rig_settings.model_armature_object:
                rig_settings.model_armature_object.update_tag()
            bpy.context.view_layer.update()

            # Delete the Objects
            for obj in objs:
                data = obj.data
                obj_type = obj.type
                bpy.data.objects.remove(obj)
                if obj_type == "MESH":
                    bpy.data.meshes.remove(data)
                elif obj_type == "ARMATURE":
                    bpy.data.armatures.remove(data)
                extras_deleted = extras_deleted + 1

            # Delete the collection if now empty
            items = (
                rig_settings.extras_collection.all_objects
                if rig_settings.outfit_config_subcollections
                else rig_settings.extras_collection.objects
            )
            if len(items) < 1:
                bpy.data.collections.remove(rig_settings.extras_collection)

            extras_deleted = extras_deleted + 1

            if addon_prefs.debug:
                print("  Extras deleted: " + str(extras_deleted))

        # Remove unselected hair
        if rig_settings.hair_collection is not None and self.remove_unselected_hair:
            current_hair = rig_settings.hair_list
            objs = [
                x
                for x in rig_settings.hair_collection.objects
                if current_hair not in x.name
            ]

            # Remove dangling Physics Items first
            items_to_remove = []
            for pi_id, item in enumerate(physics_settings.items):
                if (
                    item.outfit_enable
                    and item.outfit_collection == rig_settings.hair_collection
                    and item.outfit_object in objs
                    and item.object is not None
                ):
                    pi_obj = item.object
                    obj_name = pi_obj.name
                    try:
                        data = pi_obj.data
                        bpy.data.objects.remove(pi_obj)
                        bpy.data.meshes.remove(data)
                        if addon_prefs.debug:
                            print("  Physics item deleted: " + obj_name)
                    except:
                        if addon_prefs.debug:
                            print(
                                "  Physics item not deleted (error occurred): "
                                + obj_name
                            )
                        continue
                    items_to_remove.append(pi_id)
            for pi_id in reversed(items_to_remove):
                physics_settings.items.remove(pi_id)

            hair_cp = arm.MustardUI_CustomPropertiesHair

            # Firstly set the custom property to their default value
            for i, cp in enumerate(hair_cp):
                if cp.hair in objs:
                    mustardui_reassign_default(arm, hair_cp, i, addon_prefs)

            # Update everything
            if rig_settings.model_armature_object:
                rig_settings.model_armature_object.update_tag()
            bpy.context.view_layer.update()

            for obj in objs:
                data = obj.data
                obj_type = obj.type
                bpy.data.objects.remove(obj)
                if obj_type == "MESH":
                    bpy.data.meshes.remove(data)
                elif obj_type == "ARMATURE":
                    bpy.data.armatures.remove(data)
                hair_deleted = hair_deleted + 1

            rig_settings.hair_list = current_hair

            if addon_prefs.debug:
                print("  Hair deleted: " + str(hair_deleted))

        # Reset the Physics Items index
        index = arm.mustardui_physics_items_uilist_index
        index = min(max(0, index - 1), len(physics_settings.items) - 1)
        arm.mustardui_physics_items_uilist_index = index

        # Remove custom properties
        if self.remove_body_cp:
            body_cp_removed = mustardui_delete_all_custom_properties(
                arm, arm.MustardUI_CustomProperties, addon_prefs, rig_settings
            )
            print("  Body Custom Properties deleted: " + str(body_cp_removed))
        if self.remove_outfit_cp:
            outfit_cp_removed = mustardui_delete_all_custom_properties(
                arm, arm.MustardUI_CustomPropertiesOutfit, addon_prefs, rig_settings
            )
            print("  Outfit Custom Properties deleted: " + str(outfit_cp_removed))
        if self.remove_hair_cp:
            hair_cp_removed = mustardui_delete_all_custom_properties(
                arm, arm.MustardUI_CustomPropertiesHair, addon_prefs, rig_settings
            )
            print("  Hair Custom Properties deleted: " + str(hair_cp_removed))

        # after removing all custom properties, we check if there are any invalid or out of date drivers.
        if self.remove_body_cp or self.remove_outfit_cp or self.remove_hair_cp:
            mustardui_cleanup_dangling_drivers(rig_settings)
            mustardui_resync_drivers(rig_settings)

        # Final messages
        operations = (
            null_drivers_removed
            + morphs_props_removed
            + morphs_drivers_removed
            + morphs_shapekeys_removed
            + diffeomorphic_data_deleted
            + outfits_deleted
            + extras_deleted
            + hair_deleted
            + outfits_cp_deleted
            + body_cp_removed
            + outfit_cp_removed
            + hair_cp_removed
        )

        if operations > 0:
            self.report({"INFO"}, "MustardUI - Model cleaned.")
            rig_settings.model_cleaned = True
        else:
            self.report(
                {"WARNING"},
                "MustardUI - No operation was needed with current cleaning settings.",
            )

        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=500)

    def draw(self, context):
        res, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings
        morphs_settings = obj.MustardUI_MorphsSettings

        layout = self.layout

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Notes:")
        col.label(
            text="Read the descriptions of all buttons (keep the mouse on the buttons).",
            icon="DOT",
        )
        col.label(
            text="Do not use while producing, but before starting a project with the model.",
            icon="DOT",
        )
        col.label(
            text="This is a highly destructive operation! Use it at your own risk!",
            icon="ERROR",
        )

        box = layout.box()
        box.label(text="General", icon="MODIFIER")
        col = box.column(align=True)
        col.prop(self, "remove_unselected_outfits")
        if rig_settings.extras_collection is not None:
            col.prop(self, "remove_unselected_extras")
        if rig_settings.hair_collection is not None:
            col.prop(self, "remove_unselected_hair")
        col.prop(self, "remove_nulldrivers")

        box = layout.box()
        box.label(text="Custom Properties", icon="PROPERTIES")
        col = box.column(align=True)
        col.prop(self, "remove_body_cp")
        col.prop(self, "remove_outfit_cp")
        col.prop(self, "remove_hair_cp")

        if morphs_settings.enable_ui:
            if not hasattr(rig_settings.model_armature_object, "DazMorphCats"):
                box = layout.box()
                box.label(text="Diffeomorphic is needed to clean morphs!", icon="ERROR")

            box = layout.box()
            box.label(text="Diffeomorphic", icon="DOCUMENTS")
            box.enabled = hasattr(rig_settings.model_armature_object, "DazMorphCats")
            col = box.column(align=True)
            col.prop(self, "remove_morphs")
            if self.remove_morphs:
                col2 = col.column(align=True)
                col2.label(text="Morphs will be deleted!", icon="ERROR")
                col2.label(
                    text="Some bones of the Face rig might not work even if Remove Face Rig Morphs is disabled!",
                    icon="BLANK1",
                )
            row = col.row()
            row.enabled = self.remove_morphs
            row.prop(self, "remove_morphs_facs", text="Remove Face Rig Morphs")
            row = col.row()
            row.enabled = self.remove_morphs
            row.prop(self, "remove_morphs_jcms", text="Remove Corrective Morphs")
            row = col.row()
            row.enabled = self.remove_morphs
            row.prop(self, "remove_morphs_shapekeys")
            row = col.row()
            row.prop(self, "remove_diffeomorphic_data")
            if self.remove_diffeomorphic_data:
                col2 = col.column(align=True)
                col2.label(
                    text="After cleaning, Diffeomorphic tools might now work for this model!",
                    icon="ERROR",
                )
                col2.label(
                    text="Use this option when you are not planning to use Diffeomorphic for this model anymore.",
                    icon="BLANK1",
                )
                col2.label(
                    text="On the contrary, Morphs and face controls are NOT removed.",
                    icon="BLANK1",
                )


def register():
    bpy.utils.register_class(MustardUI_CleanModel)


def unregister():
    bpy.utils.unregister_class(MustardUI_CleanModel)
