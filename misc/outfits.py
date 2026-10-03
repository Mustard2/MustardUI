def outfits_get_collection_items(rig_settings, collection):
    """Objects of an Outfits/Extras collection, honouring the sub-collections setting."""
    use_sub = (
        rig_settings.extras_config_subcollections
        if collection == rig_settings.extras_collection
        else rig_settings.outfit_config_subcollections
    )
    return collection.all_objects if use_sub else collection.objects


def outfit_extract_items_from_collection(collection, subcollections):
    items = list(collection.all_objects if subcollections else collection.objects)
    item_set = set(items)
    return [x for x in items if x.parent is None or x.parent not in item_set]


def outfit_poll_collection(self, object):
    rig_settings = self.id_data.MustardUI_RigSettings
    collections = [
        x.collection for x in rig_settings.outfits_collections if x.collection is not None
    ]
    if rig_settings.extras_collection is not None:
        collections.append(rig_settings.extras_collection)
        if rig_settings.extras_config_subcollections:
            collections.extend(rig_settings.extras_collection.children_recursive)
    if rig_settings.hair_collection is not None:
        collections.append(rig_settings.hair_collection)
    if rig_settings.hair_extras_collection is not None:
        collections.append(rig_settings.hair_extras_collection)
    return object in collections


# Poll function for the selection of mesh belonging to an outfit in pointer properties
def outfit_poll_mesh(self, object):
    coll = self.outfit_switcher_collection
    if coll is None or object.type not in {"MESH", "CURVES"}:
        return False
    return object in list(outfits_get_collection_items(self.id_data.MustardUI_RigSettings, coll))


def outfit_poll_mesh_physics(self, object):
    if self.outfit_collection is None or object == self.object or object.type != "MESH":
        return False

    rig_settings = self.id_data.MustardUI_RigSettings
    physics_settings = self.id_data.MustardUI_PhysicsSettings
    physics_objects = {x.object for x in physics_settings.items}
    pieces = set(
        self.outfit_collection.all_objects
        if rig_settings.outfit_config_subcollections
        else self.outfit_collection.objects
    )
    pieces -= physics_objects

    return object in pieces or (object not in physics_objects and object.parent in pieces)
