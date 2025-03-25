import bpy
from ..model_selection.active_object import *


class MustardUI_PhysicsItem_Rebind(bpy.types.Operator):
    """Rebind cages to the model meshes (Body, Outfits, Hair)"""
    bl_idname = "mustardui.physics_rebind"
    bl_label = "Rebind Physics"
    bl_options = {'UNDO'}

    force: bpy.props.BoolProperty(default=False,
                                  name="Force re-binding",
                                  description="Force re-binding of cages that are not bound")

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings
        physics_settings = arm.MustardUI_PhysicsSettings

        if len(physics_settings.items) < 1:
            return {'FINISHED'}

        # Gather items to re-bind cages on
        objects = [rig_settings.model_body]
        outfit_colls = [x.collection for x in rig_settings.outfits_collections if x.collection]
        for c in outfit_colls:
            for obj in [x for x in c.objects if x.type == "MESH"]:
                objects.append(obj)
        if rig_settings.extras_collection is not None:
            for obj in [x for x in rig_settings.extras_collection.objects if x.type == "MESH"]:
                objects.append(obj)
        if rig_settings.hair_collection is not None:
            for obj in [x for x in rig_settings.hair_collection.objects if x.type == "MESH"]:
                objects.append(obj)

        # Gather cages to check as targets of modifiers
        cages = []
        for item in [x for x in physics_settings.items if x.type == "CAGE" and x.object is not None]:
            cages.append(item.object)

        for ob in objects:
            for m in ob.modifiers:
                if m.type == 'SURFACE_DEFORM':
                    target = m.target
                    if target is None:
                        continue
                    if target in cages:
                        hv = target.hide_viewport
                        target.hide_viewport = False
                        if m.is_bound:
                            with bpy.context.temp_override(object=ob):
                                bpy.ops.object.surfacedeform_bind(modifier=m.name)
                            with bpy.context.temp_override(object=ob):
                                bpy.ops.object.surfacedeform_bind(modifier=m.name)
                        elif not m.is_bound and self.force:
                            with bpy.context.temp_override(object=ob):
                                bpy.ops.object.surfacedeform_bind(modifier=m.name)
                        target.hide_viewport = hv

                elif m.type == 'MESH_DEFORM':
                    target = m.object
                    if target is None:
                        continue
                    if target in cages:
                        hv = target.hide_viewport
                        target.hide_viewport = False
                        if m.is_bound:
                            with bpy.context.temp_override(object=ob):
                                bpy.ops.object.meshdeform_bind(modifier=m.name)
                            with bpy.context.temp_override(object=ob):
                                bpy.ops.object.meshdeform_bind(modifier=m.name)
                        elif not m.is_bound and self.force:
                            with bpy.context.temp_override(object=ob):
                                bpy.ops.object.meshdeform_bind(modifier=m.name)
                        target.hide_viewport = hv

                elif m.type == 'CORRECTIVE_SMOOTH':
                    if m.rest_source != "BIND":
                        continue
                    hv = m.show_viewport
                    m.show_viewport = True
                    if m.is_bind:
                        with bpy.context.temp_override(object=ob):
                            bpy.ops.object.correctivesmooth_bind(modifier=m.name)
                        with bpy.context.temp_override(object=ob):
                            bpy.ops.object.correctivesmooth_bind(modifier=m.name)
                    elif not m.is_bound and self.force:
                        with bpy.context.temp_override(object=ob):
                            bpy.ops.object.correctivesmooth_bind(modifier=m.name)
                    m.show_viewport = hv

        self.report({'INFO'}, 'MustardUI - Cages successfully re-binded.')

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_PhysicsItem_Rebind)


def unregister():
    bpy.utils.unregister_class(MustardUI_PhysicsItem_Rebind)
