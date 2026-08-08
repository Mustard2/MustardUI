import bpy

from ..model_selection.active_object import active_object_operator_poll
from . import physics_presets


class MustardUI_ToolsCreators_AssignPhysics(bpy.types.Operator):
    """Assign the physics of a preset to the selected meshes.\nThis is the same simulation the cage tools add, on any mesh and without generating anything: it replaces the physics the meshes already have"""  # noqa: E501

    bl_idname = "mustardui.tools_creators_assign_physics"
    bl_label = "Assign Physics"
    bl_options = {"REGISTER", "UNDO"}

    physics_engine: physics_presets.physics_engine_property()
    cloth_preset: physics_presets.cloth_preset_property(default="JIGGLE")
    nodes_preset: physics_presets.nodes_preset_property(default="JIGGLE")

    use_active_group: bpy.props.BoolProperty(
        name="Use Active Vertex Group as Pin",
        description="Use the active vertex group of each mesh as the Pin group of "
        "the simulation.\nIn Edit Mode a new group is created from the selected "
        "vertices instead.\nWithout it the meshes are simulated with nothing "
        "holding them in place, and they fall",
        default=True,
    )

    @classmethod
    def poll(cls, context):
        if not active_object_operator_poll(context, config=1):
            return False
        return any(o.type == "MESH" for o in context.selected_objects)

    def execute(self, context):

        meshes = [o for o in context.selected_objects if o.type == "MESH"]
        if not meshes:
            self.report({"ERROR"}, "MustardUI - No mesh selected.")
            return {"CANCELLED"}

        engine, preset = physics_presets.selected_preset(self)

        # Reported once, and not for every mesh, if this Blender cannot provide the
        # Geometry Nodes physics
        fallback = engine == "NODES" and not physics_presets.cloth_dynamics_available()
        if fallback:
            engine = "CLOTH"
            preset = self.cloth_preset

        def pin_group_from_selection(obj, base_name="ClothPinGroup"):
            """Create a Pin group out of the vertices selected in Edit Mode."""
            bpy.ops.object.mode_set(mode="OBJECT")

            index = 1
            new_name = base_name
            while new_name in obj.vertex_groups:
                new_name = f"{base_name}_{index}"
                index += 1

            vertex_group = obj.vertex_groups.new(name=new_name)
            vertex_group.add([v.index for v in obj.data.vertices if v.select], 1.0, "ADD")

            bpy.ops.object.mode_set(mode="EDIT")
            return new_name

        active = context.view_layer.objects.active
        done = 0
        for obj in meshes:
            context.view_layer.objects.active = obj
            pin_group = ""
            if self.use_active_group:
                if obj.mode == "EDIT":
                    pin_group = pin_group_from_selection(obj)
                elif obj.vertex_groups.active:
                    pin_group = obj.vertex_groups.active.name

            if (
                physics_presets.apply_physics(
                    obj, engine=engine, preset=preset, pin_group_name=pin_group
                )
                is not None
            ):
                done += 1

        context.view_layer.objects.active = active

        if fallback:
            self.report(
                {"WARNING"},
                "MustardUI - Cloth Dynamics needs Blender 5.2 or later: the Cloth "
                "modifier was used instead.",
            )

        if not done:
            self.report({"ERROR"}, "MustardUI - The physics could not be assigned.")
            return {"CANCELLED"}

        self.report(
            {"INFO"},
            f"MustardUI - {physics_presets.preset_name(engine, preset)} assigned to "
            f"{done} object{'s' if done > 1 else ''}.",
        )

        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout

        physics_presets.draw_physics_presets(layout, self)

        layout.separator()

        layout.prop(self, "use_active_group")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)


def register():
    bpy.utils.register_class(MustardUI_ToolsCreators_AssignPhysics)


def unregister():
    bpy.utils.unregister_class(MustardUI_ToolsCreators_AssignPhysics)
