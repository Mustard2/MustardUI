import os

import bpy
from mathutils import Vector

from .effect import effects_available, is_effect, modifier_input

NODE_GROUP = "MustardUI Sticky Spurts"
MATERIAL = "MustardUI Sticky Spurts"
CONTROL_TYPE = "EFFECT_STICKY_SPURTS"
RESOURCE = os.path.join(os.path.dirname(__file__), "resources", "sticky_spurts.blend")


class MustardUI_ModelToolkit_StickySpurts(bpy.types.Operator):
    """Shoot ropes of thick liquid in spurts from a Control Empty at the 3D cursor, aimed at the selected meshes, sticking where they land with a few slow drips.\nThe meshes it sticks to are in the Targets collection\nBlender 5.2 or above is required"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_sticky_spurts"
    bl_label = "Add Sticky Spurts"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return effects_available() and any(x.type == "MESH" for x in context.selected_objects)

    def execute(self, context):
        with bpy.data.libraries.load(RESOURCE) as (_, data):
            if NODE_GROUP not in bpy.data.node_groups:
                data.node_groups = [NODE_GROUP]
            if MATERIAL not in bpy.data.materials:
                data.materials = [MATERIAL]

        meshes = [x for x in context.selected_objects if x.type == "MESH"]
        collection = bpy.data.collections.new("Sticky Spurts")
        context.scene.collection.children.link(collection)
        targets = bpy.data.collections.new("Sticky Spurts Targets")
        collection.children.link(targets)
        for obj in meshes:
            targets.objects.link(obj)
            # The liquid stays where it landed on the deformed meshes by their rest position
            obj.add_rest_position_attribute = True

        # Aimed at the center of the meshes, or down if the cursor is there
        corners = [obj.matrix_world @ Vector(c) for obj in meshes for c in obj.bound_box]
        center = sum(corners, Vector()) / len(corners)
        aim = center - context.scene.cursor.location
        control = bpy.data.objects.new("Sticky Spurts Control", None)
        collection.objects.link(control)
        control.empty_display_type = "SINGLE_ARROW"
        control.empty_display_size = 0.1
        control.location = context.scene.cursor.location
        control.rotation_euler = (
            aim.to_track_quat("Z", "Y").to_euler() if aim.length > 1e-4 else (3.14159, 0.0, 0.0)
        )
        control.MustardUI_tools_creators_is_created = True
        control.MustardUI_tools_creators_type = CONTROL_TYPE

        liquid = bpy.data.objects.new("Sticky Spurts", bpy.data.meshes.new("Sticky Spurts"))
        collection.objects.link(liquid)
        # Simulated in the space of the object, moving it would shift the liquid
        liquid.lock_location = liquid.lock_rotation = liquid.lock_scale = (True, True, True)
        modifier = liquid.modifiers.new("Sticky Spurts", "NODES")
        modifier.node_group = bpy.data.node_groups[NODE_GROUP]
        modifier_input(modifier, "Control").value = control
        modifier_input(modifier, "Targets").value = targets
        modifier_input(modifier, "Material").value = bpy.data.materials[MATERIAL]
        modifier_input(modifier, "Start Frame").value = context.scene.frame_current
        # The mesh baked frame by frame, for the playback not to mesh every frame again
        for bake in modifier.bakes:
            if bake.node.bl_idname == "GeometryNodeBake":
                bake.bake_mode = "ANIMATION"

        for obj in context.selected_objects:
            obj.select_set(False)
        control.select_set(True)
        context.view_layer.objects.active = control

        self.report({"INFO"}, f"MustardUI - Sticky Spurts added on {len(meshes)} meshes.")
        return {"FINISHED"}


class StickySpurtsLiquids:
    """Base of the operators acting on the selected liquids, or the liquids of selected Controls"""

    bl_options = {"UNDO"}

    @staticmethod
    def liquids(context):
        selected = set(context.selected_objects)
        for obj in bpy.data.objects:
            modifier = next((m for m in obj.modifiers if is_effect(m, NODE_GROUP)), None)
            if modifier and {obj, modifier_input(modifier, "Control").value} & selected:
                yield obj, modifier

    @classmethod
    def poll(cls, context):
        return any(cls.liquids(context))

    def remove(self, context, liquids):
        """Remove the liquids, their Controls and their collections, keeping the Targets"""
        for obj, modifier in liquids:
            collection = obj.users_collection[0]
            control = modifier_input(modifier, "Control").value
            targets = modifier_input(modifier, "Targets").value
            if control and control.MustardUI_tools_creators_type == CONTROL_TYPE:
                bpy.data.objects.remove(control)
            bpy.data.objects.remove(obj)
            if targets and targets in collection.children[:]:
                for target in [x for x in targets.objects if len(x.users_collection) == 1]:
                    context.scene.collection.objects.link(target)
                bpy.data.collections.remove(targets)
            if not collection.all_objects and not collection.children:
                bpy.data.collections.remove(collection)


class MustardUI_ModelToolkit_RemoveStickySpurts(StickySpurtsLiquids, bpy.types.Operator):
    """Remove the selected Sticky Spurts, or the ones of the selected Controls, with their Controls and collections"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_remove_sticky_spurts"
    bl_label = "Remove Sticky Spurts"

    def execute(self, context):
        self.remove(context, list(self.liquids(context)))
        self.report({"INFO"}, "MustardUI - Sticky Spurts removed.")
        return {"FINISHED"}


class MustardUI_ModelToolkit_ConvertStickySpurts(StickySpurtsLiquids, bpy.types.Operator):
    """Convert the selected Sticky Spurts, or the ones of the selected Controls, at the current frame to meshes parented to their first Target, removing the effects"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_convert_sticky_spurts"
    bl_label = "Convert Sticky Spurts to Mesh"

    def execute(self, context):
        liquids = list(self.liquids(context))
        depsgraph = context.evaluated_depsgraph_get()
        for obj, modifier in liquids:
            # With the attributes of the shader
            mesh = bpy.data.meshes.new_from_object(
                obj.evaluated_get(depsgraph), preserve_all_data_layers=True, depsgraph=depsgraph
            )
            mesh.name = f"{obj.name} Mesh"
            converted = bpy.data.objects.new(mesh.name, mesh)
            context.scene.collection.objects.link(converted)
            converted.matrix_basis = obj.matrix_world
            targets = modifier_input(modifier, "Targets").value
            target = next(iter(targets.objects), None) if targets else None
            if target:
                converted.parent = target
                converted.matrix_parent_inverse = target.matrix_world.inverted()
        self.remove(context, liquids)
        self.report({"INFO"}, "MustardUI - Sticky Spurts converted to meshes.")
        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_StickySpurts)
    bpy.utils.register_class(MustardUI_ModelToolkit_RemoveStickySpurts)
    bpy.utils.register_class(MustardUI_ModelToolkit_ConvertStickySpurts)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_ConvertStickySpurts)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_RemoveStickySpurts)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_StickySpurts)
