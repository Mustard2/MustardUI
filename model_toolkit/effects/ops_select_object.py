import bpy


class MustardUI_ModelToolkit_SelectObject(bpy.types.Operator):
    """Select the object, making it the active one"""

    bl_idname = "mustardui.model_toolkit_select_object"
    bl_label = "Select Object"
    bl_options = {"UNDO"}

    name: bpy.props.StringProperty(options={"HIDDEN"})

    def execute(self, context):
        obj = context.scene.objects.get(self.name)
        try:
            obj.select_set(True)
        except (AttributeError, RuntimeError):
            self.report({"WARNING"}, f"MustardUI - {self.name} can not be selected.")
            return {"CANCELLED"}
        for x in context.selected_objects:
            if x != obj:
                x.select_set(False)
        context.view_layer.objects.active = obj
        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_SelectObject)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_SelectObject)
