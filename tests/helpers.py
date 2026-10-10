import io
import sys
import unittest

import bpy

ADDON = "bl_ext.user_default.MustardUI"


class StderrTracebacks:
    """Tee stderr and collect the tracebacks printed by callbacks Blender swallows."""

    def __init__(self):
        self.buffer = io.StringIO()

    def write(self, text):
        self.buffer.write(text)
        return self.stream.write(text)

    def flush(self):
        self.stream.flush()

    def __enter__(self):
        self.stream = sys.stderr
        sys.stderr = self
        return self

    def __exit__(self, *args):
        sys.stderr = self.stream

    @property
    def tracebacks(self):
        text = self.buffer.getvalue()
        return [t for t in text.split("Traceback (most recent call last):")[1:]]


def reset_scene():
    bpy.ops.wm.read_homefile(use_empty=True)

    # Add-on preferences survive loading the homefile
    prefs = bpy.context.preferences.addons[ADDON].preferences
    for prop in prefs.bl_rna.properties:
        if not prop.is_readonly and prop.identifier != "rna_type":
            prefs.property_unset(prop.identifier)


def new_object(name, data=None, collection=None):
    obj = bpy.data.objects.new(name, data)
    (collection or bpy.context.scene.collection).objects.link(obj)
    return obj


def new_mesh_object(name, collection=None, armature=None, size=0.5, z=1.0):
    mesh = bpy.data.meshes.new(name)
    s = size
    verts = [(x * s, y * s, z + h * s) for h in (-1, 1) for y in (-1, 1) for x in (-1, 1)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = new_object(name, mesh, collection)
    if armature is not None:
        obj.parent = armature
        mod = obj.modifiers.new("Armature", "ARMATURE")
        mod.object = armature
        group = obj.vertex_groups.new(name="spine")
        group.add(range(len(verts)), 1.0, "REPLACE")
    return obj


def new_collection(name, parent=None):
    coll = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(coll)
    return coll


def set_active(obj):
    view_layer = bpy.context.view_layer
    for o in view_layer.objects:
        o.select_set(False)
    view_layer.objects.active = obj
    obj.select_set(True)


def set_active_collection(coll):
    def find(layer_coll):
        if layer_coll.collection == coll:
            return layer_coll
        for child in layer_coll.children:
            found = find(child)
            if found is not None:
                return found
        return None

    bpy.context.view_layer.active_layer_collection = find(bpy.context.view_layer.layer_collection)


def build_model(name="Tester"):
    """Armature, body with shape keys, two outfits, extras and a hair collection."""
    arm_data = bpy.data.armatures.new(name + " Armature")
    arm = new_object(name + " Armature", arm_data)
    set_active(arm)
    bpy.ops.object.mode_set(mode="EDIT")
    for bone_name, head, tail in (
        ("root", (0, 0, 0), (0, 0, 0.3)),
        ("spine", (0, 0, 0.3), (0, 0, 1.2)),
        ("head", (0, 0, 1.2), (0, 0, 1.6)),
    ):
        bone = arm_data.edit_bones.new(bone_name)
        bone.head, bone.tail = head, tail
    arm_data.edit_bones["spine"].parent = arm_data.edit_bones["root"]
    arm_data.edit_bones["head"].parent = arm_data.edit_bones["spine"]
    bpy.ops.object.mode_set(mode="OBJECT")
    bone_collection = arm_data.collections.new("Body")
    for bone in arm_data.bones:
        bone_collection.assign(bone)

    body = new_mesh_object(name + " Body", armature=arm)
    body.shape_key_add(name="Basis")
    for key_name in ("Smile", "Blink", "Blink.L", "Blink.R"):
        body.shape_key_add(name=key_name, from_mix=False).value = 0.0

    outfits = []
    for outfit_name, pieces in (("Casual", ("Shirt", "Pants")), ("Formal", ("Dress",))):
        coll = new_collection(f"{name} {outfit_name}")
        for piece in pieces:
            new_mesh_object(f"{outfit_name} - {piece}", coll, armature=arm, size=0.55)
        outfits.append(coll)

    # Skin material with a normal map
    material = bpy.data.materials.new(name + " Skin")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    normal_map = nodes.new("ShaderNodeNormalMap")
    material.node_tree.links.new(normal_map.outputs[0], nodes["Principled BSDF"].inputs["Normal"])
    body.data.materials.append(material)

    # Mask on the body driven by the Formal dress
    body.modifiers.new("Formal - Dress", "MASK").vertex_group = "spine"

    extras = new_collection(f"{name} Extras")
    new_mesh_object("Extras - Glasses", extras, armature=arm, size=0.2, z=1.4)

    hair = new_collection(f"{name} Hair")
    for hair_name in ("Hair Short", "Hair Long"):
        new_mesh_object(hair_name, hair, armature=arm, size=0.3, z=1.5)

    set_active(arm)
    return {"armature": arm, "body": body, "outfits": outfits, "extras": extras, "hair": hair}


def configure_model(model, name="Tester"):
    """Configure the model the way a creator would in the Configuration panel."""
    arm = model["armature"]
    rig_settings = arm.data.MustardUI_RigSettings
    rig_settings.model_name = name
    rig_settings.model_body = model["body"]
    rig_settings.model_MustardUI_naming_convention = True

    set_active(arm)
    for coll in model["outfits"]:
        set_active_collection(coll)
        bpy.ops.mustardui.add_collection()
    rig_settings.extras_collection = model["extras"]
    rig_settings.hair_collection = model["hair"]

    set_active(arm)
    bpy.ops.mustardui.configuration()
    return rig_settings


class BlenderTestCase(unittest.TestCase):
    """Fresh empty scene per test; fails on tracebacks printed by swallowed exceptions."""

    def setUp(self):
        reset_scene()
        self._stderr = StderrTracebacks().__enter__()

    def tearDown(self):
        self._stderr.__exit__()
        tracebacks = self._stderr.tracebacks
        if tracebacks:
            self.fail("Python errors printed during the test:\n" + "\n".join(tracebacks))


def setup_generic_morphs(model):
    """Add a generic Morphs section with the Blink shape keys, back in user mode."""
    arm = model["armature"].data
    bpy.ops.mustardui.configuration()
    morphs_settings = arm.MustardUI_MorphsSettings
    morphs_settings.enable_ui = True
    morphs_settings.type = "GENERIC"
    bpy.ops.mustardui.morphs_section_add()
    section = morphs_settings.sections[0]
    section.name = "Eyes"
    section.string = "Blink"
    section.shape_keys = True
    section.custom_properties = False
    bpy.ops.mustardui.morphs_check()
    bpy.ops.mustardui.configuration()
    return morphs_settings
