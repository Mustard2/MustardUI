def get_ui_mesh_objects(rig_settings):

    objects = []

    if rig_settings.model_body is not None:
        objects.append(rig_settings.model_body)

    for coll in [
        x for x in rig_settings.outfits_collections if x.collection is not None
    ]:
        items = (
            coll.collection.all_objects
            if rig_settings.outfit_config_subcollections
            else coll.collection.objects
        )
        objects.extend([x for x in items if x.type == "MESH"])

    for attr in ("hair_collection", "extras_collection", "hair_extras_collection"):
        coll = getattr(rig_settings, attr)
        if coll is not None:
            objects.extend([x for x in coll.objects if x.type == "MESH"])

    if rig_settings.model_armature_object is not None:
        for obj in rig_settings.model_armature_object.children:
            if obj.type == "MESH" and obj not in objects:
                objects.append(obj)

    return objects
