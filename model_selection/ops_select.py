import bpy


class MUSTARDUI_OT_SelectModel(bpy.types.Operator):
    """Select a model, respecting viewport model selection mode"""

    bl_idname = "mustardui.select_model"
    bl_label = "Select Model"
    bl_description = "Switch to the selected model (respects Viewport Model Selection setting)"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    # Property passed from the button
    model_to_select: bpy.props.StringProperty(
        name="Model to Select",
        description="Name of the armature to switch to",
        default="",
    )

    def execute(self, context):
        if not self.model_to_select:
            self.report({"WARNING"}, "MustardUI - No model specified")
            return {"CANCELLED"}

        settings = context.scene.MustardUI_Settings

        # Find the target armature
        target_arm = None
        for arm in bpy.data.armatures:
            if arm.name == self.model_to_select and arm.MustardUI_created:
                target_arm = arm
                break

        if not target_arm:
            self.report({"WARNING"}, f"MustardUI - Could not find model: {self.model_to_select}")
            return {"CANCELLED"}

        # === Viewport Model Selection Mode ===
        if settings.viewport_model_selection:
            rig_settings = target_arm.MustardUI_RigSettings
            # In viewport mode we just make the armature's object active/selected
            if (
                rig_settings.model_armature_object
                and rig_settings.model_armature_object.name in context.scene.objects
            ):
                obj = rig_settings.model_armature_object
                # Deselect all
                for o in context.selected_objects:
                    o.select_set(False)
                # Select and make active
                obj.select_set(True)
                context.view_layer.objects.active = obj
            else:
                self.report({"WARNING"}, "MustardUI - Target armature object not found in scene")
                return {"CANCELLED"}

        # === Direct Panel Mode ===
        else:
            # Check if you are trying to switch to the same model already in use
            if bpy.data.armatures[self.model_to_select] == settings.panel_model_selection_armature:
                self.report(
                    {"WARNING"},
                    "MustardUI - Already using "
                    + bpy.data.armatures[self.model_to_select].MustardUI_RigSettings.model_name
                    + " model.",
                )
                return {"CANCELLED"}

            settings.panel_model_selection_armature = target_arm
            self.report(
                {"INFO"},
                f"MustardUI - Model switched to: {target_arm.MustardUI_RigSettings.model_name}",
            )

        return {"FINISHED"}


def register():
    bpy.utils.register_class(MUSTARDUI_OT_SelectModel)


def unregister():
    bpy.utils.unregister_class(MUSTARDUI_OT_SelectModel)
