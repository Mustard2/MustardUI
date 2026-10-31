from contextlib import contextmanager

import bpy

from ..misc.mesh_intersection import MeshIntersectionChecker
from ..misc.move_modifier import move_modifier
from ..misc.scene_state import execute_restoring_state
from ..misc.surface_deform import surface_deform_bind
from ..model_selection.active_object import (
    ModelMode,
    active_object_operator_poll,
    mustardui_active_object,
)
from ..outfits.helper_functions import find_layer_collection, outfits_get_collection_items
from ..text_storage.storage import evaluated
from .update_enable import enable_physics_update


def include_collection(coll):
    """Include the collection in the view layer, returning how to restore it"""
    lc = find_layer_collection(bpy.context.view_layer.layer_collection, coll)
    if lc is None:
        return None, False
    was_excluded = lc.exclude
    if was_excluded:
        lc.exclude = False
        bpy.context.view_layer.update()
    return lc, was_excluded


def restore_collection(lc, was_excluded):
    """Restore the 'exclude' flag saved by include_collection()."""
    if lc is not None and was_excluded:
        lc.exclude = True


@contextmanager
def included_collection(coll):
    """Include the collection in the view layer while in the context"""
    state = include_collection(coll)
    try:
        yield
    finally:
        restore_collection(*state)


