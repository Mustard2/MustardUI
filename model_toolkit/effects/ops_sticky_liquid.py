import math
import os

import bpy

from .effect import effects_available, is_effect, modifier_input

NODE_GROUP = "MustardUI Sticky Liquid"
MATERIAL = "MustardUI Sticky Liquid"
CONTROL_TYPE = "EFFECT_STICKY_LIQUID"
RESOURCE = os.path.join(os.path.dirname(__file__), "resources", "sticky_liquid.blend")


class MustardUI_ModelToolkit_StickyLiquid(bpy.types.Operator):
    """Add a viscous liquid emitted from a Control Empty at the 3D cursor, pointing down, sticking to the selected meshes where it slides and drips.\nThe meshes it sticks to are in the Targets collection\nBlender 5.2 or above is required"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_sticky_liquid"
    bl_label = "Add Sticky Liquid"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return effects_available()

    def execute(self, context):
        with bpy.data.libraries.load(RESOURCE) as (_, data):
            if NODE_GROUP not in bpy.data.node_groups:
                data.node_groups = [NODE_GROUP]
            if MATERIAL not in bpy.data.materials:
                data.materials = [MATERIAL]

        collection = bpy.data.collections.new("Sticky Liquid")
        context.scene.collection.children.link(collection)
        targets = bpy.data.collections.new("Sticky Liquid Targets")
        collection.children.link(targets)
        meshes = [x for x in context.selected_objects if x.type == "MESH"]
        for obj in meshes:
            targets.objects.link(obj)
            # The liquid follows the deformed meshes from their rest position
            obj.add_rest_position_attribute = True

        control = bpy.data.objects.new("Sticky Liquid Emitter", None)
        collection.objects.link(control)
        control.empty_display_type = "SINGLE_ARROW"
        control.empty_display_size = 0.1
        control.location = context.scene.cursor.location
        control.rotation_euler = (math.pi, 0.0, 0.0)
        control.MustardUI_tools_creators_is_created = True
        control.MustardUI_tools_creators_type = CONTROL_TYPE

        liquid = bpy.data.objects.new("Sticky Liquid", bpy.data.meshes.new("Sticky Liquid"))
        collection.objects.link(liquid)
        # The liquid is simulated in the space of the object, moving it would shift it
        liquid.lock_location = liquid.lock_rotation = liquid.lock_scale = (True, True, True)
        modifier = liquid.modifiers.new("Sticky Liquid", "NODES")
        modifier.node_group = bpy.data.node_groups[NODE_GROUP]
        modifier_input(modifier, "Control").value = control
        modifier_input(modifier, "Targets").value = targets
        modifier_input(modifier, "Material").value = bpy.data.materials[MATERIAL]
        # The mesh baked frame by frame, for the playback not to mesh every frame again
        for bake in modifier.bakes:
            if bake.node.bl_idname == "GeometryNodeBake":
                bake.bake_mode = "ANIMATION"

        for obj in context.selected_objects:
            obj.select_set(False)
        control.select_set(True)
        context.view_layer.objects.active = control

        self.report({"INFO"}, f"MustardUI - Sticky Liquid added on {len(meshes)} meshes.")
        return {"FINISHED"}


class RemoveStickyLiquid:
    """Base of the operators removing the Sticky Liquids, with their Controls and collections"""

    bl_options = {"UNDO"}

    done = "removed"

    @staticmethod
    def liquids(context):
        """Sticky Liquid objects and their modifiers, if they or their Controls are selected"""
        selected = set(context.selected_objects)
        for obj in bpy.data.objects:
            modifier = next((m for m in obj.modifiers if is_effect(m, NODE_GROUP)), None)
            if modifier and {obj, modifier_input(modifier, "Control").value} & selected:
                yield obj, modifier

    @classmethod
    def poll(cls, context):
        return any(cls.liquids(context))

    def execute(self, context):
        objects, targets = set(), set()
        for obj, modifier in self.liquids(context):
            objects.add(obj)
            control = modifier_input(modifier, "Control").value
            if control and control.MustardUI_tools_creators_type == CONTROL_TYPE:
                objects.add(control)
            # Only the Targets collections created with the liquid, inside its collection
            collection = modifier_input(modifier, "Targets").value
            if collection in {c for x in obj.users_collection for c in x.children}:
                targets.add(collection)
        collections = {c for x in objects for c in x.users_collection}

        for obj in objects:
            bpy.data.objects.remove(obj)
        for collection in targets:
            # Not to remove the meshes only in the Targets collection
            for obj in collection.objects:
                if len(obj.users_collection) == 1:
                    context.scene.collection.objects.link(obj)
            bpy.data.collections.remove(collection)
        for collection in collections:
            if not collection.all_objects and not collection.children:
                bpy.data.collections.remove(collection)

        self.report({"INFO"}, f"MustardUI - Sticky Liquid {self.done}.")
        return {"FINISHED"}


class MustardUI_ModelToolkit_RemoveStickyLiquid(RemoveStickyLiquid, bpy.types.Operator):
    """Remove the selected Sticky Liquids, or the Sticky Liquids of the selected Controls, with their Targets collections and empty collections"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_remove_sticky_liquid"
    bl_label = "Remove Sticky Liquid"


class MustardUI_ModelToolkit_ConvertStickyLiquid(RemoveStickyLiquid, bpy.types.Operator):
    """Convert the selected Sticky Liquids, or the Sticky Liquids of the selected Controls, at the current frame to new meshes parented to their first Target, removing the effects"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_convert_sticky_liquid"
    bl_label = "Convert Sticky Liquid to Mesh"

    done = "converted to meshes"

    def execute(self, context):
        depsgraph = context.evaluated_depsgraph_get()
        for obj, modifier in self.liquids(context):
            # With the attributes of the shader
            mesh = bpy.data.meshes.new_from_object(
                obj.evaluated_get(depsgraph), preserve_all_data_layers=True, depsgraph=depsgraph
            )
            mesh.name = f"{obj.name} Mesh"
            # Without the empty slot of the mesh made from the volume
            if len(mesh.materials) > 1 and mesh.materials[0] is None:
                mesh.materials.pop(index=0)
            liquid = bpy.data.objects.new(mesh.name, mesh)
            obj.users_collection[0].objects.link(liquid)
            liquid.matrix_basis = obj.matrix_world
            # Following the first Target from where it is at this frame
            targets = modifier_input(modifier, "Targets").value
            target = next(iter(targets.objects), None) if targets else None
            if target:
                liquid.parent = target
                liquid.matrix_parent_inverse = target.matrix_world.inverted()
        return super().execute(context)


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_StickyLiquid)
    bpy.utils.register_class(MustardUI_ModelToolkit_RemoveStickyLiquid)
    bpy.utils.register_class(MustardUI_ModelToolkit_ConvertStickyLiquid)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_ConvertStickyLiquid)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_RemoveStickyLiquid)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_StickyLiquid)
