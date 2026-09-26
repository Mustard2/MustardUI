import re

import bpy

from ...misc.remove_objects import remove_objects
from ...model_selection.active_object import ModelMode, mustardui_active_object
from ...physics.update_enable import named_after_cage

# Vertex Groups the tools create on the meshes driven by the cages
GENERATED_GROUPS = re.compile(
    r"^(Combined Jiggle Groups|Jiggle Region \d+|Easy Sim(\.\d+)?|Accessory Physics Rigid( \d+)?)$"
)

VERTEX_GROUP_ATTRIBUTES = ("vertex_group", "vertex_group_a", "vertex_group_b")


def tool_type(obj):
    return getattr(obj, "MustardUI_tools_creators_type", "")


def deform_targets(obj):
    """Objects driving obj through Surface Deform and Mesh Deform modifiers, with the name
    of the modifier."""
    if obj.type != "MESH":
        return []
    targets = []
    for modifier in obj.modifiers:
        if modifier.type == "SURFACE_DEFORM" and modifier.target is not None:
            targets.append((modifier.target, modifier.name))
        elif modifier.type == "MESH_DEFORM" and modifier.object is not None:
            targets.append((modifier.object, modifier.name))
    return targets


def driven_by(cage):
    """Names of the deform modifiers using the cage."""
    return {
        name for obj in bpy.data.objects for target, name in deform_targets(obj) if target == cage
    }


# ----------------------------------------------------------------------------
# Recognizing the objects of each tool. The objects created by the current tools are
# tagged, the ones created before are recognized from what the tools leave on them
# ----------------------------------------------------------------------------


def is_jiggle(obj):
    if tool_type(obj):
        return tool_type(obj) == "JIGGLE"
    return (
        obj.type == "MESH"
        and any(g.name.startswith("Jiggle Pin") for g in obj.vertex_groups)
        and bool(driven_by(obj))
    )


def is_jiggle_accurate(obj):
    if tool_type(obj):
        return tool_type(obj) == "JIGGLE_ACCURATE"
    if obj.type != "MESH" or not obj.MustardUI_tools_creators_is_created:
        return False
    names = driven_by(obj)
    return (
        "Inflate" in obj.keys()
        and bool(names)
        and not any(n.startswith("Hair Deform") for n in names)
        and not any(g.name.startswith("Jiggle Pin") for g in obj.vertex_groups)
    )


def is_hair_cage(obj):
    if tool_type(obj):
        return tool_type(obj) == "HAIR"
    return obj.type == "MESH" and any(n.startswith("Hair Deform") for n in driven_by(obj))


def is_collision_cage(obj):
    if tool_type(obj):
        return tool_type(obj) == "COLLISION"
    return (
        obj.type == "MESH"
        and "Inflate" in obj.keys()
        and obj.name.endswith("Collision Cage")
        and any(m.type == "COLLISION" for m in obj.modifiers)
    )


def is_accessory(obj):
    if tool_type(obj):
        return tool_type(obj) == "ACCESSORY"
    return obj.type == "MESH" and any(n.startswith("Accessory Physics") for n in driven_by(obj))


def is_accessory_proxy(obj):
    return is_accessory(obj) and any(m.type == "CLOTH" for m in obj.modifiers)


def cages_from_selection(context, detector, sources=True):
    """The selected objects recognized by the detector, and the ones driving the other
    selected meshes."""
    selected = set(context.selected_objects)
    if context.active_object is not None:
        selected.add(context.active_object)
    cages = set()
    for obj in selected:
        if detector(obj):
            cages.add(obj)
        elif sources:
            cages.update(target for target, _ in deform_targets(obj) if detector(target))
    return cages


# ----------------------------------------------------------------------------
# Removal
# ----------------------------------------------------------------------------


def used_vertex_groups(obj):
    used = set()
    for modifier in obj.modifiers:
        for attribute in VERTEX_GROUP_ATTRIBUTES:
            used.add(getattr(modifier, attribute, ""))
        settings = getattr(modifier, "settings", None)
        if modifier.type == "CLOTH" and settings is not None:
            used.update(
                (
                    settings.vertex_group_mass,
                    settings.vertex_group_structural_stiffness,
                    settings.vertex_group_shear_stiffness,
                    settings.vertex_group_bending,
                )
            )
    used.discard("")
    return used


