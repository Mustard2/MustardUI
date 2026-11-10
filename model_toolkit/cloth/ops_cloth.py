"""Cloth Physics: add, remove, reset, rebuild and select cloths, save drapes as Shape Keys."""

import bpy

from . import solver
from .settings import (
    STATE,
    active_cloth,
    cloth_objects,
    guess_collider,
    pin_radius_update,
    rebuild_report,
    vertices_near,
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

    name: bpy.props.StringProperty(description="Cloth object, the active one if empty")

    @classmethod
    def poll(cls, context):
        return not STATE["running"]

    def execute(self, context):
        obj = bpy.data.objects.get(self.name) if self.name else context.active_object
        if obj is None:
            return {"CANCELLED"}
        obj.MustardUI_Cloth.enabled = False
        mod = obj.modifiers.get(solver.RESULT_MOD)
        if mod:
            obj.modifiers.remove(mod)
        helper = bpy.data.objects.get(solver.helper_name(obj))
        if helper:
            me = helper.data
            bpy.data.objects.remove(helper)
            bpy.data.meshes.remove(me)
            context.view_layer.update()  # else its stale entry is still listed
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


class MustardUI_ModelToolkit_ClothAddPinEmpty(bpy.types.Operator):
    """Pin the cloth around the 3D cursor to a new Empty: animate or move the Empty to move it"""

    bl_idname = "mustardui.model_toolkit_cloth_add_pin_empty"
    bl_label = "Add Pin Empty"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return not STATE["running"] and active_cloth(context) is not None

    def execute(self, context):
        obj = active_cloth(context)
        cursor = context.scene.cursor.location.copy()
        radius = 0.05
        if not len(vertices_near(obj, cursor, radius)[1]):
            self.report({"ERROR"}, "MustardUI - Place the 3D cursor on the cloth")
            return {"CANCELLED"}
        empty = bpy.data.objects.new(f"{obj.name} Pin", None)
        empty.empty_display_type = "SPHERE"
        empty.location = cursor
        obj.users_collection[0].objects.link(empty)
        context.view_layer.update()
        st = obj.MustardUI_Cloth
        item = st.pin_empties.add()
        item.empty, item.group = empty, obj.vertex_groups.new(name=f"Pin {empty.name}").name
        item.radius = radius
        pin_radius_update(item, context)  # picks the vertices
        st.pin_empties_index = len(st.pin_empties) - 1
        return {"FINISHED"} if rebuild_report(self, context) else {"CANCELLED"}


class MustardUI_ModelToolkit_ClothRemovePinEmpty(bpy.types.Operator):
    """Remove the pin, its vertex group and its Empty"""

    bl_idname = "mustardui.model_toolkit_cloth_remove_pin_empty"
    bl_label = "Remove Pin Empty"
    bl_options = {"REGISTER", "UNDO"}

    index: bpy.props.IntProperty(default=-1, description="Pin Empty, the active one if -1")

    @classmethod
    def poll(cls, context):
        return not STATE["running"] and active_cloth(context) is not None

    def execute(self, context):
        obj = active_cloth(context)
        st = obj.MustardUI_Cloth
        items, index = st.pin_empties, self.index if self.index >= 0 else st.pin_empties_index
        if not 0 <= index < len(items):
            return {"CANCELLED"}
        item = items[index]
        group = obj.vertex_groups.get(item.group)
        if group is not None:
            obj.vertex_groups.remove(group)
        if item.empty is not None:
            bpy.data.objects.remove(item.empty)
            context.view_layer.update()  # else its stale entry is still listed
        items.remove(index)
        st.pin_empties_index = min(index, len(items) - 1)
        return {"FINISHED"} if rebuild_report(self, context) else {"CANCELLED"}


classes = (
    MustardUI_ModelToolkit_ClothEnable,
    MustardUI_ModelToolkit_ClothDisable,
    MustardUI_ModelToolkit_ClothReset,
    MustardUI_ModelToolkit_ClothRebuild,
    MustardUI_ModelToolkit_ClothSaveShapeKey,
    MustardUI_ModelToolkit_ClothRemove,
    MustardUI_ModelToolkit_ClothSelect,
    MustardUI_ModelToolkit_ClothAddPinEmpty,
    MustardUI_ModelToolkit_ClothRemovePinEmpty,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
