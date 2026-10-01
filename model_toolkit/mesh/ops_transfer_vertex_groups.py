import math

import bpy
import numpy as np

from ...misc.mesh_cleanup import clear_unused_vertex_groups
from ...misc.mesh_deform import read_weights, rest_geometry, write_weights
from .weight_transfer import MIN_WEIGHT, transfer_weights

# Vertex Group marking the vertices with inpainted weights
UNMATCHED_GROUP = "Transfer Unmatched"


class MustardUI_ModelToolkit_TransferVertexGroups_Item(bpy.types.PropertyGroup):
    group_name: bpy.props.StringProperty(name="Vertex Group")


class MUSTARDUI_UL_ModelToolkit_UIList_TransferVertexGroups(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row()

        obj = context.active_object
        # check dynamically if VG still exists
        if obj and obj.type == "MESH" and obj.vertex_groups.get(item.group_name) is None:
            row.enabled = False  # gray out
            row.label(text=item.group_name, icon="ERROR")  # warning icon
        else:
            row.enabled = True
            row.label(text=item.group_name, icon="GROUP_VERTEX")


class MustardUI_ModelToolkit_TransferVertexGroups_Add(bpy.types.Operator):
    bl_idname = "mustardui.model_toolkit_transfer_vertex_groups_add"
    bl_label = "Add Vertex Group"

    vg_name: bpy.props.StringProperty(name="Vertex Group")

    def execute(self, context):
        wm = context.window_manager

        # Use search_group from operator
        vg_name = self.vg_name.strip()
        if not vg_name:
            self.report({"WARNING"}, "MustardUI - Type a vertex group name first")
            return {"CANCELLED"}

        # Prevent duplicates
        if vg_name in [
            item.group_name for item in wm.MustardUI_ModelToolkit_TransferVertexGroups_Items
        ]:
            self.report({"WARNING"}, "MustardUI - Vertex group already in list")
            return {"CANCELLED"}

        wm.MustardUI_ModelToolkit_TransferVertexGroups_Items.add().group_name = vg_name
        wm.MustardUI_ModelToolkit_TransferVertexGroups_ItemIndex = (
            len(wm.MustardUI_ModelToolkit_TransferVertexGroups_Items) - 1
        )
        return {"FINISHED"}


class MustardUI_ModelToolkit_TransferVertexGroups_Remove(bpy.types.Operator):
    bl_idname = "mustardui.model_toolkit_transfer_vertex_groups_remove"
    bl_label = "Remove Vertex Group"

    def execute(self, context):
        wm = context.window_manager

        if wm.MustardUI_ModelToolkit_TransferVertexGroups_Items:
            wm.MustardUI_ModelToolkit_TransferVertexGroups_Items.remove(
                wm.MustardUI_ModelToolkit_TransferVertexGroups_ItemIndex
            )
            wm.MustardUI_ModelToolkit_TransferVertexGroups_ItemIndex = max(
                0, wm.MustardUI_ModelToolkit_TransferVertexGroups_ItemIndex - 1
            )

        return {"FINISHED"}


def mustardui_transfer_vertex_groups_add_items(wm, vg_names):
    """Add the vertex group names to the transfer list, skipping the ones already added"""

    items = wm.MustardUI_ModelToolkit_TransferVertexGroups_Items
    already_added = {item.group_name for item in items}

    added = 0
    for vg_name in vg_names:
        if vg_name in already_added:
            continue
        items.add().group_name = vg_name
        already_added.add(vg_name)
        added += 1

    wm.MustardUI_ModelToolkit_TransferVertexGroups_ItemIndex = max(0, len(items) - 1)

    return added


def mustardui_transfer_vertex_groups_armatures(obj):
    """Find the Armatures deforming the object"""

    armatures = []

    for modifier in obj.modifiers:
        if modifier.type == "ARMATURE" and modifier.object is not None:
            if modifier.object not in armatures:
                armatures.append(modifier.object)

    if obj.parent is not None and obj.parent.type == "ARMATURE" and obj.parent not in armatures:
        armatures.append(obj.parent)

    return armatures


class MustardUI_ModelToolkit_TransferVertexGroups_AddAll(bpy.types.Operator):
    """Add all the Vertex Groups of the Active Object to the list"""

    bl_idname = "mustardui.model_toolkit_transfer_vertex_groups_add_all"
    bl_label = "All Groups"

    def execute(self, context):
        obj = context.active_object

        if obj is None or obj.type != "MESH":
            self.report({"WARNING"}, "MustardUI - Active Object must be a Mesh")
            return {"CANCELLED"}

        added = mustardui_transfer_vertex_groups_add_items(
            context.window_manager, [vg.name for vg in obj.vertex_groups]
        )

        if not added:
            self.report({"WARNING"}, "MustardUI - No Vertex Group to add")
            return {"CANCELLED"}

        self.report({"INFO"}, f"MustardUI - {added} Vertex Groups added")

        return {"FINISHED"}


class MustardUI_ModelToolkit_TransferVertexGroups_AddSelectedBones(bpy.types.Operator):
    """Add the Vertex Groups of the Active Object corresponding to the selected bones"""

    bl_idname = "mustardui.model_toolkit_transfer_vertex_groups_add_bones"
    bl_label = "From Bones"

    def execute(self, context):
        obj = context.active_object

        if obj is None or obj.type != "MESH":
            self.report({"WARNING"}, "MustardUI - Active Object must be a Mesh")
            return {"CANCELLED"}

        armatures = mustardui_transfer_vertex_groups_armatures(obj)
        if not armatures:
            self.report({"WARNING"}, "MustardUI - No Armature found for the Active Object")
            return {"CANCELLED"}

        vg_names = {vg.name for vg in obj.vertex_groups}

        selected_bones = []
        for armature in armatures:
            for bone in armature.data.bones:
                if bone.select and bone.name in vg_names and bone.name not in selected_bones:
                    selected_bones.append(bone.name)

        if not selected_bones:
            self.report({"WARNING"}, "MustardUI - No Vertex Group found for the selected bones")
            return {"CANCELLED"}

        added = mustardui_transfer_vertex_groups_add_items(context.window_manager, selected_bones)

        if not added:
            self.report({"WARNING"}, "MustardUI - No Vertex Group to add")
            return {"CANCELLED"}

        self.report({"INFO"}, f"MustardUI - {added} Vertex Groups added")

        return {"FINISHED"}


class MustardUI_ModelToolkit_TransferVertexGroups(bpy.types.Operator):
    """Transfer selected vertex groups from active object to other selected objects.\nThe weights are copied where the surfaces are close and aligned, and filled smoothly from them elsewhere (e.g. skirts between the legs)"""  # noqa: E501

    bl_idname = "mustardui.model_toolkit_transfer_vertex_groups"
    bl_label = "Transfer Vertex Groups"
    bl_options = {"UNDO"}

    search_group: bpy.props.StringProperty(
        name="Vertex Group",
        description="Vertex Group to transfer from active to selected Objects",
    )

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

        # UIList showing selected vertex groups
        row = layout.row()
        row.template_list(
            "MUSTARDUI_UL_ModelToolkit_UIList_TransferVertexGroups",
            "",
            wm,
            "MustardUI_ModelToolkit_TransferVertexGroups_Items",
            wm,
            "MustardUI_ModelToolkit_TransferVertexGroups_ItemIndex",
            rows=4,
        )

        # Remove button
        col = row.column(align=True)
        col.operator(
            "mustardui.model_toolkit_transfer_vertex_groups_remove",
            icon="REMOVE",
            text="",
        )

        layout.separator()

        # Search field + add button
        row = layout.row(align=True)
        row.prop_search(
            self,
            "search_group",
            context.active_object,
            "vertex_groups",
            text="",
            icon="GROUP_VERTEX",
        )
        op = row.operator("mustardui.model_toolkit_transfer_vertex_groups_add", text="", icon="ADD")
        op.vg_name = self.search_group

        # Bulk add buttons
        row = layout.row(align=True)
        row.operator(
            "mustardui.model_toolkit_transfer_vertex_groups_add_all",
            icon="GROUP_VERTEX",
        )
        row.operator(
            "mustardui.model_toolkit_transfer_vertex_groups_add_bones",
            icon="BONE_DATA",
        )

        layout.separator()
        col = layout.column()
        col.use_property_split = True
        col.use_property_decorate = False
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

        # The listed Vertex Groups found on the source
        names = [
            item.group_name
            for item in wm.MustardUI_ModelToolkit_TransferVertexGroups_Items
            if item.group_name in source.vertex_groups
        ]
        names = list(dict.fromkeys(names))
        if not names:
            self.report({"ERROR"}, "MustardUI - No Vertex Groups to transfer")
            return {"CANCELLED"}

        geometry = rest_geometry(context, [source], [], False)
        if not geometry:
            self.report({"ERROR"}, "MustardUI - The Active Object has no faces")
            return {"CANCELLED"}
        source_co, source_tris = geometry[0]
        source_weights = read_weights(source, names)

        matched = 0
        total = 0
        for target in targets:
            if target.type != "MESH":
                continue
            geometry = rest_geometry(context, [target], [], False, faces_only=False)
            if not geometry or not len(geometry[0][0]):
                continue
            co, tris = geometry[0]
            edges = np.empty(len(target.data.edges) * 2, dtype=np.int64)
            target.data.edges.foreach_get("vertices", edges)

            weights, found, filled = transfer_weights(
                (source_co, source_tris, source_weights), (co, tris, edges.reshape(-1, 2)), self
            )
            write_weights(target, names, weights, MIN_WEIGHT)
            # The transferred groups without weights on the target are removed, not left empty
            others = [vg.name for vg in target.vertex_groups if vg.name not in names]
            clear_unused_vertex_groups(target, keep=others)
            if self.mark_unmatched:
                write_weights(target, [UNMATCHED_GROUP], filled.astype(np.float64)[:, None])
            elif UNMATCHED_GROUP in target.vertex_groups:
                # The group of a previous transfer would be outdated
                target.vertex_groups.remove(target.vertex_groups[UNMATCHED_GROUP])
            matched += int(np.count_nonzero(found))
            total += len(found)

        if not total:
            self.report({"ERROR"}, "MustardUI - The selected Objects have no vertices")
            return {"CANCELLED"}
        self.report(
            {"INFO"},
            f"MustardUI - Vertex Groups transferred ({matched}/{total} vertices matched)",
        )
        return {"FINISHED"}

    def invoke(self, context, event):
        wm = context.window_manager

        # Fix the index
        wm.MustardUI_ModelToolkit_TransferVertexGroups_ItemIndex = min(
            wm.MustardUI_ModelToolkit_TransferVertexGroups_ItemIndex,
            len(wm.MustardUI_ModelToolkit_TransferVertexGroups_Items) - 1,
        )
        wm.MustardUI_ModelToolkit_TransferVertexGroups_ItemIndex = max(
            wm.MustardUI_ModelToolkit_TransferVertexGroups_ItemIndex, 0
        )

        return context.window_manager.invoke_props_dialog(self)


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_TransferVertexGroups_Item)
    bpy.utils.register_class(MUSTARDUI_UL_ModelToolkit_UIList_TransferVertexGroups)
    bpy.utils.register_class(MustardUI_ModelToolkit_TransferVertexGroups_Add)
    bpy.utils.register_class(MustardUI_ModelToolkit_TransferVertexGroups_Remove)
    bpy.utils.register_class(MustardUI_ModelToolkit_TransferVertexGroups_AddAll)
    bpy.utils.register_class(MustardUI_ModelToolkit_TransferVertexGroups_AddSelectedBones)
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
    bpy.utils.unregister_class(MustardUI_ModelToolkit_TransferVertexGroups_AddSelectedBones)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_TransferVertexGroups_AddAll)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_TransferVertexGroups_Remove)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_TransferVertexGroups_Add)
    bpy.utils.unregister_class(MUSTARDUI_UL_ModelToolkit_UIList_TransferVertexGroups)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_TransferVertexGroups_Item)
