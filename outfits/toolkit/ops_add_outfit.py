import itertools
import re
import time
import traceback
from types import SimpleNamespace

import bpy

from ...misc.mesh_deform import read_weights, rest_geometry
from ...misc.move_modifier import move_modifier
from ...misc.ui_progress import status_progress
from ...model_selection.active_object import (
    ModelMode,
    active_object_operator_poll,
    mustardui_active_object,
)
from ...model_toolkit.mesh.ops_transfer_shape_keys import transfer_shape_keys_steps
from ...model_toolkit.mesh.ops_transfer_vertex_groups import transfer_vertex_groups
from ...model_toolkit.mesh.shape_key_preview import create_followers_shape_keys, write_shape_key
from ...model_toolkit.model.ops_naming import rename_object
from ...model_toolkit.outfits.ops_fit_to_body import (
    FitToBodySolver,
    fit_to_body_apply_to_children,
    fit_to_body_apply_to_mesh,
)
from ..helper_functions import outfits_get_collections


class MustardUI_ModelToolkit_AddOutfit_Item(bpy.types.PropertyGroup):
    object_name: bpy.props.StringProperty(name="Object")
    name: bpy.props.StringProperty(name="Piece Name", description="Name of the outfit piece")
    child: bpy.props.BoolProperty(name="Child", description="Object parented to a piece")


