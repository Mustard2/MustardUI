import bpy
from bpy.props import *
from ..model_selection.active_object import *
from .. import __package__ as base_package


class MustardUI_Configuration_SmartCheck(bpy.types.Operator):
    """Search for MustardUI configuration options based on the name of the model and its body"""
    bl_idname = "mustardui.configuration_smartcheck"
    bl_label = "Smart Search."
    bl_options = {'UNDO'}

    smartcheck_custom_properties: bpy.props.BoolProperty(name="Body Custom Properties",
                                                         default=True,
                                                         description="Search for Body Custom Properties that respects "
                                                                     "MustardUI Naming Convention.\nThis will "
                                                                     "overwrite previous manual modifications of "
                                                                     "custom properties found with this tool")
    smartcheck_outfits: bpy.props.BoolProperty(name="Outfits", default=True)
    smartcheck_armature: bpy.props.BoolProperty(name="Armature", default=True)
    smartcheck_settings: bpy.props.BoolProperty(name="Global Settings", default=True)

    @classmethod
    def poll(cls, context):

        res, arm = mustardui_active_object(context, config=1)

        if arm is not None:
            rig_settings = arm.MustardUI_RigSettings
            return (rig_settings.model_MustardUI_naming_convention and rig_settings.model_body is not None
                    and rig_settings.model_name != "")
        else:
            return False

    def execute(self, context):

        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings
        addon_prefs = context.preferences.addons[base_package].preferences

        # Try to assign the rig object
        if not obj.MustardUI_created:
            if context.active_object is not None and context.active_object.type == "ARMATURE":
                rig_settings.model_armature_object = context.active_object

        # Initialize Smart Check header
        if addon_prefs.debug:
            print('\nMustardUI - Smart Check - Start\n')

        if self.smartcheck_custom_properties:
            if addon_prefs.debug:
                print('MustardUI - Smart Check - Searching for body additional options\n')
            # Check for body additional properties
            bpy.ops.mustardui.property_smartcheck()

        # Search for oufit collections
        if self.smartcheck_outfits:
            if addon_prefs.debug:
                print('\nMustardUI - Smart Check - Searching for outfits\n')
            bpy.ops.mustardui.outfits_smartcheck()

        # Search for hair
        if addon_prefs.debug:
            print('\nMustardUI - Smart Check - Searching for hair.')
        hair_collections = [x for x in bpy.data.collections if
                            (rig_settings.model_name in x.name) and ('Hair' in x.name)]
        if rig_settings.hair_collection is None:
            if len(hair_collections) == 1:
                rig_settings.hair_collection = hair_collections[0]
                print('\nMustardUI - Smart Check - ' + hair_collections[0].name + ' set as Hair collection')
            elif len(hair_collections) == 0:
                print(
                    '\nMustardUI - Smart Check - Can not find any Hair collection compatible with MustardUI naming '
                    'convention.')
            else:
                print(
                    '\nMustardUI - Smart Check - More than 1 collection has been found. No collection has been set as '
                    'the Hair one to avoid un-wanted behaviour.')
        else:
            print('\nMustardUI - Smart Check - Hair collection already defined. Skipping this part.')

        # Search for extras
        if addon_prefs.debug:
            print('\nMustardUI - Smart Check - Searching for extras.')

        if rig_settings.extras_collection is None:
            extras_collections = [x for x in bpy.data.collections if
                                  (rig_settings.model_name in x.name) and ('Extras' in x.name)]
            if len(extras_collections) == 1:
                rig_settings.extras_collection = extras_collections[0]
                print('\nMustardUI - Smart Check - ' + extras_collections[0].name + ' set as Extras collection')
            elif len(extras_collections) == 0:
                print(
                    '\nMustardUI - Smart Check - Can not find any Extras collection compatible with MustardUI naming '
                    'convention.')
            else:
                print(
                    '\nMustardUI - Smart Check - More than 1 collection has been found. No collection has been set as '
                    'the Extras one to avoid un-wanted behaviour.')
        else:
            print('\nMustardUI - Smart Check - Extras collection already defined. Skipping this part.')

        if self.smartcheck_armature:
            bpy.ops.mustardui.armature_smartcheck()

        if self.smartcheck_settings:
            if addon_prefs.debug:
                print('\nMustardUI - Smart Check - Searching for Global Settings to enable.')

            # Body
            if rig_settings.model_body is not None:
                rig_settings.body_enable_subdiv = False
                rig_settings.body_enable_smoothcorr = False
                rig_settings.body_enable_solidify = False
                rig_settings.body_enable_norm_autosmooth = False

                for m in rig_settings.model_body.modifiers:
                    if m.type == "SUBSURF":
                        rig_settings.body_enable_subdiv = True
                    elif m.type == "CORRECTIVE_SMOOTH":
                        rig_settings.body_enable_smoothcorr = True
                    elif m.type == "SOLIDIFY":
                        rig_settings.body_enable_solidify = True
                    elif m.type == "NODES":
                        if m.node_group is None:
                            continue
                        if m.node_group.name != "Smooth by Angle":
                            continue
                        rig_settings.body_enable_norm_autosmooth = True
            else:
                if addon_prefs.debug:
                    print('\nMustardUI - Smart Check - Could not check Body Global Properties.')

            # Outfits
            objects = []
            outfit_colls = [x.collection for x in rig_settings.outfits_collections if x.collection]
            for c in outfit_colls:
                for obj in [x for x in c.objects if x.type == "MESH"]:
                    objects.append(obj)
            if rig_settings.extras_collection is not None:
                for obj in [x for x in rig_settings.extras_collection.objects if x.type == "MESH"]:
                    objects.append(obj)

            rig_settings.outfits_enable_global_subsurface = False
            rig_settings.outfits_enable_global_smoothcorrection = False
            rig_settings.outfits_enable_global_surfacedeform = False
            rig_settings.outfits_enable_global_shrinkwrap = False
            rig_settings.outfits_enable_global_mask = False
            rig_settings.outfits_enable_global_solidify = False
            rig_settings.outfits_enable_global_triangulate = False
            rig_settings.outfits_enable_global_normalautosmooth = False

            for obj in [x for x in objects if x is not None]:
                for m in obj.modifiers:
                    if m.type == "SUBSURF":
                        rig_settings.outfits_enable_global_subsurface = True
                    elif m.type == "CORRECTIVE_SMOOTH":
                        rig_settings.outfits_enable_global_smoothcorrection = True
                    elif m.type == "SURFACE_DEFORM":
                        rig_settings.outfits_enable_global_surfacedeform = True
                    elif m.type == "SHRINKWRAP":
                        rig_settings.outfits_enable_global_shrinkwrap = True
                    elif m.type == "MASK":
                        rig_settings.outfits_enable_global_mask = True
                    elif m.type == "SOLIDIFY":
                        rig_settings.outfits_enable_global_solidify = True
                    elif m.type == "TRIANGULATE":
                        rig_settings.outfits_enable_global_triangulate = True
                    elif m.type == "NODES":
                        if m.node_group is None:
                            continue
                        if m.node_group.name != "Smooth by Angle":
                            continue
                        rig_settings.outfits_enable_global_normalautosmooth = True

            # Hair
            if rig_settings.hair_collection is not None:
                objects = []
                for obj in [x for x in rig_settings.hair_collection.objects if x.type == "MESH"]:
                    objects.append(obj)

                rig_settings.hair_enable_global_subsurface = False
                rig_settings.hair_enable_global_smoothcorrection = False
                rig_settings.hair_enable_global_solidify = False
                rig_settings.hair_enable_global_particles = False
                rig_settings.hair_enable_global_normalautosmooth = False

                for obj in [x for x in objects if x is not None]:
                    for m in obj.modifiers:
                        if m.type == "SUBSURF":
                            rig_settings.hair_enable_global_subsurface = True
                        elif m.type == "CORRECTIVE_SMOOTH":
                            rig_settings.hair_enable_global_smoothcorrection = True
                        elif m.type == "SOLIDIFY":
                            rig_settings.hair_enable_global_solidify = True
                        elif m.type == "PARTICLE_SYSTEM":
                            rig_settings.hair_enable_global_particles = True
                        elif m.type == "NODES":
                            if m.node_group is None:
                                continue
                            if m.node_group.name != "Smooth by Angle":
                                continue
                            rig_settings.hair_enable_global_normalautosmooth = True

        # End of debug messages
        if addon_prefs.debug:
            print('\nMustardUI - Smart Check - End')

        self.report({'INFO'}, 'MustardUI - Smart Check complete.')

        return {'FINISHED'}

    def invoke(self, context, event):
        addon_prefs = context.preferences.addons[base_package].preferences
        return context.window_manager.invoke_props_dialog(self, width=550 if addon_prefs.debug else 450)

    def draw(self, context):

        layout = self.layout

        box = layout.box()
        box.label(text="Categories to Smart Check")
        col = box.column()
        col.prop(self, 'smartcheck_outfits')
        col.prop(self, 'smartcheck_armature')
        col.separator()
        col.prop(self, 'smartcheck_settings')
        col.prop(self, 'smartcheck_custom_properties')


def register():
    bpy.utils.register_class(MustardUI_Configuration_SmartCheck)


def unregister():
    bpy.utils.unregister_class(MustardUI_Configuration_SmartCheck)
