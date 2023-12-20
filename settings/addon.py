import bpy
from bpy.props import *
from ..misc.updater import mustardui_check_version
import addon_utils
import sys


class MustardUI_Settings(bpy.types.PropertyGroup):
    # Main Settings definitions
    # Version of the MustardUI
    version: StringProperty(default="0.0.1",
                            name="MustardUI version",
                            description="Version of MustardUI add-on")

    # Advanced settings
    advanced: BoolProperty(default=False,
                           name="Advanced Options",
                           description="Unlock Advanced Options.\nMore advanced options will be shown in "
                                       "the UI")

    # Model selection
    viewport_model_selection: BoolProperty(default=True,
                                           name="Viewport model selection",
                                           description="Enable viewport model selection.\nIf disabled, "
                                                       "a model selection panel will appear instead, "
                                                       "where a model can be selected")
    viewport_model_selection_after_configuration: BoolProperty(default=False,
                                                               name="Viewport model selection",
                                                               description="Enable viewport model selection "
                                                                           "after the end of the "
                                                                           "configuration.\nIt is advised "
                                                                           "to leave this off if only one "
                                                                           "character with MustardUI is "
                                                                           "available on the scene")

    panel_model_selection_armature: PointerProperty(type=bpy.types.Armature)

    # MustardUI version check
    mustardui_update_available: BoolProperty(default=mustardui_check_version())

    # RIG TOOLS STATUS

    # This function checks that the rig_tools addon is installed and enabled.
    def addon_check(addon_names):

        addon_utils.modules_refresh()

        addon_num = len(addon_names)

        addon_status = []
        addon_names_found = []

        for i in range(addon_num):
            for addon in addon_utils.addons_fake_modules:
                if addon_names[i] in addon:
                    addon_names_found.append(addon)
                    default, state = addon_utils.check(addon)
                    addon_status.append(2 if default else 1)

        if 2 in addon_status:
            for i in range(len(addon_names_found)):
                if addon_status[i] == 2:
                    print("MustardUI - " + addon_names_found[i] + " add-on enabled and running.")
                    return 2
        elif 1 in addon_status and not 2 in addon_status:
            for addon_name in addon_names_found:
                print("MustardUI - " + addon_name + " add-on installed but not enabled.")
            return 1
        else:
            for addon_name in addon_names:
                print("MustardUI - %s add-on not installed." % addon_name)

        return 0

    # Rig-tools addon status definition
    status_rig_tools: IntProperty(default=addon_check(["auto_rig_pro-master", "rig_tools"]),
                                  name="rig_tools addon status")

    # Rig-tools addon status definition
    status_diffeomorphic: IntProperty(default=addon_check(["import_daz"]),
                                      name="diffeomorphic addon status")

    # Rig-tools addon status definition
    status_mhx: IntProperty(default=addon_check(["mhx_rts"]),
                            name="mhx_rts addon status")

    def addon_version_check(addon_name):
        try:
            # Find the correct addon name
            addon_utils.modules_refresh()

            an = ""
            for addon in addon_utils.addons_fake_modules:
                if addon_name in addon:
                    default, state = addon_utils.check(addon)
                    if default:
                        an = addon
                        break

            if an == "":
                print("MustardUI - Can not find " + addon_name + " version.")
                return (-1, -1, -1)

            mod = addon_utils.addons_fake_modules[an]
            version = mod.bl_info.get('version', (-1, -1, -1))
            print("MustardUI - " + an + " version is " + str(version[0]) + "." + str(version[1]) + "." + str(
                version[2]) + ".")
            return (version[0], version[1], version[2])
        except:
            print("MustardUI - Can not find " + addon_name + " version.")
            return (-1, -1, -1)

    status_diffeomorphic_version: IntVectorProperty(default=addon_version_check("import_daz"))
    status_mhx_version: IntVectorProperty(default=addon_version_check("mhx_rts"))

    # Property for custom properties errors
    custom_properties_error: BoolProperty(name="",
                                          description="Can not find the property.\nCheck the property or use the "
                                                      "Re-build Custom Properties operator in Settings")
    custom_properties_error_nonanimatable: BoolProperty(name="",
                                                        description="Can not find the property.\nRemove the property "
                                                                    "in the Configuration panel and add it again")

    # Property for morphs errors
    daz_morphs_error: BoolProperty(name="",
                                   description="Can not find the Daz Morph.\nRe-run the Check Morphs operator in the "
                                               "Configuration menu to solve this")

    # Material normals mute
    def update_material_normal(self, context):

        bpy.ops.mustardui.material_normalmap_nodes(custom=self.material_normal_nodes)

        return

    material_normal_nodes: BoolProperty(default=False,
                                        name="Eeevee Optimized Normals",
                                        description="Enable an optimized version of Eevee normals.\nThis tool "
                                                    "substitutes normal nodes with more efficient ones, which can be "
                                                    "useful to get better performance in Render Viewport mode. "
                                                    "Disable this for Cycles",
                                        update=update_material_normal)


def register():
    # Register and create the setting class in the Scene object
    bpy.utils.register_class(MustardUI_Settings)
    bpy.types.Scene.MustardUI_Settings = PointerProperty(type=MustardUI_Settings)

    # Properties to specify if the Armature has a MustardUI currently in use
    bpy.types.Armature.MustardUI_enable = bpy.props.BoolProperty(default=False,
                                                                 name="")

    # Properties to specify if the Armature has a MustardUI created
    bpy.types.Armature.MustardUI_created = bpy.props.BoolProperty(default=False,
                                                                  name="")


def unregister():
    bpy.utils.unregister_class(MustardUI_Settings)
