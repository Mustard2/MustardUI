import bpy

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
        default=True,
        name="Automatically Mute null Shape Keys",
        description="Add a driver on the Mute property of the Shape Keys, which are "
        "automatically disabled when their value is 0.\nNote: Freezable option for "
        "custom sections will be disabled as incompatible with drivers on the Mute "
        "properties",
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
        kb = sks.key_blocks

        # Skip Shape Keys already managed by Morphs
        if obj == rig_settings.model_body:
            morph_shape_keys = set()
            for section in sections:
                if not section.shape_keys:
                    continue
                for morph in section.morphs:
                    if not morph.custom_property:
                        morph_shape_keys.add(morph.path)
            kb = [x for x in kb if x.name not in morph_shape_keys]

        if not self.add_shape_key_mute_driver:
            self.report(
                {"WARNING"},
                "MustardUI - No Option Selected.",
            )
            return {"CANCELLED"}

        if not self.revert:
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
        else:
            for sk in kb:
                try:
                    driver_path = f'key_blocks["{sk.name}"].mute'
                    if sks.animation_data:
                        fcurve = sks.animation_data.drivers.find(driver_path)
                        if fcurve:
                            drv = fcurve.driver
                            if (
                                drv.type == "SCRIPTED"
                                and drv.expression == "abs(var) < 0.001"
                            ):
                                sks.driver_remove(driver_path)

                    # Unmute if muted
                    sks.key_blocks[sk.name].mute = False
                except Exception:
                    pass

        self.report(
            {"INFO"},
            "MustardUI - Shape Key drivers removed."
            if self.revert
            else "MustardUI - Shape Keys Optimized.",
        )

        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=250)

    def draw(self, context):

        layout = self.layout

        col = layout.column(align=True)

        if not self.revert:
            col.prop(self, "add_shape_key_mute_driver")
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
