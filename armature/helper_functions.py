def outfits_update_armature_collections(
    rig_settings, arm, is_extras_hidden=None, outfits=False, hair=False
):
    """Update visibility of armature bone collections like the outfit operator"""

    armature_settings = arm.MustardUI_ArmatureSettings
    hair_collections = {rig_settings.hair_collection, rig_settings.hair_extras_collection}
    hair_collections.discard(None)

    for bcoll in arm.collections_all:
        bcoll_settings = bcoll.MustardUI_ArmatureBoneCollection
        if not bcoll_settings.outfit_switcher_enable:
            continue
        if not bcoll_settings.outfit_switcher_collection:
            continue

        switcher_collection = bcoll_settings.outfit_switcher_collection

        is_hair = switcher_collection in hair_collections
        if (outfits and is_hair) or (hair and not is_hair):
            continue

        use_subcollections = (
            rig_settings.extras_config_subcollections
            if switcher_collection == rig_settings.extras_collection
            else rig_settings.outfit_config_subcollections
        )

        items = (
            switcher_collection.all_objects if use_subcollections else switcher_collection.objects
        )

        # No piece set: follow the whole collection
        visible = bcoll_settings.outfit_switcher_object is None and not (
            switcher_collection.hide_viewport
            or (switcher_collection == rig_settings.extras_collection and is_extras_hidden)
        )
        for ob in items:
            if ob == bcoll_settings.outfit_switcher_object:
                # If it is an Extras item, we should test if the collection
                # is not hidden
                is_extras_item = False
                if rig_settings.extras_collection:
                    is_extras_item = any(
                        ob == extra for extra in rig_settings.extras_collection.all_objects
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

        # Outfits/Hair checkboxes in the Armature panel
        visible = visible and (armature_settings.hair if is_hair else armature_settings.outfits)

        if bcoll.is_visible != visible:
            bcoll.is_visible = visible
