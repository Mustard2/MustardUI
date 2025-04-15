import bpy
import bmesh
from mathutils.bvhtree import BVHTree
from ..misc.mesh_intersection import check_mesh_intersection
from ..model_selection.active_object import *
from .update_enable import enable_physics_update


class MustardUI_Physics_Setup(bpy.types.Operator):
    """This button creates Surface Deform modifiers on Outfit pieces affected by Cages physics items.\nThe modifier is added only if the Outfit piece and the Cage intersect"""
    bl_idname = "mustardui.physics_setup"
    bl_label = "Setup Outfits Physics"
    bl_options = {'UNDO'}

    attempt_fix_bind: bpy.props.BoolProperty(default=False,
                                             name="Attempt Fix Binding",
                                             description="Attempt to fix the rebinding if errors occur (Simplify should be off).\nTo use the model with these fixes, read carefully the warnings if generated")
    override_armature_check: bpy.props.BoolProperty(default=False,
                                                    name="Override Armature Check",
                                                    description="Surface Deform modifiers are added even if the Armature modifier is not available on the Object")
    override_physics_check: bpy.props.BoolProperty(default=False,
                                                    name="Override Physics Check",
                                                    description="Surface Deform modifiers are not added if Physics modifiers are found on the Object.\nEnable this to remove this condition")
    clean_modifiers: bpy.props.BoolProperty(default=False,
                                            name="Clean Modifiers",
                                            description="Remove modifiers for mesh not affected by Physics cages")

    def bind(self, obj, mod):

        warnings = 0

        if not mod.is_bound:
            for m in [x for x in obj.modifiers if x.type == "SUBSURF"]:
                m.show_viewport = False
                break
            bpy.ops.object.surfacedeform_bind(modifier=mod.name)

        bpy.context.view_layer.update()

        if not mod.is_bound and self.attempt_fix_bind:
            print(
                f"MustardUI Physics Setup - Surface Deform might be fixed on {repr(obj.name)}, but will require Subdivision Surface on the Body to work properly")
            warnings += 1

        return warnings

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=1)
        physics_settings = arm.MustardUI_PhysicsSettings
        return res and physics_settings.enable_ui

    def bind_attempt_fix(self, obj, mod):

        # Attempt to fix "Concave polygons" error on binding subdividing the body mesh
        if not mod.is_bound:
            # Re-attempt binding
            bpy.ops.object.surfacedeform_bind(modifier=mod.name)

        obj.update_tag()
        mod.update_tag()
        bpy.context.view_layer.update()

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings
        physics_settings = arm.MustardUI_PhysicsSettings

        # Go to frame 0
        frame_current = context.scene.frame_current
        context.scene.frame_current = 0

        # Disable Physics
        enable_physics = physics_settings.enable_physics
        physics_settings.enable_physics = False

        items = physics_settings.items
        body = rig_settings.model_body

        arm.pose_position = 'REST'

        warnings = 0

        colls = [x.collection for x in rig_settings.outfits_collections if x.collection is not None]
        if rig_settings.extras_collection is not None:
            colls.append(rig_settings.extras_collection)

        # Clear current intersection objects
        for pi in [x for x in items if x.type == "CAGE"]:
            pi.intersecting_objects.clear()

        for coll in colls:
            objs = coll.all_objects if rig_settings.outfit_config_subcollections else coll.objects
            for obj in [x for x in objs if x.type == "MESH" and x.modifiers is not None]:
                # Check if the Armature modifier is available on the Object
                # This should be an indication of the fact that the Object should be driven by the body with Surface
                # Deform modifiers
                if not self.override_armature_check:
                    if len([x for x in obj.modifiers if
                            x.type == "ARMATURE" and x.object == rig_settings.model_armature_object]) == 0:
                        continue

                # Check if Physics modifiers are available on the mesh
                # If these modifiers are available, most probably the item does not need to be driven by Surface Deform
                if not self.override_armature_check:
                    if any(x.type in ["CLOTH", "SOFT_BODY"] for x in obj.modifiers):
                        continue

                pi_found = False

                for pi in [x for x in items if x.type == "CAGE"]:
                    if check_mesh_intersection(pi.object, obj):

                        # Add the object to the intersecting objects of the physics item
                        npi = pi.intersecting_objects.add()
                        npi.object = obj

                        if pi_found:
                            continue
                        pi_found = True

                        # If the modifier is already added, attempt to rebind if needed and skip
                        if any(x.type == "SURFACE_DEFORM" and x.target == body for x in obj.modifiers):
                            for mod in [x for x in obj.modifiers if x.type == "SURFACE_DEFORM" and x.target == body]:
                                # Attempt to rebind if found but not bound
                                if not mod.is_bound:
                                    with bpy.context.temp_override(object=obj):
                                        mod.show_viewport = True
                                        obj.update_tag()

                                        warnings += self.bind(obj, mod)

                                        mod.show_viewport = False
                                        obj.update_tag()
                                break
                            continue

                        # Add Surface Deform modifier
                        nm = obj.modifiers.new(name=body.name, type='SURFACE_DEFORM')
                        nm.target = body
                        with bpy.context.temp_override(object=obj):
                            # Bind the modifier
                            warnings += self.bind(obj, nm)

                            # Move the modifier after the Armature one
                            # Get the Armature modifier index
                            last_armature_index = max(
                                (i for i, m in enumerate(obj.modifiers) if m.type == "ARMATURE"),
                                default=-1
                            )
                            # Index of the current modifier
                            target_index = list(obj.modifiers).index(nm)
                            # Move the modifier up if needed
                            while target_index > last_armature_index + 1:
                                bpy.ops.object.modifier_move_up(modifier=nm.name)
                                target_index -= 1

                            nm.show_viewport = True
                            nm.show_render = True

                            obj.update_tag()

                # If there is no intersection, the modifier is not needed
                if not pi_found and self.clean_modifiers:
                    mods = [x for x in obj.modifiers if x.type == "SURFACE_DEFORM" and x.target == body]
                    mods.reverse()
                    for mod in mods:
                        obj.modifiers.remove(mod)

                obj.update_tag()

        if self.attempt_fix_bind:

            warnings_objects = []

            # Disable simplify
            scene = context.scene
            level = scene.render.simplify_subdivision
            if scene.render.use_simplify and scene.render.simplify_subdivision < 2:
                scene.render.simplify_subdivision = 2

            # Activate subdivision modifiers on the body
            body_levels = 0
            body_show = False
            for m in [x for x in body.modifiers if x.type == "SUBSURF"]:
                body_levels = m.levels
                m.levels = 2
                body_show = m.show_viewport
                m.show_viewport = True
                break

            for coll in colls:
                objs = coll.all_objects if rig_settings.outfit_config_subcollections else coll.objects

                show_coll = coll.hide_viewport
                coll.hide_viewport = False
                bpy.context.view_layer.update()

                for obj in [x for x in objs if x.type == "MESH" and x.modifiers is not None]:
                    show_obj = obj.hide_viewport
                    obj.hide_viewport = False

                    for mod in [x for x in obj.modifiers if x.type == "SURFACE_DEFORM" and x.target == body]:
                        # Attempt to rebind if found but not bound
                        if not mod.is_bound:
                            with bpy.context.temp_override(object=obj):
                                mod.show_viewport = True

                                self.bind_attempt_fix(obj, mod)

                                warnings_objects.append((obj.name, mod.is_bound))

                                if mod.is_bound:
                                    print(
                                        f"MustardUI Physics Setup - Surface Deform binding fixed on {repr(obj.name)}, but requires Subdivision Surface on the Body to work properly")
                                    warnings += 1

                                mod.show_viewport = False
                                mod.show_render = False

                    obj.hide_viewport = show_obj

                    obj.update_tag()

                coll.hide_viewport = show_coll
                bpy.context.view_layer.update()

            # Revert Simplify settings
            if level != 2:
                scene.render.simplify_subdivision = level

            # Disable subdivision modifiers on the Body
            for m in [x for x in body.modifiers if x.type == "SUBSURF"]:
                m.levels = body_levels
                m.show_viewport = body_show
                break

        arm.pose_position = 'POSE'

        # Force Physics recheck
        enable_physics_update(physics_settings, context)
        physics_settings.enable_physics = enable_physics

        # Revert the frame
        context.scene.frame_current = frame_current

        # Last check on binding to raise warnings
        for coll in colls:
            objs = coll.all_objects if rig_settings.outfit_config_subcollections else coll.objects
            for obj in [x for x in objs if x.type == "MESH" and x.modifiers is not None]:
                for mod in [x for x in obj.modifiers if x.type == "SURFACE_DEFORM" and x.target == body]:
                    if not mod.is_bound:
                        print(
                            f"MustardUI Physics Setup - Could not bind Surface Deform on {repr(obj.name)}")
                        warnings += 1

        if warnings == 0:
            self.report({'INFO'}, 'MustardUI - Physics Setup complete.')
        else:
            self.report({'WARNING'}, f'MustardUI - {str(warnings)} warnings have been generated during setup. Check the Console log.')

        return {'FINISHED'}

    def invoke(self, context, event):
        self.attempt_fix_bind = False
        return context.window_manager.invoke_props_dialog(self, width=450)

    def draw(self, context):

        layout = self.layout

        box = layout.box()
        col = box.column(align=True)
        col.prop(self, 'attempt_fix_bind')
        col.prop(self, 'override_armature_check')
        col.prop(self, 'override_physics_check')

        col = box.column(align=True)
        col.prop(self, 'clean_modifiers')


def register():
    bpy.utils.register_class(MustardUI_Physics_Setup)


def unregister():
    bpy.utils.unregister_class(MustardUI_Physics_Setup)