def remove_cages(arm, cages, extra_modifiers=()):
    """Remove the cages, the modifiers and constraints using them, the Vertex Groups created
    for them and their Physics Items.

    extra_modifiers is a list of (object, modifier name) to remove too."""
    cages = {c for c in cages if c is not None and c.name in bpy.data.objects}
    if not cages:
        return 0

    names = [c.name for c in cages]
    physics_settings = arm.MustardUI_PhysicsSettings if arm is not None else None
    cage_names = set(names)
    if physics_settings is not None:
        cage_names.update(x.object.name for x in physics_settings.items if x.object)

    # Modifiers on the other meshes
    removed_groups = {}
    extra = {(o.name, m) for o, m in extra_modifiers}
    for obj in [x for x in bpy.data.objects if x.type == "MESH" and x not in cages]:
        for modifier in list(obj.modifiers):
            hit = (
                (modifier.type == "SURFACE_DEFORM" and modifier.target in cages)
                or (modifier.type == "MESH_DEFORM" and modifier.object in cages)
                or (obj.name, modifier.name) in extra
                or any(named_after_cage(modifier.name, n, cage_names) for n in names)
            )
            if not hit:
                continue
            groups = removed_groups.setdefault(obj, set())
            groups.update(
                g for g in (getattr(modifier, a, "") for a in VERTEX_GROUP_ATTRIBUTES) if g
            )
            obj.modifiers.remove(modifier)

    # Vertex Groups left without a use
    for obj, groups in removed_groups.items():
        used = used_vertex_groups(obj)
        for name in groups - used:
            group = obj.vertex_groups.get(name)
            if group is not None and (
                GENERATED_GROUPS.match(name) or any(n in name for n in names)
            ):
                obj.vertex_groups.remove(group)

    # Bone constraints (e.g. Bone Physics)
    for obj in [x for x in bpy.data.objects if x.type == "ARMATURE" and x.pose]:
        for bone in obj.pose.bones:
            for constraint in list(bone.constraints):
                if getattr(constraint, "target", None) in cages:
                    bone.constraints.remove(constraint)

    # Physics Items
    if physics_settings is not None:
        for i in reversed(range(len(physics_settings.items))):
            if physics_settings.items[i].object in cages:
                physics_settings.items.remove(i)
        index = arm.mustardui_physics_items_uilist_index
        arm.mustardui_physics_items_uilist_index = max(
            0, min(index, len(physics_settings.items) - 1)
        )

    count = len(cages)
    remove_objects(list(cages))
    return count


def remove_empty_collections(collections):
    for collection in collections:
        if (
            collection.name in bpy.data.collections
            and not collection.all_objects
            and not collection.children
        ):
            bpy.data.collections.remove(collection)


# ----------------------------------------------------------------------------
# Operators
# ----------------------------------------------------------------------------


class RemovePhysicsBase:
    bl_options = {"REGISTER", "UNDO"}

    tool_name = ""

    @staticmethod
    def detector(obj):
        return False

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=ModelMode.MODEL_TOOLKIT)
        if not res or context.mode != "OBJECT":
            return False
        return bool(cages_from_selection(context, cls.detector))

    def collect(self, context, cages):
        """Other objects and modifiers created with the cages."""
        return set(), []

    def execute(self, context):
        res, arm = mustardui_active_object(context, config=ModelMode.MODEL_TOOLKIT)
        cages = cages_from_selection(context, self.detector)
        others, modifiers = self.collect(context, cages)
        collections = self.own_collections(cages | others)
        count = remove_cages(arm, cages | others, modifiers)
        remove_empty_collections(collections)
        self.after(context)
        self.report({"INFO"}, f"MustardUI - {self.tool_name} removed ({count} objects).")
        return {"FINISHED"}

    def own_collections(self, objects):
        """Collections created by the tool, removed if left empty."""
        return set()

    def after(self, context):
        return


class MustardUI_ToolsCreators_RemoveJiggle(RemovePhysicsBase, bpy.types.Operator):
    """Remove the Jiggle Cages (Quick) selected, or driving the selected meshes, together
    with their modifiers, Vertex Groups and Physics Items"""

    bl_idname = "mustardui.tools_creators_remove_jiggle"
    bl_label = "Remove Jiggle Cage (Quick)"
    tool_name = "Jiggle Cage"
    detector = staticmethod(is_jiggle)


class MustardUI_ToolsCreators_RemoveJiggleAccurate(RemovePhysicsBase, bpy.types.Operator):
    """Remove the Jiggle Cages (Accurate) selected, or driving the selected meshes, together
    with their modifiers, Vertex Groups and Physics Items"""

    bl_idname = "mustardui.tools_creators_remove_jiggle_accurate"
    bl_label = "Remove Jiggle Cage (Accurate)"
    tool_name = "Jiggle Cage"
    detector = staticmethod(is_jiggle_accurate)


