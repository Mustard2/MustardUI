import bpy

from .. import __package__ as base_package
from ..misc.set_bool import set_bool
from ..model_selection.active_object import (
    ModelMode,
    active_object_operator_poll,
    mustardui_active_object,
)
from .misc import (
    diffeomorphic_facs_bones_loc,
    diffeomorphic_facs_bones_rot,
    muteDazFcurves,
    muteDazFcurves_exceptionscheck,
)


class MustardUI_DazMorphs_DisableDrivers(bpy.types.Operator):
    """Disable drivers to improve performance"""

    bl_idname = "mustardui.morphs_disabledrivers"
    bl_label = "Disable Drivers"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if not active_object_operator_poll(context, config=ModelMode.USER):
            return False

        res, arm = mustardui_active_object(context, config=ModelMode.USER)
        morphs_settings = arm.MustardUI_MorphsSettings
        return morphs_settings.enable_ui

    # Paths of the custom properties, joined once per run ("\n" is never in a data path)
    def custom_properties_paths(self, arm):
        custom_properties = [
            *arm.MustardUI_CustomProperties,
            *arm.MustardUI_CustomPropertiesOutfit,
            *arm.MustardUI_CustomPropertiesHair,
        ]
        return "\n".join(cp.rna + "." + cp.path for cp in custom_properties)

    # Function to prevent the DisableDriver operator to switch off custom
    # properties drivers
    def check_driver(self, cp_paths, datapath):
        return datapath not in cp_paths

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=ModelMode.USER)
        rig_settings = arm.MustardUI_RigSettings
        morphs_settings = arm.MustardUI_MorphsSettings
        addon_prefs = context.preferences.addons[base_package].preferences

        objects = [rig_settings.model_body]
        aobj = context.active_object
        context.view_layer.objects.active = rig_settings.model_armature_object

        warnings = 0
        cp_paths = self.custom_properties_paths(arm)

        mutepJCM = morphs_settings.diffeomorphic_enable_pJCM

        mutefacs = morphs_settings.diffeomorphic_enable_facs
        mutefacs_bones = True if mutefacs else morphs_settings.diffeomorphic_enable_facs_bones
        check_bones_rot = diffeomorphic_facs_bones_rot if not mutefacs_bones else []
        check_bones_loc = diffeomorphic_facs_bones_loc if not mutefacs_bones else []

        muteexceptions = False
        exceptions = morphs_settings.diffeomorphic_disable_exceptions

        try:
            muteDazFcurves(
                rig_settings.model_armature_object,
                True,
                True,
                True,
                True,
                morphs_settings.diffeomorphic_enable_shapekeys,
                mutepJCM,
                mutefacs,
                check_bones_rot,
                check_bones_loc,
                muteexceptions,
                exceptions,
            )
            if hasattr(rig_settings.model_armature_object, "DazDriversDisabled"):
                rig_settings.model_armature_object.DazDriversDisabled = True
        except Exception:
            warnings = warnings + 1
            if addon_prefs.debug:
                print("MustardUI - Error occurred while muting Daz drivers.")

        for collection in [x for x in rig_settings.outfits_collections if x.collection]:
            items = (
                collection.collection.all_objects
                if rig_settings.outfit_config_subcollections
                else collection.collection.objects
            )
            for obj in items:
                if obj.type == "MESH":
                    objects.append(obj)

        for obj in objects:
            if obj.data.shape_keys is not None:
                if obj.data.shape_keys.animation_data is not None:
                    for driver in obj.data.shape_keys.animation_data.drivers:
                        if (
                            ("pJCM" not in driver.data_path or mutepJCM)
                            and ("facs" not in driver.data_path or mutefacs)
                            and muteDazFcurves_exceptionscheck(
                                muteexceptions, driver.data_path, exceptions
                            )
                            and "MustardUINotDisable" not in driver.data_path
                        ):
                            set_bool(driver, "mute", self.check_driver(cp_paths, driver.data_path))
                        else:
                            set_bool(driver, "mute", False)

        animation_data = rig_settings.model_armature_object.animation_data
        if animation_data is not None:
            for driver in animation_data.drivers:
                if "evalMorphs" in driver.driver.expression:
                    set_bool(driver, "mute", self.check_driver(cp_paths, driver.data_path))

        context.view_layer.objects.active = aobj

        if warnings < 1:
            self.report({"INFO"}, "MustardUI - Morphs disabled.")
        else:
            self.report({"WARNING"}, "MustardUI - An error occurred while disabling morphs.")

        return {"FINISHED"}