class MUSTARDUI_UL_ModelToolkit_UIList_AddOutfit(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        icon = "LINKED" if item.child else "OUTLINER_OB_MESH"
        row.prop(item, "name", text="", emboss=False, icon=icon)
        row.label(text=item.object_name)


class MustardUI_ModelToolkit_AddOutfit_ShapeKey(bpy.types.PropertyGroup):
    use: bpy.props.BoolProperty(name="Transfer", default=True)
    outfit: bpy.props.BoolProperty(name="Outfit Shape Key")


class MUSTARDUI_UL_ModelToolkit_UIList_AddOutfit_ShapeKeys(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.prop(item, "use", text="")
        row.label(text=item.name, icon="MOD_CLOTH" if item.outfit else "SHAPEKEY_DATA")


class MustardUI_ModelToolkit_AddOutfit_ShapeKeysSelect(bpy.types.Operator):
    """Select or deselect all the Shape Keys in the list"""

    bl_idname = "mustardui.model_toolkit_add_outfit_shape_keys_select"
    bl_label = "Select Shape Keys"

    use: bpy.props.BoolProperty(default=True)

    def execute(self, context):
        for item in context.window_manager.MustardUI_ModelToolkit_AddOutfit_ShapeKeys:
            item.use = self.use
        return {"FINISHED"}


def add_outfit_model(context):
    """Armature data, armature object and body of the model"""

    _, arm = mustardui_active_object(context, config=ModelMode.ANY)
    if arm is None:
        return None, None, None
    rig_settings = arm.MustardUI_RigSettings
    return arm, rig_settings.model_armature_object, rig_settings.model_body


def add_outfit_pieces(context):
    """Selected meshes, without the ones parented to other selected meshes"""

    _, arm_obj, body = add_outfit_model(context)
    selected = [
        o
        for o in context.selected_objects
        if o.type == "MESH" and o != body and (body is None or o.data != body.data)
    ]
    return [o for o in selected if not any(p in selected for p in parents(o))]


def parents(obj):
    while obj.parent is not None:
        obj = obj.parent
        yield obj


def add_outfit_children(pieces):
    """Meshes parented to the pieces, which follow them"""

    children = [c for p in pieces for c in p.children_recursive if c.type == "MESH"]
    return list(dict.fromkeys(c for c in children if c not in pieces))


def piece_default_names(names):
    """Piece names without the naming convention prefix and the words shared by all"""

    words = [re.sub(r"\.\d{3}$", "", n).split(" - ")[-1].split() for n in names]
    if len(words) > 1:
        shared = set.intersection(*(set(w) for w in words))
        if all(set(w) - shared for w in words):
            words = [[x for x in w if x not in shared] for w in words]
    # Imported meshes are often named "<name> Mesh"
    words = [w[:-1] if len(w) > 1 and w[-1] == "Mesh" else w for w in words]
    return [" ".join(w) for w in words]


def add_outfit_groups(pieces):
    """Pieces grouped by their collection"""

    groups = {}
    for piece in pieces:
        groups.setdefault(piece.users_collection[0], []).append(piece)
    return groups


def outfit_default_name(coll_name, model_name):
    """Outfit name from a collection name, without the number suffix and the model name"""

    name = re.sub(r"\.\d{3}$", "", coll_name)
    if model_name and name.startswith(f"{model_name} "):
        name = name[len(model_name) + 1 :]
    return name


def add_outfit_default_names(pieces):
    """Default names of the pieces and of their children, named after the piece"""

    names = dict(zip(pieces, piece_default_names([o.name for o in pieces]), strict=True))
    for child in add_outfit_children(pieces):
        piece = next(p for p in parents(child) if p in names)
        own = [w for w in piece_default_names([child.name])[0].split() if w not in piece.name]
        names[child] = " ".join([names[piece], *own])
    return names


def outfit_search(self, context, edit_text):
    arm, _, _ = add_outfit_model(context)
    if arm is None:
        return []
    collections = arm.MustardUI_RigSettings.outfits_collections
    return [x.collection.name for x in collections if x.collection is not None]


def outfit_shape_keys(arm, arm_obj, body):
    """Names of the body Shape Keys driven by the Outfits (e.g. fixes for an outfit)"""

    sks = body.data.shape_keys
    if sks is None or sks.animation_data is None:
        return set()

    props = {
        f'["{bpy.utils.escape_identifier(cp.prop_name)}"]'
        for cp in arm.MustardUI_CustomPropertiesOutfit
    }
    outfit_keys = {
        o.data.shape_keys
        for coll in outfits_get_collections(arm.MustardUI_RigSettings)
        for o in coll.all_objects
        if o.type == "MESH" and o.data.shape_keys is not None
    }
    paths = {kb.path_from_id("value"): kb.name for kb in sks.key_blocks}

    names = set()
    for fcurve in sks.animation_data.drivers:
        name = paths.get(fcurve.data_path)
        if name is None:
            continue
        for var in fcurve.driver.variables:
            for t in var.targets:
                if t.id in outfit_keys or (t.id in (arm, arm_obj) and t.data_path in props):
                    names.add(name)
    return names


def transfer_weights(context, body, armature, target, overwrite):
    """Robust transfer of the deform bones weights from the body, returning the count"""

    bones = {b.name for b in armature.data.bones if b.use_deform}
    names = [vg.name for vg in body.vertex_groups if vg.name in bones]
    if not names or not len(target.data.vertices):
        return 0

    if overwrite:
        for vg in [vg for vg in target.vertex_groups if vg.name in bones]:
            target.vertex_groups.remove(vg)
    written = [n for n in names if n not in target.vertex_groups]
    if not written:
        return 0

    # Default settings, not the ones changed in the Transfer Vertex Groups tool
    props = bpy.ops.mustardui.model_toolkit_transfer_vertex_groups.get_rna_type().properties
    settings = SimpleNamespace(**{p.identifier: getattr(p, "default", None) for p in props})
    source = (*rest_geometry(context, [body], [], False)[0], read_weights(body, names))
    result = transfer_vertex_groups(context, source, names, target, written, settings)
    if result is not None and not result[2]:
        print(f"MustardUI - Weights not filled on {target.name}, the closest ones are kept")
    return sum(n in target.vertex_groups for n in written)


def bind_to_armature(obj, armature):
    """Parent the object to the armature and deform it with the Armature modifier"""

    if obj.parent is None:
        matrix = obj.matrix_world.copy()
        obj.parent = armature
        obj.matrix_parent_inverse.identity()
        obj.matrix_world = matrix

    mods = [m for m in obj.modifiers if m.type == "ARMATURE"]
    for mod in mods:
        if mod.object is None:
            mod.object = armature
    if not mods:
        mod = obj.modifiers.new(name="Armature", type="ARMATURE")
        mod.object = armature
        move_modifier(obj, mod, 0)


# Datablock at the start of a custom property path, e.g. bpy.data.objects["Name"]
RNA_ID = re.compile(r'bpy\.data\.(\w+)\["((?:[^"\\]|\\.)*)"\]')


def rna_id(rna):
    """Collection name, datablock name and rest of a custom property path, or None"""

    match = RNA_ID.match(rna)
    if match is None:
        return None
    return match[1], re.sub(r"\\(.)", r"\1", match[2]), rna[match.end() :]


def rna_with_id(attr, id_data, rest):
    return f'bpy.data.{attr}["{bpy.utils.escape_identifier(id_data.name)}"]{rest}'


def custom_property_refs(arm):
    """Datablocks of the custom properties paths, to update the paths after renaming them"""

    refs = []
    for cps in (
        arm.MustardUI_CustomProperties,
        arm.MustardUI_CustomPropertiesOutfit,
        arm.MustardUI_CustomPropertiesHair,
    ):
        for cp in cps:
            for item in (cp, *cp.linked_properties):
                parsed = rna_id(item.rna)
                coll = getattr(bpy.data, parsed[0], None) if parsed else None
                if isinstance(coll, bpy.types.bpy_prop_collection) and parsed[1] in coll:
                    refs.append((item, parsed[0], coll[parsed[1]], parsed[2]))
    return refs


def update_custom_property_paths(refs):
    for item, attr, id_data, rest in refs:
        rna = rna_with_id(attr, id_data, rest)
        if item.rna != rna:
            item.rna = rna


def rebind_modifiers(context, objects, armature):
    """Bind again the modifiers in Rest Pose, returning the ones not bound"""

    mods = [
        (obj, mod)
        for obj in objects
        for mod in obj.modifiers
        if (mod.type == "SURFACE_DEFORM" and mod.target is not None)
        or (mod.type == "CORRECTIVE_SMOOTH" and mod.rest_source == "BIND")
    ]
    if not mods:
        return []

    def bound(mod):
        return mod.is_bound if mod.type == "SURFACE_DEFORM" else mod.is_bind

    pose_position = armature.data.pose_position
    shown = {mod: mod.show_viewport for _, mod in mods}
    armature.data.pose_position = "REST"
    try:
        for obj, mod in mods:
            # The binding is done when the modifier is evaluated
            mod.show_viewport = True
            if mod.type == "SURFACE_DEFORM":
                bind = bpy.ops.object.surfacedeform_bind
            else:
                bind = bpy.ops.object.correctivesmooth_bind
            with context.temp_override(object=obj, active_object=obj):
                # The operator unbinds the bound modifiers
                if bound(mod):
                    bind(modifier=mod.name)
                bind(modifier=mod.name)
        context.view_layer.update()
    finally:
        armature.data.pose_position = pose_position
        for mod, show in shown.items():
            mod.show_viewport = show
    return [f"{obj.name}: {mod.name}" for obj, mod in mods if not bound(mod)]


class PiecesBackup:
    """Pieces and children state before the tool, restored on cancel"""

    def __init__(self, pieces):
        self.objects = {
            obj: (
                obj.parent,
                obj.matrix_parent_inverse.copy(),
                obj.matrix_world.copy(),
                {m.name: getattr(m, "object", None) for m in obj.modifiers},
            )
            for obj in pieces
        }
        # Weights, Shape Keys and fitted coordinates are all in the meshes
        objs = pieces + [c for p in pieces for c in p.children_recursive]
        self.meshes = {}
        for obj in objs:
            if obj.type == "MESH" and obj.data not in self.meshes:
                self.meshes[obj.data] = obj.data.copy()

    def restore(self):
        for mesh, backup in self.meshes.items():
            name = mesh.name
            mesh.user_remap(backup)
            bpy.data.meshes.remove(mesh)
            backup.name = name
        for obj, (parent, parent_inverse, matrix, mods) in self.objects.items():
            for mod in [m for m in obj.modifiers if m.name not in mods]:
                obj.modifiers.remove(mod)
            for mod in obj.modifiers:
                if mod.type == "ARMATURE":
                    mod.object = mods[mod.name]
            obj.parent = parent
            obj.matrix_parent_inverse = parent_inverse
            obj.matrix_world = matrix

    def discard(self):
        for backup in self.meshes.values():
            bpy.data.meshes.remove(backup)


def add_outfit_fill_lists(context):
    """Fill the pieces and Shape Keys lists, returning the pieces collection"""

    wm = context.window_manager
    pieces = add_outfit_pieces(context)
    items = wm.MustardUI_ModelToolkit_AddOutfit_Items

    items.clear()
    for obj, name in add_outfit_default_names(pieces).items():
        item = items.add()
        item.object_name = obj.name
        item.name = name
        item.child = obj not in pieces
    wm.MustardUI_ModelToolkit_AddOutfit_ItemIndex = 0

    add_outfit_fill_shape_keys(context)

    colls = {c for o in pieces for c in o.users_collection}
    return colls.pop().name if len(colls) == 1 else ""


def add_outfit_fill_shape_keys(context):
    """Fill the body Shape Keys list"""

    # Keep the previous choices, skipping the Outfits Shape Keys by default
    wm = context.window_manager
    arm, arm_obj, body = add_outfit_model(context)
    sk_items = wm.MustardUI_ModelToolkit_AddOutfit_ShapeKeys
    previous = {item.name: item.use for item in sk_items}
    sk_items.clear()
    sks = body.data.shape_keys if body is not None else None
    if sks is not None:
        outfit_sks = outfit_shape_keys(arm, arm_obj, body)
        for sk in sks.key_blocks:
            if sk == sks.reference_key:
                continue
            item = sk_items.add()
            item.name = sk.name
            item.outfit = sk.name in outfit_sks
            item.use = previous.get(sk.name, not item.outfit)
    wm.MustardUI_ModelToolkit_AddOutfit_ShapeKeyIndex = 0


def fit_property(default):
    """Fit to Body setting, declared by each operator with its default"""

    return bpy.props.EnumProperty(
        name="Fit to Body",
        items=(
            ("NONE", "None", "Do not fit the pieces to the body"),
            ("SHAPE_KEY", "Shape Key", "Fit the pieces clipping through the body with a Shape Key"),
            ("MESH", "Mesh", "Fit the pieces clipping through the body, applying it to the mesh"),
        ),
        default=default,
        description="Fit the pieces clipping through the body, with the default settings of the "
        "Fit to Body tool.\nPieces not clipping are not changed",
    )


class AddOutfitSettings:
    """Settings of Add Outfit, shared with Add Outfit from File"""

    destination: bpy.props.EnumProperty(
        name="Add to",
        items=(
            ("NEW", "New Outfit", "Create a new Outfit with the selected Objects"),
            ("OUTFIT", "Outfit", "Add the selected Objects to an existing Outfit"),
            ("EXTRAS", "Extras", "Add the selected Objects to the Extras"),
        ),
        default="NEW",
    )

    outfit_name: bpy.props.StringProperty(
        name="Outfit Name",
        description="Name of the new Outfit.\nThe model name is added if the model uses the "
        "MustardUI naming convention",
        options={"SKIP_PRESET"},
    )

    split: bpy.props.BoolProperty(
        name="One Outfit per Collection",
        default=False,
        description="Create an Outfit for each collection of the selected Objects, named after it",
    )

    outfit: bpy.props.StringProperty(
        name="Outfit", search=outfit_search, search_options=set(), options={"SKIP_PRESET"}
    )

    rename: bpy.props.BoolProperty(
        name="Rename Objects",
        default=True,
        description="Rename the Objects and their data with the piece names",
    )

    fit_smooth: bpy.props.FloatProperty(
        name="Smooth",
        default=0.02,
        min=0.0,
        soft_max=0.1,
        subtype="DISTANCE",
        description="Distance the fit is smoothed over",
    )

    add_smooth: bpy.props.BoolProperty(
        name="Corrective Smooth",
        default=False,
        description="Add a Corrective Smooth modifier after the Armature, to smooth the "
        "deformation artifacts in poses",
    )

    add_shrinkwrap: bpy.props.BoolProperty(
        name="Shrinkwrap",
        default=False,
        description="Add a Shrinkwrap modifier after the Armature, pushing out of the body "
        "the parts clipping through it in poses",
    )

    rebind: bpy.props.BoolProperty(
        name="Rebind Modifiers",
        default=True,
        description="Bind again, in rest pose, the Surface Deform modifiers of the pieces and "
        "the Corrective Smooth ones using a bind, as their target or mesh might have changed",
    )

    transfer_weights: bpy.props.BoolProperty(
        name="Transfer Weights",
        default=True,
        description="Transfer the weights of the deform bones from the body",
    )

    overwrite_weights: bpy.props.BoolProperty(
        name="Overwrite",
        default=False,
        description="Replace all the deform bones Vertex Groups of the pieces with the body "
        "ones.\nIf disabled, only the Vertex Groups missing on the pieces are added",
    )

    transfer_shape_keys: bpy.props.BoolProperty(
        name="Transfer Shape Keys",
        default=True,
        description="Transfer the Shape Keys from the body",
    )

    overwrite_shape_keys: bpy.props.BoolProperty(
        name="Overwrite",
        default=False,
        description="Overwrite the Shape Keys already on the pieces, resetting the ones below "
        "the threshold.\nIf disabled, they are skipped",
    )

    link: bpy.props.BoolProperty(
        name="Link to Body",
        default=True,
        description="Drive the values of the new Shape Keys with the body ones",
    )

    max_distance: bpy.props.FloatProperty(
        name="Max Distance",
        default=0.0,
        min=0.0,
        soft_max=0.2,
        subtype="DISTANCE",
        description="Vertices farther than this from the body are not affected by the Shape "
        "Keys.\nSet to 0 to disable",
    )

    smooth: bpy.props.FloatProperty(
        name="Smooth",
        default=0.0,
        min=0.0,
        max=1.0,
        soft_max=0.1,
        subtype="DISTANCE",
        description="Distance the transferred Shape Keys are smoothed over, to reduce the "
        "artifacts on loose meshes (e.g. skirts).\nSet to 0 to disable",
    )

    threshold: bpy.props.FloatProperty(
        name="Threshold",
        default=0.0001,
        min=0.0,
        soft_max=0.001,
        step=0.001,
        precision=5,
        subtype="DISTANCE",
        description="Shape Keys moving the piece less than this are not created",
    )

    def draw_settings(self, context, pieces=None):
        """Draw the settings, with the pieces list if the pieces are known"""

        wm = context.window_manager
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column()
        col.prop(self, "destination")
        if self.destination == "NEW":
            if pieces is None or len(add_outfit_groups(pieces)) > 1:
                col.prop(self, "split")
            if not self.split:
                col.prop(self, "outfit_name", text="Name")
        elif self.destination == "OUTFIT":
            col.prop(self, "outfit")
        col.prop(self, "rename")

        self.draw_extra(layout)

        if pieces is not None:
            header, body = layout.panel("MustardUI_AddOutfit_Pieces")
            header.label(text="Pieces", icon="OUTLINER_OB_MESH")
            if body is not None:
                body.use_property_split = False
                body.template_list(
                    "MUSTARDUI_UL_ModelToolkit_UIList_AddOutfit",
                    "",
                    wm,
                    "MustardUI_ModelToolkit_AddOutfit_Items",
                    wm,
                    "MustardUI_ModelToolkit_AddOutfit_ItemIndex",
                    rows=4,
                )

        header, body = layout.panel("MustardUI_AddOutfit_Fit")
        header.label(text="Fit to Body", icon="MOD_SHRINKWRAP")
        if body is not None:
            body.row().prop(self, "fit", text="Mode", expand=True)
            col = body.column()
            col.active = self.fit != "NONE"
            col.prop(self, "fit_smooth")

        header, body = layout.panel("MustardUI_AddOutfit_Modifiers", default_closed=True)
        header.label(text="Modifiers", icon="MODIFIER")
        if body is not None:
            col = body.column(heading="Add")
            col.prop(self, "add_smooth")
            col.prop(self, "add_shrinkwrap")
            body.column(heading="Surface Deform").prop(self, "rebind", text="Rebind")

        header, body = layout.panel("MustardUI_AddOutfit_Weights", default_closed=True)
        header.use_property_split = False
        header.prop(self, "transfer_weights")
        if body is not None:
            body.active = self.transfer_weights
            body.prop(self, "overwrite_weights")

        header, body = layout.panel("MustardUI_AddOutfit_ShapeKeys", default_closed=True)
        header.use_property_split = False
        header.prop(self, "transfer_shape_keys")
        if body is not None:
            body.active = self.transfer_shape_keys
            # Full width, not in the property split column
            col = body.column(align=True)
            col.use_property_split = False
            col.template_list(
                "MUSTARDUI_UL_ModelToolkit_UIList_AddOutfit_ShapeKeys",
                "",
                wm,
                "MustardUI_ModelToolkit_AddOutfit_ShapeKeys",
                wm,
                "MustardUI_ModelToolkit_AddOutfit_ShapeKeyIndex",
                rows=6,
            )
            row = col.row(align=True)
            row.operator(
                "mustardui.model_toolkit_add_outfit_shape_keys_select",
                text="All",
                icon="CHECKBOX_HLT",
            ).use = True
            row.operator(
                "mustardui.model_toolkit_add_outfit_shape_keys_select",
                text="None",
                icon="CHECKBOX_DEHLT",
            ).use = False

            col = body.column()
            col.prop(self, "overwrite_shape_keys")
            col.prop(self, "link")
            col.separator()
            col.prop(self, "max_distance")
            col.prop(self, "smooth")
            col.prop(self, "threshold")

    def draw_extra(self, layout):
        """Draw the settings of the operator below the Outfit ones"""


class MustardUI_ModelToolkit_AddOutfit(AddOutfitSettings, bpy.types.Operator):
    """Add the selected Objects to the model as an Outfit, transferring weights and Shape Keys
    from the body and fitting them to it"""

    bl_idname = "mustardui.model_toolkit_add_outfit"
    bl_label = "Add Outfit"
    bl_options = {"UNDO"}

    fit: fit_property("MESH")

    @classmethod
    def poll(cls, context):
        if context.mode != "OBJECT":
            return False
        if not active_object_operator_poll(context, config=ModelMode.MODEL_TOOLKIT):
            return False
        return bool(add_outfit_pieces(context))

    def draw(self, context):
        self.draw_settings(context, add_outfit_pieces(context))

    def invoke(self, context, event):
        coll_name = add_outfit_fill_lists(context)
        if not self.outfit_name:
            arm, _, _ = add_outfit_model(context)
            model_name = arm.MustardUI_RigSettings.model_name if arm is not None else ""
            self.outfit_name = outfit_default_name(coll_name, model_name)

        return context.window_manager.invoke_props_dialog(self, width=400)

    def execute(self, context):
        wm = context.window_manager
        arm, arm_obj, body = add_outfit_model(context)
        rig_settings = arm.MustardUI_RigSettings

        if arm_obj is None or body is None:
            self.report({"ERROR"}, "MustardUI - The model has no Armature or Body")
            return {"CANCELLED"}

        pieces = add_outfit_pieces(context)
        named = pieces + add_outfit_children(pieces)
        names = {
            item.object_name: item.name.strip()
            for item in wm.MustardUI_ModelToolkit_AddOutfit_Items
        }
        # Default names when called from scripts
        if not all(o.name in names for o in named):
            names = {o.name: name for o, name in add_outfit_default_names(pieces).items()}
        if not all(names[o.name] for o in named):
            self.report({"ERROR"}, "MustardUI - Choose a name for all the pieces")
            return {"CANCELLED"}

        convention = rig_settings.model_MustardUI_naming_convention

        # Destination collections, with the new ones created at the end (.001 if duplicated)
        targets = []
        if self.destination == "NEW":
            if self.split:
                outfits = [
                    (outfit_default_name(c.name, rig_settings.model_name), group)
                    for c, group in add_outfit_groups(pieces).items()
                ]
            else:
                outfits = [(self.outfit_name.strip(), pieces)]
            for outfit_name, group in outfits:
                if not outfit_name:
                    self.report({"ERROR"}, "MustardUI - Choose a name for the Outfit")
                    return {"CANCELLED"}
                coll_name = (
                    f"{rig_settings.model_name} {outfit_name}" if convention else outfit_name
                )
                targets.append((coll_name, group))
        elif self.destination == "OUTFIT":
            if self.outfit not in outfit_search(self, context, ""):
                self.report({"ERROR"}, "MustardUI - Choose an Outfit")
                return {"CANCELLED"}
            targets.append((bpy.data.collections[self.outfit], pieces))
        else:
            collection = rig_settings.extras_collection
            if collection is None:
                self.report({"ERROR"}, "MustardUI - The model has no Extras collection")
                return {"CANCELLED"}
            targets.append((collection, pieces))

        keys = []
        body_sks = body.data.shape_keys
        if self.transfer_shape_keys and body_sks is not None and body_sks.use_relative:
            items = wm.MustardUI_ModelToolkit_AddOutfit_ShapeKeys
            key_names = {item.name for item in items if item.use}
            # All but the Outfits Shape Keys when called from scripts
            if not len(items):
                outfit_sks = outfit_shape_keys(arm, arm_obj, body)
                key_names = {sk.name for sk in body_sks.key_blocks if sk.name not in outfit_sks}
            keys = [
                sk
                for sk in body_sks.key_blocks
                if sk != body_sks.reference_key and sk.name in key_names
            ]

        steps = self.steps(context, pieces, names, keys, targets)
        self._backup = PiecesBackup(pieces)

        # Without a window (e.g. from scripts) all the steps are run at once
        if context.window is None or bpy.app.background:
            try:
                for _ in steps:
                    pass
            except Exception:
                self.rollback()
                raise
            self._backup.discard()
            return self.finish(context)

        self._steps = steps
        self._timer = context.window_manager.event_timer_add(0.01, window=context.window)
        context.window_manager.modal_handler_add(self)
        context.window.cursor_modal_set("WAIT")

        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if event.type == "ESC" and event.value == "PRESS":
            self.stop(context)
            self._backup.restore()
            self.report({"WARNING"}, "MustardUI - Add Outfit cancelled")
            return {"CANCELLED"}
        if event.type != "TIMER":
            return {"RUNNING_MODAL"}

        # Run the steps for a short time, then redraw the progress
        start = time.monotonic()
        try:
            while time.monotonic() - start < 0.1:
                factor, text = next(self._steps)
        except StopIteration:
            self.stop(context)
            self._backup.discard()
            return self.finish(context)
        except Exception:
            self.stop(context)
            self.rollback()
            raise

        status_progress(context, factor, f"Add Outfit: {text} (Esc to cancel)")

        return {"RUNNING_MODAL"}

    def rollback(self):
        # A failed restore must not hide the error of the step
        try:
            self._backup.restore()
        except Exception:
            traceback.print_exc()

    def stop(self, context):
        # Closing the steps restores the Fit to Body settings
        self._steps.close()
        context.window_manager.event_timer_remove(self._timer)
        context.window.cursor_modal_restore()
        context.workspace.status_text_set(None)

    def finish(self, context):
        count, name, fitted, weights, shape_keys, unbound = self.result
        print(
            f"MustardUI - Add Outfit: {fitted} pieces fitted, {weights} Vertex Groups and "
            f"{shape_keys} Shape Keys transferred"
        )
        message = f"MustardUI - {count} pieces added to '{name}'"
        if unbound:
            print("MustardUI - Modifiers not bound:\n  " + "\n  ".join(unbound))
            message += f", {len(unbound)} modifiers not bound (details in the console)"
        self.report({"WARNING"} if unbound else {"INFO"}, message)
        return {"FINISHED"}

    def steps(self, context, pieces, names, keys, targets):
        """Add the pieces with the model Nude, restoring the Outfit if not showing the new one"""

        arm, _, _ = add_outfit_model(context)
        rig_settings = arm.MustardUI_RigSettings
        previous = rig_settings.outfits_list
        nude = rig_settings.outfit_nude and previous not in ("", "Nude")
        if nude:
            rig_settings.outfits_list = "Nude"
        try:
            return (yield from self.add_steps(context, pieces, names, keys, targets))
        finally:
            if nude and rig_settings.outfits_list == "Nude":
                rig_settings.outfits_list = previous

    def add_steps(self, context, pieces, names, keys, targets):
        """Add the pieces, yielding the progress and the next step"""

        scene = context.scene
        arm, arm_obj, body = add_outfit_model(context)
        rig_settings = arm.MustardUI_RigSettings
        convention = rig_settings.model_MustardUI_naming_convention

        # Progress units, about the seconds of each step on a typical piece
        weights_unit = 0.9 if self.transfer_weights else 0.05
        keys_unit = 0.35 if keys else 0.0
        fit_unit = 5.0 if self.fit != "NONE" else 0.05
        total = (weights_unit + keys_unit + fit_unit) * len(pieces) + 0.5
        done = 0.0

        weights = 0
        for piece in pieces:
            yield done / total, f"{names[piece.name]} - Weights"
            bind_to_armature(piece, arm_obj)
            if self.transfer_weights:
                weights += transfer_weights(context, body, arm_obj, piece, self.overwrite_weights)
            done += weights_unit

        shape_keys = 0
        if keys:
            steps = transfer_shape_keys_steps(
                body,
                pieces,
                keys,
                max_distance=self.max_distance,
                smooth=self.smooth,
                threshold=self.threshold,
                overwrite=self.overwrite_shape_keys,
                link=self.link,
            )
            while True:
                try:
                    fraction = next(steps)
                except StopIteration as stop:
                    shape_keys = stop.value
                    break
                yield (done + fraction * keys_unit * len(pieces)) / total, "Shape Keys"
            done += keys_unit * len(pieces)

        # Fit after the Shape Keys, as the body is fitted with its current Shape Keys
        fitted = 0
        settings = context.window_manager.MustardUI_ModelToolkit_FitToBodySettings
        key_name = f"Fit to Body - {body.name}"
        # Default settings, not the ones changed in the Fit to Body tool
        overrides = {
            name: settings.bl_rna.properties[name].default for name in settings.__annotations__
        }
        overrides["smooth_distance"] = self.fit_smooth
        stored = {name: getattr(settings, name) for name in overrides}
        for name, value in overrides.items():
            setattr(settings, name, value)
        try:
            for piece in pieces:
                yield done / total, f"{names[piece.name]} - Fit to Body"
                done += fit_unit
                if self.fit == "NONE":
                    continue
                solver = FitToBodySolver(piece, [body], key_name)
                shape_co, count, error = solver.solve(context, settings)
                if error or not count:
                    continue
                if self.fit == "MESH":
                    fit_to_body_apply_to_mesh(piece, shape_co - solver.target.basis)
                    fit_to_body_apply_to_children(solver, settings)
                else:
                    sk = write_shape_key(piece, key_name, shape_co)
                    create_followers_shape_keys(solver, settings, piece, sk.name)
                fitted += 1
        finally:
            for name, value in stored.items():
                setattr(settings, name, value)

        # Before moving the pieces, as hidden collections are not evaluated
        unbound = []
        if self.rebind:
            yield done / total, "Rebinding Modifiers"
            unbound = rebind_modifiers(context, pieces + add_outfit_children(pieces), arm_obj)

        yield done / total, "Adding to MustardUI"
        # Next to the other Outfits
        outfits = [x.collection for x in rig_settings.outfits_collections if x.collection]
        candidates = [scene.collection, *bpy.data.collections]
        parent = next((c for c in candidates if outfits and outfits[0].name in c.children), None)
        collections = []
        for target, group in targets:
            collection = target
            if isinstance(target, str):
                collection = bpy.data.collections.new(target)
                (parent or arm_obj.users_collection[0]).children.link(collection)
            collections.append((collection, group))

        # Move the pieces with their children and own parents (e.g. armatures of wings),
        # storing where they are moved from and to
        old_collections = {}
        moved = {}
        for collection, group in collections:
            own_parents = [
                p
                for piece in group
                for p in itertools.takewhile(lambda p: p != arm_obj, parents(piece))
                if set(p.users_collection) & set(piece.users_collection)
            ]
            for obj in group + [c for p in group for c in p.children_recursive] + own_parents:
                if obj in moved:
                    continue
                moved[obj] = collection
                for coll in obj.users_collection:
                    if coll != collection:
                        coll.objects.unlink(obj)
                        old_collections.setdefault(coll, collection)
                if collection not in obj.users_collection:
                    collection.objects.link(obj)

        empty = {
            c
            for c in old_collections
            if c != scene.collection and not c.all_objects and not c.children
        }

        # Outfit custom properties follow their piece, or their emptied collection
        registered = set(outfits_get_collections(rig_settings))
        for cp in arm.MustardUI_CustomPropertiesOutfit:
            if cp.outfit_piece in moved:
                cp.outfit = moved[cp.outfit_piece]
            elif cp.outfit in empty and cp.outfit not in registered:
                cp.outfit = old_collections[cp.outfit]

        # Remove the collections left empty, unless used by other than their parents
        for coll, users in bpy.data.user_map(subset=empty).items():
            if all(isinstance(u, (bpy.types.Collection, bpy.types.Scene)) for u in users):
                bpy.data.collections.remove(coll)

        # Lowest free number suffix, now that the emptied collections are removed
        for (collection, _), (target, _) in zip(collections, targets, strict=True):
            if isinstance(target, str) and collection.name != target:
                collection.name = target

        if self.rename:
            new_names = [
                (obj, collection, names[obj.name])
                for collection, group in collections
                for obj in group + add_outfit_children(group)
            ]
            refs = custom_property_refs(arm)
            for obj, collection, name in new_names:
                obj.name = f"{collection.name} - {name}" if convention else name
                rename_object(obj)
            update_custom_property_paths(refs)

        # Modifiers after the Armature, following the global Outfit options
        modifiers = (
            ("CORRECTIVE_SMOOTH", "CorrectiveSmooth", self.add_smooth, {"ARMATURE"}),
            ("SHRINKWRAP", "Shrinkwrap", self.add_shrinkwrap, {"ARMATURE", "CORRECTIVE_SMOOTH"}),
        )
        for piece in pieces:
            for mod_type, name, add, before in modifiers:
                if not add or any(m.type == mod_type for m in piece.modifiers):
                    continue
                index = max(
                    (i for i, m in enumerate(piece.modifiers) if m.type in before), default=-1
                )
                mod = piece.modifiers.new(name=name, type=mod_type)
                if mod_type == "SHRINKWRAP":
                    mod.target = body
                    mod.wrap_mode = "OUTSIDE"
                    mod.offset = 0.001
                option = "smoothcorrection" if mod_type == "CORRECTIVE_SMOOTH" else "shrinkwrap"
                if getattr(rig_settings, f"outfits_enable_global_{option}"):
                    visible = getattr(rig_settings, f"outfits_global_{option}")
                    mod.show_viewport = mod.show_render = visible
                move_modifier(piece, mod, index + 1)

        if self.destination == "NEW":
            for collection, _ in collections:
                rig_settings.outfits_collections.add().collection = collection

        # Show the outfit in User mode
        if arm.MustardUI_enable and self.destination != "EXTRAS":
            rig_settings.outfits_list = collections[0][0].name

        coll_names = "', '".join(c.name for c, _ in collections)
        self.result = (len(pieces), coll_names, fitted, weights, shape_keys, unbound)
        # The pieces list is only needed by the dialog
        context.window_manager.MustardUI_ModelToolkit_AddOutfit_Items.clear()


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_AddOutfit_Item)
    bpy.utils.register_class(MUSTARDUI_UL_ModelToolkit_UIList_AddOutfit)
    bpy.utils.register_class(MustardUI_ModelToolkit_AddOutfit_ShapeKey)
    bpy.utils.register_class(MUSTARDUI_UL_ModelToolkit_UIList_AddOutfit_ShapeKeys)
    bpy.utils.register_class(MustardUI_ModelToolkit_AddOutfit_ShapeKeysSelect)
    bpy.utils.register_class(MustardUI_ModelToolkit_AddOutfit)

    bpy.types.WindowManager.MustardUI_ModelToolkit_AddOutfit_Items = bpy.props.CollectionProperty(
        type=MustardUI_ModelToolkit_AddOutfit_Item
    )
    bpy.types.WindowManager.MustardUI_ModelToolkit_AddOutfit_ItemIndex = bpy.props.IntProperty(
        default=0, name=""
    )
    bpy.types.WindowManager.MustardUI_ModelToolkit_AddOutfit_ShapeKeys = (
        bpy.props.CollectionProperty(type=MustardUI_ModelToolkit_AddOutfit_ShapeKey)
    )
    bpy.types.WindowManager.MustardUI_ModelToolkit_AddOutfit_ShapeKeyIndex = bpy.props.IntProperty(
        default=0, name=""
    )


def unregister():
    del bpy.types.WindowManager.MustardUI_ModelToolkit_AddOutfit_ShapeKeyIndex
    del bpy.types.WindowManager.MustardUI_ModelToolkit_AddOutfit_ShapeKeys
    del bpy.types.WindowManager.MustardUI_ModelToolkit_AddOutfit_ItemIndex
    del bpy.types.WindowManager.MustardUI_ModelToolkit_AddOutfit_Items

    bpy.utils.unregister_class(MustardUI_ModelToolkit_AddOutfit)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_AddOutfit_ShapeKeysSelect)
    bpy.utils.unregister_class(MUSTARDUI_UL_ModelToolkit_UIList_AddOutfit_ShapeKeys)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_AddOutfit_ShapeKey)
    bpy.utils.unregister_class(MUSTARDUI_UL_ModelToolkit_UIList_AddOutfit)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_AddOutfit_Item)
