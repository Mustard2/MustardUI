import bpy
from ..model_selection.active_object import *
from .misc import *
from .. import __package__ as base_package
from .misc import diffeomorphic_facs_bones_rot, diffeomorphic_facs_bones_loc


class MustardUI_DazMorphs_DisableDrivers(bpy.types.Operator):
    """Disable drivers to improve performance"""
    bl_idname = "mustardui.morphs_disabledrivers"
    bl_label = "Disable Drivers"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        morphs_settings = arm.MustardUI_MorphsSettings
        return res and morphs_settings.enable_ui

    # Function to prevent the DisableDriver operator to switch off custom properties drivers
    def check_driver(self, arm, datapath):

        for cp in arm.MustardUI_CustomProperties:
            if datapath in cp.rna + "." + cp.path:
                return False
        for cp in arm.MustardUI_CustomPropertiesOutfit:
            if datapath in cp.rna + "." + cp.path:
                return False
        for cp in arm.MustardUI_CustomPropertiesHair:
            if datapath in cp.rna + "." + cp.path:
                return False

        return True

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=0)
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
            muteDazFcurves(rig_settings.model_armature_object, True, True, True, True,
                           morphs_settings.diffeomorphic_enable_shapekeys, mutepJCM, mutefacs, check_bones_rot,
                           check_bones_loc, muteexceptions, exceptions)
            if hasattr(rig_settings.model_armature_object, 'DazDriversDisabled'):
                rig_settings.model_armature_object.DazDriversDisabled = True
        except:
            warnings = warnings + 1
            if addon_prefs.debug:
                print('MustardUI - Error occurred while muting Daz drivers.')

        for collection in [x for x in rig_settings.outfits_collections if x.collection]:
            items = collection.collection.all_objects if rig_settings.outfit_config_subcollections else collection.collection.objects
            for obj in items:
                if obj.type == "MESH":
                    objects.append(obj)

        for obj in objects:
            if obj.data.shape_keys is not None:
                if obj.data.shape_keys.animation_data is not None:
                    for driver in obj.data.shape_keys.animation_data.drivers:
                        if ((not "pJCM" in driver.data_path or mutepJCM) and
                                (not "facs" in driver.data_path or mutefacs) and
                                muteDazFcurves_exceptionscheck(muteexceptions, driver.data_path, exceptions) and
                                not "MustardUINotDisable" in driver.data_path):
                            driver.mute = self.check_driver(arm, driver.data_path)
                        else:
                            driver.mute = False

        for driver in rig_settings.model_armature_object.animation_data.drivers:
            if "evalMorphs" in driver.driver.expression:
                driver.mute = self.check_driver(arm, driver.data_path)

        context.view_layer.objects.active = aobj

        if warnings < 1:
            self.report({'INFO'}, 'MustardUI - Morphs disabled.')
        else:
            self.report({'WARNING'}, 'MustardUI - An error occurred while disabling morphs.')

        return {'FINISHED'}


class MustardUI_DazMorphs_EnableDrivers(bpy.types.Operator):
    """Enable all drivers"""
    bl_idname = "mustardui.morphs_enabledrivers"
    bl_label = "Enable Drivers"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        morphs_settings = arm.MustardUI_MorphsSettings
        return res and morphs_settings.enable_ui

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=0)
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
            muteDazFcurves(rig_settings.model_armature_object, False, True, True, True,
                           morphs_settings.diffeomorphic_enable_shapekeys, mutepJCM, mutefacs, check_bones_rot,
                           check_bones_loc, muteexceptions, exceptions)
            if hasattr(rig_settings.model_armature_object, 'DazDriversDisabled'):
                rig_settings.model_armature_object.DazDriversDisabled = False
        except:
            warnings = warnings + 1
            if addon_prefs.debug:
                print('MustardUI - Error occurred while un-muting Daz drivers.')

        for collection in [x for x in rig_settings.outfits_collections if x.collection is not None]:
            items = collection.collection.all_objects if rig_settings.outfit_config_subcollections else collection.collection.objects
            for obj in items:
                if obj.type == "MESH":
                    objects.append(obj)

        # Disable Shape Keys
        for obj in objects:
            if obj.data.shape_keys:
                if obj.data.shape_keys.animation_data:
                    for driver in obj.data.shape_keys.animation_data.drivers:
                        if (not ("pJCM" in driver.data_path or mutepJCM)
                                and not ("facs" in driver.data_path or mutefacs)
                                and muteDazFcurves_exceptionscheck(muteexceptions, driver.data_path, exceptions)
                                and not ("MustardUINotDisable" in driver.data_path)):
                            driver.mute = False

        for driver in rig_settings.model_armature_object.animation_data.drivers:
            if "evalMorphs" in driver.driver.expression or driver.driver.expression == "0.0" or driver.driver.expression == "-0.0":
                driver.mute = False

        context.view_layer.objects.active = aobj

        if warnings < 1:
            self.report({'INFO'}, 'MustardUI - Morphs enabled.')
        else:
            self.report({'WARNING'}, 'MustardUI - An error occurred while enabling morphs.')

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_DazMorphs_DisableDrivers)
    bpy.utils.register_class(MustardUI_DazMorphs_EnableDrivers)


def unregister():
    bpy.utils.unregister_class(MustardUI_DazMorphs_EnableDrivers)
    bpy.utils.unregister_class(MustardUI_DazMorphs_DisableDrivers)
