import bpy

from ...misc import mesh_cleanup
from ...model_selection.active_object import (
    ModelMode,
    active_object_operator_poll,
    mustardui_active_object,
)


class MustardUI_ModelToolkit_OptimizeShapeKeys(bpy.types.Operator):
    """Tools to optimize the Shape Keys on the Active Object"""

    bl_idname = "mustardui.model_toolkit_optimize_shape_keys"
    bl_label = "Optimize Shape Keys"
    bl_options = {"REGISTER", "UNDO"}

    remove_void_shape_keys: bpy.props.BoolProperty(
        default=True,
        name="Remove Void Shape Keys",
        description="Remove the Shape Keys which do not move a single vertex.\nThese "
        "are copies of the shape they are relative to: they deform nothing, while "
        "they take up as much space in the file as any other Shape Key.\nNote: the "
        "Shape Keys used by the Morphs of the UI are never removed",
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None
            and obj.type == "MESH"
            and obj.data is not None
            and obj.data.shape_keys is not None
            and active_object_operator_poll(context, config=ModelMode.MODEL_TOOLKIT)
        )

    def execute(self, context):
        res, arm = mustardui_active_object(context, config=ModelMode.MODEL_TOOLKIT)
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

        if not self.remove_void_shape_keys:
            self.report({"WARNING"}, "MustardUI - No Option Selected.")
            return {"CANCELLED"}

        removed = 0
        for sk in [x for x in sks.key_blocks if x.name not in morph_shape_keys]:
            if not mesh_cleanup.shape_key_is_void(sk):
                continue
            mesh_cleanup.remove_shape_key(obj, sk)
            removed += 1

        self.report({"INFO"}, f"MustardUI - {removed} void Shape Keys removed.")

        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=250)

    def draw(self, context):
        self.layout.prop(self, "remove_void_shape_keys")


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_OptimizeShapeKeys)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_OptimizeShapeKeys)
