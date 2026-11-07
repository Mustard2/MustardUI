import importlib
import json
import os
import tempfile

import bpy
from fake_ui import Drawer, FakeLayout, FakeSelf
from helpers import ADDON, BlenderTestCase, new_object, set_active

skeleton = importlib.import_module(f"{ADDON}.model_toolkit.unreal.mhx_skeleton")
ops_export = importlib.import_module(f"{ADDON}.model_toolkit.unreal.ops_export")
materials = importlib.import_module(f"{ADDON}.model_toolkit.unreal.materials")


class TestExportToUnreal(BlenderTestCase):
    def setUp(self):
        super().setUp()
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.wm = bpy.context.window_manager
        # The lists keep the choices of the session, so each test starts from empty ones
        for collection in ops_export.LIST_COLLECTIONS.values():
            getattr(self.wm, collection).clear()
        names = sorted(
            set(skeleton.PLAIN)
            | set(skeleton.SPLIT)
            | set(skeleton.JOINT.values())
            | set(skeleton.ANCESTOR)
            | set(skeleton.SPINE_JOINTS.values())
            | {"bottom.L"}
        )
        self.rig = new_object("Rig", bpy.data.armatures.new("Rig"))
        self.rig["MhxRig"] = "MHX"
        set_active(self.rig)
        bpy.ops.object.mode_set(mode="EDIT")
        for index, name in enumerate(names):
            bone = self.rig.data.edit_bones.new(name)
            bone.head = (index * 0.01, 0, 1)
            bone.tail = (index * 0.01, 0, 1.1)
        bpy.ops.object.mode_set(mode="OBJECT")

        mesh = bpy.data.meshes.new("Body")
        mesh.from_pydata([(0, 0, 1), (1, 0, 1), (0, 0, 2)], [], [(0, 1, 2)])
        self.body = new_object("Body", mesh)
        self.body.modifiers.new("Armature", "ARMATURE").object = self.rig
        for name in ("hand.twk.L", "chest.twk", "bottom.L"):
            self.body.vertex_groups.new(name=name).add([0, 1, 2], 1.0, "REPLACE")

    def path(self, name):
        return os.path.join(self.folder.name, name)

    def imported_bones(self, filepath):
        known = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=filepath, automatic_bone_orientation=False)
        return next(o for o in bpy.data.objects if o not in known and o.type == "ARMATURE")

    def test_greyed_without_mhx(self):
        del self.rig["MhxRig"]
        self.assertFalse(bpy.ops.mustardui.unreal_tools_export_character.poll())
        self.assertFalse(bpy.ops.mustardui.unreal_tools_export_animation.poll())

    def test_animation_needs_an_action(self):
        self.assertTrue(bpy.ops.mustardui.unreal_tools_export_character.poll())
        self.assertFalse(bpy.ops.mustardui.unreal_tools_export_animation.poll())

    # Only the bones of the export are bundled, with their source named
    def test_mannequin_data(self):
        self.assertEqual(set(skeleton.MANNY) - {"_source"}, set(skeleton.PARENT))
        self.assertIn("Epic Games", skeleton.MANNY["_source"])

    # Mannequin axes, turned only as much as the limb of the character differs
    def test_mannequin_axes(self):
        weighted = skeleton.weighted_bones([self.body])
        rest, _, _ = skeleton.build(self.rig, weighted)
        for name in ("root", "index_01_l", "foot_r", "spine_03", "calf_twist_01_l"):
            self.assertEqual(rest[name].determinant() > 0, True, name)
        self.assertEqual(rest["root"].to_3x3(), skeleton.manny_rotation("root"))

    # The open file is left as it was
    def test_export_character(self):
        filepath = self.path("character.fbx")
        self.assertEqual(
            bpy.ops.mustardui.unreal_tools_export_character("EXEC_DEFAULT", filepath=filepath),
            {"FINISHED"},
        )
        self.assertIn("hand.twk.L", self.body.vertex_groups)
        self.assertIn("hand.twk.L", self.rig.data.bones)

        bones = self.imported_bones(filepath).data.bones
        for name in ("root", "pelvis", "spine_03", "spine_04", "hand_l", "bottom_L", "index_03_r"):
            self.assertIn(name, bones)
        self.assertNotIn("hand.twk.L", bones)
        self.assertEqual(bones["hand_l"].parent.name, "lowerarm_l")
        self.assertIsNone(bones["root"].parent)

    def test_export_animation(self):
        animation = self.rig.animation_data_create()
        animation.action = bpy.data.actions.new("Move")
        bone = self.rig.pose.bones["hand.twk.L"]
        for frame, value in ((1, 0.0), (5, 0.3)):
            bone.location.x = value
            bone.keyframe_insert("location", index=0, frame=frame)
        animation.action = None

        filepath = self.path("animation.fbx")
        self.assertEqual(
            bpy.ops.mustardui.unreal_tools_export_animation(
                "EXEC_DEFAULT", filepath=filepath, action="Move", height_offset=2.0
            ),
            {"FINISHED"},
        )
        self.assertFalse(bpy.data.actions["Move"].use_fake_user)
        rig = self.imported_bones(filepath)
        self.assertIn("hand_l", rig.data.bones)
        self.assertIsNotNone(rig.animation_data.action)
        first, last = rig.animation_data.action.frame_range
        self.assertEqual(last - first, 4.0)

        def hand(frame):
            bpy.context.scene.frame_set(int(frame))
            return rig.pose.bones["hand_l"].matrix.translation.copy()

        self.assertGreater((hand(last) - hand(first)).length, 0.0)

    def add_morphs(self):
        """A morph moving a bone through a driver, and a morph of a shape key."""
        self.rig["Wave"] = 0.0
        driver = self.rig.driver_add('pose.bones["hand.twk.L"].location', 0).driver
        variable = driver.variables.new()
        variable.targets[0].id = self.rig
        variable.targets[0].data_path = '["Wave"]'
        driver.expression = f"{variable.name} * 0.3"
        self.body.shape_key_add(name="Basis")
        for name in ("Smile", "Other"):
            key = self.body.shape_key_add(name=name, from_mix=False)
            key.data[0].co.z += 0.1
            key.value = 0.0
        rig_settings = self.rig.data.MustardUI_RigSettings
        rig_settings.model_armature_object = self.rig
        rig_settings.model_body = self.body
        section = self.rig.data.MustardUI_MorphsSettings.sections.add()
        section.name = "Face"
        for name, path, custom_property in (("Wave", "Wave", True), ("Big Smile", "Smile", False)):
            morph = section.morphs.add()
            morph.name, morph.path = name, path
            morph.custom_property, morph.shape_key = custom_property, not custom_property

    def imported_keys(self, filepath):
        known = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=filepath)
        body = next(o for o in bpy.data.objects if o not in known and o.type == "MESH")
        keys = body.data.shape_keys.key_blocks
        basis = keys[0].data
        return {
            k.name: max((a.co - b.co).length for a, b in zip(k.data, basis, strict=True))
            for k in keys
        }

    def add_outfit(self):
        """An outfit with a visible piece and a hidden one, both deformed by the rig."""
        outfit = bpy.data.collections.new("Model Sport")
        bpy.context.scene.collection.children.link(outfit)
        pieces = []
        for name, hidden in (("Model Sport - Shirt", False), ("Model Sport - Shoes", True)):
            mesh = bpy.data.meshes.new(name)
            mesh.from_pydata([(0, 0, 1), (1, 0, 1), (0, 0, 2)], [], [(0, 1, 2)])
            piece = new_object(name, mesh, outfit)
            piece.modifiers.new("Armature", "ARMATURE").object = self.rig
            piece.vertex_groups.new(name="chest.twk").add([0, 1, 2], 1.0, "REPLACE")
            piece.hide_set(hidden)
            pieces.append(piece)
        rig_settings = self.rig.data.MustardUI_RigSettings
        rig_settings.model_name = "Model"
        rig_settings.model_MustardUI_naming_convention = True
        rig_settings.outfits_collections.add().collection = outfit
        return pieces

    def imported_meshes(self, filepath):
        known = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=filepath)
        # Imported names get a number, as the scene already has objects with the same names
        new = [o for o in bpy.data.objects if o not in known and o.type == "MESH"]
        return {o.name.rsplit(".", 1)[0] for o in new}

    def test_outfit_list(self):
        self.add_outfit()
        pieces = self.items("outfits")
        self.assertEqual(pieces["Model Sport - Shirt"].name, "Shirt")
        self.assertEqual(pieces["Model Sport - Shirt"].section, "Sport")
        self.assertTrue(pieces["Model Sport - Shirt"].use)
        self.assertFalse(pieces["Model Sport - Shoes"].use)
        self.assertNotIn("Body", pieces)

    # Chosen pieces are exported also if hidden, the others are left out also if visible
    def test_export_chosen_outfit_pieces(self):
        shirt, shoes = self.add_outfit()
        shoes.hide_select = True
        pieces = self.items("outfits")
        pieces[shirt.name].use, pieces[shoes.name].use = False, True
        filepath = self.path("character.fbx")
        bpy.ops.mustardui.unreal_tools_export_character(
            "EXEC_DEFAULT", filepath=filepath, outfits=True
        )
        self.assertTrue(shoes.hide_get())
        meshes = self.imported_meshes(filepath)
        self.assertIn("Body", meshes)
        self.assertIn(shoes.name, meshes)
        self.assertNotIn(shirt.name, meshes)

    def test_export_without_outfits(self):
        shirt, _ = self.add_outfit()
        filepath = self.path("character.fbx")
        bpy.ops.mustardui.unreal_tools_export_character(
            "EXEC_DEFAULT", filepath=filepath, outfits=False
        )
        meshes = self.imported_meshes(filepath)
        self.assertIn("Body", meshes)
        self.assertNotIn(shirt.name, meshes)

    def items(self, kind):
        """A list of Export Character, by key."""
        ops_export.update_export_items(bpy.context)
        return {i.key: i for i in getattr(self.wm, ops_export.LIST_COLLECTIONS[kind])}

    def test_lists_of_morph_targets(self):
        self.add_morphs()
        keys = self.items("shape_keys")
        self.assertTrue(keys["Other"].use)
        self.assertNotIn("Basis", keys)
        morphs = self.items("morphs")
        self.assertTrue(morphs["Face/Wave"].use)
        self.assertEqual(morphs["Face/Smile"].name, "Big Smile")
        self.assertEqual(morphs["Face/Smile"].section, "Face")

    # Active shape keys are part of the character's shape, so they are not in the list
    def test_active_shape_keys_are_not_listed(self):
        self.add_morphs()
        self.body.data.shape_keys.key_blocks["Other"].value = 1.0
        self.assertNotIn("Other", self.items("shape_keys"))

    def test_choices_are_kept(self):
        self.add_morphs()
        self.items("shape_keys")["Other"].use = False
        self.items("morphs")["Face/Wave"].use = False
        self.assertFalse(self.items("shape_keys")["Other"].use)
        self.assertTrue(self.items("shape_keys")["Smile"].use)
        self.assertFalse(self.items("morphs")["Face/Wave"].use)

    # All and None change only their own list
    def test_select_all_and_none(self):
        self.add_morphs()
        self.items("morphs")
        bpy.ops.mustardui.unreal_tools_export_select(kind="morphs", use=False)
        self.assertFalse(self.items("morphs")["Face/Wave"].use)
        self.assertTrue(self.items("shape_keys")["Other"].use)
        bpy.ops.mustardui.unreal_tools_export_select(kind="morphs", use=True)
        self.assertTrue(self.items("morphs")["Face/Smile"].use)

    def test_search_matches_name_or_section(self):
        self.add_morphs()
        self.items("morphs")
        drawer = Drawer()
        for text, shown in (("wav", 1), ("face", 2), ("nothing", 0)):
            ui_list = FakeSelf(
                ops_export.MUSTARDUI_UL_UnrealTools_Export,
                FakeLayout(drawer),
                filter_name=text,
                bitflag_filter_item=1,
            )
            flags, _ = ui_list.filter_items(bpy.context, self.wm, "MustardUI_UnrealTools_Morphs")
            self.assertEqual(sum(flags), shown, text)

    def test_draw_lists(self):
        self.add_morphs()
        self.add_outfit()
        self.items("morphs")
        drawer = Drawer()
        operator = FakeSelf(
            ops_export.MustardUI_UnrealTools_ExportCharacter,
            FakeLayout(drawer),
            # Blender keeps the properties of operators on their own type
            bl_rna=bpy.ops.mustardui.unreal_tools_export_character.get_rna_type(),
            outfits=True,
            shape_keys=True,
            face_controls=True,
            morphs=False,
        )
        drawer.run("ExportCharacter.draw", operator.draw, bpy.context)
        self.assertEqual(drawer.errors, [])

    # Morphs moving bones are converted to morph targets, with the name in the UI
    def test_export_morphs(self):
        self.add_morphs()
        filepath = self.path("character.fbx")
        self.assertEqual(
            bpy.ops.mustardui.unreal_tools_export_character(
                "EXEC_DEFAULT", filepath=filepath, shape_keys=False, morphs=True
            ),
            {"FINISHED"},
        )
        self.assertEqual(self.rig["Wave"], 0.0)
        keys = self.imported_keys(filepath)
        self.assertNotIn("Other", keys)
        self.assertNotIn("Smile", keys)
        self.assertGreater(keys["Wave"], 0.01)
        self.assertGreater(keys["Big Smile"], 0.01)

    def test_chosen_shape_keys(self):
        self.add_morphs()
        self.items("shape_keys")["Smile"].use = False
        filepath = self.path("character.fbx")
        # The operator keeps the last options, so they are given
        bpy.ops.mustardui.unreal_tools_export_character(
            "EXEC_DEFAULT", filepath=filepath, shape_keys=True, morphs=False
        )
        keys = self.imported_keys(filepath)
        self.assertIn("Other", keys)
        self.assertNotIn("Smile", keys)
        self.assertNotIn("Wave", keys)

    def test_disabled_morphs_are_reported(self):
        self.add_morphs()
        self.rig.data.MustardUI_MorphsSettings["diffeomorphic_enable"] = False
        with self.assertRaisesRegex(RuntimeError, "Enable the Morphs"):
            bpy.ops.mustardui.unreal_tools_export_character(
                "EXEC_DEFAULT", filepath=self.path("character.fbx"), morphs=True
            )

    def save_image(self, name, tiles=()):
        """An image saved to a file, or to a file per UDIM tile if given."""
        for file_name in [f"{name}.{t}.png" for t in tiles] or [f"{name}.png"]:
            image = bpy.data.images.new(file_name, 4, 4)
            image.filepath_raw = self.path(file_name)
            image.file_format = "PNG"
            image.save()
            bpy.data.images.remove(image)
        if not tiles:
            return bpy.data.images.load(self.path(f"{name}.png"))
        image = bpy.data.images.load(self.path(f"{name}.{tiles[0]}.png"))
        image.name = name
        image.source = "TILED"
        image.filepath = self.path(f"{name}.<UDIM>.png")
        return image

    def textured_material(self, tile=1001):
        """Material with a color image through a node group, and a normal map, on the body.
        Its faces are in the UDIM tile given."""
        group = bpy.data.node_groups.new("Skin", "ShaderNodeTree")
        group.interface.new_socket("Diffuse Color", in_out="INPUT", socket_type="NodeSocketColor")
        group.interface.new_socket("Normal", in_out="INPUT", socket_type="NodeSocketVector")
        group.interface.new_socket("BSDF", in_out="OUTPUT", socket_type="NodeSocketShader")
        inside = group.nodes.new("ShaderNodeBsdfPrincipled")
        group_input = group.nodes.new("NodeGroupInput")
        group_output = group.nodes.new("NodeGroupOutput")
        group.links.new(group_input.outputs["Diffuse Color"], inside.inputs["Base Color"])
        group.links.new(inside.outputs[0], group_output.inputs["BSDF"])

        material = bpy.data.materials.new("Skin")
        material.use_nodes = True
        tree = material.node_tree
        tree.nodes.clear()
        output = tree.nodes.new("ShaderNodeOutputMaterial")
        node = tree.nodes.new("ShaderNodeGroup")
        node.node_tree = group
        tree.links.new(node.outputs["BSDF"], output.inputs["Surface"])
        color = tree.nodes.new("ShaderNodeTexImage")
        color.image = self.save_image("Body_D", tiles=(1001, 1002))
        tint = tree.nodes.new("ShaderNodeMix")
        tint.data_type = "RGBA"
        tree.links.new(color.outputs["Color"], tint.inputs["A"])
        tree.links.new(tint.outputs["Result"], node.inputs["Diffuse Color"])
        normal = tree.nodes.new("ShaderNodeTexImage")
        normal.image = self.save_image("Body_N")
        normal_map = tree.nodes.new("ShaderNodeNormalMap")
        tree.links.new(normal.outputs["Color"], normal_map.inputs["Color"])
        tree.links.new(normal_map.outputs["Normal"], node.inputs["Normal"])
        # Images not used by the shader are left out
        unused = tree.nodes.new("ShaderNodeTexImage")
        unused.image = self.save_image("Unused_D")

        self.body.data.materials.append(material)
        uv = self.body.data.uv_layers.new()
        offset = (tile - 1001) % 10
        for loop in uv.data:
            loop.uv = (loop.uv[0] * 0.5 + offset + 0.25, loop.uv[1] * 0.5 + 0.25)
        return material

    def test_material_textures(self):
        material = self.textured_material(tile=1002)
        found = {
            role: image.name for role, (image, _) in materials.material_textures(material).items()
        }
        self.assertEqual(found, {"color": "Body_D", "normal": "Body_N.png"})

    # The Unreal script picks the parent material from the kind
    def test_material_kinds(self):
        material = self.textured_material()
        self.assertEqual(materials.material_kind(material, {}), "opaque")
        self.assertEqual(materials.material_kind(material, {"alpha": None}), "masked")
        inside = bpy.data.node_groups["Skin"].nodes["Principled BSDF"]
        inside.inputs["Subsurface Weight"].default_value = 0.2
        self.assertEqual(materials.material_kind(material, {}), "skin")
        material.name = "Eye Left"
        self.assertEqual(materials.material_kind(material, {}), "eye")
        material.name = "Eyelashes"
        self.assertEqual(materials.material_kind(material, {}), "skin")

    # Textures are copied next to the FBX, which uses them in simple materials
    def test_export_materials(self):
        self.textured_material(tile=1002)
        filepath = self.path("export/character.fbx")
        os.makedirs(os.path.dirname(filepath))
        self.assertEqual(
            bpy.ops.mustardui.unreal_tools_export_character(
                "EXEC_DEFAULT", filepath=filepath, materials=True
            ),
            {"FINISHED"},
        )
        textures = os.path.join(os.path.dirname(filepath), "character_Textures")
        # The tile is renamed, or Unreal would read it as a UDIM texture
        self.assertEqual(
            sorted(os.listdir(textures)), ["Body_D_T1002.png", "Body_N.png", "materials.json"]
        )
        # The list of textures and the script read by Unreal
        with open(os.path.join(textures, "materials.json")) as file:
            entry = json.load(file)["materials"]["Skin"]
        self.assertEqual(entry["color"], "Body_D_T1002.png")
        self.assertEqual(entry["normal"], "Body_N.png")
        self.assertNotIn("alpha", entry)
        self.assertEqual(entry["kind"], "opaque")
        folder = os.path.dirname(filepath)
        self.assertIn("MustardUI_Unreal_Materials.py", os.listdir(folder))
        self.assertEqual(len(self.rig.data.bones), len(bpy.data.armatures["Rig"].bones))
        self.assertIsNotNone(bpy.data.materials["Skin"].node_tree.nodes.get("Group"))

        known = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=filepath)
        body = next(o for o in bpy.data.objects if o not in known and o.type == "MESH")
        images = {
            os.path.basename(n.image.filepath)
            for n in body.material_slots[0].material.node_tree.nodes
            if n.bl_idname == "ShaderNodeTexImage"
        }
        self.assertEqual(images, {"Body_D_T1002.png", "Body_N.png"})

    # Unreal makes materials opaque, so see-through surfaces would hide what is behind them
    def test_see_through_faces_are_left_out(self):
        material = bpy.data.materials.new("Moisture")
        material.use_nodes = True
        tree = material.node_tree
        tree.nodes.clear()
        output = tree.nodes.new("ShaderNodeOutputMaterial")
        clear = tree.nodes.new("ShaderNodeBsdfTransparent")
        tree.links.new(clear.outputs[0], output.inputs["Surface"])
        self.body.data.materials.append(material)
        filepath = self.path("character.fbx")
        bpy.ops.mustardui.unreal_tools_export_character(
            "EXEC_DEFAULT", filepath=filepath, materials=True
        )
        self.assertEqual(len(self.body.data.polygons), 1)
        self.assertNotIn("Body", self.imported_meshes(filepath))

    def test_morph_curve_names(self):
        self.add_morphs()
        self.assertEqual(ops_export.morph_curve_names(self.rig), {"Wave": ["Wave"]})

    # Animated morphs and shape keys become curves, on a small mesh as FBX needs
    def test_export_morph_curves(self):
        self.add_morphs()
        animation = self.rig.animation_data_create()
        action = bpy.data.actions.new("Talk")
        animation.action = action
        for frame, value in ((1, 0.0), (5, 0.8)):
            self.rig["Wave"] = value
            self.rig.keyframe_insert('["Wave"]', frame=frame)
        bone = self.rig.pose.bones["hand.twk.L"]
        bone.keyframe_insert("location", frame=1)
        # Keyframes on the shape keys go to a slot of the same action, from Blender 4.4
        keys = self.body.data.shape_keys
        keys.animation_data_create().action = action
        for frame, value in ((1, 0.0), (5, 0.5)):
            keys.key_blocks["Other"].value = value
            keys.key_blocks["Other"].keyframe_insert("value", frame=frame)
        animation.action = None

        filepath = self.path("animation.fbx")
        self.assertEqual(
            bpy.ops.mustardui.unreal_tools_export_animation(
                "EXEC_DEFAULT", filepath=filepath, action="Talk", morph_curves=True
            ),
            {"FINISHED"},
        )
        known = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=filepath)
        carrier = next(o for o in bpy.data.objects if o not in known and o.type == "MESH")
        blocks = carrier.data.shape_keys.key_blocks
        names = {k.name for k in blocks}
        self.assertIn("Wave", names)
        if hasattr(action, "layers"):
            self.assertIn("Other", names)
        first, last = carrier.data.shape_keys.animation_data.action.frame_range
        bpy.context.scene.frame_set(int(last))
        self.assertAlmostEqual(blocks["Wave"].value, 0.8, places=2)

    def test_incomplete_rig_is_reported(self):
        set_active(self.rig)
        bpy.ops.object.mode_set(mode="EDIT")
        self.rig.data.edit_bones.remove(self.rig.data.edit_bones["head"])
        bpy.ops.object.mode_set(mode="OBJECT")
        with self.assertRaisesRegex(RuntimeError, "Not a complete MHX rig"):
            bpy.ops.mustardui.unreal_tools_export_character(
                "EXEC_DEFAULT", filepath=self.path("character.fbx")
            )
