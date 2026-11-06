import os

import bpy

from . import ops_dust_puff, ops_shatter
from .effect import effects_available, is_effect, modifier_input

NODE_GROUP = "MustardUI Shockwave"
MATERIAL = "MustardUI Shockwave Air"
DUST = "MustardUI Shockwave Dust"
RESOURCE = os.path.join(os.path.dirname(__file__), "resources", "shockwave.blend")
# Effects the wave hits, among their Colliders
HIT = (ops_shatter.NODE_GROUP, ops_dust_puff.NODE_GROUP)
# Height the dust rises to, relative to the radius
DUST_HEIGHT = 0.3


class MustardUI_ModelToolkit_Shockwave(bpy.types.Operator):
    """Add a blast wave growing from the 3D cursor on the ground, fast then slowing down, kicking up a ring of dust and shattering the meshes with Shatter where its front hits them.\nIt hits the effects added later with it among their Colliders\nBlender 5.2 or above is required"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_shockwave"
    bl_label = "Add Shockwave"
    bl_options = {"REGISTER", "UNDO"}

    radius: bpy.props.FloatProperty(
        name="Radius",
        default=5.0,
        min=0.01,
        subtype="DISTANCE",
        description="Radius the wave stops at",
    )

    @classmethod
    def poll(cls, context):
        return effects_available()

    def execute(self, context):
        with bpy.data.libraries.load(RESOURCE) as (_, data):
            if NODE_GROUP not in bpy.data.node_groups:
                data.node_groups = [NODE_GROUP]
            data.materials = [x for x in (MATERIAL, DUST) if x not in bpy.data.materials]

        wave = bpy.data.objects.new("Shockwave", bpy.data.meshes.new("Shockwave"))
        context.scene.collection.objects.link(wave)
        wave.location = context.scene.cursor.location
        modifier = wave.modifiers.new("Shockwave", "NODES")
        modifier.node_group = bpy.data.node_groups[NODE_GROUP]
        modifier_input(modifier, "Radius").value = self.radius
        modifier_input(modifier, "Material").value = bpy.data.materials[MATERIAL]
        modifier_input(modifier, "Dust Material").value = bpy.data.materials[DUST]
        modifier_input(modifier, "Height").value = self.radius * DUST_HEIGHT
        modifier_input(modifier, "Start Frame").value = context.scene.frame_current
        # Changing the modifier inputs from Python does not tag the object
        wave.update_tag()

        hit = 0
        for obj in context.scene.objects:
            for m in obj.modifiers:
                collection = (
                    modifier_input(m, "Colliders").value
                    if any(is_effect(m, x) for x in HIT)
                    else None
                )
                if collection is not None and wave.name not in collection.objects:
                    collection.objects.link(wave)
                    hit += 1

        # Selected, to be moved right away
        for obj in context.selected_objects:
            obj.select_set(False)
        wave.select_set(True)
        context.view_layer.objects.active = wave
        self.report({"INFO"}, f"MustardUI - Shockwave added, hitting {hit} effects.")
        return {"FINISHED"}


class MustardUI_ModelToolkit_RemoveShockwave(bpy.types.Operator):
    """Remove the selected Shockwaves, also from the Colliders of the effects they hit"""

    bl_idname = "mustardui.model_toolkit_remove_shockwave"
    bl_label = "Remove Shockwave"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        return any(is_effect(m, NODE_GROUP) for x in context.selected_objects for m in x.modifiers)

    def execute(self, context):
        for wave in [
            x
            for x in context.selected_objects
            if any(is_effect(m, NODE_GROUP) for m in x.modifiers)
        ]:
            mesh = wave.data
            bpy.data.objects.remove(wave)
            if not mesh.users:
                bpy.data.meshes.remove(mesh)
        self.report({"INFO"}, "MustardUI - Shockwave removed.")
        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_Shockwave)
    bpy.utils.register_class(MustardUI_ModelToolkit_RemoveShockwave)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_RemoveShockwave)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_Shockwave)
