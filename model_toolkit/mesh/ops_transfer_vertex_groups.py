import math

import bpy
import numpy as np

from ...misc.mesh_cleanup import clear_unused_vertex_groups
from ...misc.mesh_deform import read_weights, rest_geometry, write_weights
from .weight_transfer import MIN_WEIGHT, transfer_weights

# Vertex Group marking the vertices with inpainted weights
UNMATCHED_GROUP = "Transfer Unmatched"


def transfer_vertex_groups(context, source, names, target, written, settings):
    """Robust transfer writing only the written groups: matched, filled, solved, or None"""

    geometry = rest_geometry(context, [target], [], False, faces_only=False)
    if not geometry or not len(geometry[0][0]):
        return None
    co, tris = geometry[0]
    edges = np.empty(len(target.data.edges) * 2, dtype=np.int64)
    target.data.edges.foreach_get("vertices", edges)

    weights, found, filled, solved = transfer_weights(
        source, (co, tris, edges.reshape(-1, 2)), settings
    )
    write_weights(target, written, weights[:, [names.index(n) for n in written]], MIN_WEIGHT)
    # The transferred groups without weights on the target are removed, not left empty
    others = [vg.name for vg in target.vertex_groups if vg.name not in written]
    clear_unused_vertex_groups(target, keep=others)
    return found, filled, solved


class MustardUI_ModelToolkit_TransferVertexGroups_Item(bpy.types.PropertyGroup):
    use: bpy.props.BoolProperty(name="Transfer", default=True)


