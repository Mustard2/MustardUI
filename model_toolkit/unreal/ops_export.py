import json
import os
import re
import subprocess
import tempfile

import bpy
from bpy_extras.io_utils import ExportHelper

from ...misc.outfits import outfits_get_collection_items
from ...model_selection.active_object import ModelMode, mustardui_active_object
from ...morphs.misc import get_cp_source
from ...outfits.helper_functions import outfits_get_collections
from . import morph_targets

WORKER = os.path.join(os.path.dirname(__file__), "worker.py")


def mhx_rig(context):
    """The MHX armature object of the model, or None."""
    _, arm = mustardui_active_object(context, config=ModelMode.ANY)
    if arm is None:
        return None
    rig = next((o for o in bpy.data.objects if o.data is arm), None)
    return rig if rig is not None and rig.get("MhxRig") else None


def bound_meshes(rig):
    """Meshes deformed by the rig."""
    return [
        o
        for o in bpy.data.objects
        if o.type == "MESH" and any(m.type == "ARMATURE" and m.object is rig for m in o.modifiers)
    ]


def collection_label(rig_settings, collection):
    """Name of an outfit or hair collection in the UI."""
    label = collection.name
    if rig_settings.model_MustardUI_naming_convention:
        label = label.removeprefix(rig_settings.model_name + " ")
    return re.sub(r"\.\d{3}$", "", label)


def outfit_pieces(rig):
    """Pieces of the Outfits and Extras of the model deformed by the rig, as
    (piece, name in the UI, outfit name in the UI)."""
    rig_settings = rig.data.MustardUI_RigSettings
    bound = set(bound_meshes(rig))
    pieces, seen = [], set()
    for collection in outfits_get_collections(rig_settings):
        outfit = collection_label(rig_settings, collection)
        for obj in outfits_get_collection_items(rig_settings, collection):
            if obj in bound and obj not in seen:
                seen.add(obj)
                name = obj.name.removeprefix(collection.name + " - ")
                pieces.append((obj, name, outfit))
    return pieces


def grows_hair(obj):
    """Meshes with particle hair, which FBX can not carry."""
    return any(
        m.type == "PARTICLE_SYSTEM" and m.particle_system.settings.type == "HAIR"
        for m in obj.modifiers
    )


def hair_pieces(rig):
    """Mesh hair of the model, as (object, name in the UI, collection name in the UI).
    Meshes growing particle hair are left out."""
    rig_settings = rig.data.MustardUI_RigSettings
    pieces, seen = [], set()
    for collection in (rig_settings.hair_collection, rig_settings.hair_extras_collection):
        if collection is None:
            continue
        label = collection_label(rig_settings, collection)
        for obj in collection.all_objects:
            if obj.type == "MESH" and obj not in seen and not grows_hair(obj):
                seen.add(obj)
                pieces.append((obj, obj.name.removeprefix(collection.name + " - "), label))
    return pieces


def exportable_meshes(rig):
    """Meshes Export Character can export: the outfit pieces, the mesh hair, and the other
    visible meshes."""
    pieces = {obj for obj, _, _ in outfit_pieces(rig)}
    hair = [obj for obj, _, _ in hair_pieces(rig)]
    bound = [o for o in bound_meshes(rig) if o in pieces or o.visible_get()]
    return bound + [o for o in hair if o not in bound]


def model_morphs(arm):
    """MustardUI morphs of the model, as (section, morph)."""
    return [(s, m) for s in arm.MustardUI_MorphsSettings.sections for m in s.morphs]


def morph_target_names(arm):
    """MustardUI morphs of the model, as (section, morph, name of the morph target).
    Unreal needs unique names, so repeated ones get their section. The names do not depend on
    the morphs chosen, so animations exported later find the same names"""
    result, names = [], set()
    for section, morph in model_morphs(arm):
        name = morph.name if morph.name not in names else f"{morph.name} ({section.name})"
        names.add(name)
        result.append((section, morph, name))
    return result


# Collections of bpy.data holding the owners of morph values
DATA_COLLECTIONS = {
    "OBJECT": "objects",
    "ARMATURE": "armatures",
    "MESH": "meshes",
    "KEY": "shape_keys",
}

