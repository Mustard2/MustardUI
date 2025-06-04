import bpy
from ..model_selection.active_object import *
from ..misc.mesh_intersection import check_mesh_intersection


def set_cage_modifiers(physics_item, iterator, s, obj, body):
    intersecting_objects = [x.object for x in physics_item.intersecting_objects]
    for mod in iterator:
        if mod.type == 'MESH_DEFORM':
            if mod.object == physics_item.object:
                mod.show_viewport = s
                mod.show_render = s
        elif mod.type == 'SURFACE_DEFORM':
            if mod.target == physics_item.object:
                mod.show_viewport = s
                mod.show_render = s
            elif obj is not None and mod.target == body and obj in intersecting_objects:
                mod.show_viewport = s
                mod.show_render = s


def influence_cage_modifiers(physics_item, iterator, influence):
    for mod in iterator:
        if mod.type == 'SURFACE_DEFORM':
            if physics_item.object == mod.target:
                mod.strength = influence
                mod.show_viewport = influence > 0.001
                mod.show_render = influence > 0.001


def set_modifiers(physics_item, obj, status):
    for modifier in obj.modifiers:
        if physics_item.object.name in modifier.name:
            modifier.show_viewport = status
            modifier.show_render = status


def enable_physics_update(self, context):

    res, arm = mustardui_active_object(context, config=0)

    if arm is None or not res:
        return

    rig_settings = arm.MustardUI_RigSettings
    body = rig_settings.model_body

    for pi in [x for x in self.items]:
        status = self.enable_physics and pi.enable
        for modifier in pi.object.modifiers:
            modifier.show_viewport = status
            modifier.show_render = status
            if modifier.type == 'COLLISION' and pi.type == "COLLISION":
                pi.object.collision.use = status
                # Make the object visibile otherwise collisions might not work (Blender bug)
                pi.object.hide_viewport = not status
        if pi.type == "CAGE":
            set_cage_modifiers(pi, rig_settings.model_body.modifiers, status, None, body)
            set_modifiers(pi, rig_settings.model_body, status)
        elif pi.type == "BONES_DRIVER":
            pi.bone_influence = status

        if not status:
            pi.object.hide_viewport = True
        if not self.enable_physics:
            pi.collapse_cloth = True
            pi.collapse_softbody = True
            pi.collapse_collisions = True

    for obj in rig_settings.model_armature_object.children:
        for pi in [x for x in self.items if x.type == "CAGE"]:
            status = self.enable_physics and pi.enable and not obj.hide_viewport
            set_cage_modifiers(pi, obj.modifiers, status, obj, body)
            set_modifiers(pi, obj, status)

    for coll in [x for x in rig_settings.outfits_collections if x.collection is not None]:
        items = coll.collection.all_objects if rig_settings.outfit_config_subcollections else coll.collection.objects
        for obj in [x for x in items if x.type == "MESH"]:
            for pi in [x for x in self.items if x.type == "CAGE"]:
                status = self.enable_physics and pi.enable and not coll.collection.hide_viewport and not obj.hide_viewport
                set_cage_modifiers(pi, obj.modifiers, status, obj, body)
                set_modifiers(pi, obj, status)

    if rig_settings.hair_collection is not None:
        for obj in [x for x in rig_settings.hair_collection.objects if x.type == "MESH"]:
            for pi in [x for x in self.items if x.type == "CAGE"]:
                status = self.enable_physics and pi.enable and not rig_settings.hair_collection.hide_viewport and not obj.hide_viewport
                set_cage_modifiers(pi, obj.modifiers, status, obj, body)
                set_modifiers(pi, obj, status)

    if rig_settings.extras_collection is not None:
        for obj in [x for x in rig_settings.extras_collection.objects if x.type == "MESH"]:
            for pi in [x for x in self.items if x.type == "CAGE"]:
                status = self.enable_physics and pi.enable and not rig_settings.extras_collection.hide_viewport and not obj.hide_viewport
                set_cage_modifiers(pi, obj.modifiers, status, obj, body)
                set_modifiers(pi, obj, status)

    return


