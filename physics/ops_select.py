import bpy

from ..model_selection.active_object import (
    active_object_operator_poll,
    mustardui_active_object,
)


class MustardUI_PhysicsSelectItem(bpy.types.Operator):
    """Select the object of this Physics Item in the viewport"""

    bl_idname = "mustardui.physics_select"
    bl_label = "Select Physics Item"
    bl_options = {"UNDO"}

    object_name: bpy.props.StringProperty(options={"HIDDEN"})
    item_index: bpy.props.IntProperty(default=-1, options={"HIDDEN"})

    @classmethod
    def poll(cls, context):
        return active_object_operator_poll(context, config=0)

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=0)

        if arm is not None:
            physics_settings = arm.MustardUI_PhysicsSettings
            if 0 <= self.item_index < len(physics_settings.items):
                arm.mustardui_physics_items_uilist_index = self.item_index

        obj = bpy.data.objects.get(self.object_name)

        if obj is None:
            self.report({"WARNING"}, "MustardUI - Physics Item object not found.")
            return {"CANCELLED"}

        try:
            for o in context.selected_objects:
                o.select_set(False)
            obj.select_set(True)
            context.view_layer.objects.active = obj
        except (RuntimeError, ReferenceError) as e:
            print(f"MustardUI - Physics Item selection error: {e}")
            self.report({"WARNING"}, f"MustardUI - {obj.name} can not be selected.")
            return {"CANCELLED"}

        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_PhysicsSelectItem)


def unregister():
    bpy.utils.unregister_class(MustardUI_PhysicsSelectItem)
