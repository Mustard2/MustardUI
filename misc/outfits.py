import bpy


def outfit_poll_collection(self, object):
    rig_settings = self.id_data.MustardUI_RigSettings
    collections = [x.collection for x in rig_settings.outfits_collections if x.collection is not None]
    if rig_settings.extras_collection is not None:
        collections.append(rig_settings.extras_collection)
    if rig_settings.hair_collection is not None:
        collections.append(rig_settings.hair_collection)
    return object in collections


# Poll function for the selection of mesh belonging to an outfit in pointer properties
def outfit_poll_mesh(self, object):
    rig_settings = self.id_data.MustardUI_RigSettings
    if self.outfit_switcher_collection is not None:
        items = self.outfit_switcher_collection.all_objects if rig_settings.outfit_config_subcollections else self.outfit_switcher_collection.objects
        if object in [x for x in items]:
            return object.type == 'MESH'
    return False

def outfit_poll_mesh_physics(self, object):
    rig_settings = self.id_data.MustardUI_RigSettings
    physics_settings = self.id_data.MustardUI_PhysicsSettings
    if self.outfit_collection is not None:
        physics_items = [x.object for x in physics_settings.items]
        items = []
        for obj in (self.outfit_collection.all_objects if rig_settings.outfit_config_subcollections else self.outfit_collection.objects):
            if obj not in physics_items:
                items.append(obj)
        for children in [x.children for x in items]:
            for obj in children:
                if obj not in physics_items:
                    items.append(obj)
        if object in [x for x in items] and object != self.object:
            return object.type == 'MESH'
    return False