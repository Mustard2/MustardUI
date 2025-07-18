import bpy
from . import MainPanel
from .misc import mustardui_custom_properties_print
from ..model_selection.active_object import *
from ..warnings.ops_fix_old_UI import check_old_UI
from ..settings.rig import *
from .. import __package__ as base_package


# Function to format dynamic name
def format_dynamic_name(x):
    return x.particle_system.name if not ("Dynamic" in x.particle_system.name) else x.particle_system.name.replace(
        "Dynamic", "").lstrip().rstrip()


class PANEL_PT_MustardUI_Hair(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Hair"
    bl_label = "Hair"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):

        if check_old_UI():
            return False

        res, arm = mustardui_active_object(context, config=0)

        if arm is not None:
            rig_settings = arm.MustardUI_RigSettings

            # Check if one of these should be shown in the UI
            hair_global_properties_avail = len([x for x in arm.MustardUI_CustomPropertiesHair if x.hair is None])
            hair_avail = len([x for x in rig_settings.hair_collection.objects if x.type == "MESH"]) > 0 if rig_settings.hair_collection is not None else False
            particle_avail = len([x for x in rig_settings.model_body.modifiers if x.type == "PARTICLE_SYSTEM"]) > 0 and rig_settings.particle_systems_enable if rig_settings.model_body is not None else False
            curved_hair = len([x for x in rig_settings.hair_collection.objects if x.type == "CURVES"]) > 0 if rig_settings.hair_collection is not None else False

            return res if (hair_avail or particle_avail or curved_hair or hair_global_properties_avail) else False

        return res

    def draw(self, context):

        settings = bpy.context.scene.MustardUI_Settings

        poll, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings
        addon_prefs = context.preferences.addons[base_package].preferences

        layout = self.layout

        # Hair
        hair_global_properties = [x for x in arm.MustardUI_CustomPropertiesHair if x.hair is None]
        if len(hair_global_properties) > 0:
            box = layout.box()
            row = box.row(align=True)
            row.label(text="Global settings", icon="MODIFIER")

            mustardui_custom_properties_print(arm, settings, hair_global_properties, box,
                                          rig_settings.hair_custom_properties_icons)

        if rig_settings.hair_collection is not None:

            hair_num = len([x for x in rig_settings.hair_collection.objects if x.type == "MESH"])

            if hair_num > 1:

                box = layout.box()
                row = box.row(align=True)
                row.label(text="Hair list", icon="STRANDS")
                row.prop(rig_settings.hair_collection, "hide_viewport", text="")
                row.prop(rig_settings.hair_collection, "hide_render", text="")

                row = box.row(align=True)
                row.prop(rig_settings, "hair_list", text="")

            elif hair_num > 0:
                box = layout.box()
                row = box.row(align=True)
                row.label(text="Hair", icon="STRANDS")
                row.prop(rig_settings.hair_collection, "hide_viewport", text="")
                row.prop(rig_settings.hair_collection, "hide_render", text="")

            if hair_num > 0:

                try:
                    obj = context.scene.objects[rig_settings.hair_list]

                    if rig_settings.hair_custom_properties_name_order:
                        custom_properties_obj = sorted([x for x in arm.MustardUI_CustomPropertiesHair if x.hair == obj],
                                                       key=lambda x: x.name)
                    else:
                        custom_properties_obj = [x for x in arm.MustardUI_CustomPropertiesHair if x.hair == obj]
                    if len(custom_properties_obj) > 0:
                        row.prop(obj.MustardUI_OutfitSettings, "additional_options_show", toggle=True, icon="PREFERENCES")
                        if obj.MustardUI_OutfitSettings.additional_options_show:
                            mustardui_custom_properties_print(arm, settings, custom_properties_obj, box,
                                                              rig_settings.hair_custom_properties_icons)

                    mod_particle_system = sorted([x for x in obj.modifiers if x.type == "PARTICLE_SYSTEM"],
                                                 key=format_dynamic_name)
                    if rig_settings.particle_systems_enable and len(mod_particle_system) > 0:
                        row = box.row(align=True)
                        row.prop(rig_settings, 'hair_particle_children_viewport_factor')
                        if any("Dynamic" in x.particle_system.name for x in mod_particle_system):
                            status = any(x.particle_system.use_hair_dynamics for x in mod_particle_system)
                            op = row.operator('mustardui.physics_particlehair_switch', text="", icon="PHYSICS")
                            op.enable = not status
                            op.obj = obj.name
                        box2 = box.box()
                        for mod in mod_particle_system:
                            row = box2.row(align=True)
                            row.label(text=format_dynamic_name(mod), icon="PARTICLES")
                            row2 = row.row(align=True)
                            if "Dynamic" in mod.particle_system.name:
                                row2.prop(mod.particle_system, "use_hair_dynamics", text="", icon="PHYSICS")
                            row2.prop(mod, "show_viewport", text="")
                            row2.prop(mod, "show_render", text="")
                except:
                    box = box.box()
                    box.label(text="An error occurred.", icon="ERROR")
                    box.label(text="The UI Hair data seems corrupted.", icon="BLANK1")
                    if addon_prefs.developer:
                        box.label(text="Enter and exit Configuration mode to fix.", icon="BLANK1")
                        box.operator('mustardui.configuration', text="Enter Configuration Mode", icon="PREFERENCES")

                # Hair global properties
                if (rig_settings.hair_enable_global_subsurface or rig_settings.hair_enable_global_smoothcorrection or
                        rig_settings.hair_enable_global_solidify or rig_settings.hair_enable_global_particles or
                        rig_settings.hair_enable_global_normalautosmooth):

                    box = layout.box()
                    row = box.row(align=True)
                    row.label(text="Global properties", icon="MODIFIER")
                    col = box.column(align=True)
                    if rig_settings.hair_enable_global_subsurface:
                        col.prop(rig_settings, "hair_global_subsurface")
                    if rig_settings.hair_enable_global_smoothcorrection:
                        col.prop(rig_settings, "hair_global_smoothcorrection")
                    if rig_settings.hair_enable_global_solidify:
                        col.prop(rig_settings, "hair_global_solidify")
                    if rig_settings.hair_enable_global_particles:
                        col.prop(rig_settings, "hair_global_particles")
                    if rig_settings.hair_enable_global_normalautosmooth:
                        col.prop(rig_settings, "hair_global_normalautosmooth")

            # Curves
            curves_hair = sorted([x for x in rig_settings.hair_collection.objects if x.type == "CURVES"],
                                 key=lambda x: x.name)
            if rig_settings.curves_hair_enable and len(curves_hair) > 0:
                box = layout.box()
                row = box.row(align=True)
                row.label(text="Curves Hair", icon="OUTLINER_OB_CURVES")
                if hair_num < 1:
                    row.prop(rig_settings.hair_collection, "hide_viewport", text="")
                    row.prop(rig_settings.hair_collection, "hide_render", text="")
                box2 = box.box()
                for obj in curves_hair:
                    row = box2.row()
                    row.label(text=obj.name, icon="OUTLINER_DATA_CURVES")
                    row2 = row.row(align=True)
                    row2.prop(obj, "hide_viewport", text="")
                    row2.prop(obj, "hide_render", text="")

        # Particle systems
        mod_particle_system = sorted([x for x in rig_settings.model_body.modifiers if x.type == "PARTICLE_SYSTEM"],
                                     key=lambda x: x.particle_system.name)
        if rig_settings.particle_systems_enable and len(mod_particle_system) > 0:
            box = layout.box()
            box.label(text="Hair particles", icon="MOD_PARTICLE_INSTANCE")
            box2 = box.box()
            for mod in mod_particle_system:
                row = box2.row()
                row.label(text=mod.particle_system.name, icon="PARTICLES")
                row2 = row.row(align=True)
                row2.prop(mod, "show_viewport", text="")
                row2.prop(mod, "show_render", text="")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_Hair)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Hair)
