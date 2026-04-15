def outfits_update_armature_collections(rig_settings, arm, is_extras_hidden=None):
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
                # If it is an Extras item, we should test if the collection
                # is not hidden
                is_extras_item = False
                if rig_settings.extras_collection:
                    is_extras_item = any(
                        ob == extra
                        for extra in rig_settings.extras_collection.all_objects
                    )

                if is_extras_item:
                    visible = (
                        not ob.hide_viewport
                        and not bcoll_settings.outfit_switcher_collection.hide_viewport
                        and not is_extras_hidden
                    )
                else:
                    visible = (
                        not ob.hide_viewport
                        and not bcoll_settings.outfit_switcher_collection.hide_viewport
                    )
                break

        if bcoll.is_visible != visible:
            bcoll.is_visible = visible
