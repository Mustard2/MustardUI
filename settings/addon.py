import bpy
from bpy.props import *
from bpy.app.handlers import persistent
from .. import __package__ as base_package
from ..outfits.ops_rename_outfit import MustardUI_RenameOutfit_Class


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

    # Tools (internal)
    # Class to store temporary settings for outfit rename
    rename_outfits_temp_class: CollectionProperty(
            type=MustardUI_RenameOutfit_Class)


# Handler to solve a missing UI when: developer mode is on, but the UI has been left in configuration mode
@persistent
def load_handler(_):
    context = bpy.context
    scene = context.scene
    addon_prefs = context.preferences.addons[base_package].preferences
    if addon_prefs.debug:
        print('MustardUI - Checking for missing UIs')
    if hasattr(scene, 'MustardUI_Settings'):
        for obj in [x for x in scene.objects if x.type == "ARMATURE"]:
            arm = obj.data
            if hasattr(arm, 'MustardUI_created') and hasattr(arm, 'MustardUI_enable'):
                if arm.MustardUI_created and not arm.MustardUI_enable and not addon_prefs.developer:
                    arm.MustardUI_enable = not arm.MustardUI_enable
                    if addon_prefs.debug:
                        print(f'MustardUI - Fixed missing UI on {repr(obj.name)}')


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

    bpy.app.handlers.load_post.append(load_handler)


def unregister():
    bpy.app.handlers.load_post.remove(load_handler)

    del bpy.types.Armature.MustardUI_created
    del bpy.types.Armature.MustardUI_enable
    del bpy.types.Scene.MustardUI_Settings

    bpy.utils.unregister_class(MustardUI_Settings)
