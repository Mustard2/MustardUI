import bpy
from ..model_selection.active_object import *


def set_cage_modifiers(physics_item, iterator, s):
    for mod in iterator:
        if mod.type == 'MESH_DEFORM':
            if physics_item.object == mod.object:
                mod.show_viewport = s
                mod.show_render = s
        elif mod.type == 'SURFACE_DEFORM':
            if physics_item.object == mod.target:
                mod.show_viewport = s
                mod.show_render = s


def enable_physics_update(self, context):

    res, arm = mustardui_active_object(context, config=0)

    if arm is None or not res:
        return

    rig_settings = arm.MustardUI_RigSettings

    for pi in [x for x in self.items]:
        status = self.enable_physics and pi.enable
        for modifier in pi.object.modifiers:
            if modifier.type in ['CLOTH', 'SOFT_BODY'] and pi.type in ["CAGE", "SINGLE_ITEM"]:
                modifier.show_viewport = status
                modifier.show_render = status
            elif modifier.type == 'COLLISION' and pi.type == "COLLISION":
                pi.object.collision.use = status
        if pi.type == "CAGE":
            set_cage_modifiers(pi, rig_settings.model_body.modifiers, status)
            for modifier in rig_settings.model_body.modifiers:
                if modifier.type == 'CORRECTIVE_SMOOTH' and pi.object.name in modifier.name:
                    modifier.show_viewport = status
                    modifier.show_render = status
            pi.object.hide_viewport = not status

    for coll in [x for x in rig_settings.outfits_collections if x.collection is not None]:
        items = coll.collection.all_objects if rig_settings.outfit_config_subcollections else coll.collection.objects
        for obj in items:
            for pi in [x for x in self.items if x.type == "CAGE"]:
                status = self.enable_physics and pi.enable
                set_cage_modifiers(pi, obj.modifiers, status)
                for modifier in obj.modifiers:
                    if modifier.type == 'CORRECTIVE_SMOOTH' and pi.object.name in modifier.name:
                        modifier.show_viewport = status
                        modifier.show_render = status

    return


def enable_physics_update_single(self, context):

    res, arm = mustardui_active_object(context, config=0)

    if arm is None or not res or not self.object:
        return

    rig_settings = arm.MustardUI_RigSettings
    physics_settings = arm.MustardUI_PhysicsSettings

    status = physics_settings.enable_physics and self.enable
    for modifier in self.object.modifiers:
        if modifier.type in ['CLOTH', 'SOFT_BODY'] and self.type in ["CAGE", "SINGLE_ITEM"]:
            modifier.show_viewport = status
            modifier.show_render = status
        elif modifier.type == 'COLLISION' and self.type == "COLLISION":
            self.object.collision.use = status
    if self.type == "CAGE":
        set_cage_modifiers(self, rig_settings.model_body.modifiers, status)

    for coll in [x for x in rig_settings.outfits_collections if x.collection is not None]:
        items = coll.collection.all_objects if rig_settings.outfit_config_subcollections else coll.collection.objects
        for obj in items:
            if self.type == "CAGE":
                status = physics_settings.enable_physics and self.enable
                set_cage_modifiers(self, obj.modifiers, status)
                self.object.hide_viewport = not status

    return


def collisions_physics_update_single(self, context):
    res, arm = mustardui_active_object(context, config=0)

    if arm is None or not res or not self.object and not (self.type in ["CAGE", "SINGLE_ITEM"]):
        return

    status = self.collisions and self.enable
    for modifier in self.object.modifiers:
        if modifier.type in ['CLOTH']:
            modifier.collision_settings.use_collision = status

    return
