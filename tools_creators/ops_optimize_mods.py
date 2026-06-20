import bpy

sm_vg_name = "MustardUI - Smooth Corrective"
mask_vg_name = "MustardUI - Mask"


def add_corrective_smooth_modifier(
    obj, group_name=None, name="", iterations=20, smooth_type="SIMPLE"
):
    # Add a Corrective Smooth modifier with specified settings
    mod = obj.modifiers.new(name=name, type="CORRECTIVE_SMOOTH")
    mod.iterations = iterations
    mod.smooth_type = smooth_type
    mod.rest_source = "BIND"
    if group_name:
        mod.vertex_group = group_name
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.correctivesmooth_bind(modifier=mod.name)
    return mod


def add_mask_modifier(obj, group_name=None, name=""):
    # Add a Corrective Smooth modifier with specified settings
    mod = obj.modifiers.new(name=name, type="MASK")
    mod.invert_vertex_group = True
    if group_name:
        mod.vertex_group = group_name
    return mod


def get_index(obj, name):
    return next(
        (i for i, m in enumerate(obj.modifiers) if m.name == name),
        len(obj.modifiers),
    )


def optimize_modifiers(
    context, obj, mod_type, mod_vg_name, sm_influence=True, preserve_modifiers=True
):
    arm = None
    pose_position = None
    for mod in obj.modifiers:
        if mod.type == "ARMATURE":
            arm = (
                mod.object.data if mod.object is not None and mod.object.data is not None else None
            )
    if arm is not None:
        pose_position = arm.pose_position
        arm.pose_position = "REST"

    if mod_vg_name not in obj.vertex_groups:
        obj.vertex_groups.new(name=mod_vg_name)

    # Temporarily set body as active for modifier_move_to_index
    prev_active = context.view_layer.objects.active
    context.view_layer.objects.active = obj

    mods = []
    max_iterations = 0
    lst_index = 0
    for mod in list(obj.modifiers):
        if not mod.type == mod_type:
            continue

        iterations = 0
        scale = 0

        if mod.vertex_group == "" or mod.vertex_group == mod_vg_name:
            continue
        name = mod.name
        vg = mod.vertex_group
        if mod_type == "CORRECTIVE_SMOOTH":
            iterations = mod.iterations
            scale = mod.scale
        visibility = mod.show_viewport
        lst_index = get_index(obj, name)

        if not preserve_modifiers:
            obj.modifiers.remove(mod)
        else:
            mod.show_viewport = False
            mod.show_render = False
            mod.name = mod.name + "Disabled"

        mod = obj.modifiers.new(name=name, type="VERTEX_WEIGHT_MIX")
        mod.vertex_group_a = mod_vg_name
        mod.vertex_group_b = vg
        mod.mix_set = "ALL"
        mod.mix_mode = "ADD"
        mod.show_expanded = False

        mods.append((mod, iterations, scale))
        max_iterations = max(max_iterations, iterations)

        mod.show_viewport = visibility
        mod.show_render = visibility

        bpy.ops.object.modifier_move_to_index(
            modifier=mod.name,
            index=lst_index,
        )

    if len(mods) < 1:
        return 0

    if mod_type == "CORRECTIVE_SMOOTH" and sm_influence and max_iterations > 0:
        for mod, iterations, scale in [x for x in mods if x is not None]:
            mod.mask_constant = 1.0 * float(iterations) / float(max_iterations)
            mod.mask_constant *= scale

    master_mod = next(
        (m for m in obj.modifiers if m.type == mod_type and m.name == mod_vg_name),
        None,
    )
    if master_mod is not None:
        obj.modifiers.remove(master_mod)

    if mod_type == "CORRECTIVE_SMOOTH":
        master_mod = add_corrective_smooth_modifier(
            obj,
            mod_vg_name,
            mod_vg_name,
            iterations=max_iterations,
            smooth_type="SIMPLE",
        )
    else:
        master_mod = add_mask_modifier(obj, mod_vg_name, mod_vg_name)

    master_mod.show_expanded = False
    bpy.ops.object.modifier_move_to_index(
        modifier=master_mod.name,
        index=lst_index + 1,
    )

    context.view_layer.objects.active = prev_active
    if arm is not None and pose_position is not None:
        arm.pose_position = pose_position

    return len(mods)


class MustardUI_ToolsCreators_OptimizeModifiers(bpy.types.Operator):
    """Optimize the Smooth Corrective modifiers on the Active Object.\nCreates a unique Smooth Corrective modifier and use the Vertex Weight Mix modifiers to generate the Vertex Group"""  # noqa: E501

    bl_idname = "mustardui.tools_creators_optimize_modifiers"
    bl_label = "Optimize Modifiers"
    bl_options = {"UNDO"}

    sm_influence: bpy.props.BoolProperty(
        default=True,
        name="Set Vertex Groups Influence",
        description="Use the Iterations number and the Scale settings of the Smooth "
        "Modifier settings to set the Vertex Mix Modifiers influence "
        "to preserve relative strength of the correction",
    )

    preserve_modifiers: bpy.props.BoolProperty(
        default=False,
        name="Preserve Smooth Corrective modifiers",
        description="Disable existent Smooth Corrective modifiers instead of removing them",
    )

    smooth_corrective: bpy.props.BoolProperty(
        default=True,
        name="Smooth Corrective",
    )
    mask: bpy.props.BoolProperty(
        default=True,
        name="Mask",
    )

    @classmethod
    def poll(cls, context):
        active_object = context.active_object
        return (
            active_object is not None
            and active_object.type == "MESH"
            and any(
                (mod.type == "CORRECTIVE_SMOOTH" and mod.vertex_group != sm_vg_name)
                or (mod.type == "MASK" and mod.vertex_group != mask_vg_name)
                for mod in active_object.modifiers
            )
        )

    def execute(self, context):

        if not (self.smooth_corrective or self.mask):
            self.report(
                {"WARNING"},
                "MustardUI - No Modifier type selected",
            )
            return {"CANCELLED"}

        sm_converted = 0
        mask_converted = 0
        if self.smooth_corrective:
            sm_converted = optimize_modifiers(
                context,
                context.active_object,
                "CORRECTIVE_SMOOTH",
                sm_vg_name,
                self.sm_influence,
                self.preserve_modifiers,
            )
        if self.mask:
            mask_converted = optimize_modifiers(
                context,
                context.active_object,
                "MASK",
                mask_vg_name,
                False,
                self.preserve_modifiers,
            )

        if sm_converted + mask_converted > 0:
            self.report(
                {"INFO"},
                f"MustardUI - {sm_converted + mask_converted} Modifiers optimized",
            )
        else:
            self.report(
                {"WARNING"},
                "MustardUI - No Modifiers needs to be optimized",
            )

        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=250)

    def draw(self, context):
        layout = self.layout

        col = layout.column(align=True)
        col.prop(self, "mask", icon="MOD_MASK")
        col.prop(self, "smooth_corrective", icon="MOD_SMOOTH")

        layout.separator()

        col = layout.column(align=True)
        col.prop(self, "preserve_modifiers")
        row = col.row()
        row.enabled = self.smooth_corrective
        row.prop(self, "sm_influence")


def register():
    bpy.utils.register_class(MustardUI_ToolsCreators_OptimizeModifiers)


def unregister():
    bpy.utils.unregister_class(MustardUI_ToolsCreators_OptimizeModifiers)