# Lists of Export Character: (kind, collection of the window manager, label, icon)
EXPORT_LISTS = (
    ("outfits", "MustardUI_UnrealTools_Outfits", "Outfits", "MOD_CLOTH"),
    ("hair", "MustardUI_UnrealTools_Hair", "Hair", "OUTLINER_OB_CURVES"),
    ("shape_keys", "MustardUI_UnrealTools_ShapeKeys", "Shape Keys", "SHAPEKEY_DATA"),
    ("face_controls", "MustardUI_UnrealTools_FaceControls", "Face Controls", "BONE_DATA"),
    ("morphs", "MustardUI_UnrealTools_Morphs", "Morphs", "PROPERTIES"),
)
LIST_COLLECTIONS = {kind: collection for kind, collection, _, _ in EXPORT_LISTS}


class MustardUI_UnrealTools_ExportItem(bpy.types.PropertyGroup):
    use: bpy.props.BoolProperty(name="Export", description="Export as a morph target")
    # Shape key name, face control property, or section and path of the morph
    key: bpy.props.StringProperty()
    section: bpy.props.StringProperty()


def update_export_items(context):
    """Fill the lists of Export Character with the outfit pieces and morph targets of the model.
    Choices made before are kept. New outfit pieces are exported if visible, and new morph
    targets always"""
    wm = context.window_manager
    rig = mhx_rig(context)
    shape_keys = morph_targets.exported_shape_keys(exportable_meshes(rig))
    # Lists of (key, name, section, exported by default)
    sources = {
        "outfits": [(o.name, n, outfit, o.visible_get()) for o, n, outfit in outfit_pieces(rig)],
        "hair": [(o.name, n, label, o.visible_get()) for o, n, label in hair_pieces(rig)],
        "shape_keys": [(n, n, "", True) for n in shape_keys],
        "face_controls": [(n, n, "", True) for n in morph_targets.face_controls(rig)],
        "morphs": [
            (f"{section.name}/{morph.path}", morph.name, section.name, True)
            for section, morph in model_morphs(rig.data)
        ],
    }
    for kind, collection in LIST_COLLECTIONS.items():
        items = getattr(wm, collection)
        previous = {item.key: item.use for item in items}
        items.clear()
        for key, name, section, default in sources[kind]:
            item = items.add()
            item.key, item.name, item.section = key, name, section
            item.use = previous.get(key, default)
        setattr(wm, collection + "Index", 0)


