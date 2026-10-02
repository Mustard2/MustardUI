import os
import re

import bpy
from bpy_extras.io_utils import ExportHelper

from ...model_selection.active_object import ModelMode, active_object_operator_poll
from ..helper_functions import outfits_get_collection_items, outfits_get_collections
from ..ops_delete import delete_extras_pieces
from .ops_add_outfit import add_outfit_model, outfit_default_name, parents
from .ops_add_outfit_from_file import copy_id_property, copy_settings

# Collections of geometry and other data without datablock pointers
SKIP = {
    "vertices",
    "edges",
    "polygons",
    "loops",
    "loop_triangles",
    "loop_triangle_polygons",
    "data",
    "points",
    "splines",
    "key_blocks",
    "uv_layers",
    "attributes",
    "color_attributes",
    "vertex_colors",
    "vertex_normals",
    "polygon_normals",
    "corner_normals",
    "keyframe_points",
    "sampled_points",
    "bones",
    "edit_bones",
}

# Top level properties walked on object data, as the rest is geometry
DATA_PROPS = ("animation_data", "materials", "texture_mesh", "bevel_object", "taper_object")

# Datablocks of the model not copied, but cut if they would add the model to the file
NOT_COPIED = (bpy.types.Collection, bpy.types.Scene, bpy.types.Key)


class MustardUI_ModelToolkit_ExportOutfits_Item(bpy.types.PropertyGroup):
    use: bpy.props.BoolProperty(name="Export", description="Export this item")