class MustardUI_DazMorphs_EnableDrivers(bpy.types.Operator):
    """Enable all drivers"""

    bl_idname = "mustardui.morphs_enabledrivers"
    bl_label = "Enable Drivers"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if not active_object_operator_poll(context, config=ModelMode.USER):
            return False

        res, arm = mustardui_active_object(context, config=ModelMode.USER)
        morphs_settings = arm.MustardUI_MorphsSettings
        return morphs_settings.enable_ui

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=ModelMode.USER)
        rig_settings = arm.MustardUI_RigSettings
        morphs_settings = arm.MustardUI_MorphsSettings
        addon_prefs = context.preferences.addons[base_package].preferences

        objects = [rig_settings.model_body]
        aobj = context.active_object
        context.view_layer.objects.active = rig_settings.model_armature_object

        warnings = 0

        mutepJCM = morphs_settings.diffeomorphic_enable_pJCM

        mutefacs = morphs_settings.diffeomorphic_enable_facs
        mutefacs_bones = True if mutefacs else morphs_settings.diffeomorphic_enable_facs_bones
        check_bones_rot = diffeomorphic_facs_bones_rot if not mutefacs_bones else []
        check_bones_loc = diffeomorphic_facs_bones_loc if not mutefacs_bones else []

        muteexceptions = False
        exceptions = morphs_settings.diffeomorphic_disable_exceptions

        try:
            muteDazFcurves(
                rig_settings.model_armature_object,
                False,
                True,
                True,
                True,
                morphs_settings.diffeomorphic_enable_shapekeys,
                mutepJCM,
                mutefacs,
                check_bones_rot,
                check_bones_loc,
                muteexceptions,
                exceptions,
            )
            if hasattr(rig_settings.model_armature_object, "DazDriversDisabled"):
                rig_settings.model_armature_object.DazDriversDisabled = False
        except Exception:
            warnings = warnings + 1
            if addon_prefs.debug:
                print("MustardUI - Error occurred while un-muting Daz drivers.")

        for collection in [x for x in rig_settings.outfits_collections if x.collection is not None]:
            items = (
                collection.collection.all_objects
                if rig_settings.outfit_config_subcollections
                else collection.collection.objects
            )
            for obj in items:
                if obj.type == "MESH":
                    objects.append(obj)

        # Enable Shape Keys drivers
        for obj in objects:
            if obj.data.shape_keys:
                if obj.data.shape_keys.animation_data:
                    for driver in obj.data.shape_keys.animation_data.drivers:
                        if (
                            ("pJCM" not in driver.data_path or mutepJCM)
                            and ("facs" not in driver.data_path or mutefacs)
                            and muteDazFcurves_exceptionscheck(
                                muteexceptions, driver.data_path, exceptions
                            )
                            and "MustardUINotDisable" not in driver.data_path
                        ):
                            set_bool(driver, "mute", False)

        animation_data = rig_settings.model_armature_object.animation_data
        if animation_data is not None:
            for driver in animation_data.drivers:
                if (
                    "evalMorphs" in driver.driver.expression
                    or driver.driver.expression == "0.0"
                    or driver.driver.expression == "-0.0"
                ):
                    set_bool(driver, "mute", False)

        context.view_layer.objects.active = aobj

        if warnings < 1:
            self.report({"INFO"}, "MustardUI - Morphs enabled.")
        else:
            self.report({"WARNING"}, "MustardUI - An error occurred while enabling morphs.")

        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_DazMorphs_DisableDrivers)
    bpy.utils.register_class(MustardUI_DazMorphs_EnableDrivers)


def unregister():
    bpy.utils.unregister_class(MustardUI_DazMorphs_EnableDrivers)
    bpy.utils.unregister_class(MustardUI_DazMorphs_DisableDrivers)
