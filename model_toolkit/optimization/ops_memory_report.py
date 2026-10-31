import os

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    StringProperty,
)

from ... import __package__ as base_package
from ...misc.outfits import outfits_get_collection_items
from ...model_selection.active_object import (
    ModelMode,
    active_object_operator_poll,
    mustardui_active_object,
)
from ...outfits.ops_delete import delete_extras_pieces, purge_new_orphans
from .ops_convert_images import header_info

MB = 1024**2

# Bytes of an element of each attribute type
ATTRIBUTE_SIZES = {
    "BOOLEAN": 1,
    "INT8": 1,
    "INT": 4,
    "FLOAT": 4,
    "BYTE_COLOR": 4,
    "INT16_2D": 4,
    "FLOAT2": 8,
    "INT32_2D": 8,
    "FLOAT_VECTOR": 12,
    "FLOAT_COLOR": 16,
    "QUATERNION": 16,
    "FLOAT4X4": 64,
}
# Bytes of a vertex in the vertex groups, of each of its weights, of a particle and of a hair key
DEFORM_VERT, DEFORM_WEIGHT, PARTICLE, HAIR_KEY = 16, 8, 112, 24

ICONS = {"BODY": "OUTLINER_OB_MESH", "OUTFIT": "OUTLINER_COLLECTION", "EXTRAS": "MOD_CLOTH"}
ICONS["HAIR"] = "STRANDS"

# Columns of the list, with their width
COLUMNS = (("ram", "RAM", 4), ("keys", "Shape Keys", 5), ("textures", "Textures", 4))
# Rows of the list, width of its scroll bar with its margin and of the margin of a box, in UI units
ROWS, SCROLL_BAR, BOX_MARGIN = 10, 0.75, 0.2


def columns(row, texts, space=0.0):
    """Right aligned columns of the list with the texts, followed by space, in UI units"""
    for text, (_, _, width) in zip(texts, COLUMNS, strict=True):
        column = row.row()
        column.alignment = "RIGHT"
        column.ui_units_x = width
        column.label(text=text)
    if space > 0:
        column = row.row()
        column.ui_units_x = space
        column.label(text="")


def geometry_bytes(data):
    """Bytes of the attributes of a mesh or curves, topology included, with the face offsets"""
    if isinstance(data, bpy.types.Mesh):
        sizes = {
            "POINT": len(data.vertices),
            "EDGE": len(data.edges),
            "FACE": len(data.polygons),
            "CORNER": len(data.loops),
        }
        total = (len(data.polygons) + 1) * 4
    elif isinstance(data, bpy.types.Curves):
        sizes = {"POINT": len(data.points), "CURVE": len(data.curves)}
        total = (len(data.curves) + 1) * 4
    else:
        return 0
    return total + sum(
        sizes.get(a.domain, 0) * ATTRIBUTE_SIZES.get(a.data_type, 4) for a in data.attributes
    )


def image_bytes(image):
    """Bytes of the pixels of the Image once loaded, read from the file headers, 0 if unknown"""
    if image.source == "TILED":
        path = bpy.path.abspath(image.filepath, library=image.library)
        infos = [header_info(image, path.replace("<UDIM>", str(t.number))) for t in image.tiles]
    elif image.source == "FILE":
        infos = [header_info(image)]
    else:
        return 0
    total = sum(w * h * (16 if is_float else 4) for w, h, is_float, _ in filter(None, infos))
    # Other formats, if already loaded
    if not total and image.has_data:
        total = image.size[0] * image.size[1] * (16 if image.is_float else 4)
    return total


def node_images(tree, trees):
    """Images of the node tree and of its nested groups not in trees yet"""
    for node in tree.nodes:
        if node.type == "TEX_IMAGE" and node.image is not None:
            yield node.image
        elif node.type == "GROUP" and node.node_tree is not None and node.node_tree not in trees:
            trees.add(node.node_tree)
            yield from node_images(node.node_tree, trees)