class MUSTARDUI_UL_UnrealTools_Export(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.prop(item, "use", text="")
        row.label(text=item.name)
        if item.section:
            sub = row.row()
            sub.alignment = "RIGHT"
            sub.enabled = False
            sub.label(text=item.section)

    def draw_filter(self, context, layout):
        layout.prop(self, "filter_name", text="", icon="VIEWZOOM")

    # The search matches the name, or the section of the morphs
    def filter_items(self, context, data, propname):
        text = self.filter_name.lower()
        flags = [
            self.bitflag_filter_item
            if text in item.name.lower() or text in item.section.lower()
            else 0
            for item in getattr(data, propname)
        ]
        return flags, []


class MustardUI_UnrealTools_ExportSelect(bpy.types.Operator):
    """Select or deselect all the items of the list"""

    bl_idname = "mustardui.unreal_tools_export_select"
    bl_label = "Select Morph Targets"
    bl_options = {"INTERNAL"}

    kind: bpy.props.EnumProperty(
        items=[(kind, label, "") for kind, _, label, _ in EXPORT_LISTS], options={"HIDDEN"}
    )
    use: bpy.props.BoolProperty(default=True)

    def execute(self, context):
        for item in getattr(context.window_manager, LIST_COLLECTIONS[self.kind]):
            item.use = self.use
        return {"FINISHED"}


def image_paths():
    """Absolute paths of the image files, by image."""
    return {
        image.name_full: os.path.normpath(bpy.path.abspath(image.filepath, library=image.library))
        for image in bpy.data.images
        if image.filepath
    }


class ExportToUnreal(ExportHelper):
    """Runs the export in a background Blender, working on a copy of the file."""

    bl_options = {"REGISTER"}
    filename_ext = ".fbx"
    filter_glob: bpy.props.StringProperty(default="*.fbx", options={"HIDDEN"})

    @classmethod
    def poll(cls, context):
        if mhx_rig(context) is None:
            cls.poll_message_set("Only available for MHX armatures")
            return False
        return True

    def settings(self, context):
        return {}

    def execute(self, context):
        self.folder = tempfile.TemporaryDirectory(prefix="mustardui_unreal_")
        blend = os.path.join(self.folder.name, "scene.blend")
        bpy.ops.wm.save_as_mainfile(filepath=blend, copy=True, check_existing=False)
        self.result = os.path.join(self.folder.name, "result.json")
        path = os.path.join(self.folder.name, "settings.json")
        with open(path, "w") as file:
            json.dump(
                {
                    "rig": mhx_rig(context).name,
                    # Hair armatures add bones, so characters and animations need the hair
                    "hair_meshes": [obj.name for obj, _, _ in hair_pieces(mhx_rig(context))],
                    # Saving the copy can change relative paths, so the files are given here
                    "images": image_paths(),
                    "filepath": bpy.path.abspath(self.filepath),
                    "result": self.result,
                    **self.settings(context),
                },
                file,
            )
        self.log = open(os.path.join(self.folder.name, "log.txt"), "w+")
        self.process = subprocess.Popen(
            [
                bpy.app.binary_path,
                "--background",
                blend,
                "--factory-startup",
                "--disable-autoexec",
                "--python-exit-code",
                "1",
                "--python",
                WORKER,
                "--",
                path,
            ],
            stdout=self.log,
            stderr=subprocess.STDOUT,
        )
        if bpy.app.background:
            self.process.wait()
            return self.finish(context)
        self.timer = context.window_manager.event_timer_add(0.5, window=context.window)
        context.window_manager.modal_handler_add(self)
        context.workspace.status_text_set(
            "MustardUI - Exporting to Unreal in the background, Esc to cancel"
        )
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if event.type == "ESC" and event.value == "PRESS":
            self.process.kill()
            self.process.wait()
            self.report({"WARNING"}, "MustardUI - Export to Unreal cancelled")
            self.cleanup(context)
            return {"CANCELLED"}
        if event.type != "TIMER" or self.process.poll() is None:
            return {"PASS_THROUGH"}
        self.cleanup(context, keep_folder=True)
        return self.finish(context)

    def cleanup(self, context, keep_folder=False):
        context.window_manager.event_timer_remove(self.timer)
        context.workspace.status_text_set(None)
        if not keep_folder:
            self.log.close()
            self.folder.cleanup()

    def finish(self, context):
        self.log.seek(0)
        output = self.log.read()
        self.log.close()
        info = json.load(open(self.result)) if os.path.exists(self.result) else {}
        self.folder.cleanup()
        if not info or "error" in info:
            print(output)
            reason = info.get("error", "see the console")
            self.report({"ERROR"}, f"MustardUI - Export to Unreal failed: {reason}")
            return {"CANCELLED"}
        details = ", ".join(f"{value} {key}" for key, value in info.items())
        self.report({"INFO"}, f"MustardUI - Exported {os.path.basename(self.filepath)} ({details})")
        return {"FINISHED"}


class MustardUI_UnrealTools_ExportCharacter(ExportToUnreal, bpy.types.Operator):
    """Export the MHX model with the chosen outfits, and a skeleton with Unreal bone names.
    Shape keys, face controls and morphs chosen in the lists become morph targets.
    The open file is not changed"""

    bl_idname = "mustardui.unreal_tools_export_character"
    bl_label = "Export Character"

    materials: bpy.props.BoolProperty(
        name="Materials",
        default=False,
        description="Export simple materials with the textures found in the materials: base "
        "color, normal, roughness and alpha.\nThe textures are copied to a folder next to the "
        "FBX. Effects made with nodes, as color corrections, are not exported.\nSurfaces to "
        "see through without an alpha texture, as the moisture over the eyes, are left out",
    )
    outfits: bpy.props.BoolProperty(
        name="Outfits",
        default=True,
        description="Export the outfit pieces chosen in the list, also if hidden.\n"
        "Without outfits, the body and the other visible meshes are exported",
    )
    hair: bpy.props.BoolProperty(
        name="Hair",
        default=True,
        description="Export the mesh hair chosen in the list, also if hidden, with the bones "
        "of its hair armature.\nHair made of particles is not exported",
    )
    shape_keys: bpy.props.BoolProperty(
        name="Shape Keys",
        default=True,
        description="Export the shape keys chosen in the list as morph targets",
    )
    face_controls: bpy.props.BoolProperty(
        name="Face Controls",
        default=True,
        description="Export the face controls chosen in the list as morph targets",
    )
    morphs: bpy.props.BoolProperty(
        name="Morphs",
        default=False,
        description="Export the MustardUI morphs chosen in the list as morph targets.\n"
        "Morphs moving bones or several shape keys are converted to a single morph target",
    )

    def invoke(self, context, event):
        update_export_items(context)
        return super().invoke(context, event)

    def chosen(self, context, kind):
        """Keys of the items chosen in a list, empty if its switch is off."""
        if not getattr(self, kind):
            return set()
        return {i.key for i in getattr(context.window_manager, LIST_COLLECTIONS[kind]) if i.use}

    def skipped(self, context, kind):
        """Keys of the items not chosen in a list.
        The export skips these instead of keeping only the chosen ones, because drivers can
        make it find shape keys which were active, and so not listed, in this session"""
        return sorted(
            i.key for i in getattr(context.window_manager, LIST_COLLECTIONS[kind]) if not i.use
        )

    def execute(self, context):
        update_export_items(context)
        enabled = mhx_rig(context).data.MustardUI_MorphsSettings.diffeomorphic_enable
        if self.chosen(context, "morphs") and not enabled:
            self.report({"ERROR"}, "MustardUI - Enable the Morphs to export them")
            return {"CANCELLED"}
        return super().execute(context)

    def settings(self, context):
        chosen = self.chosen(context, "morphs")
        rig_settings = mhx_rig(context).data.MustardUI_RigSettings
        morphs = []
        for section, morph, name in morph_target_names(mhx_rig(context).data):
            if f"{section.name}/{morph.path}" not in chosen:
                continue
            if morph.custom_property:
                owner = get_cp_source(morph.custom_property_source, rig_settings)
                value = {"property": morph.path}
            else:
                body = rig_settings.model_body
                owner = body.data.shape_keys if body is not None else None
                value = {"shape_key": morph.path}
            if owner is None or owner.id_type not in DATA_COLLECTIONS:
                continue
            morphs.append(
                {
                    "name": name,
                    "collection": DATA_COLLECTIONS[owner.id_type],
                    "owner": owner.name,
                    **value,
                }
            )
        return {
            "mode": "CHARACTER",
            "materials": self.materials,
            "outfit_pieces": [i.key for i in context.window_manager.MustardUI_UnrealTools_Outfits],
            "outfits": sorted(self.chosen(context, "outfits")),
            "hair": sorted(self.chosen(context, "hair")),
            "shape_keys": self.shape_keys,
            "skip_shape_keys": self.skipped(context, "shape_keys"),
            "face_controls": self.face_controls,
            "skip_face_controls": self.skipped(context, "face_controls"),
            "morphs": morphs,
        }

    def draw(self, context):
        wm = context.window_manager
        self.layout.prop(self, "materials")
        for kind, collection, label, icon in EXPORT_LISTS:
            items = getattr(wm, collection)
            header, body = self.layout.panel(collection, default_closed=False)
            header.prop(self, kind, text="")
            selected = sum(1 for i in items if i.use)
            header.label(text=f"{label} ({selected}/{len(items)})", icon=icon)
            if body is None:
                continue
            body.active = getattr(self, kind)
            if not len(items):
                body.label(text=f"The model has no {label.lower()}")
                continue
            body.template_list(
                "MUSTARDUI_UL_UnrealTools_Export",
                collection,
                wm,
                collection,
                wm,
                collection + "Index",
                rows=6,
            )
            row = body.row(align=True)
            select = row.operator(
                "mustardui.unreal_tools_export_select", text="All", icon="CHECKBOX_HLT"
            )
            select.kind, select.use = kind, True
            select = row.operator(
                "mustardui.unreal_tools_export_select", text="None", icon="CHECKBOX_DEHLT"
            )
            select.kind, select.use = kind, False


def morph_curve_names(rig):
    """Names of the morph targets a property of the rig can drive, by property: the MustardUI
    morph, and the face control. Unreal uses the curves of the morph targets in the character,
    so a property exported both ways is not applied twice"""
    curves = {}
    for _, morph, name in morph_target_names(rig.data):
        if morph.custom_property and morph.custom_property_source == "ARMATURE_OBJ":
            curves.setdefault(morph.path, []).append(name)
    for name in morph_targets.face_controls(rig):
        curves.setdefault(name, []).append(name)
    return curves


def action_items(self, context):
    # Blender needs the strings of the enum to stay referenced
    action_items.items = [(a.name, a.name, "") for a in bpy.data.actions]
    return action_items.items


class MustardUI_UnrealTools_ExportAnimation(ExportToUnreal, bpy.types.Operator):
    """Export an action of the MHX model for the skeleton of Export Character.
    The open file is not changed"""

    bl_idname = "mustardui.unreal_tools_export_animation"
    bl_label = "Export Animation"

    action: bpy.props.EnumProperty(name="Action", items=action_items)
    frame_start: bpy.props.IntProperty(
        name="First Frame", default=0, min=0, description="0 starts where the action starts"
    )
    frame_end: bpy.props.IntProperty(
        name="Last Frame", default=0, min=0, description="0 ends where the action ends"
    )
    height_offset: bpy.props.FloatProperty(
        name="Height Offset",
        default=0.0,
        subtype="DISTANCE",
        unit="NONE",
        description="Centimeters added to the body height, if the feet hover or sink",
    )
    morph_curves: bpy.props.BoolProperty(
        name="Morph Curves",
        default=False,
        description="Export the animated values of face controls, MustardUI morphs and shape "
        "keys as curves, which drive the morph targets of Export Character in Unreal",
    )

    @classmethod
    def poll(cls, context):
        if not super().poll(context):
            return False
        if not bpy.data.actions:
            cls.poll_message_set("The file has no actions")
            return False
        return True

    def execute(self, context):
        # Actions without users would be left out of the copy of the file
        action = bpy.data.actions[self.action]
        fake_user = action.use_fake_user
        action.use_fake_user = True
        result = super().execute(context)
        action.use_fake_user = fake_user
        return result

    def settings(self, context):
        return {
            "mode": "ANIMATION",
            "action": self.action,
            "frame_start": self.frame_start,
            "frame_end": self.frame_end,
            "height_offset": self.height_offset,
            "morph_curves": self.morph_curves,
            "curves": morph_curve_names(mhx_rig(context)) if self.morph_curves else {},
        }

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.prop(self, "action")
        layout.prop(self, "frame_start")
        layout.prop(self, "frame_end")
        layout.prop(self, "height_offset")
        layout.prop(self, "morph_curves")


def register():
    bpy.utils.register_class(MustardUI_UnrealTools_ExportItem)
    bpy.utils.register_class(MUSTARDUI_UL_UnrealTools_Export)
    bpy.utils.register_class(MustardUI_UnrealTools_ExportSelect)
    bpy.utils.register_class(MustardUI_UnrealTools_ExportCharacter)
    bpy.utils.register_class(MustardUI_UnrealTools_ExportAnimation)

    wm = bpy.types.WindowManager
    for _, collection, _, _ in EXPORT_LISTS:
        prop = bpy.props.CollectionProperty(type=MustardUI_UnrealTools_ExportItem)
        setattr(wm, collection, prop)
        setattr(wm, collection + "Index", bpy.props.IntProperty(default=0, name=""))


def unregister():
    for _, collection, _, _ in EXPORT_LISTS:
        delattr(bpy.types.WindowManager, collection + "Index")
        delattr(bpy.types.WindowManager, collection)

    bpy.utils.unregister_class(MustardUI_UnrealTools_ExportAnimation)
    bpy.utils.unregister_class(MustardUI_UnrealTools_ExportCharacter)
    bpy.utils.unregister_class(MustardUI_UnrealTools_ExportSelect)
    bpy.utils.unregister_class(MUSTARDUI_UL_UnrealTools_Export)
    bpy.utils.unregister_class(MustardUI_UnrealTools_ExportItem)