def enable_physics_update_single(self, context):

    res, arm = mustardui_active_object(context, config=0)

    if arm is None or not res or not self.object:
        return

    rig_settings = arm.MustardUI_RigSettings
    physics_settings = arm.MustardUI_PhysicsSettings

    body = rig_settings.model_body

    status = physics_settings.enable_physics and self.enable
    for modifier in self.object.modifiers:
        modifier.show_viewport = status
        modifier.show_render = status
        if modifier.type == 'COLLISION' and self.type == "COLLISION":
            self.object.collision.use = status
            # Make the object visibile otherwise collisions might not work (Blender bug)
            self.object.hide_viewport = not status
    if self.type == "CAGE":
        set_cage_modifiers(self, rig_settings.model_body.modifiers, status, None, body)
        set_modifiers(self, rig_settings.model_body, status)

        for obj in rig_settings.model_armature_object.children:
            status = status and not obj.hide_viewport
            set_cage_modifiers(self, obj.modifiers, status, obj, body)
            set_modifiers(self, obj, status)

        for coll in [x for x in rig_settings.outfits_collections if x.collection is not None]:
            items = coll.collection.all_objects if rig_settings.outfit_config_subcollections else coll.collection.objects
            for obj in [x for x in items if x.type == "MESH"]:
                status_int = status and not coll.collection.hide_viewport and not obj.hide_viewport
                set_cage_modifiers(self, obj.modifiers, status_int, obj, body)
                set_modifiers(self, obj, status_int)

        if rig_settings.extras_collection is not None:
            for obj in [x for x in rig_settings.extras_collection.objects if x.type == "MESH"]:
                status_int = status and not rig_settings.extras_collection.hide_viewport and not obj.hide_viewport
                set_cage_modifiers(self, obj.modifiers, status_int, obj, body)
                set_modifiers(self, obj, status_int)

        if rig_settings.hair_collection is not None:
            for obj in [x for x in rig_settings.hair_collection.objects if x.type == "MESH"]:
                status_int = status and not rig_settings.hair_collection.hide_viewport and not obj.hide_viewport
                set_cage_modifiers(self, obj.modifiers, status_int, obj, body)
                set_modifiers(self, obj, status_int)
    elif self.type == "BONES_DRIVER":
        self.bone_influence = status

    if not status:
        self.object.hide_viewport = True

    if not self.enable:
        self.collapse_cloth = True
        self.collapse_softbody = True
        self.collapse_collisions = True

    return


def collisions_physics_update_single(self, context):
    res, arm = mustardui_active_object(context, config=0)

    if arm is None or not res or not self.object and not (self.type in ["CAGE", "SINGLE_ITEM", "BONES_DRIVER"]):
        return

    status = self.collisions and self.enable
    for modifier in self.object.modifiers:
        if modifier.type in ['CLOTH']:
            modifier.collision_settings.use_collision = status

    return


def cage_influence_update(self, context):
    res, arm = mustardui_active_object(context, config=0)

    if arm is None or not res and self.type != "CAGE":
        return

    influence = self.cage_influence

    rig_settings = arm.MustardUI_RigSettings

    influence_cage_modifiers(self, rig_settings.model_body.modifiers, influence)

    for coll in [x for x in rig_settings.outfits_collections if x.collection is not None]:
        items = coll.collection.all_objects if rig_settings.outfit_config_subcollections else coll.collection.objects
        for obj in items:
            influence_cage_modifiers(self, obj.modifiers, influence)
    return


def bone_influence_update(self, context):
    res, arm = mustardui_active_object(context, config=0)

    if arm is None or not res and self.type != "BONES_DRIVER":
        return

    parent = self.object.parent

    if parent.type != "ARMATURE":
        return

    influence = self.bone_influence
    status = influence > 0.001
    for bone in parent.pose.bones:
        for constraint in [x for x in bone.constraints if hasattr(x, "target") and x.target == self.object]:
            if hasattr(constraint, 'influence'):
                constraint.influence = influence
            elif hasattr(constraint, 'strength'):
                constraint.strength = influence
            constraint.enabled = status

    return