def report_groups(rig_settings):
    """Kind, name and objects of the body, Outfits, Extras pieces and hair of the model"""
    from ...outfits.toolkit.ops_export_outfits import extras_keep, extras_pieces

    groups = []
    if rig_settings.model_body is not None:
        groups.append(("BODY", rig_settings.model_body.name, [rig_settings.model_body]))
    for x in rig_settings.outfits_collections:
        if x.collection is not None:
            objects = list(outfits_get_collection_items(rig_settings, x.collection))
            groups.append(("OUTFIT", x.collection.name, objects))
    for piece in sorted(extras_pieces(rig_settings), key=lambda o: o.name):
        groups.append(
            ("EXTRAS", piece.name, list(extras_keep(rig_settings.extras_collection, [piece])))
        )
    for coll in (rig_settings.hair_collection, rig_settings.hair_extras_collection):
        if coll is not None:
            groups.extend(("HAIR", obj.name, [obj]) for obj in coll.objects)
    return groups


def memory_report(context, rig_settings):
    """Memory of the body, Outfits, Extras pieces and hair of the model, in bytes"""

    prefs = context.preferences
    # The undo keeps a copy of all the data
    copies = 2 if prefs.edit.use_global_undo and prefs.edit.undo_steps > 0 else 1
    # Shape Keys evaluated also for hidden objects, which Armature storage adds to the depsgraph
    armature_storage = prefs.addons[base_package].preferences.settings_storage == "ARMATURE"

    rows = []
    for kind, name, objects in report_groups(rig_settings):
        data, keys, done = 0, 0, set()
        images = set()
        for obj in objects:
            for psys in getattr(obj, "particle_systems", ()):
                count = len(psys.particles)
                steps = len(psys.particles[0].hair_keys) if count else 0
                data += count * (PARTICLE + steps * HAIR_KEY)
            for slot in getattr(obj, "material_slots", ()):
                if slot.material is not None and slot.material.node_tree is not None:
                    images.update(node_images(slot.material.node_tree, set()))
            if obj.data is None or obj.data in done:
                continue
            done.add(obj.data)
            data += geometry_bytes(obj.data)
            if obj.type == "MESH":
                mesh = obj.data
                if obj.vertex_groups:
                    weights = sum(len(v.groups) for v in mesh.vertices)
                    data += len(mesh.vertices) * DEFORM_VERT + weights * DEFORM_WEIGHT
                if mesh.shape_keys is not None:
                    keys += len(mesh.shape_keys.key_blocks) * len(mesh.vertices) * 12
        hidden = not any(o.visible_get() for o in objects)
        evaluated = keys if armature_storage or not hidden else 0
        rows.append(
            {
                "kind": kind,
                "name": name,
                "objects": objects,
                "ram": (data + keys) * copies + evaluated,
                "keys": keys,
                "images": images,
                "hidden": hidden,
            }
        )

    # Images of the body are always loaded
    body = set().union(*(x["images"] for x in rows if x["kind"] == "BODY"))
    sizes = {x: image_bytes(x) for row in rows for x in row["images"]}
    for row in rows:
        shown = row["images"] if row["kind"] == "BODY" else row["images"] - body
        row["textures"] = sum(sizes[x] for x in shown)
    return rows


class MustardUI_MemoryReport_Item(bpy.types.PropertyGroup):
    """Outfit, Extras piece, hair or body listed in the Memory Report"""

    use: BoolProperty(name="Choose", description="Delete or export this item")
    kind: StringProperty()
    pieces: IntProperty()
    ram: FloatProperty(
        description="RAM used by the item, in MB, also while hidden: its data, the copy kept by "
        "the undo and the Shape Keys evaluated"
    )
    keys: FloatProperty(description="Shape Keys of the item, in MB, counted once")
    textures: FloatProperty(
        description="Textures of the item not used by the body, in MB, loaded only when shown, "
        "both in RAM and in the GPU memory"
    )
    hidden: BoolProperty()