class MustardUI_Physics_OutfitsSetup(bpy.types.Operator):
    """This button creates Surface Deform modifiers on Outfit pieces affected by Cages physics items.\nThe modifier is added only if the Outfit piece and the Cage intersect.\nBlender might freeze during the process"""  # noqa: E501

    bl_idname = "mustardui.physics_outfits_setup"
    bl_label = "Setup Outfits Physics"
    bl_options = {"UNDO"}

    override_armature_check: bpy.props.BoolProperty(
        default=False,
        name="Override Armature Check",
        description="Enable this to add Surface Deform modifiers even if the Armature "
        "modifier is not available on the Object",
    )
    override_physics_check: bpy.props.BoolProperty(
        default=False,
        name="Override Physics Check",
        description="Enable this to add Surface Deform modifiers even if Physics "
        "modifiers are found on the Object",
    )
    clean_modifiers: bpy.props.BoolProperty(
        default=False,
        name="Clean Modifiers",
        description="Remove modifiers for mesh not affected by Physics cages",
    )

    single_outfit: bpy.props.StringProperty(default="")

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=ModelMode.CONFIG)
        if arm is None:
            return False

        physics_settings = arm.MustardUI_PhysicsSettings
        return (
            res
            and physics_settings.enable_ui
            and [x for x in physics_settings.items if x.type == "CAGE"]
        )

    def execute(self, context):
        return execute_restoring_state(self, context)

    def _execute(self, context):

        res, arm = mustardui_active_object(context, config=ModelMode.CONFIG)
        rig_settings = arm.MustardUI_RigSettings
        physics_settings = arm.MustardUI_PhysicsSettings

        body = rig_settings.model_body
        enable_physics = physics_settings.enable_physics
        warnings = 0

        # Go to frame 0
        context.scene.frame_current = 0

        try:
            # Disable Physics
            physics_settings.enable_physics = False

            items = physics_settings.items

            # Surface Deform target: a custom mesh if one was selected in the popup,
            # otherwise the body itself. This only changes what the Surface Deform
            # modifiers bind to; intersection checks still use the body cages.
            target = physics_settings.outfits_setup_surface_deform_target
            if target is None or target.type != "MESH":
                target = body

            # Disabling Physics may have excluded the cage collections: re-include them
            # for binding (the final exclude state is restored with enable_physics below).
            physics_objs = [x.object for x in items if x.object is not None]
            physics_objs.append(target)
            for pcoll in {c for o in physics_objs for c in o.users_collection}:
                include_collection(pcoll)

            # Update everything
            body.data.update_tag()
            body.data.update()
            body.update_tag()
            bpy.context.view_layer.update()

            arm.pose_position = "REST"

            if self.single_outfit != "":
                colls = [
                    x.collection
                    for x in rig_settings.outfits_collections
                    if x.collection is not None and x.collection.name == self.single_outfit
                ]
                if (
                    rig_settings.extras_collection is not None
                    and rig_settings.extras_collection.name == self.single_outfit
                ):
                    colls.append(rig_settings.extras_collection)
            else:
                colls = [
                    x.collection
                    for x in rig_settings.outfits_collections
                    if x.collection is not None
                ]
                if rig_settings.extras_collection is not None:
                    colls.append(rig_settings.extras_collection)

                # Clear current intersection objects
                for pi in [x for x in items if x.type == "CAGE"]:
                    pi.intersecting_objects.clear()

            # Caches BVH trees/bounding boxes so each cage and object mesh is only
            # built once across all intersection checks below.
            intersection_checker = MeshIntersectionChecker()

            for coll in colls:
                with included_collection(coll), evaluated([coll]):
                    objs = outfits_get_collection_items(rig_settings, coll)
                    for obj in [x for x in objs if x.type == "MESH" and x.modifiers is not None]:
                        # Check if the Armature modifier is available on the Object
                        # This should be an indication of the fact that the Object should be
                        # driven by the body with Surface Deform modifiers
                        if not self.override_armature_check:
                            if (
                                len(
                                    [
                                        x
                                        for x in obj.modifiers
                                        if x.type == "ARMATURE"
                                        and x.object == rig_settings.model_armature_object
                                    ]
                                )
                                == 0
                            ):
                                continue

                        # Check if Physics modifiers are available on the mesh
                        # If these modifiers are available, most probably the item does not
                        # need to be driven by Surface Deform
                        if not self.override_physics_check:
                            if any(
                                x.type in ["CLOTH", "SOFT_BODY", "NODES"] for x in obj.modifiers
                            ):
                                continue

                        pi_found = False

                        for pi in [x for x in items if x.type == "CAGE"]:
                            if intersection_checker.intersect(pi.object, obj):
                                # Add the object to the intersecting objects of the physics
                                # item, avoiding duplicates (the single_outfit path does not
                                # clear intersecting_objects beforehand)
                                if obj not in [x.object for x in pi.intersecting_objects]:
                                    npi = pi.intersecting_objects.add()
                                    npi.object = obj

                                if pi_found:
                                    continue
                                pi_found = True

                                # If the modifier is already added, attempt to rebind if
                                # needed and skip
                                if any(
                                    x.type == "SURFACE_DEFORM" and x.target == target
                                    for x in obj.modifiers
                                ):
                                    for mod in [
                                        x
                                        for x in obj.modifiers
                                        if x.type == "SURFACE_DEFORM" and x.target == target
                                    ]:
                                        # Attempt to rebind if found but not bound
                                        if not mod.is_bound:
                                            mod.show_viewport = True
                                            obj.update_tag()

                                            surface_deform_bind(obj, mod)

                                            mod.show_viewport = False
                                            obj.update_tag()
                                        break
                                    continue

                                # Add Surface Deform modifier after the Armature one, before
                                # binding it to the piece without its subdivision
                                nm = obj.modifiers.new(name=target.name, type="SURFACE_DEFORM")
                                nm.target = target
                                last_armature_index = max(
                                    (
                                        i
                                        for i, m in enumerate(obj.modifiers)
                                        if m.type == "ARMATURE"
                                    ),
                                    default=-1,
                                )
                                if obj.modifiers.find(nm.name) > last_armature_index + 1:
                                    move_modifier(obj, nm, last_armature_index + 1)
                                surface_deform_bind(obj, nm)

                                nm.show_viewport = True
                                nm.show_render = True

                                obj.update_tag()

                        # If there is no intersection, the modifier is not needed
                        if not pi_found and self.clean_modifiers:
                            mods = [
                                x
                                for x in obj.modifiers
                                if x.type == "SURFACE_DEFORM" and x.target == target
                            ]
                            mods.reverse()
                            for mod in mods:
                                obj.modifiers.remove(mod)

                        obj.update_tag()

        finally:
            # Force Physics recheck
            enable_physics_update(physics_settings, context)
            physics_settings.enable_physics = enable_physics

        # Last check on binding to raise warnings
        for coll in colls:
            objs = outfits_get_collection_items(rig_settings, coll)
            for obj in [x for x in objs if x.type == "MESH" and x.modifiers is not None]:
                for mod in [
                    x for x in obj.modifiers if x.type == "SURFACE_DEFORM" and x.target == target
                ]:
                    if not mod.is_bound:
                        print(
                            f"MustardUI Physics Setup - Could not bind Surface Deform "
                            f"on {repr(obj.name)}"
                        )
                        warnings += 1

        if warnings == 0:
            self.report({"INFO"}, "MustardUI - Physics Setup complete.")
        else:
            self.report(
                {"WARNING"},
                f"MustardUI - {str(warnings)} warnings have been generated during "
                f"setup. Check the Console log.",
            )

        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):

        layout = self.layout

        settings = context.scene.MustardUI_Settings
        res, arm = mustardui_active_object(context, config=ModelMode.CONFIG)
        physics_settings = arm.MustardUI_PhysicsSettings

        col = layout.column(align=True)
        col.prop(self, "override_armature_check")
        col.prop(self, "override_physics_check")

        col = layout.column(align=True)
        col.prop(self, "clean_modifiers")

        # Advanced: optional custom Surface Deform target
        if settings.advanced:
            col = layout.column(align=True)
            col.prop(
                physics_settings,
                "outfits_setup_surface_deform_target",
                icon="MESH_DATA",
            )


