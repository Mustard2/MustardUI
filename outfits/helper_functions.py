import bpy

def outfits_update_armature_collections(rig_settings, arm):
    """Update visibility of armature bone collections like the outfit operator"""

    use_subcollections = rig_settings.outfit_config_subcollections

    for bcoll in arm.collections_all:
        bcoll_settings = bcoll.MustardUI_ArmatureBoneCollection
        if not bcoll_settings.outfit_switcher_enable:
            continue
        if not bcoll_settings.outfit_switcher_collection:
            continue

        items = (
            bcoll_settings.outfit_switcher_collection.all_objects
            if use_subcollections
            else bcoll_settings.outfit_switcher_collection.objects
        )

        visible = False
        for ob in items:
            if ob == bcoll_settings.outfit_switcher_object:
                visible = (
                        not ob.hide_viewport
                        and not bcoll_settings.outfit_switcher_collection.hide_viewport
                )
                break

        if bcoll.is_visible != visible:
            bcoll.is_visible = visible
