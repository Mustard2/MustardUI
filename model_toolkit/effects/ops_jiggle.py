import bpy

from ...physics.definitions_nodes import JIGGLE_DYNAMICS_NODE_GROUP, jiggle_dynamics_node_group
from .effect import RemoveEffect, add_effect_modifier, effects_available, modifier_input

NODE_GROUP = JIGGLE_DYNAMICS_NODE_GROUP
# Rings over which a Zone made out of the selected vertices fades into the rest of the mesh
EDGE_FADE = 4


class MustardUI_ModelToolkit_JiggleEffect(bpy.types.Operator):
    """Make the selected meshes jiggle with their motion, settling back to the animated shape: the vertices selected in Edit Mode, or the whole meshes in Object Mode.\nBlender 5.2 or above is required"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_jiggle_effect"
    bl_label = "Add Jiggle"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        return effects_available() and any(x.type == "MESH" for x in context.selected_objects)

    def execute(self, context):
        objects = [x for x in context.selected_objects if x.type == "MESH"]

        # The selection is written to the meshes in Object Mode
        edit = context.mode == "EDIT_MESH"
        if edit:
            bpy.ops.object.mode_set(mode="OBJECT")

        jiggle_dynamics_node_group()
        for obj in objects:
            modifier = add_effect_modifier(obj, "Jiggle", NODE_GROUP)
            zone = modifier_input(modifier, "Zone")
            selected = [v.index for v in obj.data.vertices if v.select] if edit else []
            if selected:
                group = obj.vertex_groups.new(name="Jiggle")
                group.add(selected, 1.0, "REPLACE")
                zone.type = "ATTRIBUTE"
                zone.attribute_name = group.name
                modifier_input(modifier, "Edge Fade").value = EDGE_FADE
            else:
                zone.value = 1.0

        if edit:
            bpy.ops.object.mode_set(mode="EDIT")

        self.report({"INFO"}, f"MustardUI - Jiggle added to {len(objects)} objects.")
        return {"FINISHED"}


class MustardUI_ModelToolkit_RemoveJiggleEffect(RemoveEffect, bpy.types.Operator):
    """Remove the Jiggle from the selected meshes"""

    bl_idname = "mustardui.model_toolkit_remove_jiggle_effect"
    bl_label = "Remove Jiggle"

    effect = "Jiggle"
    node_group = NODE_GROUP
    controls = False


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_JiggleEffect)
    bpy.utils.register_class(MustardUI_ModelToolkit_RemoveJiggleEffect)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_RemoveJiggleEffect)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_JiggleEffect)