class MustardUI_Physics_OutfitsSetup_IntersectingObjects(bpy.types.Operator):
    """Compute Outfits Intersecting with Physics Items.\nBlender might freeze for a while, depending on the complexity of the Outfits mesh"""  # noqa: E501

    bl_idname = "mustardui.physics_outfits_setup_intersecting_objects"
    bl_label = "Compute Intersecting Outfits"
    bl_options = {"UNDO"}

    override_armature_check: bpy.props.BoolProperty(
        default=False,
        name="Override Armature Check",
        description="Enable this to add Surface Deform modifiers even if the Armature "
        "modifier is not available on the Object",
    )
    override_physics_check: bpy.props.BoolProperty(
        default=False,
        name="Override Physics Check",
        description="Enable this to add Surface Deform modifiers even if Physics "
        "modifiers are found on the Object",
    )
    unique: bpy.props.BoolProperty(default=False)

    @classmethod
    def poll(cls, context):
        if not active_object_operator_poll(context, config=ModelMode.CONFIG):
            return False

        res, arm = mustardui_active_object(context, config=ModelMode.CONFIG)
        physics_settings = arm.MustardUI_PhysicsSettings
        for pi in physics_settings.items:
            if len(pi.intersecting_objects) > 0:
                return physics_settings.enable_ui and [
                    x for x in physics_settings.items if x.type == "CAGE"
                ]
        return False

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=ModelMode.CONFIG)
        rig_settings = arm.MustardUI_RigSettings
        physics_settings = arm.MustardUI_PhysicsSettings

        items = physics_settings.items

        if self.unique:
            if not 0 <= arm.mustardui_physics_items_uilist_index < len(items):
                return {"FINISHED"}
            if physics_settings.items[arm.mustardui_physics_items_uilist_index].object is None:
                return {"FINISHED"}

        # Clear current intersection objects, keeping the Surface Deform modifiers as they are
        if self.unique:
            pi = physics_settings.items[arm.mustardui_physics_items_uilist_index]
            pi.intersecting_objects.clear()
        else:
            for pi in [x for x in items if x.type == "CAGE"]:
                pi.intersecting_objects.clear()

        colls = [x.collection for x in rig_settings.outfits_collections if x.collection is not None]
        if rig_settings.extras_collection is not None:
            colls.append(rig_settings.extras_collection)

        # Physics may be disabled, excluding the cage collections: re-include them for
        # the intersection checks, then restore their exclude state at the end.
        cage_objs = [x.object for x in items if x.type == "CAGE" and x.object]
        cage_colls = {coll for o in cage_objs for coll in o.users_collection}
        cage_states = [include_collection(coll) for coll in cage_colls]

        # Caches BVH trees/bounding boxes so each cage and object mesh is only
        # built once across all intersection checks below.
        intersection_checker = MeshIntersectionChecker()

        for coll in colls:
            with included_collection(coll), evaluated([coll]):
                objs = outfits_get_collection_items(rig_settings, coll)
                for obj in [x for x in objs if x.type == "MESH" and x.modifiers is not None]:
                    # Check if the Armature modifier is available on the Object
                    # This should be an indication of the fact that the Object should be
                    # driven by the body with Surface Deform modifiers
                    if not self.override_armature_check:
                        if (
                            len(
                                [
                                    x
                                    for x in obj.modifiers
                                    if x.type == "ARMATURE"
                                    and x.object == rig_settings.model_armature_object
                                ]
                            )
                            == 0
                        ):
                            continue

                    # Check if Physics modifiers are available on the mesh
                    # If these modifiers are available, most probably the item does not
                    # need to be driven by Surface Deform
                    if not self.override_physics_check:
                        if any(x.type in ["CLOTH", "SOFT_BODY", "NODES"] for x in obj.modifiers):
                            continue

                    if self.unique:
                        pi = physics_settings.items[arm.mustardui_physics_items_uilist_index]
                        if intersection_checker.intersect(pi.object, obj):
                            # Add the object to the intersecting objects of the physics item
                            npi = pi.intersecting_objects.add()
                            npi.object = obj
                    else:
                        for pi in [x for x in items if x.type == "CAGE"]:
                            if intersection_checker.intersect(pi.object, obj):
                                # Add the object to the intersecting objects of the
                                # physics item
                                npi = pi.intersecting_objects.add()
                                npi.object = obj

        for cage_lc, cage_was_excluded in cage_states:
            restore_collection(cage_lc, cage_was_excluded)

        self.report({"INFO"}, "MustardUI - Recomputed Physics Outfits settings.")

        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=450)

    def draw(self, context):

        layout = self.layout

        col = layout.column(align=True)
        col.prop(self, "override_armature_check")
        col.prop(self, "override_physics_check")