class MUSTARDUI_UL_ModelToolkit_UIList_ExportOutfits(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        obj = bpy.data.objects.get(item.name)
        icon = "OUTLINER_COLLECTION" if obj is None else f"OUTLINER_OB_{obj.type}"
        row = layout.row(align=True)
        row.prop(item, "use", text="")
        row.label(text=item.name, icon=icon)


class MustardUI_ModelToolkit_ExportOutfits_Select(bpy.types.Operator):
    """Select or deselect all the items in the list"""

    bl_idname = "mustardui.model_toolkit_export_outfits_select"
    bl_label = "Select Items"

    use: bpy.props.BoolProperty(default=True)
    extras: bpy.props.BoolProperty(default=False)

    def execute(self, context):
        wm = context.window_manager
        items = (
            wm.MustardUI_ModelToolkit_ExportOutfits_Extras
            if self.extras
            else wm.MustardUI_ModelToolkit_ExportOutfits_Items
        )
        for item in items:
            item.use = self.use
        return {"FINISHED"}


def extras_pieces(rig_settings):
    """Extras pieces, without the ones parented to other pieces"""

    extras = rig_settings.extras_collection
    if extras is None:
        return []
    objects = set(outfits_get_collection_items(rig_settings, extras))
    return [o for o in objects if o.parent not in objects]


def export_fill_items(context):
    """List the Outfits, with the shown one selected, and the Extras pieces"""

    wm = context.window_manager
    items = wm.MustardUI_ModelToolkit_ExportOutfits_Items
    extras = wm.MustardUI_ModelToolkit_ExportOutfits_Extras
    items.clear()
    extras.clear()
    arm, _, _ = add_outfit_model(context)
    if arm is None:
        return
    rig_settings = arm.MustardUI_RigSettings
    for x in rig_settings.outfits_collections:
        if x.collection is not None:
            item = items.add()
            item.name = x.collection.name
            item.use = x.collection.name == rig_settings.outfits_list
    for obj in sorted(extras_pieces(rig_settings), key=lambda o: o.name):
        extras.add().name = obj.name


def closure(graph, roots, stop=()):
    """Datablocks reached from the roots in the graph, not past the stop ones"""

    found = set(roots)
    queue = list(roots)
    while queue:
        id_data = queue.pop()
        if id_data in stop:
            continue
        for linked in graph.get(id_data, ()):
            if linked not in found:
                found.add(linked)
                queue.append(linked)
    return found


class OutfitCopier:
    """Copies of the Outfits using the stand-ins of the model armature and body"""

    def __init__(self, mapping, drags, queue):
        # Original datablocks to their copies or stand-ins
        self.mapping = mapping
        self.drags = drags
        self.copies = list(mapping.items())
        self.created = set(mapping.values())
        self.queue = list(queue)
        self.cut = []
        self.seen = set()

    def replace(self, value, owner):
        new = self.mapping.get(value)
        if new is not None:
            return new
        if value in self.created or value not in self.drags:
            return value
        if isinstance(value, NOT_COPIED):
            self.cut.append(f"{owner}: {value.name}")
            return None
        new = value.copy()
        self.add(value, new)
        keys = getattr(value, "shape_keys", None)
        if keys is not None:
            self.add(keys, new.shape_keys)
        return new

    def add(self, original, copy):
        self.mapping[original] = copy
        self.copies.append((original, copy))
        self.created.add(copy)
        self.queue.append(copy)

    def run(self):
        while self.queue:
            id_data = self.queue.pop()
            if isinstance(id_data, bpy.types.Key):
                self.walk(id_data, id_data.name, only=("animation_data",))
            elif isinstance(
                id_data,
                (bpy.types.Object, bpy.types.Material, bpy.types.NodeTree, bpy.types.Armature),
            ):
                self.walk(id_data, id_data.name)
            elif not isinstance(id_data, bpy.types.Collection):
                self.walk(id_data, id_data.name, only=DATA_PROPS)

    def walk(self, struct, owner, depth=0, only=None):
        pointer = struct.as_pointer()
        if depth > 10 or pointer in self.seen:
            return
        self.seen.add(pointer)
        # Slots linked to the mesh would change its material, not the object one
        if isinstance(struct, bpy.types.MaterialSlot) and struct.link == "DATA":
            return

        for prop in struct.bl_rna.properties:
            pid = prop.identifier
            if pid in ("rna_type", "active_material") or (only is not None and pid not in only):
                continue
            if prop.type not in ("POINTER", "COLLECTION"):
                continue
            try:
                value = getattr(struct, pid)
            except AttributeError:
                continue

            if prop.type == "POINTER" and value is not None:
                if not isinstance(value, bpy.types.ID):
                    self.walk(value, owner, depth + 1)
                elif value.is_embedded_data:
                    self.walk(value, owner, depth + 1)
                elif not prop.is_readonly:
                    new = self.replace(value, owner)
                    if new != value:
                        try:
                            setattr(struct, pid, new)
                        except (AttributeError, TypeError, ValueError):
                            self.cut.append(f"{owner}: {value.name} (not replaced)")

            elif prop.type == "COLLECTION" and pid not in SKIP:
                for i, item in enumerate(value):
                    if item is None:
                        continue
                    if not isinstance(item, bpy.types.ID):
                        self.walk(item, owner, depth + 1)
                    elif pid == "materials":
                        new = self.replace(item, owner)
                        if new != item:
                            value[i] = new


def copy_collection(coll, mapping, objects, keep=None):
    """Copy of the collection and its children, only with the keep objects"""

    if keep is not None and not any(o in keep for o in coll.all_objects):
        return None
    new = bpy.data.collections.new(coll.name)
    mapping[coll] = new
    for attr in ("hide_viewport", "hide_render", "hide_select"):
        setattr(new, attr, getattr(coll, attr))
    for obj in coll.objects:
        if keep is not None and obj not in keep:
            continue
        if obj not in mapping:
            mapping[obj] = obj.copy()
        new.objects.link(mapping[obj])
        objects.add(obj)
    for child in coll.children:
        child_copy = copy_collection(child, mapping, objects, keep)
        if child_copy is not None:
            new.children.link(child_copy)
    return new


def extras_keep(extras, pieces):
    """The Extras pieces with the objects parented to them"""

    keep = set(pieces)
    return keep | {o for o in extras.all_objects if not keep.isdisjoint(parents(o))}


def stand_ins(arm, arm_obj, body, rig_settings):
    """Armature and body with no geometry, standing in for the ones of the model"""

    data = bpy.data.armatures.new(arm.name)
    rig = bpy.data.objects.new(arm_obj.name, data)
    rig.matrix_world = arm_obj.matrix_world
    mesh = bpy.data.meshes.new(body.data.name)
    stand_in_body = bpy.data.objects.new(body.name, mesh)
    stand_in_body.matrix_world = body.matrix_world

    mapping = {arm: data, arm_obj: rig, body: stand_in_body, body.data: mesh}
    # Shape Keys with the body names, for the drivers linked to them
    keys = body.data.shape_keys
    if keys is not None:
        for kb in keys.key_blocks:
            stand_in_body.shape_key_add(name=kb.name, from_mix=False)
        mapping[keys] = mesh.shape_keys

    settings = data.MustardUI_RigSettings
    settings.model_name = rig_settings.model_name
    settings.model_body = stand_in_body
    settings.model_armature_object = rig
    return mapping


class MustardUI_ModelToolkit_ExportOutfits(bpy.types.Operator, ExportHelper):
    """Export Outfits to a blend file, with their custom properties, to add them to another
    model with Add Outfit from File"""

    bl_idname = "mustardui.model_toolkit_export_outfits"
    bl_label = "Export Outfits"
    bl_options = {"UNDO", "PRESET"}

    filename_ext = ".blend"
    filter_glob: bpy.props.StringProperty(default="*.blend", options={"HIDDEN"})

    compress: bpy.props.BoolProperty(
        name="Compress", default=True, description="Write a compressed blend file"
    )

    pack_images: bpy.props.BoolProperty(
        name="Pack Images",
        default=True,
        description="Pack the images of the Outfits in the file, to share it without the "
        "texture files.\nThe images of the model are not changed",
    )

    separate_files: bpy.props.BoolProperty(
        name="One File per Item",
        default=False,
        description="Write each Outfit and Extras piece in its own file, named after the chosen "
        "file and the item",
    )

    delete_outfits: bpy.props.BoolProperty(
        name="Delete Exported",
        default=False,
        description="Delete the exported Outfits and Extras pieces from the model after the export",
    )

    @classmethod
    def poll(cls, context):
        if context.mode != "OBJECT":
            return False
        if not active_object_operator_poll(context, config=ModelMode.MODEL_TOOLKIT):
            return False
        arm, _, _ = add_outfit_model(context)
        return bool(outfits_get_collections(arm.MustardUI_RigSettings))

    def draw(self, context):
        wm = context.window_manager
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        lists = [("Outfits", "Items", False, "MOD_CLOTH")]
        if wm.MustardUI_ModelToolkit_ExportOutfits_Extras:
            lists.append(("Extras", "Extras", True, "OBJECT_DATA"))
        for label, prop, extras, icon in lists:
            items = getattr(wm, f"MustardUI_ModelToolkit_ExportOutfits_{prop}")
            chosen = sum(i.use for i in items)
            header, body = layout.panel(f"MustardUI_ExportOutfits_{prop}")
            header.label(text=f"{label} ({chosen}/{len(items)})", icon=icon)
            if body is None:
                continue
            # Full width, not in the property split column
            col = body.column(align=True)
            col.use_property_split = False
            col.template_list(
                "MUSTARDUI_UL_ModelToolkit_UIList_ExportOutfits",
                prop,
                wm,
                f"MustardUI_ModelToolkit_ExportOutfits_{prop}",
                wm,
                f"MustardUI_ModelToolkit_ExportOutfits_{prop}Index",
                rows=4,
            )
            row = col.row(align=True)
            for text, use, select_icon in (
                ("All", True, "CHECKBOX_HLT"),
                ("None", False, "CHECKBOX_DEHLT"),
            ):
                op = row.operator(
                    "mustardui.model_toolkit_export_outfits_select", text=text, icon=select_icon
                )
                op.use, op.extras = use, extras

        header, body = layout.panel("MustardUI_ExportOutfits_File")
        header.label(text="File", icon="FILE_BLEND")
        if body is not None:
            col = body.column(heading="Write")
            col.prop(self, "separate_files")
            col.prop(self, "compress")
            body.column(heading="Images").prop(self, "pack_images", text="Pack")
            body.column(heading="Exported").prop(self, "delete_outfits", text="Delete")

    def invoke(self, context, event):
        export_fill_items(context)
        arm, _, _ = add_outfit_model(context)
        folder = os.path.dirname(bpy.data.filepath)
        name = f"{arm.MustardUI_RigSettings.model_name or arm.name} Outfits.blend"
        self.filepath = os.path.join(folder, name)
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        arm, arm_obj, body = add_outfit_model(context)
        if arm_obj is None or body is None:
            self.report({"ERROR"}, "MustardUI - The model has no Armature or Body")
            return {"CANCELLED"}
        rig_settings = arm.MustardUI_RigSettings

        wm = context.window_manager
        chosen = {i.name for i in wm.MustardUI_ModelToolkit_ExportOutfits_Items if i.use}
        outfits = [
            x.collection
            for x in rig_settings.outfits_collections
            if x.collection is not None and x.collection.name in chosen
        ]
        chosen = {i.name for i in wm.MustardUI_ModelToolkit_ExportOutfits_Extras if i.use}
        pieces = [o for o in extras_pieces(rig_settings) if o.name in chosen]
        if not outfits and not pieces:
            self.report({"ERROR"}, "MustardUI - Choose the Outfits or Extras to export")
            return {"CANCELLED"}

        # Files with the collections to export, and the objects kept for the Extras
        extras = rig_settings.extras_collection
        filepath = bpy.path.abspath(self.filepath)
        if self.separate_files:
            base = os.path.splitext(filepath)[0]
            items = [(root, root, None) for root in outfits]
            items += [(piece, extras, extras_keep(extras, [piece])) for piece in pieces]
            files = []
            for item, root, keep in items:
                name = outfit_default_name(item.name, rig_settings.model_name)
                # Without the characters not allowed in file names
                name = re.sub(r'[\\/:*?"<>|]', "_", name)
                files.append((f"{base} - {name}.blend", [(root, keep)]))
        else:
            roots = [(root, None) for root in outfits]
            if pieces:
                roots.append((extras, extras_keep(extras, pieces)))
            files = [(filepath, roots)]
        model_file = os.path.abspath(bpy.data.filepath) if bpy.data.filepath else None
        if any(os.path.abspath(path) == model_file for path, _ in files):
            self.report({"ERROR"}, "MustardUI - Choose another file than the model one")
            return {"CANCELLED"}

        # Images not found, not packed
        self.missing = []
        count = 0
        cut = []
        for path, file_roots in files:
            result = self.export_file(context, path, file_roots)
            if result is None:
                return {"CANCELLED"}
            count += result[0]
            cut += result[1]

        if self.delete_outfits:
            for outfit in outfits:
                collections = [x.collection for x in rig_settings.outfits_collections]
                context.scene.mustardui_outfits_uilist_index = collections.index(outfit)
                bpy.ops.mustardui.delete_outfit(is_config=True)
            if pieces:
                delete_extras_pieces(
                    context, arm, extras_keep(rig_settings.extras_collection, pieces)
                )

        print(f"MustardUI - Export Outfits: {len(files)} files, {count} custom properties")
        issues = []
        if cut:
            print("MustardUI - References to the model removed:\n  " + "\n  ".join(cut))
            issues.append(f"{len(cut)} references removed")
        self.missing = sorted(set(self.missing))
        if self.missing:
            print("MustardUI - Images not found, not packed:\n  " + "\n  ".join(self.missing))
            issues.append(f"{len(self.missing)} images not found")
        exported = [f"{len(outfits)} Outfits"] if outfits else []
        if pieces:
            exported.append(f"{len(pieces)} Extras")
        message = f"MustardUI - {' and '.join(exported)} exported"
        if self.delete_outfits:
            message += " and deleted"
        if issues:
            message += f", {' and '.join(issues)} (details in the console)"
        self.report({"WARNING"} if issues else {"INFO"}, message)
        return {"FINISHED"}

    def export_file(self, context, filepath, roots):
        """Write the Outfits in a file, returning the custom properties and cut references"""

        created = []
        names = []
        # Images packed only for the export
        self.packed = []
        try:
            count, cut = self.write(context, filepath, roots, created, names)
        finally:
            for image in self.packed:
                image.unpack(method="REMOVE")
            # Remove the copies before giving back the names to the originals
            bpy.data.batch_remove([i for i in created if not isinstance(i, bpy.types.Key)])
            for id_data, name in names:
                id_data.name = name
        return None if count is None else (count, cut)

    def write(self, context, filepath, roots, created, names):
        """Write the copies of the Outfits, returning the custom properties and cut references"""

        arm, arm_obj, body = add_outfit_model(context)
        rig_settings = arm.MustardUI_RigSettings
        model = stand_ins(arm, arm_obj, body, rig_settings)
        heavy = set(model)
        created.extend(model.values())

        mapping = dict(model)
        objects = set()
        copies = [copy_collection(c, mapping, objects, keep) for c, keep in roots]
        created.extend(v for k, v in mapping.items() if k not in heavy)
        # Appended with any Outfit, as it has the model name and custom properties
        for copy in copies:
            copy.objects.link(model[arm_obj])

        # Outfit custom properties of the exported Outfits on the stand-in armature
        collections = {c for c in mapping if isinstance(c, bpy.types.Collection)}
        cps = model[arm].MustardUI_CustomPropertiesOutfit
        for cp in arm.MustardUI_CustomPropertiesOutfit:
            piece = cp.outfit_piece
            if not (piece in objects if piece is not None else cp.outfit in collections):
                continue
            new = cps.add()
            copy_settings(cp, new)
            for lp in cp.linked_properties:
                new_lp = new.linked_properties.add()
                new_lp.rna, new_lp.path = lp.rna, lp.path
            if cp.prop_name in arm.keys():
                copy_id_property(arm, cp.prop_name, model[arm], cp.prop_name)

        # Datablocks that would add the model to the file, through their users
        drags = closure(bpy.data.user_map(), heavy | {context.scene})
        copier = OutfitCopier(mapping, drags, [mapping[o] for o in objects])
        copier.run()
        # After the pieces, as their data copies are used by the custom properties
        for cp in cps:
            copier.walk(cp, cp.name)
        copier.run()
        created.extend(c for o, c in copier.copies if c not in created)

        written = [*copies, model[arm_obj], model[arm]]
        uses = {}
        for id_data, users in bpy.data.user_map().items():
            for user in users:
                uses.setdefault(user, set()).add(id_data)
        forbidden = heavy | set(bpy.data.scenes)
        reached = closure(uses, written, forbidden)
        leaks = reached & forbidden
        if leaks:
            # The exported datablocks using the model ones, to find what to fix
            users = {
                f"{u.name} ({type(u).__name__}) uses {i.name} ({type(i).__name__})"
                for i, us in bpy.data.user_map(subset=leaks).items()
                for u in us & reached - forbidden
            }

            print("MustardUI - Export stopped:\n  " + "\n  ".join(sorted(users)))
            self.report(
                {"ERROR"},
                "MustardUI - The Outfits still use the model (details in the console), "
                "nothing exported",
            )
            return None, None

        # The copies take the names of the originals, used by the custom properties paths
        for i, (original, copy) in enumerate(copier.copies):
            name = original.name
            original.name = f"MustardUI Export {i}"
            names.append((original, name))
            copy.name = name

        # Packed until the file is written
        for image in [i for i in reached if isinstance(i, bpy.types.Image)]:
            if not self.pack_images or image.packed_file or image.source not in ("FILE", "TILED"):
                continue
            try:
                image.pack()
            except RuntimeError:
                self.missing.append(image.name)
                continue
            self.packed.append(image)

        bpy.data.libraries.write(
            filepath, set(written), path_remap="RELATIVE", fake_user=True, compress=self.compress
        )
        return len(cps), copier.cut


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_ExportOutfits_Item)
    bpy.utils.register_class(MUSTARDUI_UL_ModelToolkit_UIList_ExportOutfits)
    bpy.utils.register_class(MustardUI_ModelToolkit_ExportOutfits_Select)
    bpy.utils.register_class(MustardUI_ModelToolkit_ExportOutfits)
    wm = bpy.types.WindowManager
    for prop in ("Items", "Extras"):
        setattr(
            wm,
            f"MustardUI_ModelToolkit_ExportOutfits_{prop}",
            bpy.props.CollectionProperty(type=MustardUI_ModelToolkit_ExportOutfits_Item),
        )
        setattr(
            wm,
            f"MustardUI_ModelToolkit_ExportOutfits_{prop}Index",
            bpy.props.IntProperty(default=0, name=""),
        )


def unregister():
    for prop in ("Extras", "Items"):
        delattr(bpy.types.WindowManager, f"MustardUI_ModelToolkit_ExportOutfits_{prop}Index")
        delattr(bpy.types.WindowManager, f"MustardUI_ModelToolkit_ExportOutfits_{prop}")
    bpy.utils.unregister_class(MustardUI_ModelToolkit_ExportOutfits)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_ExportOutfits_Select)
    bpy.utils.unregister_class(MUSTARDUI_UL_ModelToolkit_UIList_ExportOutfits)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_ExportOutfits_Item)