class MUSTARDUI_UL_MemoryReport(bpy.types.UIList):
    """Memory used by the Outfits, Extras pieces, hair and body of the model"""

    sort_by: EnumProperty(
        name="Sort By",
        items=[(x, label, f"Sort by {label}") for x, label, _ in COLUMNS]
        + [("name", "Name", "Sort by name")],
        default="ram",
    )
    reverse_order: BoolProperty(name="Reverse", description="Reverse the order")
    min_ram: FloatProperty(
        name="Min RAM",
        default=0.0,
        min=0.0,
        description="List the items using at least this RAM, in MB",
    )
    hidden_only: BoolProperty(name="Hidden Only", description="List only the hidden items")

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        if item.kind in {"OUTFIT", "EXTRAS"}:
            row.prop(item, "use", text="")
        else:
            row.label(text="", icon="BLANK1")
        row.label(text=item.name, icon=ICONS.get(item.kind, "NONE"))
        columns(row, [f"{getattr(item, attr):.0f} MB" for attr, _, _ in COLUMNS])

    def draw_filter(self, context, layout):
        row = layout.row(align=True)
        row.prop(self, "filter_name", text="")
        row.prop(self, "use_filter_invert", text="", icon="ARROW_LEFTRIGHT")
        row = layout.row(align=True)
        row.prop(self, "sort_by", expand=True)
        icon = "SORT_ASC" if self.reverse_order else "SORT_DESC"
        row.prop(self, "reverse_order", text="", icon=icon)
        row = layout.row(align=True)
        row.prop(self, "min_ram")
        row.prop(self, "hidden_only", toggle=True)

    def filter_items(self, context, data, propname):
        items = getattr(data, propname)
        helper = bpy.types.UI_UL_list
        flags = helper.filter_items_by_name(
            self.filter_name, self.bitflag_filter_item, items, reverse=self.use_filter_invert
        ) or [self.bitflag_filter_item] * len(items)
        flags = [
            flag if x.ram >= self.min_ram and (x.hidden or not self.hidden_only) else 0
            for flag, x in zip(flags, items, strict=True)
        ]
        # Names in alphabetical order, sizes from the largest
        if self.sort_by == "name":
            keys = [(i, x.name.lower()) for i, x in enumerate(items)]
        else:
            keys = [(i, -getattr(x, self.sort_by)) for i, x in enumerate(items)]
        order = helper.sort_items_helper(keys, key=lambda x: x[1])
        if self.reverse_order:
            order = [len(order) - 1 - x for x in order]
        return flags, order