class MustardUI_ToolsCreators_RemoveHairCage(RemovePhysicsBase, bpy.types.Operator):
    """Remove the Hair Cages selected, or driving the selected hair, together with their
    modifiers, Vertex Groups and Physics Items"""

    bl_idname = "mustardui.tools_creators_remove_hair_cage"
    bl_label = "Remove Hair Cage"
    tool_name = "Hair Cage"
    detector = staticmethod(is_hair_cage)

    def collect(self, context, cages):
        # The Corrective Smooth added on the hair with the cage
        modifiers = []
        for obj in [x for x in bpy.data.objects if x.type == "MESH"]:
            if any(target in cages for target, _ in deform_targets(obj)):
                modifiers += [
                    (obj, m.name)
                    for m in obj.modifiers
                    if m.type == "CORRECTIVE_SMOOTH" and m.name.startswith("Hair Corrective")
                ]
        return set(), modifiers


class MustardUI_ToolsCreators_RemoveCollisionCage(RemovePhysicsBase, bpy.types.Operator):
    """Remove the Collision Cages selected, or created from the selected meshes, and their
    Physics Items"""

    bl_idname = "mustardui.tools_creators_remove_collision_cage"
    bl_label = "Remove Collision Cage"
    tool_name = "Collision Cage"
    detector = staticmethod(is_collision_cage)

    @staticmethod
    def from_sources(context):
        selected = {x.name for x in context.selected_objects}
        return {
            obj
            for obj in bpy.data.objects
            if is_collision_cage(obj)
            and any(obj.name.endswith(f"{name} Collision Cage") for name in selected)
        }

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=ModelMode.MODEL_TOOLKIT)
        if not res or context.mode != "OBJECT":
            return False
        return bool(cages_from_selection(context, is_collision_cage) or cls.from_sources(context))

    def collect(self, context, cages):
        return self.from_sources(context), []


class MustardUI_ToolsCreators_RemoveAccessoryPhysics(RemovePhysicsBase, bpy.types.Operator):
    """Remove the Accessory Physics of the selected accessories (or of the selected
    proxies): the proxy, the rigid parts, the generated collision mesh, the modifiers and
    the Physics Items"""

    bl_idname = "mustardui.tools_creators_remove_accessory_physics"
    bl_label = "Remove Accessory Physics"
    tool_name = "Accessory Physics"
    detector = staticmethod(is_accessory)

    def collect(self, context, cages):
        # From the rigid parts and the collision mesh, back to the proxy
        proxies = set()
        for obj in cages:
            if any(m.type == "CLOTH" for m in obj.modifiers):
                proxies.add(obj)
            for collection in obj.users_collection:
                proxies.update(x for x in collection.objects if is_accessory_proxy(x))

        others = set(proxies)
        modifiers = []
        for proxy in proxies:
            others.update(x for x in bpy.data.objects if x.name.startswith(f"{proxy.name} Rigid"))
            # The generated collision mesh
            for collection in proxy.users_collection:
                others.update(
                    x for x in collection.objects if any(m.type == "COLLISION" for m in x.modifiers)
                )
            # The Armature modifier added to accessories without one
            for obj in bpy.data.objects:
                if any(t == proxy for t, _ in deform_targets(obj)):
                    added = [m for m in obj.modifiers if m.name == "Accessory Physics Armature"]
                    modifiers += [(obj, m.name) for m in added]
                    self.unrigged += [(obj, m.object) for m in added]
        # Keep the collision meshes other accessories still collide with (all of them
        # when no Collision collection is set)
        removed = cages | others
        for obj in [x for x in bpy.data.objects if x not in removed and is_accessory_proxy(x)]:
            for modifier in [m for m in obj.modifiers if m.type == "CLOTH"]:
                settings = modifier.collision_settings
                if not settings.use_collision:
                    continue
                others -= {
                    x
                    for x in others
                    if any(m.type == "COLLISION" for m in x.modifiers)
                    and (settings.collection is None or x.name in settings.collection.all_objects)
                }
        return others - cages, modifiers

    def own_collections(self, objects):
        return {
            c
            for obj in objects
            if is_accessory_proxy(obj)
            for c in obj.users_collection
            if c.name.endswith(" Physics")
        }

    def execute(self, context):
        self.unrigged = []
        return super().execute(context)

    def after(self, context):
        # The weights transferred with the Armature modifier the tool added
        for obj, armature in self.unrigged:
            if armature is None or any(m.type == "ARMATURE" for m in obj.modifiers):
                continue
            for group in list(obj.vertex_groups):
                bone = armature.data.bones.get(group.name)
                if bone is not None and bone.use_deform:
                    obj.vertex_groups.remove(group)

        node_group = bpy.data.node_groups.get("MustardUI Accessory Rigid Patch")
        if node_group is not None and node_group.users == 0:
            bpy.data.node_groups.remove(node_group)


classes = (
    MustardUI_ToolsCreators_RemoveJiggle,
    MustardUI_ToolsCreators_RemoveJiggleAccurate,
    MustardUI_ToolsCreators_RemoveHairCage,
    MustardUI_ToolsCreators_RemoveCollisionCage,
    MustardUI_ToolsCreators_RemoveAccessoryPhysics,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
