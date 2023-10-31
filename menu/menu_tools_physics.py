import bpy
from . import MainPanel
from ..model_selection.active_object import *
from ..settings.rig import *
from ..tools.physics import *


class PANEL_PT_MustardUI_Tools_Physics(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Tools_Physics"
    bl_label = "Physics"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        res, obj = mustardui_active_object(context, config=0)
        if obj is not None:
            physics_settings = obj.MustardUI_PhysicsSettings
            return res and len(physics_settings.physics_items) > 0
        else:
            return res

    def draw_header(self, context):

        poll, obj = mustardui_active_object(context, config=0)
        physics_settings = obj.MustardUI_PhysicsSettings

        self.layout.prop(physics_settings, "physics_enable", text="", toggle=False)

    def draw(self, context):

        settings = bpy.context.scene.MustardUI_Settings
        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings
        physics_settings = obj.MustardUI_PhysicsSettings
        addon_prefs = context.preferences.addons["MustardUI"].preferences

        layout = self.layout

        box = layout.box()
        box.label(text="Item settings", icon="OBJECT_DATA")
        box.prop(physics_settings, "physics_items_list", text="")

        if not physics_settings.physics_enable:
            layout.enabled = False

        if physics_settings.physics_items_list == "":
            box.label(text="Item not selected.", icon="ERROR")
            return

        # Cage specific settings
        cage = bpy.data.objects[physics_settings.physics_items_list]

        try:
            cage_settings = [x for x in physics_settings.physics_items if x.cage_object.name == cage.name][0]
        except:
            box.label(text="Item not found.", icon="ERROR")
            box.operator('mustardui.tools_physics_deleteitem', text="Fix Issues", icon="HELP").cage_object_name = ""
            return

        try:
            mod = [x for x in cage.modifiers if x.type == "CLOTH"][0]
        except:
            box.label(text="Cloth modifier not found.", icon="ERROR")
            return

        cage_cloth = mod.settings
        cage_collisions = mod.collision_settings
        cage_cache = mod.point_cache

        box.prop(cage_settings, "physics_enable")

        box2 = box.box()
        box2.enabled = not cage_cache.is_baked and cage_settings.physics_enable

        box2.label(text="Physical Properties", icon="PHYSICS")
        box2.prop(cage_cloth, "time_scale")
        box2.prop(cage_cloth.effector_weights, "gravity")

        box2 = box.box()
        box2.enabled = not cage_cache.is_baked and cage_settings.physics_enable

        box2.label(text="Structural Properties", icon="MOD_EXPLODE")
        if cage_settings.MustardUI_preset:

            box2.prop(cage_settings, "inertia")
            box2.prop(cage_settings, "stiffness")
            box2.prop(cage_settings, "bounciness")

        else:

            col = box2.column(align=False)

            row = col.row(align=True)
            row.label(text="")
            row.scale_x = 1.
            row.label(text='Stiffness')
            row.scale_x = 1.
            row.label(text='Damping')

            row = col.row(align=True)
            row.label(text="Structural")
            row.scale_x = 1.
            row.prop(cage_cloth, "tension_stiffness", text="")
            row.scale_x = 1.
            row.prop(cage_cloth, "tension_damping", text="")

            row = col.row(align=True)
            row.label(text="Compression")
            row.scale_x = 1.
            row.prop(cage_cloth, "compression_stiffness", text="")
            row.scale_x = 1.
            row.prop(cage_cloth, "compression_damping", text="")

            row = col.row(align=True)
            row.label(text="Shear")
            row.scale_x = 1.
            row.prop(cage_cloth, "shear_stiffness", text="")
            row.scale_x = 1.
            row.prop(cage_cloth, "shear_damping", text="")

            row = col.row(align=True)
            row.label(text="Bending")
            row.scale_x = 1.
            row.prop(cage_cloth, "bending_stiffness", text="")
            row.scale_x = 1.
            row.prop(cage_cloth, "bending_damping", text="")

            if cage_cloth.vertex_group_bending != "":
                box2.prop(cage_cloth, "bending_stiffness_max", text="Max Bending")

            # box2.separator()

            # box2.label(text = "Internal Springs Properties" , icon = "FORCE_MAGNETIC")
            box2.prop(cage_cloth, "use_internal_springs", text="Enable Internal Springs")

            col = box2.column(align=False)
            col.enabled = cage_cloth.use_internal_springs

            row = col.row(align=True)
            row.label(text="")
            row.scale_x = 1.
            row.label(text='Value')
            row.scale_x = 1.
            row.label(text='Max')

            row = col.row(align=True)
            row.label(text="Tension")
            row.scale_x = 1.
            row.prop(cage_cloth, "internal_tension_stiffness", text="")
            row.scale_x = 1.
            row.prop(cage_cloth, "internal_tension_stiffness_max", text="")

            row = col.row(align=True)
            row.label(text="Compression")
            row.scale_x = 1.
            row.prop(cage_cloth, "internal_compression_stiffness", text="")
            row.scale_x = 1.
            row.prop(cage_cloth, "internal_compression_stiffness_max", text="")

            # box2.separator()

            # box2.label(text = "Pressure Properties" , icon = "MOD_SOFT")
            box2.prop(cage_cloth, "use_pressure", text="Enable Pressure")

            col = box2.column(align=False)
            col.enabled = cage_cloth.use_pressure

            col.prop(cage_cloth, 'uniform_pressure_force', text="Force")

        box2 = box.box()
        box2.enabled = not cage_cache.is_baked and cage_settings.physics_enable

        box2.label(text="Collision Properties", icon="MOD_PHYSICS")
        box2.prop(cage_collisions, "use_collision")
        row = box2.row(align=True)
        row.enabled = cage_collisions.use_collision
        row.prop(cage_collisions, 'collision_quality')
        row = box2.row(align=True)
        row.enabled = cage_collisions.use_collision
        row.prop(cage_collisions, "distance_min")
        row = box2.row(align=True)
        row.enabled = cage_collisions.use_collision
        row.prop(cage_collisions, "impulse_clamp")

        box2 = box.box()
        box2.enabled = cage_settings.physics_enable

        box2.label(text="Item Simulation", icon="FILE_CACHE")
        row = box2.row(align=True)
        row.enabled = not cage_cache.is_baked
        row.prop(cage_cloth, 'quality')
        box2.separator()
        row = box2.row(align=True)
        row.prop(cage_cache, "frame_start", text="Start")
        row.prop(cage_cache, "frame_end", text="End")
        cache_info = cage_cache.info
        if cache_info and addon_prefs.debug:
            col = box2.column(align=True)
            col.alignment = 'CENTER'
            col.label(text='Info: ' + cache_info)
        bake_op = box2.operator('mustardui.tools_physics_simulateobject',
                                text="Bake Single Item Physics" if not cage_cache.is_baked else "Delete Single Item Bake",
                                icon="PHYSICS" if not cage_cache.is_baked else "X",
                                depress=cage_cache.is_baked).cage_object_name = physics_settings.physics_items_list

        # Global simulation
        box = layout.box()
        box.label(text="Global Simulation", icon="FILE_CACHE")
        box.prop(physics_settings, 'simulation_quality')
        box.separator()
        row = box.row(align=True)
        row.prop(physics_settings, "simulation_start", text="Start")
        row.prop(physics_settings, "simulation_end", text="End")
        box.operator('ptcache.bake_all', icon="PHYSICS").bake = True
        box.operator('ptcache.free_bake_all', icon="X")

        if addon_prefs.developer:
            box = layout.box()
            box.label(text="Developer", icon="SETTINGS")
            box.operator('mustardui.tools_physics_rebind', text="Re-bind Cages", icon="MOD_MESHDEFORM")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_Tools_Physics)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Tools_Physics)
