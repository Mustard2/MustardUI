import bpy
from bpy.props import *
from ..model_selection.active_object import *
import os


def tab(n=1):
    return "\t" * n


def new_line(n=1):
    return "\n" * n


def bar(l=15):
    return "-" * l + new_line()


def addon_status(status, addon_name, tabs=2):
    if status == 2:
        return addon_name + " status:" + tab(tabs) + "Correctly installed and enabled" + new_line()
    elif status == 1:
        return addon_name + " status:" + tab(tabs) + "Installed but not enabled" + new_line()
    else:
        return addon_name + " status:" + tab(
            tabs) + "Not correctly installed or wrong add-on folder name" + new_line()


def header(name):
    return bar() + name + new_line() + new_line()


class MustardUI_Debug_Log(bpy.types.Operator):
    """Create a file with information to debug errors.\nThis tool will only write on a .txt file and will NOT change any model or Blender setting"""
    bl_idname = "mustardui.debug_log"
    bl_label = "Generate Log File"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=1)
        return arm is not None

    def execute(self, context):

        settings = bpy.context.scene.MustardUI_Settings
        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings
        physics_settings = arm.MustardUI_PhysicsSettings
        morphs_settings = arm.MustardUI_MorphsSettings

        tabs_num = 4

        log = ""

        # Create logs

        # System
        log += header("System")

        log += "Blender version:" + tab(tabs_num - 1) + bpy.app.version_string
        log += new_line()

        if bpy.context.preferences.addons['cycles']:

            device_type = bpy.context.preferences.addons['cycles'].preferences.compute_device_type

            log += "Device type:" + tab(tabs_num) + device_type
            log += new_line()

            log += "Devices"
            log += new_line()
            for device in [x for x in bpy.context.preferences.addons['cycles'].preferences.devices if
                           (x.type == device_type or x.type == "CPU")]:
                log += tab() + '- '
                if device.use:
                    log += "[active] "
                log += device.name
                log += new_line()

        log += new_line(2)

        # Model
        log += header("Model")

        log += "Model name:" + tab(tabs_num) + rig_settings.model_name
        log += new_line()
        if rig_settings.model_version != '':
            log += "Model version:" + tab(tabs_num) + rig_settings.model_version
            log += new_line()
        log += new_line()
        log += "Model rig type:" + tab(tabs_num - 1) + rig_settings.model_rig_type
        log += new_line()
        log += "Model cleaned:" + tab(tabs_num) + str(rig_settings.model_cleaned)
        log += new_line(2)

        log += "Custom Properties:"
        log += new_line()
        body_cp = len(arm.MustardUI_CustomProperties)
        log += tab() + "- Body: " + tab(tabs_num) + str(body_cp)
        log += new_line()
        outf_cp = len(arm.MustardUI_CustomPropertiesOutfit)
        log += tab() + "- Outfit: " + tab(tabs_num - 1) + str(outf_cp)
        log += new_line()
        hair_cp = len(arm.MustardUI_CustomPropertiesHair)
        log += tab() + "- Hair: " + tab(tabs_num) + str(hair_cp)
        log += new_line()
        log += tab() + "Total: " + tab(tabs_num) + str(body_cp + outf_cp + hair_cp)

        log += new_line(3)

        # Diffeomorphic
        if morphs_settings.enable_ui:
            log += header("Morphs")

            log += new_line()
            log += "Morphs: " + tab(tabs_num + 1) + str(morphs_settings.morphs_number)
            log += new_line()

            log += new_line(3)

        # Viewport
        log += header("Viewport")

        if rig_settings.simplify_main_enable:
            log += "Simplify status:" + tab(tabs_num - 1) + (
                "Enabled" if rig_settings.simplify_enable else "Disabled")
            log += new_line()

        log += "Custom normals:" + tab(tabs_num - 1) + (
            "Disabled" if not settings.material_normal_nodes else "Enabled")
        log += new_line()

        if morphs_settings.enable_ui:
            log += "Morphs:" + tab(tabs_num + 1) + ("Enabled" if morphs_settings.diffeomorphic_enable else "Disabled")
            log += new_line()

        if len(physics_settings.items) > 0:
            log += "Physics:" + tab(tabs_num) + ("Enabled" if physics_settings.enable_physics else "Disabled")
            log += new_line()
            log += "- Physics items:" + tab(tabs_num) + str(len(physics_settings.items))
            log += new_line()

        if rig_settings.hair_collection is not None:
            log += "Hair status:" + tab(tabs_num) + (
                "Hidden" if rig_settings.hair_collection.hide_viewport else "Shown")
            log += new_line()
        if rig_settings.extras_collection is not None:
            log += "Extras status:" + tab(tabs_num) + (
                "Hidden" if rig_settings.extras_collection.hide_viewport else "Shown")
            log += new_line()

        log += new_line()

        # Write to file
        try:
            abs_path = os.path.join(bpy.path.abspath("//"), 'mustardui_log.txt')
            log_file = open(abs_path, 'w')
            log_file.write(log)
            log_file.close()

            self.report({'INFO'}, "MustardUI - A log file 'mustardui_log.txt' has been created in the model folder.")
        except:
            self.report({'WARNING'}, "MustardUI - Cannot create a log file. Try to run Blender with admin privilegies.")

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_Debug_Log)


def unregister():
    bpy.utils.unregister_class(MustardUI_Debug_Log)
