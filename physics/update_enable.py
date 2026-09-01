from ..misc.set_bool import set_bool
from ..model_selection.active_object import mustardui_active_object
from ..outfits.helper_functions import find_layer_collection


def model_objects(rig_settings):
    """Iterate over the model objects that can be driven by the Physics Items.

    Yield (object, visible) tuples, where visible takes into account the visibility of
    the collection the object belongs to.
    """
    for obj in rig_settings.model_armature_object.children:
        yield obj, not obj.hide_viewport

    for coll in [x.collection for x in rig_settings.outfits_collections if x.collection]:
        objects = coll.all_objects if rig_settings.outfit_config_subcollections else coll.objects
        for obj in [x for x in objects if x.type == "MESH"]:
            yield obj, not coll.hide_viewport and not obj.hide_viewport

    extras = rig_settings.extras_collection
    if extras is not None:
        objects = (
            extras.all_objects if rig_settings.extras_config_subcollections else extras.objects
        )
        for obj in [x for x in objects if x.type == "MESH"]:
            yield obj, not extras.hide_viewport and not obj.hide_viewport

    for coll in [rig_settings.hair_collection, rig_settings.hair_extras_collection]:
        if coll is None:
            continue
        for obj in [x for x in coll.objects if x.type == "MESH"]:
            yield obj, not coll.hide_viewport and not obj.hide_viewport


def update_physics_collections_exclude(physics_settings, context):
    """Exclude (or re-include) collections that contain only UI physics items."""
    physics_objects = {pi.object for pi in physics_settings.items if pi.object}
    if not physics_objects:
        return

    master = context.scene.collection
    view_layer = context.view_layer

    # Collections directly holding at least one physics item object
    candidate_colls = {coll for obj in physics_objects for coll in obj.users_collection}

    for coll in candidate_colls:
        if coll == master:
            continue
        # Only act on collections whose contents are exclusively physics items
        if all(obj in physics_objects for obj in coll.all_objects):
            lc = find_layer_collection(view_layer.layer_collection, coll)
            if lc is not None:
                set_bool(lc, "exclude", not physics_settings.enable_physics)


def set_physics_item(physics_item, status):
    """Apply the enable status to the Physics Item object itself."""
    obj = physics_item.object

    mod_types = {"COLLISION": {"COLLISION", "ARMATURE", "DISPLACE"}}.get(physics_item.type)

    for modifier in obj.modifiers:
        if mod_types is not None and modifier.type not in mod_types:
            continue
        modifier.show_viewport = status
        modifier.show_render = status
        if modifier.type == "COLLISION" and physics_item.type == "COLLISION":
            obj.collision.use = status

    if physics_item.type == "BONES_DRIVER":
        physics_item.bone_influence = status

    # Shape Keys and their drivers
    shape_keys = obj.data.shape_keys if obj.data else None
    if shape_keys is not None:
        for key in shape_keys.key_blocks:
            set_bool(key, "mute", not status)
        if shape_keys.animation_data and shape_keys.animation_data.drivers:
            for fcurve in shape_keys.animation_data.drivers:
                set_bool(fcurve, "mute", not status)

    # Collision items are always shown when enabled, otherwise the collisions might not
    # work (Blender bug), while the other items restore the visibility they had
    if physics_item.type == "COLLISION":
        obj.hide_viewport = not status
    elif status:
        obj.hide_viewport = physics_item.visibility_pre_disable
    else:
        physics_item.visibility_pre_disable = obj.hide_viewport
        obj.hide_viewport = True


def set_cage_object_modifiers(physics_item, obj, status, body, mtype=""):
    """Update the modifiers of an object driven by a Cage Physics Item.

    Both the deform modifiers bound to the Cage and the modifiers named after it (Smooth
    Corrective, Vertex Weight Mix, ...) are updated. If mtype is provided, only the
    modifiers of that type are updated, together with the Vertex Weight Mix feeding them.
    """
    cage = physics_item.object
    if cage is None:
        return

    if mtype == "":
        intersecting_objects = [x.object for x in physics_item.intersecting_objects]
        for modifier in obj.modifiers:
            if (modifier.type == "MESH_DEFORM" and modifier.object == cage) or (
                modifier.type == "SURFACE_DEFORM"
                and (
                    modifier.target == cage
                    or (modifier.target == body and obj in intersecting_objects)
                )
            ):
                modifier.show_viewport = status
                modifier.show_render = status

    smooth_mods = {}  # vertex_group -> CORRECTIVE_SMOOTH modifier
    weight_mix_active = {}  # vertex_group_a -> whether any feeding weight mix is active

    for modifier in obj.modifiers:
        name_match = cage.name in modifier.name
        if name_match and (mtype == "" or modifier.type == mtype):
            modifier.show_viewport = status
            modifier.show_render = status
        if modifier.type == "CORRECTIVE_SMOOTH" and modifier.vertex_group:
            smooth_mods[modifier.vertex_group] = modifier
        if modifier.type == "VERTEX_WEIGHT_MIX" and modifier.vertex_group_a:
            # Optimized smooth corrective: a VERTEX_WEIGHT_MIX feeds a master
            # CORRECTIVE_SMOOTH when vertex_group_a matches the vertex_group
            # of one of the smooth modifiers
            if name_match and (mtype == "" or mtype == "CORRECTIVE_SMOOTH"):
                modifier.show_viewport = status
                modifier.show_render = status
            vg_a = modifier.vertex_group_a
            weight_mix_active[vg_a] = weight_mix_active.get(vg_a, False) or modifier.show_viewport

    for vg, mod in smooth_mods.items():
        if vg in weight_mix_active:
            mod.show_viewport = weight_mix_active[vg]
            mod.show_render = weight_mix_active[vg]