class MUSTARDUI_UL_ModelToolkit_UIList_TransferVertexGroups(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.prop(item, "use", text="")
        row.label(text=item.name, icon="GROUP_VERTEX")


class MustardUI_ModelToolkit_TransferVertexGroups_Select(bpy.types.Operator):
    """Select or deselect all the Vertex Groups in the list"""

    bl_idname = "mustardui.model_toolkit_transfer_vertex_groups_select"
    bl_label = "Select Vertex Groups"

    use: bpy.props.BoolProperty(default=True)

    def execute(self, context):
        for item in context.window_manager.MustardUI_ModelToolkit_TransferVertexGroups_Items:
            item.use = self.use
        return {"FINISHED"}


class MustardUI_ModelToolkit_TransferVertexGroups_SelectBones(bpy.types.Operator):
    bl_idname = "mustardui.model_toolkit_transfer_vertex_groups_select_bones"
    bl_label = "Selected Bones"

    deform: bpy.props.BoolProperty(name="Deform", description="Use the deform bones")

    @classmethod
    def description(cls, context, properties):
        bones = "deform" if properties.deform else "selected"
        return f"Select only the Vertex Groups of the {bones} bones"

    def execute(self, context):
        obj = context.active_object

        if obj is None or obj.type != "MESH":
            self.report({"WARNING"}, "MustardUI - Active Object must be a Mesh")
            return {"CANCELLED"}

        # Armatures deforming the object
        armatures = [m.object for m in obj.modifiers if m.type == "ARMATURE" and m.object]
        if obj.parent is not None and obj.parent.type == "ARMATURE":
            armatures.append(obj.parent)
        if not armatures:
            self.report({"WARNING"}, "MustardUI - No Armature found for the Active Object")
            return {"CANCELLED"}

        # Selection is on the pose bones since Blender 5.0
        pose_select = bpy.app.version >= (5, 0, 0)
        bones = {
            bone.name
            for armature in armatures
            for bone in armature.pose.bones
            if (
                bone.bone.use_deform if self.deform else (bone if pose_select else bone.bone).select
            )
        }

        items = context.window_manager.MustardUI_ModelToolkit_TransferVertexGroups_Items
        if not any(item.name in bones for item in items):
            kind = "deform" if self.deform else "selected"
            self.report({"WARNING"}, f"MustardUI - No Vertex Group found for the {kind} bones")
            return {"CANCELLED"}

        for item in items:
            item.use = item.name in bones

        return {"FINISHED"}


class MustardUI_ModelToolkit_TransferVertexGroups(bpy.types.Operator):
    """Transfer selected vertex groups from active object to other selected objects"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_transfer_vertex_groups"
    bl_label = "Transfer Vertex Groups"
    bl_options = {"UNDO"}

    max_distance: bpy.props.FloatProperty(
        name="Max Distance",
        default=0.02,
        min=0.0,
        soft_max=0.1,
        subtype="DISTANCE",
        description="Maximum distance from the source to copy its weights, the farther "
        "vertices are filled smoothly.\nWith a large distance and Max Angle at 180°, the weights "
        "of the nearest point are copied everywhere",
    )

    max_angle: bpy.props.FloatProperty(
        name="Max Angle",
        default=math.radians(30.0),
        min=0.0,
        max=math.pi,
        subtype="ANGLE",
        description="Maximum angle between the source and target normals to copy the weights, "
        "the other vertices are filled smoothly",
    )

    overwrite: bpy.props.BoolProperty(
        name="Overwrite",
        default=True,
        description="Replace the listed Vertex Groups already on the targets.\n"
        "If disabled, only the missing ones are added.\nLocked Vertex Groups are never replaced",
    )

    both_sides: bpy.props.BoolProperty(
        name="Both Sides",
        default=False,
        description="Also copy the weights where the normals point in opposite directions",
    )

    smooth: bpy.props.IntProperty(
        name="Smooth",
        default=0,
        min=0,
        soft_max=20,
        description="Smoothing iterations of the filled weights and of the copied ones around them",
    )

    smooth_all: bpy.props.BoolProperty(
        name="Smooth All",
        default=False,
        description="Smooth all the weights, also the copied ones far from the filled vertices",
    )

    limit_influences: bpy.props.IntProperty(
        name="Limit Influences",
        default=0,
        min=0,
        soft_max=8,
        description="Maximum Vertex Groups per vertex, 0 for no limit",
    )

    mark_unmatched: bpy.props.BoolProperty(
        name="Mark Filled Vertices",
        default=False,
        description=f"Add the vertices with filled weights to the '{UNMATCHED_GROUP}' Vertex Group",
    )

    @classmethod
    def poll(cls, context):
        selected_objs = [x for x in context.selected_objects if x.type == "MESH"]
        return len(selected_objs) > 1

    def draw(self, context):
        wm = context.window_manager
        layout = self.layout

        row = layout.row()
        row.template_list(
            "MUSTARDUI_UL_ModelToolkit_UIList_TransferVertexGroups",
            "",
            wm,
            "MustardUI_ModelToolkit_TransferVertexGroups_Items",
            wm,
            "MustardUI_ModelToolkit_TransferVertexGroups_ItemIndex",
            rows=8,
        )

        row = layout.row()
        sub = row.row(align=True)
        sub.operator(
            "mustardui.model_toolkit_transfer_vertex_groups_select",
            text="All",
            icon="CHECKBOX_HLT",
        ).use = True
        sub.operator(
            "mustardui.model_toolkit_transfer_vertex_groups_select",
            text="None",
            icon="CHECKBOX_DEHLT",
        ).use = False
        sub = row.row(align=True)
        sub.operator(
            "mustardui.model_toolkit_transfer_vertex_groups_select_bones", icon="BONE_DATA"
        )
        sub.operator(
            "mustardui.model_toolkit_transfer_vertex_groups_select_bones",
            text="Deform Bones",
            icon="MOD_ARMATURE",
        ).deform = True

        layout.separator()
        col = layout.column()
        col.use_property_split = True
        col.use_property_decorate = False
        col.prop(self, "overwrite")
        col.separator()
        col.prop(self, "max_distance")
        col.prop(self, "max_angle")
        col.prop(self, "both_sides")
        col.separator()
        col.prop(self, "smooth")
        row = col.row()
        row.enabled = self.smooth > 0
        row.prop(self, "smooth_all")
        col.prop(self, "limit_influences")
        col.prop(self, "mark_unmatched")

    def execute(self, context):
        wm = context.window_manager
        source = context.active_object
        targets = [o for o in context.selected_objects if o != source]

        if not source or source.type != "MESH":
            self.report({"ERROR"}, "MustardUI - Active Object must be a Mesh")
            return {"CANCELLED"}

        items = wm.MustardUI_ModelToolkit_TransferVertexGroups_Items
        names = [item.name for item in items if item.use and item.name in source.vertex_groups]
        # Transfer all the Vertex Groups when called from scripts
        if not len(items):
            names = [vg.name for vg in source.vertex_groups]
        if not names:
            self.report({"ERROR"}, "MustardUI - No Vertex Groups to transfer")
            return {"CANCELLED"}

        geometry = rest_geometry(context, [source], [], False)
        if not geometry:
            self.report({"ERROR"}, "MustardUI - The Active Object has no faces")
            return {"CANCELLED"}
        source_data = (*geometry[0], read_weights(source, names))

        matched = 0
        total = 0
        transferred = 0
        skipped = False
        # Objects keeping the closest weights where they could not be filled
        unsolved = []
        for target in targets:
            if target.type != "MESH":
                continue

            vgs = target.vertex_groups
            written = [
                n for n in names if n not in vgs or (self.overwrite and not vgs[n].lock_weight)
            ]

            if not written:
                skipped = True
                continue

            result = transfer_vertex_groups(context, source_data, names, target, written, self)
            if result is None:
                continue

            found, filled, solved = result
            if not solved:
                unsolved.append(target.name)
            if self.mark_unmatched:
                write_weights(target, [UNMATCHED_GROUP], filled.astype(np.float64)[:, None])
            elif UNMATCHED_GROUP in target.vertex_groups:
                # The group of a previous transfer would be outdated
                target.vertex_groups.remove(target.vertex_groups[UNMATCHED_GROUP])

            matched += int(np.count_nonzero(found))
            total += len(found)
            transferred += 1

        if not total and skipped:
            self.report(
                {"WARNING"},
                "MustardUI - The Vertex Groups are already on the targets or locked",
            )
            return {"CANCELLED"}

        if not total:
            self.report({"ERROR"}, "MustardUI - The selected Objects have no vertices")
            return {"CANCELLED"}

        print(f"MustardUI - Transfer Vertex Groups: {matched}/{total} vertices matched")
        message = f"MustardUI - {len(names)} Vertex Groups transferred to {transferred} Objects"
        if unsolved:
            print("MustardUI - Weights not filled, closest ones kept:\n  " + "\n  ".join(unsolved))
            message += f", closest weights kept on {len(unsolved)} Objects (details in the console)"

        self.report({"WARNING"} if unsolved else {"INFO"}, message)
        return {"FINISHED"}

    def invoke(self, context, event):
        wm = context.window_manager
        source = context.active_object

        if not source or source.type != "MESH":
            self.report({"ERROR"}, "MustardUI - Active Object must be a Mesh")
            return {"CANCELLED"}

        # Keep the previous choices for the Vertex Groups still there
        items = wm.MustardUI_ModelToolkit_TransferVertexGroups_Items
        previous = {item.name: item.use for item in items}
        items.clear()
        for vg in source.vertex_groups:
            item = items.add()
            item.name = vg.name
            item.use = previous.get(vg.name, True)
        wm.MustardUI_ModelToolkit_TransferVertexGroups_ItemIndex = 0

        return context.window_manager.invoke_props_dialog(self, width=350)


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_TransferVertexGroups_Item)
    bpy.utils.register_class(MUSTARDUI_UL_ModelToolkit_UIList_TransferVertexGroups)
    bpy.utils.register_class(MustardUI_ModelToolkit_TransferVertexGroups_Select)
    bpy.utils.register_class(MustardUI_ModelToolkit_TransferVertexGroups_SelectBones)
    bpy.utils.register_class(MustardUI_ModelToolkit_TransferVertexGroups)

    bpy.types.WindowManager.MustardUI_ModelToolkit_TransferVertexGroups_Items = (
        bpy.props.CollectionProperty(type=MustardUI_ModelToolkit_TransferVertexGroups_Item)
    )
    bpy.types.WindowManager.MustardUI_ModelToolkit_TransferVertexGroups_ItemIndex = (
        bpy.props.IntProperty(default=0, name="")
    )


def unregister():
    del bpy.types.WindowManager.MustardUI_ModelToolkit_TransferVertexGroups_Items
    del bpy.types.WindowManager.MustardUI_ModelToolkit_TransferVertexGroups_ItemIndex

    bpy.utils.unregister_class(MustardUI_ModelToolkit_TransferVertexGroups)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_TransferVertexGroups_SelectBones)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_TransferVertexGroups_Select)
    bpy.utils.unregister_class(MUSTARDUI_UL_ModelToolkit_UIList_TransferVertexGroups)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_TransferVertexGroups_Item)