class MustardUI_Physics_OutfitsSetup_Clear(bpy.types.Operator):
    """Clear the data driving the enable/disable of surface deform modifiers when Physics is activated/disabled"""  # noqa: E501

    bl_idname = "mustardui.physics_outfits_setup_clear"
    bl_label = "Clear Setup Outfits Physics"
    bl_options = {"UNDO"}

    clean_modifiers: bpy.props.BoolProperty(
        default=False,
        name="Clean Modifiers",
        description="Remove Surface Deform modifiers",
    )

    @classmethod
    def poll(cls, context):
        if not active_object_operator_poll(context, config=ModelMode.CONFIG):
            return False

        res, arm = mustardui_active_object(context, config=ModelMode.CONFIG)
        physics_settings = arm.MustardUI_PhysicsSettings
        return physics_settings.enable_ui and [
            x for x in physics_settings.items if x.type == "CAGE"
        ]

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=ModelMode.CONFIG)
        rig_settings = arm.MustardUI_RigSettings
        physics_settings = arm.MustardUI_PhysicsSettings

        body = rig_settings.model_body
        items = physics_settings.items

        # Surface Deform modifiers may target the body or a custom target chosen
        # during setup, so clear both.
        targets = {body}
        custom_target = physics_settings.outfits_setup_surface_deform_target
        if custom_target is not None and custom_target.type == "MESH":
            targets.add(custom_target)

        # Clear current intersection objects
        for pi in [x for x in items if x.type == "CAGE"]:
            pi.intersecting_objects.clear()

        # Disable or remove all Surface Deform modifiers
        colls = [x.collection for x in rig_settings.outfits_collections if x.collection is not None]
        if rig_settings.extras_collection is not None:
            colls.append(rig_settings.extras_collection)

        for coll in colls:
            objs = outfits_get_collection_items(rig_settings, coll)
            for obj in [x for x in objs if x.type == "MESH" and x.modifiers is not None]:
                mods = [
                    x for x in obj.modifiers if x.type == "SURFACE_DEFORM" and x.target in targets
                ]
                mods.reverse()
                for mod in mods:
                    if self.clean_modifiers:
                        obj.modifiers.remove(mod)
                    else:
                        mod.show_viewport = False
                        mod.show_render = False

        self.report({"INFO"}, "MustardUI - Cleared Physics Setup settings.")

        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=450)

    def draw(self, context):

        layout = self.layout

        col = layout.column(align=True)
        col.prop(self, "clean_modifiers")


def register():
    bpy.utils.register_class(MustardUI_Physics_OutfitsSetup)
    bpy.utils.register_class(MustardUI_Physics_OutfitsSetup_IntersectingObjects)
    bpy.utils.register_class(MustardUI_Physics_OutfitsSetup_Clear)


def unregister():
    bpy.utils.unregister_class(MustardUI_Physics_OutfitsSetup_Clear)
    bpy.utils.unregister_class(MustardUI_Physics_OutfitsSetup_IntersectingObjects)
    bpy.utils.unregister_class(MustardUI_Physics_OutfitsSetup)