def set_cage_driven_modifiers(physics_item, rig_settings, status, mtype=""):
    """Update the modifiers driven by a Cage Physics Item on all the model objects."""
    body = rig_settings.model_body

    set_cage_object_modifiers(physics_item, body, status, body, mtype)

    for obj, visible in model_objects(rig_settings):
        if obj == physics_item.object:
            continue
        set_cage_object_modifiers(physics_item, obj, status and visible, body, mtype)


def set_cage_item_modifiers(physics_settings, rig_settings, obj, visible=None):
    """Update the modifiers of an object driven by the Cages."""
    if visible is None:
        visible = not obj.hide_viewport

    for pi in [x for x in physics_settings.items if x.type == "CAGE" and x.object]:
        if pi.object == obj:
            continue
        status = physics_settings.enable_physics and pi.enable and visible
        set_cage_object_modifiers(pi, obj, status, rig_settings.model_body)


def influence_cage_modifiers(physics_item, iterator, influence):
    if physics_item.object is None:
        return

    for mod in iterator:
        if mod.type == "SURFACE_DEFORM":
            if physics_item.object == mod.target:
                mod.strength = influence
                mod.show_viewport = influence > 0.001
                mod.show_render = influence > 0.001


def enable_physics_update(self, context):
    res, arm = mustardui_active_object(context, config=0)

    if arm is None or not res:
        return

    rig_settings = arm.MustardUI_RigSettings
    body = rig_settings.model_body

    for pi in [x for x in self.items if x.object]:
        status = self.enable_physics and pi.enable
        set_physics_item(pi, status)
        if pi.type == "CAGE":
            set_cage_object_modifiers(pi, body, status, body)

    # The Cages are applied to the other objects only after the visibility of all the
    # Physics Items has been updated
    for obj, visible in model_objects(rig_settings):
        set_cage_item_modifiers(self, rig_settings, obj, visible)

    # Exclude collections that hold only UI physics items when Physics is disabled
    update_physics_collections_exclude(self, context)


def enable_physics_update_single(self, context):
    res, arm = mustardui_active_object(context, config=0)

    if arm is None or not res or not self.object:
        return

    rig_settings = arm.MustardUI_RigSettings
    physics_settings = arm.MustardUI_PhysicsSettings

    status = physics_settings.enable_physics and self.enable

    set_physics_item(self, status)

    if self.type == "CAGE":
        set_cage_driven_modifiers(self, rig_settings, status)
    else:
        # The modifiers driven by the Cages on this object follow their own Cage item
        set_cage_item_modifiers(physics_settings, rig_settings, self.object)


def enable_physics_update_single_smooth_corrective(self, context):
    res, arm = mustardui_active_object(context, config=0)

    if arm is None or not res or not self.object:
        return

    rig_settings = arm.MustardUI_RigSettings
    physics_settings = arm.MustardUI_PhysicsSettings

    status = physics_settings.enable_physics and self.enable and self.smooth_corrective

    for modifier in [x for x in self.object.modifiers if x.type == "CORRECTIVE_SMOOTH"]:
        modifier.show_viewport = status
        modifier.show_render = status

    if self.type == "CAGE":
        set_cage_driven_modifiers(self, rig_settings, status, "CORRECTIVE_SMOOTH")


def collisions_physics_update_single(self, context):
    res, arm = mustardui_active_object(context, config=0)

    if (
        arm is None
        or not res
        or not self.object
        and self.type not in ["CAGE", "SINGLE_ITEM", "BONES_DRIVER"]
    ):
        return

    status = self.collisions and self.enable
    for modifier in [x for x in self.object.modifiers if x.type == "CLOTH"]:
        modifier.collision_settings.use_collision = status


def cage_influence_update(self, context):
    res, arm = mustardui_active_object(context, config=0)

    if arm is None or not res and self.type != "CAGE":
        return

    influence = self.cage_influence

    rig_settings = arm.MustardUI_RigSettings

    influence_cage_modifiers(self, rig_settings.model_body.modifiers, influence)

    for obj, _ in model_objects(rig_settings):
        influence_cage_modifiers(self, obj.modifiers, influence)


def bone_influence_update(self, context):
    res, arm = mustardui_active_object(context, config=0)

    if arm is None or not res and self.type != "BONES_DRIVER":
        return

    parent = self.object.parent

    if not parent or parent.type != "ARMATURE":
        return

    influence = self.bone_influence
    status = influence > 0.001
    for bone in parent.pose.bones:
        for constraint in [
            x for x in bone.constraints if hasattr(x, "target") and x.target == self.object
        ]:
            if hasattr(constraint, "influence"):
                constraint.influence = influence
            elif hasattr(constraint, "strength"):
                constraint.strength = influence
            constraint.enabled = status
