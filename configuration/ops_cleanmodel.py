import bpy
from bpy.props import *
from ..custom_properties.misc import mustardui_clean_prop
from ..model_selection.active_object import *


class MustardUI_CleanModel(bpy.types.Operator):
    """Clean the model to get better performance, at the cost of deleting some features/shape keys/morphs/outfits"""
    bl_idname = "mustardui.cleanmodel"
    bl_label = "Clean Model"
    bl_options = {'UNDO'}

    remove_body_cp: BoolProperty(default=False,
                                 name="Remove Body Custom Properties")
    remove_outfit_cp: BoolProperty(default=False,
                                   name="Remove Outfit Custom Properties")
    remove_hair_cp: BoolProperty(default=False,
                                 name="Remove Hair Custom Properties")

    remove_unselected_outfits: BoolProperty(default=False,
                                            name="Delete Unselected Outfits",
                                            description="Remove all the outfits that are not selected in the UI ("
                                                        "Outfits list)")
    remove_unselected_extras: BoolProperty(default=False,
                                           name="Delete Unselected Extras",
                                           description="Remove all the Extras objects that are not selected in the UI")
    remove_unselected_hair: BoolProperty(default=False,
                                         name="Delete Unselected Hair",
                                         description="Remove all the Hair that are not currently in use")

    remove_nulldrivers: BoolProperty(default=False,
                                     name="Remove Null Drivers",
                                     description="Remove drivers whose equations are \'0.0\' or \'-0.0\'")

    remove_morphs: BoolProperty(default=False,
                                name="Remove Morphs",
                                description="Remove all morphs (except JCMs and FACS if not enabled below)")
    remove_morphs_shapekeys: BoolProperty(default=False,
                                          name="Remove Shape Keys",
                                          description="Remove selected morphs shape keys")
    remove_morphs_jcms: BoolProperty(default=False,
                                     name="Remove JCMs",
                                     description="Remove JCMs")
    remove_morphs_facs: BoolProperty(default=False,
                                     name="Remove FACS",
                                     description="Remove FACS (Advanced Emotions)")
    remove_diffeomorphic_data: BoolProperty(default=False,
                                            name="Remove Diffeomorphic Data",
                                            description="Remove Diffeomorphic data.\nAfter this operation, Morph "
                                                        "settings in the DAZ Importer (Diffeomorphic) tool might not "
                                                        "work")

    def isDazFcurve(self, path):
        for string in [":Loc:", ":Rot:", ":Sca:", ":Hdo:", ":Tlo"]:
            if string in path:
                return True
        return False

    def remove_props_from_group(self, obj, group, props_removed):

        if hasattr(obj, group):
            props = eval("obj." + group)
            idx = []
            for n, prop in enumerate(props):
                prop_name = prop.name
                if not "pJCM" in prop.name or self.remove_morphs_jcms:
                    idx.append(n)
                    props_removed.append(prop.name)

            for i in reversed(idx):
                props.remove(i)

        return props_removed

    def remove_props_from_cat_group(self, obj, group, props_removed):

        if hasattr(obj, group):
            categories = eval("obj." + group)
            for cat in categories:
                props = cat['morphs']
                idx = []
                for n, prop in enumerate(props):
                    if "name" in prop:
                        prop_name = prop['name']
                        if not "pJCM" in prop_name or self.remove_morphs_jcms:
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
        check_pJCM = not "pJCM" in string_cmp or self.remove_morphs_jcms
        check_facs = not "facs" in string_cmp or self.remove_morphs_facs

        return (string == string_cmp or check_eCTRL or check_eJCM) and check_pJCM and check_facs

    def remove_cps(self, arm, uilist, settings):

        to_remove = []
        for i, cp in enumerate(uilist):
            mustardui_clean_prop(arm, uilist, i, settings)
            to_remove.append(i)
        for i in reversed(to_remove):
            uilist.remove(i)

        return len(to_remove)

    def remove_diffeomorphic_data_result(self, obj, attr):

        try:
            del obj[attr]
            return 1
        except:
            return 0

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        return res

    def execute(self, context):

        settings = bpy.context.scene.MustardUI_Settings
        res, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings

        options = self.remove_nulldrivers or self.remove_morphs or self.remove_diffeomorphic_data or self.remove_unselected_outfits or self.remove_unselected_extras or self.remove_unselected_hair or self.remove_body_cp or self.remove_outfit_cp or self.remove_hair_cp

        if not options:
            return {'FINISHED'}

        if settings.debug:
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

            for obj in [x for x in bpy.data.objects if x.type == "MESH"]:
                if obj.animation_data is not None:
                    drivers = obj.animation_data.drivers
                    for driver in drivers:
                        if driver.driver.expression == "0.0" or driver.driver.expression == "-0.0":
                            drivers.remove(driver)
                            null_drivers_removed = null_drivers_removed + 1
                if obj.data.shape_keys is not None:
                    if obj.data.shape_keys.animation_data is not None:
                        drivers = obj.data.shape_keys.animation_data.drivers
                        for driver in drivers:
                            if driver.driver.expression == "0.0" or driver.driver.expression == "-0.0":
                                drivers.remove(driver)
                                morphs_drivers_removed = morphs_drivers_removed + 1

            if settings.debug:
                print("  Null drivers removed: " + str(null_drivers_removed))

        # Check diffeomorphic custom morphs existance and delete all of them (except JCMs)
        if self.remove_morphs:

            props_removed = []

            # Add props to the removed list from the armature
            if self.remove_morphs_jcms:
                props_removed = self.remove_props_from_group(rig_settings.model_armature_object,
                                                             "DazStandardjcms", props_removed)
                props_removed.append("pJCM")
            if self.remove_morphs_facs:
                props_removed = self.remove_props_from_group(rig_settings.model_armature_object,
                                                             "DazFacs", props_removed)
                props_removed.append("facs")
            props_removed = self.remove_props_from_group(rig_settings.model_armature_object,
                                                         "DazUnits", props_removed)
            props_removed = self.remove_props_from_group(rig_settings.model_armature_object,
                                                         "DazExpressions", props_removed)
            props_removed = self.remove_props_from_group(rig_settings.model_armature_object,
                                                         "DazBody", props_removed)
            props_removed = self.remove_props_from_group(rig_settings.model_armature_object,
                                                         "DazCustom", props_removed)
            props_removed = self.remove_props_from_group(rig_settings.model_armature_object,
                                                         "DazCustom", props_removed)
            props_removed = self.remove_props_from_cat_group(rig_settings.model_armature_object,
                                                             "DazMorphCats", props_removed)

            # Add props to the removed list from the body
            if self.remove_morphs_jcms:
                props_removed = self.remove_props_from_group(rig_settings.model_body,
                                                             "DazStandardjcms", props_removed)
            if self.remove_morphs_facs:
                props_removed = self.remove_props_from_group(rig_settings.model_body,
                                                             "DazFacs", props_removed)
            props_removed = self.remove_props_from_group(rig_settings.model_body,
                                                         "DazUnits", props_removed)
            props_removed = self.remove_props_from_group(rig_settings.model_body,
                                                         "DazExpressions", props_removed)
            props_removed = self.remove_props_from_group(rig_settings.model_body,
                                                         "DazBody", props_removed)
            props_removed = self.remove_props_from_group(rig_settings.model_body,
                                                         "DazCustom", props_removed)
            props_removed = self.remove_props_from_cat_group(rig_settings.model_body,
                                                             "DazMorphCats", props_removed)

            # Remove unused drivers and shape keys
            aobj = context.active_object
            context.view_layer.objects.active = rig_settings.model_armature_object

            # Find objects where to remove drivers and shape keys
            objects = [rig_settings.model_body]

            for collection in [x for x in [y for y in rig_settings.outfits_collections if y.collection is not None] if
                               x.collection is not None]:
                items = collection.collection.all_objects if rig_settings.outfit_config_subcollections else collection.collection.objects
                for obj in items:
                    if obj.type == "MESH":
                        objects.append(obj)
            if rig_settings.extras_collection is not None:
                items = rig_settings.extras_collection.all_objects if rig_settings.outfit_config_subcollections else rig_settings.extras_collection.objects
                for obj in items:
                    if obj.type == "MESH":
                        objects.append(obj)
            for obj in bpy.data.objects:
                if obj.find_armature() == rig_settings.model_armature_object and obj.type == "MESH":
                    objects.append(obj)

            # Remove shape keys and their drivers
            for obj in objects:
                if obj.data.shape_keys is not None:
                    if obj.data.shape_keys.animation_data is not None:
                        drivers = obj.data.shape_keys.animation_data.drivers
                        for driver in drivers:
                            words = driver.data_path.split('"')
                            for cp in props_removed:
                                if words[0] == "key_blocks[" and self.check_removal(cp, words[1]):
                                    drivers.remove(driver)
                                    morphs_drivers_removed = morphs_drivers_removed + 1
                                    break
                    if self.remove_morphs_shapekeys:
                        for sk in obj.data.shape_keys.key_blocks:
                            for cp in props_removed:
                                if self.check_removal(cp, sk.name):
                                    obj.shape_key_remove(sk)
                                    morphs_shapekeys_removed = morphs_shapekeys_removed + 1
                                    break

                obj.update_tag()

            # Remove drivers from objects
            objects.append(arm)
            for obj in objects:
                if obj.animation_data is not None:
                    if obj.animation_data.drivers is not None:
                        drivers = obj.animation_data.drivers
                        for driver in drivers:
                            ddelete = "evalMorphs" in driver.driver.expression or driver.driver.expression == "0.0" or driver.driver.expression == "-0.0"
                            for cp in props_removed:
                                ddelete = ddelete or (self.check_removal(cp, driver.data_path) or self.isDazFcurve(
                                    driver.data_path))
                                for v in driver.driver.variables:
                                    ddelete = ddelete or cp in v.targets[0].data_path
                            if ddelete:
                                drivers.remove(driver)
                                morphs_drivers_removed = morphs_drivers_removed + 1
                        obj.update_tag()

            # Remove drivers from bones
            for bone in [x for x in rig_settings.model_armature_object.pose.bones if "(drv)" in x.name]:
                bone.driver_remove('location')
                bone.driver_remove('rotation_euler')
                bone.driver_remove('scale')

            context.view_layer.objects.active = aobj

            # Remove custom properties from armature
            for cp in props_removed:
                for kp in [x for x in rig_settings.model_armature_object.keys()]:
                    if self.check_removal(cp, kp) or self.isDazFcurve(kp):
                        del rig_settings.model_armature_object[kp]
                        morphs_props_removed = morphs_props_removed + 1
                for kp in [x for x in arm.keys()]:
                    if self.check_removal(cp, kp) or self.isDazFcurve(kp):
                        del arm[kp]
                        morphs_props_removed = morphs_props_removed + 1

            # Remove diffeomorphic support from the UI to avoid errors in the UI, or restore it if FACS are asked
            if not self.remove_morphs_facs:
                rig_settings.diffeomorphic_morphs_list.clear()
                rig_settings.diffeomorphic_body_morphs = False
                rig_settings.diffeomorphic_emotions = False
                rig_settings.diffeomorphic_emotions_units = False
                bpy.ops.mustardui.configuration()
                bpy.ops.mustardui.dazmorphs_checkmorphs()
                bpy.ops.mustardui.configuration()
            else:
                rig_settings.diffeomorphic_morphs_list.clear()
                rig_settings.diffeomorphic_support = False

            if settings.debug:
                print("  Morph properties removed: " + str(morphs_props_removed))
                print("  Morph drivers removed: " + str(morphs_drivers_removed))
                print("  Morph shape keys removed: " + str(morphs_shapekeys_removed))

        if self.remove_diffeomorphic_data:

            objects = [rig_settings.model_body, rig_settings.model_body.data]

            dd_colls = [x.collection for x in rig_settings.outfits_collections if x.collection is not None]
            if rig_settings.extras_collection is not None:
                dd_colls.append(rig_settings.extras_collection)
            if rig_settings.hair_collection is not None:
                dd_colls.append(rig_settings.hair_collection)

            for col in dd_colls:
                items = col.all_objects if rig_settings.outfit_config_subcollections else col.objects
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
                    diffeomorphic_data_deleted = diffeomorphic_data_deleted + self.remove_diffeomorphic_data_result(obj,
                                                                                                                    k)
                obj.update_tag()

            if settings.debug:
                print("  Diffeomorphic Data Blocks removed: " + str(diffeomorphic_data_deleted))

        # Remove unselected outfits
        if self.remove_unselected_outfits:

            current_outfit = rig_settings.outfits_list

            to_remove = [x.collection for x in [y for y in rig_settings.outfits_collections if y.collection is not None]
                         if x.collection.name != current_outfit]

            for col in to_remove:

                # Find the index of the collection to remove
                i = 0
                for v in rig_settings.outfits_collections:
                    if v.collection == col:
                        break
                    i += 1

                context.scene.mustardui_outfits_uilist_index = i
                bpy.ops.mustardui.delete_outfit()
                outfits_deleted = outfits_deleted + 1

            rig_settings.outfits_list = current_outfit

            if settings.debug:
                print("  Outfits deleted: " + str(outfits_deleted))

        # Remove unselected extras
        if rig_settings.extras_collection is not None and self.remove_unselected_extras:

            items = rig_settings.extras_collection.all_objects if rig_settings.outfit_config_subcollections else rig_settings.extras_collection.objects
            for obj in [x for x in items if x.hide_viewport]:
                data = obj.data
                obj_type = obj.type
                bpy.data.objects.remove(obj)
                if obj_type == "MESH":
                    bpy.data.meshes.remove(data)
                elif obj_type == "ARMATURE":
                    bpy.data.armatures.remove(data)
                extras_deleted = extras_deleted + 1

            items = rig_settings.extras_collection.all_objects if rig_settings.outfit_config_subcollections else rig_settings.extras_collection.objects
            if len(items) < 1:
                bpy.data.collections.remove(rig_settings.extras_collection)

            extras_deleted = extras_deleted + 1

            if settings.debug:
                print("  Extras deleted: " + str(extras_deleted))

        # Remove unselected hair
        if rig_settings.hair_collection is not None and self.remove_unselected_hair:

            current_hair = rig_settings.hair_list

            for obj in [x for x in rig_settings.hair_collection.objects if not current_hair in x.name]:
                data = obj.data
                obj_type = obj.type
                bpy.data.objects.remove(obj)
                if obj_type == "MESH":
                    bpy.data.meshes.remove(data)
                elif obj_type == "ARMATURE":
                    bpy.data.armatures.remove(data)
                hair_deleted = hair_deleted + 1

            rig_settings.hair_list = current_hair

            if settings.debug:
                print("  Hair deleted: " + str(hair_deleted))

        # Remove custom properties
        if self.remove_body_cp:
            body_cp_removed = self.remove_cps(arm, arm.MustardUI_CustomProperties, settings)
            print("  Body Custom Properties deleted: " + str(body_cp_removed))
        if self.remove_outfit_cp:
            outfit_cp_removed = self.remove_cps(arm, arm.MustardUI_CustomPropertiesOutfit, settings)
            print("  Outfit Custom Properties deleted: " + str(outfit_cp_removed))
        if self.remove_hair_cp:
            hair_cp_removed = self.remove_cps(arm, arm.MustardUI_CustomPropertiesHair, settings)
            print("  Hair Custom Properties deleted: " + str(hair_cp_removed))

        # Final messages
        operations = (null_drivers_removed + morphs_props_removed + morphs_drivers_removed + morphs_shapekeys_removed
                      + diffeomorphic_data_deleted + outfits_deleted + extras_deleted + hair_deleted
                      + outfits_cp_deleted + body_cp_removed + outfit_cp_removed + hair_cp_removed)

        if operations > 0:
            self.report({'INFO'}, "MustardUI - Model cleaned.")
            rig_settings.model_cleaned = True
        else:
            self.report({'WARNING'}, "MustardUI - No operation was needed with current cleaning settings.")

        return {'FINISHED'}

    def invoke(self, context, event):

        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings

        return context.window_manager.invoke_props_dialog(self, width=500)

    def draw(self, context):

        settings = bpy.context.scene.MustardUI_Settings
        res, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings
        sec_obj = rig_settings.body_custom_properties_sections

        layout = self.layout

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Notes:")
        col.label(text="Read the descriptions of all buttons (keep the mouse on the buttons).", icon="DOT")
        col.label(text="Do not use while producing, but before starting a project with the model.", icon="DOT")
        col.label(text="This is a highly destructive operation! Use it at your own risk!", icon="ERROR")

        box = layout.box()
        box.label(text="General", icon="MODIFIER")
        box.prop(self, "remove_unselected_outfits")
        if rig_settings.extras_collection != None:
            box.prop(self, "remove_unselected_extras")
        if rig_settings.hair_collection != None:
            box.prop(self, "remove_unselected_hair")
        box.prop(self, "remove_nulldrivers")

        box = layout.box()
        box.label(text="Custom Properties", icon="PROPERTIES")
        box.prop(self, "remove_body_cp")
        box.prop(self, "remove_outfit_cp")
        box.prop(self, "remove_hair_cp")

        if rig_settings.diffeomorphic_support:

            if not hasattr(rig_settings.model_armature_object, "DazMorphCats"):
                box = layout.box()
                box.label(text="Diffeomorphic is needed to clean morphs!", icon="ERROR")

            box = layout.box()
            box.label(text="Diffeomorphic", icon="DOCUMENTS")
            box.enabled = hasattr(rig_settings.model_armature_object, "DazMorphCats")
            box.prop(self, "remove_morphs")
            if self.remove_morphs:
                col = box.column(align=True)
                col.label(text="Morphs will be deleted!", icon="ERROR")
                col.label(text="Some bones of the Face rig might not work even if Remove Face Rig Morphs is disabled!",
                          icon="BLANK1")
            row = box.row()
            row.enabled = self.remove_morphs
            row.prop(self, "remove_morphs_facs", text="Remove Face Rig Morphs")
            row = box.row()
            row.enabled = self.remove_morphs
            row.prop(self, "remove_morphs_jcms", text="Remove Corrective Morphs")
            row = box.row()
            row.enabled = self.remove_morphs
            row.prop(self, "remove_morphs_shapekeys")
            row = box.row()
            row.prop(self, "remove_diffeomorphic_data")
            if self.remove_diffeomorphic_data:
                col = box.column(align=True)
                col.label(text="After cleaning, Diffeomorphic tools might now work for this model!", icon="ERROR")
                col.label(text="Use this option when you are not planning to use Diffeomorphic for this model anymore.",
                          icon="BLANK1")
                col.label(text="On the contrary, Morphs and face controls are NOT removed.", icon="BLANK1")


def register():
    bpy.utils.register_class(MustardUI_CleanModel)


def unregister():
    bpy.utils.unregister_class(MustardUI_CleanModel)
