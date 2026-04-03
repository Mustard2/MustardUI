import bpy
from ..model_selection.active_object import *
from .. import __package__ as base_package


def bind_object(obj, cages, addon_prefs,
                surface_deform=True, mesh_deform=True, corrective_smooth=True, force=False):
    for m in obj.modifiers:
        if surface_deform and m.type == 'SURFACE_DEFORM':
            target = m.target
            if target is None:
                continue
            if target in cages:
                hv = target.hide_viewport
                target.hide_viewport = False
                if m.is_bound:
                    with bpy.context.temp_override(object=obj):
                        try:
                            bpy.ops.object.surfacedeform_bind(modifier=m.name)
                        except:
                            if addon_prefs.debug:
                                print(obj.name + " modifier: " + m.name + " could not be binded")
                    with bpy.context.temp_override(object=obj):
                        try:
                            bpy.ops.object.surfacedeform_bind(modifier=m.name)
                        except:
                            pass
                elif not m.is_bound and force:
                    with bpy.context.temp_override(object=obj):
                        try:
                            bpy.ops.object.surfacedeform_bind(modifier=m.name)
                        except Exception:
                            if addon_prefs.debug:
                                print(obj.name + " modifier: " + m.name + " could not be binded")
                target.hide_viewport = hv

        elif mesh_deform and m.type == 'MESH_DEFORM':
            target = m.object
            if target is None:
                continue
            if target in cages:
                hv = target.hide_viewport
                target.hide_viewport = False
                if m.is_bound:
                    with bpy.context.temp_override(object=obj):
                        try:
                            bpy.ops.object.meshdeform_bind(modifier=m.name)
                        except:
                            if addon_prefs.debug:
                                print(obj.name + " modifier: " + m.name + " could not be binded")
                    with bpy.context.temp_override(object=obj):
                        try:
                            bpy.ops.object.meshdeform_bind(modifier=m.name)
                        except:
                            pass
                elif not m.is_bound and force:
                    with bpy.context.temp_override(object=obj):
                        try:
                            bpy.ops.object.meshdeform_bind(modifier=m.name)
                        except:
                            if addon_prefs.debug:
                                print(obj.name + " modifier: " + m.name + " could not be binded")
                target.hide_viewport = hv

        elif corrective_smooth and m.type == 'CORRECTIVE_SMOOTH':
            if m.rest_source != "BIND":
                continue
            hv = m.show_viewport
            m.show_viewport = True
            if m.is_bind:
                with bpy.context.temp_override(object=obj):
                    try:
                        bpy.ops.object.correctivesmooth_bind(modifier=m.name)
                    except:
                        if addon_prefs.debug:
                            print(obj.name + " modifier: " + m.name + " could not be binded")
                with bpy.context.temp_override(object=obj):
                    try:
                        bpy.ops.object.correctivesmooth_bind(modifier=m.name)
                    except:
                        pass
            elif not m.is_bound and force:
                with bpy.context.temp_override(object=obj):
                    try:
                        bpy.ops.object.correctivesmooth_bind(modifier=m.name)
                    except:
                        if addon_prefs.debug:
                            print(obj.name + " modifier: " + m.name + " could not be binded")
            m.show_viewport = hv


class MustardUI_PhysicsItem_Rebind(bpy.types.Operator):
    """Rebind cages to the model meshes (Body, Outfits, Hair).\nDepending on the number of Physics Items, Blender might freeze for a while"""
    bl_idname = "mustardui.physics_rebind"
    bl_label = "Rebind Physics"
    bl_options = {'UNDO'}

    force: bpy.props.BoolProperty(default=False,
                                  name="Force re-binding",
                                  description="Force re-binding of cages that are not bound")

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        return res if arm is not None else False

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings
        physics_settings = arm.MustardUI_PhysicsSettings
        addon_prefs = context.preferences.addons[base_package].preferences

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
        for item in [x for x in physics_settings.items if x.type == "COLLISION" and x.object is not None]:
            objects.append(item.object)

        # Gather cages to check as targets of modifiers
        cages = []
        for item in [x for x in physics_settings.items if x.type == "CAGE" and x.object is not None]:
            cages.append(item.object)

        for obj in objects:
            bind_object(obj,
                        cages,
                        addon_prefs,
                        surface_deform=True,
                        mesh_deform=True,
                        corrective_smooth=True,
                        force=self.force
                        )

        self.report({'INFO'}, 'MustardUI - Cages successfully re-binded.')

        return {'FINISHED'}


