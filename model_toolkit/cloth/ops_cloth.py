"""Cloth Physics: add, remove, reset, rebuild and select cloths, save drapes as Shape Keys."""

import bpy

from . import solver
from .settings import (
    STATE,
    cloth_objects,
    guess_collider,
    rebuild_report,
)


class MustardUI_ModelToolkit_ClothEnable(bpy.types.Operator):
    """Simulate the active mesh as cloth with Cloth Physics"""

    bl_idname = "mustardui.model_toolkit_cloth_enable"
    bl_label = "Enable Cloth"

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return not STATE["running"] and obj and obj.type == "MESH" and solver.gpu_available()

    def execute(self, context):
        obj = context.active_object
        st = obj.MustardUI_Cloth
        if st.collider is None:
            st.collider = guess_collider(obj)
        st.enabled = True
        if not rebuild_report(self, context):
            st.enabled = False
            return {"CANCELLED"}
        return {"FINISHED"}


class MustardUI_ModelToolkit_ClothDisable(bpy.types.Operator):
    """Stop simulating the active mesh and hide the result (Enable Cloth brings it back)"""

    bl_idname = "mustardui.model_toolkit_cloth_disable"
    bl_label = "Disable"

    @classmethod
    def poll(cls, context):
        return not STATE["running"] and context.active_object

    def execute(self, context):
        obj = context.active_object
        obj.MustardUI_Cloth.enabled = False
        mod = obj.modifiers.get(solver.RESULT_MOD)
        if mod:
            mod.show_viewport = mod.show_render = False
        return {"FINISHED"} if rebuild_report(self, context) else {"CANCELLED"}


class MustardUI_ModelToolkit_ClothReset(bpy.types.Operator):
    """Back to the rest shape"""

    bl_idname = "mustardui.model_toolkit_cloth_reset"
    bl_label = "Reset"

    all: bpy.props.BoolProperty(name="All", description="Reset every cloth")

    def execute(self, context):
        world = solver.WORLD["world"]
        obj = context.active_object
        if world and (self.all or (obj and obj.name in solver.SIMS)):
            world.reset(None if self.all else solver.SIMS[obj.name])
            world.cache.clear()
        return {"FINISHED"}


class MustardUI_ModelToolkit_ClothRebuild(bpy.types.Operator):
    """Rebuild the simulation of all cloths from their current meshes, colliders and settings"""

    bl_idname = "mustardui.model_toolkit_cloth_rebuild"
    bl_label = "Rebuild"

    @classmethod
    def poll(cls, context):
        return not STATE["running"] and cloth_objects(context) and solver.gpu_available()

    def execute(self, context):
        return {"FINISHED"} if rebuild_report(self, context) else {"CANCELLED"}


class MustardUI_ModelToolkit_ClothSaveShapeKey(bpy.types.Operator):
    """Save the drape as a Shape Key of the mesh and disable the cloth"""

    bl_idname = "mustardui.model_toolkit_cloth_save_shape_key"
    bl_label = "Save as Shape Key"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        return (
            not STATE["running"]
            and context.active_object
            and context.active_object.name in solver.SIMS
        )

    def execute(self, context):
        obj = context.active_object
        try:
            key = solver.WORLD["world"].save_shape_key(context, solver.SIMS[obj.name])
        except ValueError as e:
            self.report({"ERROR"}, f"MustardUI - {e}")
            return {"CANCELLED"}
        bpy.ops.mustardui.model_toolkit_cloth_disable()
        self.report({"INFO"}, f"MustardUI - saved as Shape Key '{key.name}'")
        return {"FINISHED"}


class MustardUI_ModelToolkit_ClothRemove(bpy.types.Operator):
    """Remove the simulation, its Result modifier and helper mesh"""

    bl_idname = "mustardui.model_toolkit_cloth_remove"
    bl_label = "Remove"

    @classmethod
    def poll(cls, context):
        return not STATE["running"] and context.active_object

    def execute(self, context):
        obj = context.active_object
        obj.MustardUI_Cloth.enabled = False
        mod = obj.modifiers.get(solver.RESULT_MOD)
        if mod:
            obj.modifiers.remove(mod)
        helper = bpy.data.objects.get(solver.helper_name(obj))
        if helper:
            me = helper.data
            bpy.data.objects.remove(helper)
            bpy.data.meshes.remove(me)
        return {"FINISHED"} if rebuild_report(self, context) else {"CANCELLED"}


class MustardUI_ModelToolkit_ClothSelect(bpy.types.Operator):
    """Select this cloth"""

    bl_idname = "mustardui.model_toolkit_cloth_select"
    bl_label = "Select Cloth"

    name: bpy.props.StringProperty()

    def execute(self, context):
        obj = bpy.data.objects.get(self.name)
        if obj is None or obj.name not in context.view_layer.objects:
            return {"CANCELLED"}
        for o in context.selected_objects:
            o.select_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj
        return {"FINISHED"}


classes = (
    MustardUI_ModelToolkit_ClothEnable,
    MustardUI_ModelToolkit_ClothDisable,
    MustardUI_ModelToolkit_ClothReset,
    MustardUI_ModelToolkit_ClothRebuild,
    MustardUI_ModelToolkit_ClothSaveShapeKey,
    MustardUI_ModelToolkit_ClothRemove,
    MustardUI_ModelToolkit_ClothSelect,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
