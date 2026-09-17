import bpy


def remove_objects(objects):
    """Remove the Objects, together with their Mesh and Armature data if no other Object
    uses it."""

    data_collections = {"MESH": bpy.data.meshes, "ARMATURE": bpy.data.armatures}

    data_blocks = {
        obj.data: data_collections[obj.type]
        for obj in objects
        if obj.type in data_collections and obj.data is not None
    }

    for obj in objects:
        bpy.data.objects.remove(obj)

    used = {obj.data for obj in bpy.data.objects if obj.data is not None}

    for data, collection in data_blocks.items():
        if data not in used and not data.use_fake_user:
            collection.remove(data)
