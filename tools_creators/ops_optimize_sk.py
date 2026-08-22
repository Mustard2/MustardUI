import bpy

from ..misc import mesh_cleanup
from ..model_selection.active_object import (
    active_object_operator_poll,
    mustardui_active_object,
)


class MustardUI_ToolsCreators_OptimizeShapeKeys(bpy.types.Operator):
    """Tools to optimize the Shape Keys on the Active Object"""

    bl_idname = "mustardui.tools_creators_optimize_shape_keys"
    bl_label = "Optimize Shape Keys"
    bl_options = {"REGISTER", "UNDO"}

    add_shape_key_mute_driver: bpy.props.BoolProperty(
        default=False,
        name="Automatically Mute null Shape Keys",
        description="Add a driver on the Mute property of the Shape Keys, which are "
        "automatically disabled when their value is 0.\nNote: Freezable option for "
        "custom sections will be disabled as incompatible with drivers on the Mute "
        "properties.\nWarning: This option might affect performance, check before and "
        "after using this tool.",
    )

    remove_void_shape_keys: bpy.props.BoolProperty(
        default=True,
        name="Remove Void Shape Keys",
        description="Remove the Shape Keys which do not move a single vertex.\nThese "
        "are copies of the shape they are relative to: they deform nothing, while "
        "they take up as much space in the file as any other Shape Key.\nNote: the "
        "Shape Keys used by the Morphs of the UI are never removed",
    )

    revert: bpy.props.BoolProperty(default=False)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None
            and obj.type == "MESH"
            and obj.data is not None
            and obj.data.shape_keys is not None
            and active_object_operator_poll(context, config=1)
        )

    def execute(self, context):
        res, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings
        morphs_settings = arm.MustardUI_MorphsSettings

        sections = morphs_settings.sections

        obj = context.active_object

        sks = obj.data.shape_keys

        # Skip Shape Keys already managed by Morphs
        morph_shape_keys = set()
        if obj == rig_settings.model_body:
            for section in sections:
                if not section.shape_keys:
                    continue
                for morph in section.morphs:
                    if not morph.custom_property:
                        morph_shape_keys.add(morph.path)

        def managed_key_blocks():
            return [x for x in sks.key_blocks if x.name not in morph_shape_keys]

        # Removing a Shape Key can not be reverted by the tool
        remove_void = self.remove_void_shape_keys and not self.revert

        if not self.add_shape_key_mute_driver and not remove_void:
            self.report(
                {"WARNING"},
                "MustardUI - No Option Selected.",
            )
            return {"CANCELLED"}

        removed = 0
        if remove_void:
            for sk in managed_key_blocks():
                if not mesh_cleanup.shape_key_is_void(sk):
                    continue
                mesh_cleanup.remove_shape_key(obj, sk)
                removed += 1

        kb = managed_key_blocks()

        if self.add_shape_key_mute_driver and not self.revert:
            for sk in kb:
                # Skip Basis
                if sk == sks.reference_key:
                    continue

                # Remove existing driver if present
                try:
                    sk.driver_remove("mute")
                except Exception:
                    pass

                fcurve = sk.driver_add("mute")
                driver = fcurve.driver

                driver.type = "SCRIPTED"

                var = driver.variables.new()
                var.name = "var"

                target = var.targets[0]
                target.id_type = "KEY"
                target.id = sks
                target.data_path = f'key_blocks["{sk.name}"].value'

                driver.expression = "abs(var) < 0.001"

        # Otherwise remove the mute driver
        elif self.add_shape_key_mute_driver:
            for sk in kb:
                try:
                    driver_path = f'key_blocks["{sk.name}"].mute'
                    if sks.animation_data:
                        fcurve = sks.animation_data.drivers.find(driver_path)
                        if fcurve:
                            drv = fcurve.driver
                            if drv.type == "SCRIPTED" and drv.expression == "abs(var) < 0.001":
                                sks.driver_remove(driver_path)

                    # Unmute if muted
                    sks.key_blocks[sk.name].mute = False
                except Exception:
                    pass

        if self.revert:
            message = "MustardUI - Shape Key drivers removed."
        else:
            message = (
                "MustardUI - Shape Keys Optimized."
                if self.add_shape_key_mute_driver
                else "MustardUI - Shape Keys checked."
            )
        if remove_void:
            message += f" {removed} void Shape Keys removed."

        self.report({"INFO"}, message)

        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=250)

    def draw(self, context):

        layout = self.layout

        col = layout.column(align=True)

        if not self.revert:
            col.prop(self, "add_shape_key_mute_driver")
            col.prop(self, "remove_void_shape_keys")
        else:
            col.prop(
                self,
                "add_shape_key_mute_driver",
                text="Remove Drivers from Shape Key's Mute",
            )


def register():
    bpy.utils.register_class(MustardUI_ToolsCreators_OptimizeShapeKeys)


def unregister():
    bpy.utils.unregister_class(MustardUI_ToolsCreators_OptimizeShapeKeys)