class MustardUI_ModelToolkit_MemoryReport(bpy.types.Operator):
    """Memory used by the Outfits, Extras pieces, hair and body, to delete or export the heaviest"""

    bl_idname = "mustardui.model_toolkit_memory_report"
    bl_label = "Memory Report"
    bl_options = {"UNDO"}

    memory: CollectionProperty(type=MustardUI_MemoryReport_Item, options={"SKIP_SAVE"})
    memory_index: IntProperty(default=0, options={"SKIP_SAVE"})

    action: EnumProperty(
        name="Action",
        items=[
            (
                "EXPORT",
                "Export and Delete",
                "Export each chosen Outfit and Extras piece in its own file, named after the "
                "model and the item, then delete it from the model",
            ),
            (
                "DELETE",
                "Delete",
                "Delete the chosen Outfits and Extras pieces, freeing their memory",
            ),
        ],
        default="EXPORT",
        options={"SKIP_SAVE"},
        description="Action on the chosen Outfits and Extras pieces",
    )
    directory: StringProperty(
        name="Folder",
        subtype="DIR_PATH",
        description="Folder of the exported files",
    )

    @classmethod
    def poll(cls, context):
        return active_object_operator_poll(context, config=ModelMode.MODEL_TOOLKIT)

    def chosen(self):
        return [x for x in self.memory if x.use and x.kind in {"OUTFIT", "EXTRAS"}]

    def invoke(self, context, event):
        res, arm = mustardui_active_object(context, config=ModelMode.MODEL_TOOLKIT)
        for row in memory_report(context, arm.MustardUI_RigSettings):
            item = self.memory.add()
            item.name, item.kind, item.hidden = row["name"], row["kind"], row["hidden"]
            item.pieces = len(row["objects"])
            item.ram, item.keys, item.textures = (row[x] / MB for x in ("ram", "keys", "textures"))
        if not self.directory:
            self.directory = os.path.dirname(bpy.data.filepath)
        return context.window_manager.invoke_props_dialog(self, width=700, confirm_text="Apply")

    def draw(self, context):
        layout = self.layout

        # Column titles, aligned with the list
        row = layout.row(align=True)
        # Place of the checkbox and icon of the items
        column = row.row()
        column.ui_units_x = 0.75
        column.label(text="")
        row.label(text="Name", icon="BLANK1")
        # With the space of the scroll bar, shown with more items than rows
        scroll = SCROLL_BAR if len(self.memory) > ROWS else 0.0
        columns(row, [label for _, label, _ in COLUMNS], scroll)
        layout.template_list(
            "MUSTARDUI_UL_MemoryReport", "", self, "memory", self, "memory_index", rows=ROWS
        )

        # Totals aligned with the list columns
        col = layout.box().column(align=True)
        hidden = [x for x in self.memory if x.hidden]
        for label, icon, items in (("Total", "INFO", self.memory), ("Hidden", "HIDE_ON", hidden)):
            row = col.row(align=True)
            row.label(text=label, icon=icon)
            totals = [sum(getattr(x, attr) for x in items) / 1024 for attr, _, _ in COLUMNS]
            columns(row, [f"{x:.2f} GB" for x in totals], scroll - BOX_MARGIN)

        box = layout.box()
        row = box.row(align=True)
        count = len(self.chosen())
        row.prop_enum(self, "action", "EXPORT", text=f"Export and Delete ({count})")
        row.prop_enum(self, "action", "DELETE", text=f"Delete ({count})")
        if self.action == "EXPORT":
            box.prop(self, "directory")
            if context.mode != "OBJECT":
                box.label(text="Switch to Object Mode to export", icon="ERROR")

    def execute(self, context):
        from ...outfits.toolkit.ops_export_outfits import export_fill_items, extras_keep

        chosen = self.chosen()
        if not chosen:
            return {"FINISHED"}
        res, arm = mustardui_active_object(context, config=ModelMode.MODEL_TOOLKIT)
        rig_settings = arm.MustardUI_RigSettings

        if self.action == "EXPORT":
            if context.mode != "OBJECT":
                self.report({"ERROR"}, "MustardUI - Switch to Object Mode to export")
                return {"CANCELLED"}
            wm = context.window_manager
            export_fill_items(context)
            names = {x.name for x in chosen}
            for item in wm.MustardUI_ModelToolkit_ExportOutfits_Items:
                item.use = item.name in names
            for item in wm.MustardUI_ModelToolkit_ExportOutfits_Extras:
                item.use = item.name in names
            # Files named after the model and each item, as with One File per Item
            name = f"{rig_settings.model_name or arm.name} Outfits.blend"
            result = bpy.ops.mustardui.model_toolkit_export_outfits(
                filepath=os.path.join(bpy.path.abspath(self.directory), name),
                separate_files=True,
                delete_outfits=True,
            )
            return {"FINISHED"} if "FINISHED" in result else {"CANCELLED"}

        outfits = [x.name for x in chosen if x.kind == "OUTFIT"]
        pieces = [bpy.data.objects[x.name] for x in chosen if x.kind == "EXTRAS"]
        for name in outfits:
            collections = [x.collection for x in rig_settings.outfits_collections]
            context.scene.mustardui_outfits_uilist_index = collections.index(
                bpy.data.collections[name]
            )
            bpy.ops.mustardui.delete_outfit(is_config=True)
        if pieces:
            with purge_new_orphans():
                delete_extras_pieces(
                    context, arm, extras_keep(rig_settings.extras_collection, pieces)
                )
        self.report({"INFO"}, f"MustardUI - {len(outfits) + len(pieces)} items deleted")
        return {"FINISHED"}


classes = (
    MustardUI_MemoryReport_Item,
    MUSTARDUI_UL_MemoryReport,
    MustardUI_ModelToolkit_MemoryReport,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
