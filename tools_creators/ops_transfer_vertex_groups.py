import bpy


class MustardUI_ToolsCreators_TransferVertexGroups_Item(bpy.types.PropertyGroup):
    group_name: bpy.props.StringProperty(name="Vertex Group")


class MustardUI_ToolsCreators_UIList_TransferVertexGroups(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row()

        obj = context.active_object
        # check dynamically if VG still exists
        if obj and obj.type == 'MESH' and item.group_name not in {vg.name for vg in obj.vertex_groups}:
            row.enabled = False  # gray out
            row.label(text=item.group_name, icon='ERROR')  # warning icon
        else:
            row.enabled = True
            row.label(text=item.group_name, icon='GROUP_VERTEX')


class MustardUI_ToolsCreators_TransferVertexGroups_Add(bpy.types.Operator):
    bl_idname = "mustardui.tools_creators_transfer_vertex_groups_add"
    bl_label = "Add Vertex Group"

    vg_name: bpy.props.StringProperty(name="Vertex Group")

    def execute(self, context):
        scene = context.scene

        # Use search_group from operator
        vg_name = self.vg_name.strip()
        if not vg_name:
            self.report({'WARNING'}, "MustardUI - Type a vertex group name first")
            return {'CANCELLED'}

        # Prevent duplicates
        if vg_name in [item.group_name for item in scene.MustardUI_ToolsCreators_TransferVertexGroups_Items]:
            self.report({'WARNING'}, "MustardUI - Vertex group already in list")
            return {'CANCELLED'}

        scene.MustardUI_ToolsCreators_TransferVertexGroups_Items.add().group_name = vg_name
        scene.MustardUI_ToolsCreators_TransferVertexGroups_ItemIndex = len(
            scene.MustardUI_ToolsCreators_TransferVertexGroups_Items) - 1
        return {'FINISHED'}


class MustardUI_ToolsCreators_TransferVertexGroups_Remove(bpy.types.Operator):
    bl_idname = "mustardui.tools_creators_transfer_vertex_groups_remove"
    bl_label = "Remove Vertex Group"

    def execute(self, context):
        scene = context.scene

        if scene.MustardUI_ToolsCreators_TransferVertexGroups_Items:
            scene.MustardUI_ToolsCreators_TransferVertexGroups_Items.remove(
                scene.MustardUI_ToolsCreators_TransferVertexGroups_ItemIndex)
            scene.MustardUI_ToolsCreators_TransferVertexGroups_ItemIndex = max(
                0, scene.MustardUI_ToolsCreators_TransferVertexGroups_ItemIndex - 1)

        return {'FINISHED'}


class MustardUI_ToolsCreators_TransferVertexGroups(bpy.types.Operator):
    """Transfer selected vertex groups from active object to other selected objects"""
    bl_idname = "mustardui.tools_creators_transfer_vertex_groups"
    bl_label = "Transfer Vertex Groups"
    bl_options = {'UNDO'}

    search_group: bpy.props.StringProperty(name="Vertex Group",
                                           description="Vertex Group to transfer from active to selected Objects")

    def draw(self, context):
        scene = context.scene
        layout = self.layout

        # UIList showing selected vertex groups
        row = layout.row()
        row.template_list(
            "MustardUI_ToolsCreators_UIList_TransferVertexGroups",
            "",
            scene,
            "MustardUI_ToolsCreators_TransferVertexGroups_Items",
            scene,
            "MustardUI_ToolsCreators_TransferVertexGroups_ItemIndex",
            rows=4
        )

        # Remove button
        col = row.column(align=True)
        col.operator("mustardui.tools_creators_transfer_vertex_groups_remove", icon='REMOVE', text="")

        layout.separator()

        # Search field + add button
        row = layout.row(align=True)
        row.prop_search(self, "search_group", context.active_object, "vertex_groups", text="", icon='GROUP_VERTEX')
        op = row.operator("mustardui.tools_creators_transfer_vertex_groups_add", text="", icon="ADD")
        op.vg_name = self.search_group

    def execute(self, context):
        scene = context.scene
        source = context.active_object
        targets = [o for o in context.selected_objects if o != source]

        if not source or source.type != 'MESH':
            self.report({'ERROR'}, "MustardUI - Active object must be a mesh")
            return {'CANCELLED'}

        # Filter out invalid vertex groups from the list
        source_vg_names = {vg.name for vg in source.vertex_groups}
        items_not_valid = [
            i for i, item in enumerate(scene.MustardUI_ToolsCreators_TransferVertexGroups_Items)
            if item.group_name not in source_vg_names
        ]

        items_to_transfer = len(scene.MustardUI_ToolsCreators_TransferVertexGroups_Items) - len(items_not_valid)
        if items_to_transfer < 1:
            self.report({'ERROR'}, "MustardUI - No vertex groups selected")
            return {'CANCELLED'}

        for target in targets:
            if target.type != 'MESH':
                continue

            # Ensure all needed vertex groups exist on target
            target_vg_names = {vg.name for vg in target.vertex_groups}

            bpy.context.view_layer.objects.active = target
            bpy.context.view_layer.update()

            for item in scene.MustardUI_ToolsCreators_TransferVertexGroups_Items:
                vg_name = item.group_name

                if vg_name not in source_vg_names:
                    continue

                if vg_name not in target_vg_names:
                    target.vertex_groups.new(name=vg_name)

                # Create Data Transfer modifier
                mod = target.modifiers.new(name=f"Transfer_{vg_name}", type='DATA_TRANSFER')
                mod.object = source

                mod.use_vert_data = True
                mod.data_types_verts = {'VGROUP_WEIGHTS'}
                mod.vert_mapping = 'POLYINTERP_NEAREST'

                # Assign vertex group names directly (Blender 5.0 API)
                mod.layers_vgroup_select_src = vg_name
                mod.layers_vgroup_select_dst = vg_name

                mod.mix_mode = 'REPLACE'
                mod.mix_factor = 1.0

                # Apply modifier
                bpy.ops.object.modifier_apply(modifier=mod.name)

        context.view_layer.objects.active = source

        self.report({'INFO'}, "MustardUI - Vertex groups transferred")

        return {'FINISHED'}

    def invoke(self, context, event):
        scene = context.scene

        # Fix the index
        scene.MustardUI_ToolsCreators_TransferVertexGroups_ItemIndex = min(
            scene.MustardUI_ToolsCreators_TransferVertexGroups_ItemIndex,
            len(scene.MustardUI_ToolsCreators_TransferVertexGroups_Items) - 1)
        scene.MustardUI_ToolsCreators_TransferVertexGroups_ItemIndex = max(
            scene.MustardUI_ToolsCreators_TransferVertexGroups_ItemIndex, 0)

        return context.window_manager.invoke_props_dialog(self)


def register():
    bpy.utils.register_class(MustardUI_ToolsCreators_TransferVertexGroups_Item)
    bpy.utils.register_class(MustardUI_ToolsCreators_UIList_TransferVertexGroups)
    bpy.utils.register_class(MustardUI_ToolsCreators_TransferVertexGroups_Add)
    bpy.utils.register_class(MustardUI_ToolsCreators_TransferVertexGroups_Remove)
    bpy.utils.register_class(MustardUI_ToolsCreators_TransferVertexGroups)

    bpy.types.Scene.MustardUI_ToolsCreators_TransferVertexGroups_Items = bpy.props.CollectionProperty(
        type=MustardUI_ToolsCreators_TransferVertexGroups_Item
    )
    bpy.types.Scene.MustardUI_ToolsCreators_TransferVertexGroups_ItemIndex = bpy.props.IntProperty(default=0,
                                                                                                   name="")


def unregister():
    del bpy.types.Scene.MustardUI_ToolsCreators_TransferVertexGroups_Items
    del bpy.types.Scene.MustardUI_ToolsCreators_TransferVertexGroups_ItemIndex

    bpy.utils.unregister_class(MustardUI_ToolsCreators_TransferVertexGroups)
    bpy.utils.unregister_class(MustardUI_ToolsCreators_TransferVertexGroups_Remove)
    bpy.utils.unregister_class(MustardUI_ToolsCreators_TransferVertexGroups_Add)
    bpy.utils.unregister_class(MustardUI_ToolsCreators_UIList_TransferVertexGroups)
    bpy.utils.unregister_class(MustardUI_ToolsCreators_TransferVertexGroups_Item)
