import bpy

from .. import __package__ as base_package
from ..model_selection.active_object import (
    active_object_operator_poll,
    mustardui_active_object,
)


def rename_object(obj):
    if obj.data is None:
        return

    obj.data.name = obj.name

    if obj.type != "MESH":
        return

    if obj.data.shape_keys is not None:
        obj.data.shape_keys.name = obj.name


class MustardUI_ToolsCreators_Naming(bpy.types.Operator):
    """Enforce naming based on the model name and its objects."""  # noqa: E501

    bl_idname = "mustardui.tool_naming"
    bl_label = "Rename Model"
    bl_options = {"UNDO"}

    attempt_fix_paths: bpy.props.BoolProperty(
        name="Attempt to Fix Paths",
        default=True,
        description="Attempt to fix the paths of custom properties"
        " that can not be rebuilt because their path can not be found. "
        "This will try to find the new path of the property if it "
        "was moved to another object or if it was renamed.",
    )

    @classmethod
    def poll(cls, context):
        return active_object_operator_poll(context, config=1)

    def execute(self, context):

        if self.name == "":
            self.report(
                {"WARNING"},
                "MustardUI - Renaming not performed: the name should be not null",
            )
            return {"FINISHED"}

        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings
        physics_settings = arm.MustardUI_PhysicsSettings

        # First call to ensure that the pointers are correctly set
        if self.attempt_fix_paths:
            bpy.ops.mustardui.property_fix_path(
                remove_invalid_properties=False, assign_pointers=True
            )

        # Body and children of the armature
        for obj in [
            x
            for x in rig_settings.model_armature_object.children
            if x is not None and x.data is not None
        ]:
            rename_object(obj)

        # Physics items
        for pi in [
            x
            for x in physics_settings.items
            if x.object is not None and x.object.data is not None
        ]:
            rename_object(pi.object)

        # Outfits
        for coll in [
            x.collection
            for x in rig_settings.outfits_collections
            if x.collection is not None
        ]:
            items = coll.all_objects
            for obj in [x for x in items if x is not None and x.data is not None]:
                rename_object(obj)

        # Extras
        if rig_settings.extras_collection is not None:
            for obj in [
                x
                for x in rig_settings.extras_collection.all_objects
                if x is not None and x.data is not None
            ]:
                rename_object(obj)

        # Hair
        if rig_settings.hair_collection is not None:
            for obj in [
                x
                for x in rig_settings.hair_collection.all_objects
                if x is not None and x.data is not None
            ]:
                rename_object(obj)

        bpy.context.view_layer.update()

        # Second call to ensure the paths are fixed
        if self.attempt_fix_paths:
            bpy.ops.mustardui.property_fix_path(
                remove_invalid_properties=False, assign_pointers=False
            )

        self.report(
            {"INFO"},
            "MustardUI - Objects renamed",
        )

        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=450)

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        col = box.column(align=True)
        col.label(
            text="This tool renames Objects data and Shape Keys.",
            icon="INFO",
        )

        box = layout.box()
        col = box.column(align=True)
        col.prop(self, "attempt_fix_paths")


def register():
    bpy.utils.register_class(MustardUI_ToolsCreators_Naming)


def unregister():
    bpy.utils.unregister_class(MustardUI_ToolsCreators_Naming)
