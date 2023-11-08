import bpy
from bpy.props import *
from ..model_selection.active_object import *


class MustardUI_Debug_Log(bpy.types.Operator):
    """Create a file with information to debug errors.\nThis tool will only write on a .txt file and will NOT change any model or Blender setting"""
    bl_idname = "mustardui.debug_log"
    bl_label = "Generate Log File"
    bl_options = {'REGISTER'}

    def new_line(self, n=1):
        return "\n" * n

    def tab(self, n=1):
        return "\t" * n

    def bar(self, l=15):
        return "-" * l + self.new_line()

    def header(self, name):
        return self.bar() + name + self.new_line() + self.new_line()

    def addon_status(self, status, addon_name, tabs=2):
        if status == 2:
            return addon_name + " status:" + self.tab(tabs) + "Correctly installed and enabled" + self.new_line()
        elif status == 1:
            return addon_name + " status:" + self.tab(tabs) + "Installed but not enabled" + self.new_line()
        else:
            return addon_name + " status:" + self.tab(
                tabs) + "Not correctly installed or wrong add-on folder name" + self.new_line()

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=1)
        return arm is not None

    def execute(self, context):

        settings = bpy.context.scene.MustardUI_Settings
        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings
        physics_settings = arm.MustardUI_PhysicsSettings

        tabs_num = 4

        log = ""

        # Create logs

        # System
        log += self.header("System")

        log += "Blender version:" + self.tab(tabs_num - 1) + bpy.app.version_string
        log += self.new_line()

        if bpy.context.preferences.addons['cycles']:

            device_type = bpy.context.preferences.addons['cycles'].preferences.compute_device_type

            log += "Device type:" + self.tab(tabs_num) + device_type
            log += self.new_line()

            log += "Devices"
            log += self.new_line()
            for device in [x for x in bpy.context.preferences.addons['cycles'].preferences.devices if
                           (x.type == device_type or x.type == "CPU")]:
                log += self.tab() + '- '
                if device.use:
                    log += "[active] "
                log += device.name
                log += self.new_line()

        log += self.new_line(2)

        # Model
        log += self.header("Model")

        log += "Model name:" + self.tab(tabs_num) + rig_settings.model_name
        log += self.new_line()
        if rig_settings.model_version != '':
            log += "Model version:" + self.tab(tabs_num) + rig_settings.model_version
            log += self.new_line()
        log += self.new_line()
        log += "Model rig type:" + self.tab(tabs_num - 1) + rig_settings.model_rig_type
        log += self.new_line()
        log += "Model cleaned:" + self.tab(tabs_num) + str(rig_settings.model_cleaned)
        log += self.new_line(2)

        log += "Custom Properties:"
        log += self.new_line()
        body_cp = len(arm.MustardUI_CustomProperties)
        log += self.tab() + "- Body: " + self.tab(tabs_num) + str(body_cp)
        log += self.new_line()
        outf_cp = len(arm.MustardUI_CustomPropertiesOutfit)
        log += self.tab() + "- Outfit: " + self.tab(tabs_num - 1) + str(outf_cp)
        log += self.new_line()
        hair_cp = len(arm.MustardUI_CustomPropertiesHair)
        log += self.tab() + "- Hair: " + self.tab(tabs_num) + str(hair_cp)
        log += self.new_line()
        log += self.tab() + "Total: " + self.tab(tabs_num) + str(body_cp + outf_cp + hair_cp)

        log += self.new_line(3)

        # Diffeomorphic
        if rig_settings.diffeomorphic_support:
            log += self.header("Diffeomorphic")

            log += self.addon_status(settings.status_diffeomorphic, "Diffeomorphic")

            if settings.status_diffeomorphic > 1:
                log += "Diffeomorphic Version:" + self.tab(tabs_num - 2) + str(
                    settings.status_diffeomorphic_version[0]) + '.' + str(
                    settings.status_diffeomorphic_version[1]) + '.' + str(settings.status_diffeomorphic_version[2])
                log += self.new_line()

            log += self.new_line()
            log += self.addon_status(settings.status_mhx, "MHX Addon", tabs_num - 1)

            if settings.status_mhx > 1:
                log += "MHX Version:" + self.tab() * tabs_num + str(settings.status_mhx_version[0]) + '.' + str(
                    settings.status_mhx_version[1]) + '.' + str(settings.status_mhx_version[2])
                log += self.new_line()

            log += self.new_line()
            log += "Morphs: " + self.tab(tabs_num + 1) + str(rig_settings.diffeomorphic_morphs_number)
            log += self.new_line()

            log += self.new_line(3)

        # Viewport
        log += self.header("Viewport")

        if rig_settings.simplify_main_enable:
            log += "Simplify status:" + self.tab(tabs_num - 1) + (
                "Enabled" if rig_settings.simplify_enable else "Disabled")
            log += self.new_line()

        log += "Custom normals:" + self.tab(tabs_num - 1) + (
            "Disabled" if not settings.material_normal_nodes else "Enabled")
        log += self.new_line()

        if rig_settings.diffeomorphic_support and settings.status_diffeomorphic > 1:
            log += "Morphs:" + self.tab(tabs_num + 1) + ("Enabled" if rig_settings.diffeomorphic_enable else "Disabled")
            log += self.new_line()
        if len(physics_settings.physics_items) > 0:
            log += "Physics:" + self.tab(tabs_num) + ("Enabled" if physics_settings.physics_enable else "Disabled")
            log += self.new_line()

        if rig_settings.hair_collection is not None:
            log += "Hair status:" + self.tab(tabs_num) + (
                "Hidden" if rig_settings.hair_collection.hide_viewport else "Shown")
            log += self.new_line()
        if rig_settings.extras_collection is not None:
            log += "Extras status:" + self.tab(tabs_num) + (
                "Hidden" if rig_settings.extras_collection.hide_viewport else "Shown")
            log += self.new_line()

        log += self.new_line()

        # Write to file
        try:
            abs_path = bpy.context.blend_data.filepath[:bpy.context.blend_data.filepath.rfind('\\')] + '\\'
            log_file = open(abs_path + 'mustardui_log.txt', 'w')
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
