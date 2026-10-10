import os

import bpy

from .effect import effects_available, is_effect, modifier_input

NODE_GROUP = "MustardUI Fireball"
MATERIAL = "MustardUI Fireball"
CONTROL_TYPE = "EFFECT_FIREBALL"
RESOURCE = os.path.join(os.path.dirname(__file__), "resources", "fireball.blend")


class MustardUI_ModelToolkit_Fireball(bpy.types.Operator):
    """Add a fireball on a Control Empty at the 3D cursor, leaving a trail of flames as the Control moves\nBlender 5.2 or above is required"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_fireball"
    bl_label = "Add Fireball"
    bl_options = {"REGISTER", "UNDO"}

    radius: bpy.props.FloatProperty(
        name="Radius", default=0.07, min=0.001, subtype="DISTANCE", description="Radius of the core"
    )

    @classmethod
    def poll(cls, context):
        return effects_available()

    def execute(self, context):
        with bpy.data.libraries.load(RESOURCE) as (_, target):
            if NODE_GROUP not in bpy.data.node_groups:
                target.node_groups = [NODE_GROUP]
            if MATERIAL not in bpy.data.materials:
                target.materials = [MATERIAL]

        collection = bpy.data.collections.new("Fireball")
        context.scene.collection.children.link(collection)

        control = bpy.data.objects.new("Fireball Control", None)
        collection.objects.link(control)
        control.empty_display_type = "SPHERE"
        control.location = context.scene.cursor.location
        control.scale = (self.radius, self.radius, self.radius)
        control.MustardUI_tools_creators_is_created = True
        control.MustardUI_tools_creators_type = CONTROL_TYPE

        fireball = bpy.data.objects.new("Fireball", bpy.data.meshes.new("Fireball"))
        collection.objects.link(fireball)
        # The Fireball follows the Control, moving the object would shift the particles
        fireball.lock_location = fireball.lock_rotation = fireball.lock_scale = (True, True, True)
        modifier = fireball.modifiers.new("Fireball", "NODES")
        modifier.node_group = bpy.data.node_groups[NODE_GROUP]
        modifier_input(modifier, "Control").value = control
        modifier_input(modifier, "Material").value = bpy.data.materials[MATERIAL]

        for obj in context.selected_objects:
            obj.select_set(False)
        control.select_set(True)
        context.view_layer.objects.active = control

        self.report({"INFO"}, "MustardUI - Fireball added.")
        return {"FINISHED"}


class MustardUI_ModelToolkit_RemoveFireball(bpy.types.Operator):
    """Remove the selected Fireballs, or the Fireballs of the selected Controls, and their empty collections"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_remove_fireball"
    bl_label = "Remove Fireball"
    bl_options = {"UNDO"}

    @staticmethod
    def fireballs(context):
        """Fireball objects and their Controls, if either is selected"""
        selected = set(context.selected_objects)
        for obj in bpy.data.objects:
            modifier = next((m for m in obj.modifiers if is_effect(m, NODE_GROUP)), None)
            if modifier is None:
                continue
            control = modifier_input(modifier, "Control").value
            if {obj, control} & selected:
                yield obj, control

    @classmethod
    def poll(cls, context):
        return any(cls.fireballs(context))

    def execute(self, context):
        fireballs = list(self.fireballs(context))
        controls = {
            c for _, c in fireballs if c and c.MustardUI_tools_creators_type == CONTROL_TYPE
        }
        objects = {x for x, _ in fireballs} | controls
        collections = {c for x in objects for c in x.users_collection}
        for obj in objects:
            bpy.data.objects.remove(obj)

        # Remove the collections left empty
        for collection in collections:
            if not collection.all_objects and not collection.children:
                bpy.data.collections.remove(collection)

        self.report({"INFO"}, "MustardUI - Fireball removed.")
        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_Fireball)
    bpy.utils.register_class(MustardUI_ModelToolkit_RemoveFireball)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_RemoveFireball)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_Fireball)
