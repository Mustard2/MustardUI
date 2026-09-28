import re
import time

import bpy
import numpy as np

from ...misc.mesh_deform import mesh_triangles
from ...misc.ui_progress import status_progress
from ...model_selection.active_object import (
    ModelMode,
    active_object_operator_poll,
    mustardui_active_object,
)
from ...outfits.helper_functions import outfits_get_collections
from ..mesh.ops_fit_to_body import (
    FitToBodySolver,
    fit_to_body_apply_to_children,
    fit_to_body_apply_to_mesh,
)
from ..mesh.ops_transfer_shape_keys import (
    mesh_rest_coordinates,
    transfer_mapping,
    transfer_shape_keys_steps,
)
from ..mesh.shape_key_preview import create_followers_shape_keys, write_shape_key
from .ops_naming import rename_object

# Weights below this are not written
WEIGHT_THRESHOLD = 0.0001


class MustardUI_ToolsCreators_AddOutfit_Item(bpy.types.PropertyGroup):
    object_name: bpy.props.StringProperty(name="Object")
    name: bpy.props.StringProperty(name="Piece Name", description="Name of the outfit piece")
    child: bpy.props.BoolProperty(name="Child", description="Object parented to a piece")


class MUSTARDUI_UL_ToolsCreators_UIList_AddOutfit(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        icon = "LINKED" if item.child else "OUTLINER_OB_MESH"
        row.prop(item, "name", text="", emboss=False, icon=icon)
        row.label(text=item.object_name)


class MustardUI_ToolsCreators_AddOutfit_ShapeKey(bpy.types.PropertyGroup):
    use: bpy.props.BoolProperty(name="Transfer", default=True)
    outfit: bpy.props.BoolProperty(name="Outfit Shape Key")


class MUSTARDUI_UL_ToolsCreators_UIList_AddOutfit_ShapeKeys(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.prop(item, "use", text="")
        row.label(text=item.name, icon="MOD_CLOTH" if item.outfit else "SHAPEKEY_DATA")


class MustardUI_ToolsCreators_AddOutfit_ShapeKeysSelect(bpy.types.Operator):
    """Select or deselect all the Shape Keys in the list"""

    bl_idname = "mustardui.tools_creators_add_outfit_shape_keys_select"
    bl_label = "Select Shape Keys"

    use: bpy.props.BoolProperty(default=True)

    def execute(self, context):
        for item in context.window_manager.MustardUI_ToolsCreators_AddOutfit_ShapeKeys:
            item.use = self.use
        return {"FINISHED"}


def add_outfit_model(context):
    """Armature data, armature object and body of the model"""

    _, arm = mustardui_active_object(context, config=ModelMode.MODEL_TOOLKIT)
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


def add_outfit_default_names(pieces):
    """Default names of the pieces and of their children, named after the piece"""

    names = dict(zip(pieces, piece_default_names([o.name for o in pieces]), strict=True))
    for child in add_outfit_children(pieces):
        piece = next(p for p in parents(child) if p in names)
        own = [w for w in piece_default_names([child.name])[0].split() if w not in piece.name]
        names[child] = " ".join([names[piece], *own])
    return names


# Keep the Enum strings alive, as Blender does not store them
OUTFIT_ITEMS = []


def outfit_items(self, context):
    arm, _, _ = add_outfit_model(context)
    collections = []
    if arm is not None:
        collections = [
            x.collection
            for x in arm.MustardUI_RigSettings.outfits_collections
            if x.collection is not None
        ]
    OUTFIT_ITEMS[:] = [(c.name, c.name, "") for c in collections] or [
        ("NONE", "None", "No Outfit available")
    ]
    return OUTFIT_ITEMS


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


def transfer_weights(body, armature, target, overwrite):
    """Transfer the weights of the deform bones from the body, returning the number of
    Vertex Groups written"""

    bones = {b.name for b in armature.data.bones if b.use_deform}
    names = [vg.name for vg in body.vertex_groups if vg.name in bones]
    if not names or not len(target.data.vertices):
        return 0

    # Weights of the body for each vertex and Vertex Group
    columns = {body.vertex_groups[n].index: k for k, n in enumerate(names)}
    body_weights = np.zeros((len(body.data.vertices), len(names)))
    for v in body.data.vertices:
        for g in v.groups:
            k = columns.get(g.group)
            if k is not None:
                body_weights[v.index, k] = g.weight

    world = []
    for obj in (body, target):
        mat = np.array(obj.matrix_world, dtype=np.float64)
        world.append(mesh_rest_coordinates(obj) @ mat[:3, :3].T + mat[:3, 3])
    indices, bary = transfer_mapping(world[0], mesh_triangles(body.data), world[1], "SURFACE", 0.0)

    if overwrite:
        for vg in [vg for vg in target.vertex_groups if vg.name in bones]:
            target.vertex_groups.remove(vg)

    written = 0
    for k in np.nonzero(body_weights[np.unique(indices)].any(axis=0))[0]:
        name = names[k]
        if name in target.vertex_groups:
            continue

        values = np.einsum("ij,ij->i", bary, body_weights[indices, k])
        verts = np.nonzero(values > WEIGHT_THRESHOLD)[0]
        if not len(verts):
            continue

        vg = target.vertex_groups.new(name=name)
        for i in verts:
            vg.add([int(i)], float(values[i]), "REPLACE")
        written += 1

    return written


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
        with bpy.context.temp_override(object=obj):
            bpy.ops.object.modifier_move_to_index(modifier=mod.name, index=0)


def add_outfit_fill_lists(context):
    """Fill the pieces and Shape Keys lists, returning the name of the collection of the
    pieces"""

    wm = context.window_manager
    pieces = add_outfit_pieces(context)
    items = wm.MustardUI_ToolsCreators_AddOutfit_Items

    items.clear()
    for obj, name in add_outfit_default_names(pieces).items():
        item = items.add()
        item.object_name = obj.name
        item.name = name
        item.child = obj not in pieces
    wm.MustardUI_ToolsCreators_AddOutfit_ItemIndex = 0

    # Keep the previous choices, skipping the Outfits Shape Keys by default
    arm, arm_obj, body = add_outfit_model(context)
    sk_items = wm.MustardUI_ToolsCreators_AddOutfit_ShapeKeys
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
    wm.MustardUI_ToolsCreators_AddOutfit_ShapeKeyIndex = 0

    colls = {c for o in pieces for c in o.users_collection}
    return colls.pop().name if len(colls) == 1 else ""


class MustardUI_ToolsCreators_AddOutfit(bpy.types.Operator):
    """Add the selected Objects to the model as an Outfit, transferring weights and Shape Keys
    from the body and fitting them to it"""

    bl_idname = "mustardui.tools_creators_add_outfit"
    bl_label = "Add Outfit"
    bl_options = {"UNDO"}

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
    )

    outfit: bpy.props.EnumProperty(name="Outfit", items=outfit_items)

    rename: bpy.props.BoolProperty(
        name="Rename Objects",
        default=True,
        description="Rename the Objects and their data with the piece names",
    )

    fit: bpy.props.EnumProperty(
        name="Fit to Body",
        items=(
            ("NONE", "None", "Do not fit the pieces to the body"),
            ("SHAPE_KEY", "Shape Key", "Fit the pieces clipping through the body with a Shape Key"),
            ("MESH", "Mesh", "Fit the pieces clipping through the body, applying it to the mesh"),
        ),
        default="MESH",
        description="Fit the pieces clipping through the body, with the default settings of the "
        "Fit to Body tool.\nPieces not clipping are not changed",
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
        description="Overwrite the Shape Keys already on the pieces.\nIf disabled, they are "
        "skipped",
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

    @classmethod
    def poll(cls, context):
        if context.mode != "OBJECT":
            return False
        if not active_object_operator_poll(context, config=ModelMode.MODEL_TOOLKIT):
            return False
        return bool(add_outfit_pieces(context))

    def draw(self, context):
        wm = context.window_manager
        layout = self.layout

        col = layout.column()
        col.use_property_split = True
        col.use_property_decorate = False
        col.prop(self, "destination")
        if self.destination == "NEW":
            col.prop(self, "outfit_name")
        elif self.destination == "OUTFIT":
            col.prop(self, "outfit")

        layout.template_list(
            "MUSTARDUI_UL_ToolsCreators_UIList_AddOutfit",
            "",
            wm,
            "MustardUI_ToolsCreators_AddOutfit_Items",
            wm,
            "MustardUI_ToolsCreators_AddOutfit_ItemIndex",
            rows=4,
        )
        col = layout.column()
        col.use_property_split = True
        col.use_property_decorate = False
        col.prop(self, "rename")

        box = layout.box()
        col = box.column()
        col.use_property_split = True
        col.use_property_decorate = False
        col.prop(self, "fit")
        row = col.row()
        row.enabled = self.fit != "NONE"
        row.prop(self, "fit_smooth")

        box = layout.box()
        col = box.column(heading="Add Modifiers")
        col.use_property_split = True
        col.use_property_decorate = False
        col.prop(self, "add_smooth")
        col.prop(self, "add_shrinkwrap")

        box = layout.box()
        col = box.column()
        col.use_property_split = True
        col.use_property_decorate = False
        col.prop(self, "transfer_weights")
        row = col.row()
        row.enabled = self.transfer_weights
        row.prop(self, "overwrite_weights")

        box = layout.box()
        col = box.column()
        col.use_property_split = True
        col.use_property_decorate = False
        col.prop(self, "transfer_shape_keys")
        col = col.column()
        col.enabled = self.transfer_shape_keys
        col.template_list(
            "MUSTARDUI_UL_ToolsCreators_UIList_AddOutfit_ShapeKeys",
            "",
            wm,
            "MustardUI_ToolsCreators_AddOutfit_ShapeKeys",
            wm,
            "MustardUI_ToolsCreators_AddOutfit_ShapeKeyIndex",
            rows=6,
        )
        row = col.row(align=True)
        row.operator(
            "mustardui.tools_creators_add_outfit_shape_keys_select",
            text="All",
            icon="CHECKBOX_HLT",
        ).use = True
        row.operator(
            "mustardui.tools_creators_add_outfit_shape_keys_select",
            text="None",
            icon="CHECKBOX_DEHLT",
        ).use = False
        col.prop(self, "overwrite_shape_keys")
        col.prop(self, "link")
        col.prop(self, "max_distance")
        col.prop(self, "smooth")
        col.prop(self, "threshold")

    def invoke(self, context, event):
        coll_name = add_outfit_fill_lists(context)
        if not self.outfit_name:
            self.outfit_name = coll_name

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
            for item in wm.MustardUI_ToolsCreators_AddOutfit_Items
        }
        # Default names when called from scripts
        if not all(o.name in names for o in named):
            names = {o.name: name for o, name in add_outfit_default_names(pieces).items()}
        if not all(names[o.name] for o in named):
            self.report({"ERROR"}, "MustardUI - Choose a name for all the pieces")
            return {"CANCELLED"}

        convention = rig_settings.model_MustardUI_naming_convention

        # Destination collection
        collection = None
        if self.destination == "NEW":
            outfit_name = self.outfit_name.strip()
            if not outfit_name:
                self.report({"ERROR"}, "MustardUI - Choose a name for the Outfit")
                return {"CANCELLED"}
            coll_name = f"{rig_settings.model_name} {outfit_name}" if convention else outfit_name
            if coll_name in bpy.data.collections:
                self.report({"ERROR"}, f"MustardUI - Collection '{coll_name}' already exists")
                return {"CANCELLED"}
        elif self.destination == "OUTFIT":
            collection = bpy.data.collections.get(self.outfit)
            if collection is None:
                self.report({"ERROR"}, "MustardUI - Choose an Outfit")
                return {"CANCELLED"}
        else:
            collection = rig_settings.extras_collection
            if collection is None:
                self.report({"ERROR"}, "MustardUI - The model has no Extras collection")
                return {"CANCELLED"}

        keys = []
        body_sks = body.data.shape_keys
        if self.transfer_shape_keys and body_sks is not None and body_sks.use_relative:
            items = wm.MustardUI_ToolsCreators_AddOutfit_ShapeKeys
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

        steps = self.steps(context, pieces, named, names, keys, collection)

        # Without a window (e.g. from scripts) all the steps are run at once
        if context.window is None or bpy.app.background:
            for _ in steps:
                pass
            return self.finish(context)

        self._steps = steps
        self._timer = context.window_manager.event_timer_add(0.01, window=context.window)
        context.window_manager.modal_handler_add(self)
        context.window.cursor_modal_set("WAIT")
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if event.type != "TIMER":
            return {"RUNNING_MODAL"}

        # Run the steps for a short time, then redraw the progress
        start = time.monotonic()
        try:
            while time.monotonic() - start < 0.1:
                factor, text = next(self._steps)
        except StopIteration:
            self.stop(context)
            return self.finish(context)
        except Exception:
            self.stop(context)
            raise

        status_progress(context, factor, f"Add Outfit: {text}")
        return {"RUNNING_MODAL"}

    def stop(self, context):
        context.window_manager.event_timer_remove(self._timer)
        context.window.cursor_modal_restore()
        context.workspace.status_text_set(None)

    def finish(self, context):
        self.report(
            {"INFO"},
            f"MustardUI - {self.result[0]} pieces added to '{self.result[1]}': "
            f"{self.result[2]} fitted, {self.result[3]} Vertex Groups and {self.result[4]} Shape "
            "Keys transferred",
        )
        return {"FINISHED"}

    def steps(self, context, pieces, named, names, keys, collection):
        """Add the pieces, yielding the progress and the next step"""

        scene = context.scene
        arm, arm_obj, body = add_outfit_model(context)
        rig_settings = arm.MustardUI_RigSettings
        convention = rig_settings.model_MustardUI_naming_convention

        # Progress units, roughly proportional to the time of each step
        total = 0.2 * len(pieces) + (len(pieces) if keys else 0) + len(pieces) + 0.2
        done = 0.0

        weights = 0
        for piece in pieces:
            yield done / total, f"{names[piece.name]} - Weights"
            bind_to_armature(piece, arm_obj)
            if self.transfer_weights:
                weights += transfer_weights(body, arm_obj, piece, self.overwrite_weights)
            done += 0.2

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
                yield (done + fraction * len(pieces)) / total, "Shape Keys"
            done += len(pieces)

        # Fit after the Shape Keys, as the body is fitted with its current Shape Keys
        fitted = 0
        settings = context.window_manager.MustardUI_ToolsCreators_FitToBodySettings
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
                done += 1
                if self.fit == "NONE":
                    continue
                solver = FitToBodySolver(context, piece, [body], key_name)
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

        yield done / total, "Adding to MustardUI"
        if collection is None:
            outfit_name = self.outfit_name.strip()
            coll_name = f"{rig_settings.model_name} {outfit_name}" if convention else outfit_name
            collection = bpy.data.collections.new(coll_name)
            # Next to the other Outfits
            outfits = [x.collection for x in rig_settings.outfits_collections if x.collection]
            parents = [scene.collection, *bpy.data.collections]
            parent = next((c for c in parents if outfits and outfits[0].name in c.children), None)
            (parent or arm_obj.users_collection[0]).children.link(collection)

        # Move the pieces with their children
        old_collections = set()
        moved = set()
        for obj in pieces + [c for p in pieces for c in p.children_recursive]:
            if obj in moved:
                continue
            moved.add(obj)
            for coll in obj.users_collection:
                if coll != collection:
                    coll.objects.unlink(obj)
                    old_collections.add(coll)
            if collection not in obj.users_collection:
                collection.objects.link(obj)

        # Remove the collections left empty
        for coll in old_collections:
            if coll != scene.collection and not coll.all_objects and not coll.children:
                bpy.data.collections.remove(coll)

        if self.rename:
            new_names = {obj: names[obj.name] for obj in named}
            for obj, name in new_names.items():
                obj.name = f"{collection.name} - {name}" if convention else name
                rename_object(obj)

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
                with context.temp_override(object=piece):
                    bpy.ops.object.modifier_move_to_index(modifier=mod.name, index=index + 1)

        if self.destination == "NEW":
            rig_settings.outfits_collections.add().collection = collection

        # Show the outfit in User mode
        if arm.MustardUI_enable and self.destination != "EXTRAS":
            rig_settings.outfits_list = collection.name

        self.result = (len(pieces), collection.name, fitted, weights, shape_keys)
        # The pieces list is only needed by the dialog
        context.window_manager.MustardUI_ToolsCreators_AddOutfit_Items.clear()


def register():
    bpy.utils.register_class(MustardUI_ToolsCreators_AddOutfit_Item)
    bpy.utils.register_class(MUSTARDUI_UL_ToolsCreators_UIList_AddOutfit)
    bpy.utils.register_class(MustardUI_ToolsCreators_AddOutfit_ShapeKey)
    bpy.utils.register_class(MUSTARDUI_UL_ToolsCreators_UIList_AddOutfit_ShapeKeys)
    bpy.utils.register_class(MustardUI_ToolsCreators_AddOutfit_ShapeKeysSelect)
    bpy.utils.register_class(MustardUI_ToolsCreators_AddOutfit)

    bpy.types.WindowManager.MustardUI_ToolsCreators_AddOutfit_Items = bpy.props.CollectionProperty(
        type=MustardUI_ToolsCreators_AddOutfit_Item
    )
    bpy.types.WindowManager.MustardUI_ToolsCreators_AddOutfit_ItemIndex = bpy.props.IntProperty(
        default=0, name=""
    )
    bpy.types.WindowManager.MustardUI_ToolsCreators_AddOutfit_ShapeKeys = (
        bpy.props.CollectionProperty(type=MustardUI_ToolsCreators_AddOutfit_ShapeKey)
    )
    bpy.types.WindowManager.MustardUI_ToolsCreators_AddOutfit_ShapeKeyIndex = bpy.props.IntProperty(
        default=0, name=""
    )


def unregister():
    del bpy.types.WindowManager.MustardUI_ToolsCreators_AddOutfit_ShapeKeyIndex
    del bpy.types.WindowManager.MustardUI_ToolsCreators_AddOutfit_ShapeKeys
    del bpy.types.WindowManager.MustardUI_ToolsCreators_AddOutfit_ItemIndex
    del bpy.types.WindowManager.MustardUI_ToolsCreators_AddOutfit_Items

    bpy.utils.unregister_class(MustardUI_ToolsCreators_AddOutfit)
    bpy.utils.unregister_class(MustardUI_ToolsCreators_AddOutfit_ShapeKeysSelect)
    bpy.utils.unregister_class(MUSTARDUI_UL_ToolsCreators_UIList_AddOutfit_ShapeKeys)
    bpy.utils.unregister_class(MustardUI_ToolsCreators_AddOutfit_ShapeKey)
    bpy.utils.unregister_class(MUSTARDUI_UL_ToolsCreators_UIList_AddOutfit)
    bpy.utils.unregister_class(MustardUI_ToolsCreators_AddOutfit_Item)