class MustardUI_PhysicsItem_Rebind_Outfit(bpy.types.Operator):
    """Rebind cages to the current Outfit.\nDepending on the number of Physics Items, Blender might freeze for a
    while"""
    bl_idname = "mustardui.physics_rebind_outfit"
    bl_label = "Rebind Physics"
    bl_options = {'UNDO'}

    force: bpy.props.BoolProperty(default=False,
                                  name="Force re-binding",
                                  description="Force re-binding of cages that are not bound")

    outfit: bpy.props.StringProperty(default="")

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        return res if arm is not None else False

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings
        physics_settings = arm.MustardUI_PhysicsSettings
        addon_prefs = context.preferences.addons[base_package].preferences

        if len(physics_settings.items) < 1:
            self.report({'WARNING'}, f'MustardUI - Nothing to bind.')
            return {'CANCELLED'}

        # Gather items to re-bind cages on
        objects = [rig_settings.model_body]
        collection = bpy.data.collections[self.outfit]

        if collection is None or len(collection.objects) < 1:
            self.report({'WARNING'}, f'MustardUI - Nothing to bind.')
            return {'CANCELLED'}

        for obj in [x for x in collection.objects if x.type == "MESH"]:
            objects.append(obj)

        # Gather cages to check as targets of modifiers
        cages = []
        for item in [x for x in physics_settings.items if x.type == "CAGE" and x.object is not None]:
            cages.append(item.object)

        for obj in objects:
            bind_object(obj,
                        cages,
                        addon_prefs,
                        surface_deform=True,
                        mesh_deform=True,
                        corrective_smooth=True,
                        force=self.force
                        )

        self.report({'INFO'}, f'MustardUI - Cages successfully re-binded for Outfit "{self.outfit}".')

        return {'FINISHED'}


class MustardUI_PhysicsItem_Rebind_Single(bpy.types.Operator):
    """Rebind cages to a single mesh.\nDepending on the number of Physics Items, Blender might freeze for a while"""
    bl_idname = "mustardui.physics_rebind_single"
    bl_label = "Rebind Physics"
    bl_options = {'UNDO'}

    force: bpy.props.BoolProperty(default=False,
                                  name="Force re-binding",
                                  description="Force re-binding of cages that are not bound")

    object_name: bpy.props.StringProperty(default="")

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        return res if arm is not None else False

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=0)
        physics_settings = arm.MustardUI_PhysicsSettings
        addon_prefs = context.preferences.addons[base_package].preferences

        if len(physics_settings.items) < 1:
            return {'FINISHED'}

        # Gather items to re-bind cages on
        obj = context.scene.objects[self.object_name]

        # Gather cages to check as targets of modifiers
        cages = []
        for item in [x for x in physics_settings.items if x.type == "CAGE" and x.object is not None]:
            cages.append(item.object)

        bind_object(obj,
                    cages,
                    addon_prefs,
                    surface_deform=True,
                    mesh_deform=True,
                    corrective_smooth=True,
                    force=self.force
                    )

        self.report({'INFO'}, f'MustardUI - Cages successfully re-binded to "{self.object_name}".')

        return {'FINISHED'}


class MustardUI_PhysicsItem_Rebind_SingleCage(bpy.types.Operator):
    """Rebind one cage to the model meshes (Body, Outfits, Hair).\nDepending on the number of Objects, Blender might freeze for a while"""
    bl_idname = "mustardui.physics_rebind_single_cage"
    bl_label = "Rebind Physics"
    bl_options = {'UNDO'}

    force: bpy.props.BoolProperty(default=False,
                                  name="Force re-binding",
                                  description="Force re-binding of cages that are not bound")

    cage_name: bpy.props.StringProperty(default="")

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        return res if arm is not None else False

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings
        physics_settings = arm.MustardUI_PhysicsSettings
        addon_prefs = context.preferences.addons[base_package].preferences

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
        for item in [x for x in physics_settings.items if x.type == "COLLISION" and x.object is not None]:
            objects.append(item.object)

        # Fetch the cage to check as targets of modifiers
        cages = []
        for item in [x for x in physics_settings.items if x.type == "CAGE" and x.object is not None and x.object.name == self.cage_name]:
            cages.append(item.object)
            break

        for obj in objects:
            bind_object(obj,
                        cages,
                        addon_prefs,
                        surface_deform=True,
                        mesh_deform=True,
                        corrective_smooth=True,
                        force=self.force
                        )

        self.report({'INFO'}, f'MustardUI - Cage "{self.cage_name}" successfully re-binded.')

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_PhysicsItem_Rebind)
    bpy.utils.register_class(MustardUI_PhysicsItem_Rebind_Single)
    bpy.utils.register_class(MustardUI_PhysicsItem_Rebind_Outfit)
    bpy.utils.register_class(MustardUI_PhysicsItem_Rebind_SingleCage)


def unregister():
    bpy.utils.unregister_class(MustardUI_PhysicsItem_Rebind_SingleCage)
    bpy.utils.unregister_class(MustardUI_PhysicsItem_Rebind_Outfit)
    bpy.utils.unregister_class(MustardUI_PhysicsItem_Rebind_Single)
    bpy.utils.unregister_class(MustardUI_PhysicsItem_Rebind)
