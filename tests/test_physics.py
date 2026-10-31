import importlib
import math
import unittest

import bmesh
import bpy
import numpy as np
from helpers import (
    ADDON,
    BlenderTestCase,
    build_model,
    configure_model,
    new_collection,
    new_mesh_object,
    reset_scene,
    set_active,
)
from mathutils import Vector

ops_outfits_setup = importlib.import_module(ADDON + ".physics.ops_outfits_setup")
settings_presets = importlib.import_module(ADDON + ".physics.settings_presets")
physics_presets = importlib.import_module(ADDON + ".model_toolkit.physics.physics_presets")
definitions_nodes = importlib.import_module(ADDON + ".physics.definitions_nodes")


def evaluated_co(obj):
    bpy.context.view_layer.update()
    mesh = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    co = np.empty(len(mesh.vertices) * 3)
    mesh.vertices.foreach_get("co", co)
    return co.reshape(-1, 3)


class TestPhysics(BlenderTestCase):
    def setUp(self):
        super().setUp()
        self.model = build_model()
        arm = self.model["armature"]
        configure_model(self.model)
        self.physics_settings = arm.data.MustardUI_PhysicsSettings

        # Cloth cage deforming the body
        self.cage = new_mesh_object("Chest Cage", armature=arm, size=0.4)
        self.cloth = self.cage.modifiers.new("Cloth", "CLOTH")
        self.deform = self.model["body"].modifiers.new("Chest Cage", "SURFACE_DEFORM")
        self.deform.target = self.cage

        bpy.ops.mustardui.configuration()
        self.physics_settings.enable_ui = True
        set_active(self.cage)
        bpy.ops.mustardui.physics_add_item()
        self.physics_settings.items[0].type = "CAGE"
        set_active(arm)
        bpy.ops.mustardui.configuration()
        self.physics_settings.items[0].enable = True

    # Scale Character rescales the cloth, hair dynamics and collision settings
    def test_scale_character(self):
        body = self.model["body"]
        collision = body.modifiers.new("Collision", "COLLISION")
        hair = body.modifiers.new("Hair", "PARTICLE_SYSTEM").particle_system
        hair.settings.type = "HAIR"
        hair.use_hair_dynamics = True
        cloth = self.cloth.settings

        def values():
            return (
                cloth.mass,
                cloth.tension_damping,
                cloth.pressure_factor,
                cloth.effector_weights.gravity,
                self.cloth.collision_settings.distance_min,
                collision.settings.thickness_outer,
                hair.cloth.settings.mass,
                hair.cloth.settings.bending_damping,
                hair.settings.effector_weights.gravity,
            )

        before = values()
        bpy.ops.mustardui.model_toolkit_scale_character(scale=0.5)
        factors = (2.0, 2.0, 4.0, 0.5, 0.5, 0.5, 2.0, 1.0, 0.5)
        for old, new, factor in zip(before, values(), factors, strict=True):
            self.assertAlmostEqual(new, old * factor, places=5)

        # Without the physics options only the armature is scaled
        scaled = values()
        bpy.ops.mustardui.model_toolkit_scale_character(
            scale=0.5, hair_physics=False, physics=False
        )
        self.assertEqual(values(), scaled)

    # Animate drives the physics settings by the armature scale, exact on the way
    def test_scale_character_animate(self):
        # Hidden, the cage and its drivers are not evaluated
        self.physics_settings.enable_physics = True
        cloth = self.cloth.settings
        mass, gravity = cloth.mass, cloth.effector_weights.gravity
        bpy.context.scene.frame_set(1)
        bpy.ops.mustardui.model_toolkit_scale_character(scale=0.5, animate=True, duration=10)
        arm = self.model["armature"]
        self.assertTrue(
            all(x.driver.is_simple_expression for x in self.cage.animation_data.drivers)
        )
        for frame in (1, 6, 11):
            bpy.context.scene.frame_set(frame)
            scale = arm.scale[0]
            self.assertAlmostEqual(cloth.mass, mass / scale, places=5)
            self.assertAlmostEqual(cloth.effector_weights.gravity, gravity * scale, places=5)
        self.assertEqual(scale, 0.5)

        # Another growth, keyed on the armature scale only
        arm.scale = (2.0, 2.0, 2.0)
        arm.keyframe_insert("scale", frame=6)
        bpy.context.scene.frame_set(6)
        self.assertAlmostEqual(cloth.mass, mass / 2.0, places=5)

    # Outfit pieces cannot be added as physics items
    def test_add_outfit_piece_is_rejected(self):
        bpy.ops.mustardui.configuration()
        set_active(bpy.data.objects["Casual - Shirt"])
        with self.assertRaisesRegex(RuntimeError, "already added in Outfits"):
            bpy.ops.mustardui.physics_add_item()
        self.assertEqual(len(self.physics_settings.items), 1)

    # Global physics switch toggles cloth, deform modifiers and cage visibility
    def test_enable_physics(self):
        self.physics_settings.enable_physics = True
        self.assertTrue(self.cloth.show_viewport)
        self.assertTrue(self.deform.show_viewport)

        self.physics_settings.enable_physics = False
        self.assertFalse(self.cloth.show_viewport)
        self.assertFalse(self.deform.show_viewport)
        self.assertTrue(self.cage.hide_viewport)

        self.physics_settings.enable_physics = True
        self.assertTrue(self.deform.show_viewport)
        self.assertFalse(self.cage.hide_viewport)

    # Per-item switch toggles its cloth and deform modifiers
    def test_enable_single_item(self):
        self.physics_settings.enable_physics = True
        item = self.physics_settings.items[0]
        item.enable = False
        self.assertFalse(self.cloth.show_viewport)
        self.assertFalse(self.deform.show_viewport)
        item.enable = True
        self.assertTrue(self.cloth.show_viewport)
        self.assertTrue(self.deform.show_viewport)

    # Removing a physics item keeps its object
    def test_remove_item(self):
        bpy.ops.mustardui.configuration()
        bpy.ops.mustardui.physics_item_remove()
        self.assertEqual(len(self.physics_settings.items), 0)
        self.assertIn("Chest Cage", bpy.data.objects)

    # The physics preset check rejects an item index past the end
    def test_preset_poll_stale_index(self):
        arm = self.model["armature"].data
        arm.mustardui_physics_items_uilist_index = 3
        err, _ = settings_presets.physics_preset_poll(arm, self.physics_settings)
        self.assertEqual(err, "ERROR")

    # Rebinding on a posed rig binds in rest pose, so the rest shape is kept
    def test_rebind_in_pose(self):
        body = self.model["body"]
        spine = self.model["armature"].pose.bones["spine"]

        # Column bent by the spine, with a Corrective Smooth bound at rest
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, segments=16, radius1=0.2, radius2=0.2, depth=1.0)
        bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, 0.9))
        long_edges = [e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 0.5]
        bmesh.ops.subdivide_edges(bm, edges=long_edges, cuts=19)
        bm.to_mesh(body.data)
        bm.free()
        body.vertex_groups.clear()
        root = body.vertex_groups.new(name="root")
        bend = body.vertex_groups.new(name="spine")
        for v in body.data.vertices:
            weight = min(max(v.co.z - 0.4, 0.0), 1.0)
            root.add([v.index], 1.0 - weight, "REPLACE")
            bend.add([v.index], weight, "REPLACE")
        smooth = body.modifiers.new("Smooth", "CORRECTIVE_SMOOTH")
        smooth.rest_source = "BIND"
        with bpy.context.temp_override(object=body):
            bpy.ops.object.correctivesmooth_bind(modifier=smooth.name)
        rest = evaluated_co(body)

        spine.rotation_mode = "XYZ"
        for rebind in (
            bpy.ops.mustardui.physics_rebind,
            lambda: bpy.ops.mustardui.physics_rebind_single_cage(cage_name="Chest Cage"),
        ):
            spine.rotation_euler.x = math.radians(60)
            rebind()
            self.assertEqual(self.model["armature"].data.pose_position, "POSE")
            spine.rotation_euler.x = 0.0
            np.testing.assert_allclose(evaluated_co(body), rest, atol=1e-5)

    # Rebinding with Physics disabled keeps the deforms bound, with cages out of the view layer
    def test_rebind_physics_disabled(self):
        physics = new_collection("Tester Physics")
        bpy.context.scene.collection.objects.unlink(self.cage)
        physics.objects.link(self.cage)
        collision = new_mesh_object("Body Collision", physics)
        deform = collision.modifiers.new("Chest Cage", "SURFACE_DEFORM")
        deform.target = self.cage
        bpy.ops.mustardui.configuration()
        set_active(collision)
        bpy.ops.mustardui.physics_add_item()
        self.physics_settings.items[1].type = "COLLISION"
        set_active(self.model["armature"])
        bpy.ops.mustardui.configuration()
        for obj, mod in ((self.model["body"], self.deform), (collision, deform)):
            with bpy.context.temp_override(object=obj):
                bpy.ops.object.surfacedeform_bind(modifier=mod.name)

        # Deforms disabled and the Physics collection excluded, as on models with Physics disabled
        self.physics_settings.enable_physics = False
        layer = bpy.context.view_layer.layer_collection.children["Tester Physics"]
        layer.exclude = True
        bpy.ops.mustardui.physics_rebind()
        self.assertTrue(self.deform.is_bound)
        self.assertTrue(deform.is_bound)
        self.assertFalse(self.deform.show_viewport)
        self.assertTrue(layer.exclude)

    # Rebinding a single Extras piece rebinds it to both the cages and the body
    def test_rebind_single(self):
        glasses = bpy.data.objects["Extras - Glasses"]
        targets = (self.cage, self.model["body"])
        for target in targets:
            deform = glasses.modifiers.new(target.name, "SURFACE_DEFORM")
            deform.target = target
            with bpy.context.temp_override(object=glasses):
                bpy.ops.object.surfacedeform_bind(modifier=deform.name)
        rest = evaluated_co(glasses)

        # Inflating the targets moves the bound piece until it is rebound
        for target in targets:
            target.modifiers.new("Inflate", "DISPLACE").strength = 0.1
        self.assertGreater(np.abs(evaluated_co(glasses) - rest).max(), 1e-3)
        bpy.ops.mustardui.physics_rebind_single(object_name=glasses.name)
        np.testing.assert_allclose(evaluated_co(glasses), rest, atol=1e-5)

    # Only the Corrective Smooth modifiers after a rebound deform are rebound
    def test_rebind_corrective_smooth(self):
        glasses = bpy.data.objects["Extras - Glasses"]
        before = glasses.modifiers.new("Before", "CORRECTIVE_SMOOTH")
        glasses.modifiers.new(self.cage.name, "SURFACE_DEFORM").target = self.cage
        after = glasses.modifiers.new("After", "CORRECTIVE_SMOOTH")
        for smooth in (before, after):
            smooth.rest_source = "BIND"

        bpy.ops.mustardui.physics_rebind_single(object_name=glasses.name, force=True)
        self.assertFalse(before.is_bind)
        self.assertTrue(after.is_bind)

    # Bindings are made without the cage subdivision, so they work at the lower levels
    def test_rebind_subdivided_cage(self):
        subsurf = self.cage.modifiers.new("Subdivision", "SUBSURF")
        subsurf.levels = 1
        glasses = bpy.data.objects["Extras - Glasses"]
        deform = glasses.modifiers.new(self.cage.name, "SURFACE_DEFORM")
        deform.target = self.cage

        bpy.ops.mustardui.physics_rebind_single(object_name=glasses.name, force=True)
        self.assertTrue(deform.is_bound)
        self.assertTrue(subsurf.show_viewport)

        subsurf.levels = 0
        rest = evaluated_co(glasses)
        self.cage.modifiers.new("Inflate", "DISPLACE").strength = 0.1
        self.assertGreater(np.abs(evaluated_co(glasses) - rest).max(), 1e-3)

    # Cages with concave faces are bound through a temporary Triangulate modifier
    def test_rebind_concave_cage(self):
        bm = bmesh.new()
        bm.from_mesh(self.cage.data)
        top = max(bm.edges, key=lambda e: e.verts[0].co.z + e.verts[1].co.z)
        cut = bmesh.ops.subdivide_edges(bm, edges=[top], cuts=1)["geom_inner"][0]
        cut.co.xy *= 0.2
        bm.to_mesh(self.cage.data)
        bm.free()

        glasses = bpy.data.objects["Extras - Glasses"]
        deform = glasses.modifiers.new(self.cage.name, "SURFACE_DEFORM")
        deform.target = self.cage
        with bpy.context.temp_override(object=glasses):
            bpy.ops.object.surfacedeform_bind(modifier=deform.name)
        self.assertFalse(deform.is_bound)

        bpy.ops.mustardui.physics_rebind_single(object_name=glasses.name, force=True)
        self.assertTrue(deform.is_bound)
        self.assertNotIn("TRIANGULATE", [m.type for m in self.cage.modifiers])

        # The binding follows the cage without the Triangulate modifier
        rest = evaluated_co(glasses)
        self.cage.modifiers.new("Inflate", "DISPLACE").strength = 0.1
        self.assertGreater(np.abs(evaluated_co(glasses) - rest).max(), 1e-3)


class TestOutfitsPhysicsSetup(BlenderTestCase):
    def setUp(self):
        super().setUp()
        self.model = build_model()
        arm = self.model["armature"]
        self.rig_settings = configure_model(self.model)
        self.physics_settings = arm.data.MustardUI_PhysicsSettings
        self.subsurf = self.model["body"].modifiers.new("Subdivision", "SUBSURF")

        # Cage crossing the top of the outfit pieces, and an Extras piece in a sub-collection
        cage = new_mesh_object("Chest Cage", armature=arm, size=0.4, z=1.5)
        cage.modifiers.new("Cloth", "CLOTH")
        hats = new_collection("Tester Extras Hats", self.model["extras"])
        self.hat = new_mesh_object("Extras - Hat", hats, armature=arm, size=0.55)

        bpy.ops.mustardui.configuration()
        self.rig_settings.extras_config_subcollections = True
        self.physics_settings.enable_ui = True
        set_active(cage)
        bpy.ops.mustardui.physics_add_item()
        self.physics_settings.items[0].type = "CAGE"
        set_active(arm)

    @staticmethod
    def surface_deforms(obj):
        return [m for m in obj.modifiers if m.type == "SURFACE_DEFORM"]

    # Pieces in Extras sub-collections follow the Extras sub-collections setting
    def test_extras_subcollections(self):
        bpy.ops.mustardui.physics_outfits_setup()
        self.assertEqual(len(self.surface_deforms(bpy.data.objects["Casual - Shirt"])), 1)
        self.assertEqual(len(self.surface_deforms(self.hat)), 1)
        self.assertIn(
            self.hat, [x.object for x in self.physics_settings.items[0].intersecting_objects]
        )

    # New modifiers are bound after the Armature, leaving the piece subdivision shown
    def test_piece_subdivision_kept(self):
        shirt = bpy.data.objects["Casual - Shirt"]
        subsurf = shirt.modifiers.new("Subdivision", "SUBSURF")
        bpy.ops.mustardui.physics_outfits_setup()
        deform = self.surface_deforms(shirt)[0]
        self.assertTrue(deform.is_bound)
        self.assertEqual(
            [m.type for m in shirt.modifiers], ["ARMATURE", "SURFACE_DEFORM", "SUBSURF"]
        )
        self.assertTrue(subsurf.show_viewport)

    # The armature keeps its pose position
    def test_rest_position_kept(self):
        self.model["armature"].data.pose_position = "REST"
        bpy.ops.mustardui.physics_outfits_setup()
        self.assertEqual(self.model["armature"].data.pose_position, "REST")

    # Compute Intersecting Outfits rebuilds the lists and keeps the Surface Deform modifiers shown
    def test_compute_intersecting_outfits(self):
        self.physics_settings.items[0].enable = True
        bpy.ops.mustardui.physics_outfits_setup()
        self.physics_settings.enable_physics = True
        item = self.physics_settings.items[0]
        intersecting = {x.object for x in item.intersecting_objects}

        bpy.ops.mustardui.physics_outfits_setup_intersecting_objects()
        self.assertEqual({x.object for x in item.intersecting_objects}, intersecting)
        for obj in intersecting:
            for mod in self.surface_deforms(obj):
                self.assertTrue(mod.show_viewport and mod.show_render, obj.name)

    # A failure halfway restores the scene state
    def test_state_restored_on_failure(self):
        def fail(*args):
            raise ValueError("Bind failed")

        scene = bpy.context.scene
        scene.frame_current = 5
        self.physics_settings.enable_physics = True
        original_bind = ops_outfits_setup.surface_deform_bind
        ops_outfits_setup.surface_deform_bind = fail
        try:
            with self.assertRaisesRegex(RuntimeError, "Bind failed"):
                bpy.ops.mustardui.physics_outfits_setup()
        finally:
            ops_outfits_setup.surface_deform_bind = original_bind
        # The expected error is printed
        self._stderr.buffer.seek(0)
        self._stderr.buffer.truncate()

        self.assertEqual(scene.frame_current, 5)
        self.assertTrue(self.physics_settings.enable_physics)
        self.assertTrue(self.subsurf.show_viewport)
        self.assertEqual(self.model["armature"].data.pose_position, "POSE")


class TestJiggleParentToModel(BlenderTestCase):
    # Parent to Model keeps the cage on the body when the armature is not at the origin
    def test_cage_stays_on_body(self):
        for op in (
            bpy.ops.mustardui.model_toolkit_create_jiggle,
            bpy.ops.mustardui.model_toolkit_create_jiggle_accurate,
        ):
            with self.subTest(op.idname_py()):
                reset_scene()
                model = build_model()
                configure_model(model)
                arm, body = model["armature"], model["body"]
                arm.location = (1.0, 0.0, 0.0)
                bm = bmesh.new()
                bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=16, radius=0.5)
                bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, 1))
                bm.to_mesh(body.data)
                bm.free()
                body.vertex_groups["spine"].add(range(len(body.data.vertices)), 1.0, "REPLACE")
                settings = bpy.context.scene.MustardUI_Settings
                settings.viewport_model_selection = False
                settings.panel_model_selection_armature = arm.data

                before = set(bpy.data.objects)
                for v in body.data.vertices:
                    v.select = v.co.x > 0.25
                set_active(body)
                bpy.ops.object.mode_set(mode="EDIT")
                op(parent_to_model=True)
                bpy.ops.object.mode_set(mode="OBJECT")
                bpy.context.view_layer.update()

                cage = max(
                    (o for o in set(bpy.data.objects) - before if o.type == "MESH"),
                    key=lambda o: len(o.data.vertices),
                )
                self.assertEqual(cage.parent, arm)
                world = [cage.matrix_world @ v.co for v in cage.data.vertices]
                center = sum(world, Vector()) / len(world)
                self.assertAlmostEqual(center.x, 1.38, delta=0.05)


class TestCollisionCage(BlenderTestCase):
    def setUp(self):
        super().setUp()
        self.model = build_model()
        configure_model(self.model)
        arm = self.model["armature"]

        # Dense source mesh, so that decimation changes its topology
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, location=(0, 0, 1))
        self.source = bpy.context.active_object
        self.source.parent = arm
        self.source.modifiers.new("Particles", "PARTICLE_SYSTEM")
        self.source.modifiers.new("Dynamic Paint", "DYNAMIC_PAINT")
        self.source.modifiers.new("Collision", "COLLISION")

        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, location=(0, 0, 1))
        self.target = bpy.context.active_object
        self.target.parent = arm
        deform = self.source.modifiers.new("Surface Deform", "SURFACE_DEFORM")
        deform.target = self.target
        smooth = self.source.modifiers.new("Corrective Smooth", "CORRECTIVE_SMOOTH")
        smooth.rest_source = "BIND"
        with bpy.context.temp_override(object=self.source):
            bpy.ops.object.surfacedeform_bind(modifier=deform.name)
            bpy.ops.object.correctivesmooth_bind(modifier=smooth.name)
        set_active(self.source)

    # Non-deforming modifiers are removed, and bound modifiers are rebound to the new topology
    def test_create_cage(self):
        bpy.ops.mustardui.model_toolkit_create_collision_cage(decimate_proxy=True)
        cage = bpy.context.active_object
        self.assertNotEqual(cage, self.source)
        types = {m.type for m in cage.modifiers}
        self.assertFalse(types & {"PARTICLE_SYSTEM", "DYNAMIC_PAINT"})
        self.assertEqual([m.type for m in cage.modifiers].count("COLLISION"), 1)
        self.assertEqual(len(self.source.particle_systems), 1)
        self.assertTrue(cage.modifiers["Surface Deform"].is_bound)
        self.assertTrue(cage.modifiers["Corrective Smooth"].is_bind)

        # Cage follows its Surface Deform target
        def lowest_z():
            depsgraph = bpy.context.evaluated_depsgraph_get()
            return min(v.co.z for v in cage.evaluated_get(depsgraph).data.vertices)

        before = lowest_z()
        for v in self.target.data.vertices:
            v.co.z += 1.0
        self.target.data.update()
        self.assertAlmostEqual(lowest_z() - before, 1.0, places=2)


class TestJiggleDynamics(BlenderTestCase):
    # The jiggle presets run Jiggle Dynamics: the Pin group follows the animation, the rest
    # swings with the motion and settles back to the animated shape
    @unittest.skipIf(bpy.app.version < (5, 2, 0), "Jiggle Dynamics needs Blender 5.2")
    def test_jiggle_preset(self):
        obj = new_mesh_object("Jiggle")
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=0.2)
        verts = [v.co.copy() for v in bm.verts]
        faces = [[v.index for v in face.verts] for face in bm.faces]
        bm.free()
        # Faces in a fixed order: bmesh orders the edges differently at each run, changing the solve
        faces = sorted(min(f[i:] + f[:i] for i in range(len(f))) for f in faces)
        obj.data.clear_geometry()
        obj.data.from_pydata(verts, [], faces)
        rest = np.array([v.co for v in obj.data.vertices])
        pinned = rest[:, 2] < 0.0
        pin = obj.vertex_groups.new(name="Pin")
        pin.add([int(i) for i in np.flatnonzero(pinned)], 1.0, "REPLACE")

        modifier = physics_presets.apply_physics(obj, "NODES", "JIGGLE", pin_group_name="Pin")
        self.assertEqual(modifier.node_group.name, definitions_nodes.JIGGLE_DYNAMICS_NODE_GROUP)
        zone = definitions_nodes.modifier_input(modifier, "Zone")
        self.assertEqual((zone.type, zone.attribute_name), ("ATTRIBUTE", "Pin"))
        self.assertTrue(definitions_nodes.modifier_input(modifier, "Invert Zone").value)
        self.assertAlmostEqual(definitions_nodes.modifier_input(modifier, "Softness").value, 0.274)

        scene = bpy.context.scene
        scene.frame_start, scene.frame_end = 1, 120
        for frame, z in ((1, 0.0), (5, 0.3), (9, 0.0), (120, 0.0)):
            obj.location.z = z
            obj.keyframe_insert("location", frame=frame)
        offsets = []
        for frame in range(1, 121):
            scene.frame_set(frame)
            offsets.append(np.linalg.norm(evaluated_co(obj) - rest, axis=1))
        offsets = np.array(offsets)

        swing = offsets[:, ~pinned].max(axis=1)
        self.assertLess(offsets[:, pinned].max(), 1e-5)
        self.assertGreater(swing.max(), 0.01)
        self.assertLess(swing[-1], 0.1 * swing.max())

        # Switching to the Cloth modifier removes the Jiggle Dynamics one
        physics_presets.apply_physics(obj, "CLOTH", "JIGGLE", pin_group_name="Pin")
        self.assertEqual([m.type for m in obj.modifiers], ["CLOTH"])

    # Assign Physics keeps the Pin group of the physics it replaces, not the active vertex group
    @unittest.skipIf(bpy.app.version < (5, 2, 0), "Jiggle Dynamics needs Blender 5.2")
    def test_assign_keeps_pin_group(self):
        obj = new_mesh_object("Cage")
        obj.vertex_groups.new(name="Pin")
        obj.vertex_groups.new(name="Structural")
        cloth = obj.modifiers.new("Cloth", "CLOTH")
        cloth.settings.vertex_group_mass = "Pin"
        set_active(obj)

        bpy.ops.mustardui.model_toolkit_assign_physics(physics_engine="NODES", nodes_preset="CAGE")
        modifier = obj.modifiers[0]
        self.assertEqual(modifier.node_group.name, definitions_nodes.JIGGLE_DYNAMICS_NODE_GROUP)
        self.assertEqual(definitions_nodes.modifier_input(modifier, "Zone").attribute_name, "Pin")

        bpy.ops.mustardui.model_toolkit_assign_physics(physics_engine="CLOTH")
        self.assertEqual(obj.modifiers[0].settings.vertex_group_mass, "Pin")


@unittest.skipIf(bpy.app.version < (5, 2, 0), "Jiggle Dynamics needs Blender 5.2")
class TestDynamicsBake(BlenderTestCase):
    def setUp(self):
        super().setUp()
        self.model = build_model()
        arm = self.model["armature"]
        configure_model(self.model)
        self.physics_settings = arm.data.MustardUI_PhysicsSettings
        self.cage = new_mesh_object("Jiggle Cage", armature=arm, size=0.4)
        self.modifier = physics_presets.apply_physics(self.cage, "NODES", "CAGE")

        bpy.ops.mustardui.configuration()
        self.physics_settings.enable_ui = True
        set_active(self.cage)
        bpy.ops.mustardui.physics_add_item()
        self.physics_settings.items[0].type = "CAGE"
        set_active(arm)
        bpy.ops.mustardui.configuration()
        self.physics_settings.items[0].enable = True
        self.physics_settings.enable_physics = True

        bpy.context.scene.frame_start, bpy.context.scene.frame_end = 1, 12
        for frame, z in ((1, 0.0), (4, 0.3), (8, 0.0)):
            arm.location.z = z
            arm.keyframe_insert("location", frame=frame)

    def motion(self):
        self.cage.update_tag()
        co = []
        for frame in range(1, 13):
            bpy.context.scene.frame_set(frame)
            co.append(evaluated_co(self.cage))
        return np.array(co)

    # The frame range of the physics is the one of the Geometry Nodes simulations too
    def test_frame_range(self):
        self.physics_settings.frame_start, self.physics_settings.frame_end = 2, 9
        bakes = [
            b for b in self.modifier.bakes if b.node.bl_idname == "GeometryNodeSimulationOutput"
        ]
        self.assertTrue(bakes)
        for bake in bakes:
            self.assertTrue(bake.use_custom_simulation_frame_range)
            self.assertEqual((bake.frame_start, bake.frame_end), (2, 9))

        # Unless the item has its own
        self.physics_settings.items[0].unique_cache_frames = True
        self.physics_settings.frame_end = 11
        self.assertEqual(bakes[0].frame_end, 9)

    # Bake All bakes the Geometry Nodes simulations, and Delete All Bake frees them
    def test_bake_all(self):
        self.physics_settings.frame_start, self.physics_settings.frame_end = 1, 12
        bpy.ops.mustardui.physics_bake_all(bake=True)
        baked = self.motion()
        softness = definitions_nodes.modifier_input(self.modifier, "Softness")
        softness.value = 0.95
        self.assertLess(np.abs(self.motion() - baked).max(), 1e-6)

        bpy.ops.mustardui.physics_bake_delete_all()
        self.assertGreater(np.abs(self.motion() - baked).max(), 1e-3)

    # Physics presets keep the Geometry Nodes inputs by name, menus included
    def test_preset(self):
        get = definitions_nodes.modifier_input
        bpy.ops.mustardui.preset_create(preset_type="PHYSICS", new_preset_name="Soft")
        preset = self.physics_settings.presets[0]
        self.assertTrue(preset.has_nodes)

        get(self.modifier, "Softness").value = 0.9
        get(self.modifier, "Collide With").value = "Group"
        get(self.modifier, "Self Friction").value = 0.9
        bpy.ops.mustardui.preset_apply(preset_type="PHYSICS")

        self.assertAlmostEqual(get(self.modifier, "Softness").value, 0.16, places=5)
        self.assertEqual(get(self.modifier, "Collide With").value, "Whole Mesh")
        self.assertAlmostEqual(get(self.modifier, "Self Friction").value, 0.1, places=5)

    # Mirror copies the Geometry Nodes values and frame range, each side keeping its Pin group
    def test_mirror(self):
        get = definitions_nodes.modifier_input
        self.cage.name = "Jiggle Cage.L"
        right = new_mesh_object("Jiggle Cage.R", armature=self.model["armature"], size=0.4)
        right.vertex_groups.new(name="Pin R")
        right_modifier = physics_presets.apply_physics(right, "NODES", "CAGE", "Pin R")
        item = self.physics_settings.items.add()
        item.object, item.type = right, "CAGE"

        get(self.modifier, "Softness").value = 0.77
        bake = next(b for b in self.modifier.bakes if b.node.name == "Result Cache Out")
        bake.use_custom_simulation_frame_range = True
        bake.frame_start, bake.frame_end = 3, 9
        bpy.ops.mustardui.physics_mirror(obj_name=self.cage.name)

        self.assertAlmostEqual(get(right_modifier, "Softness").value, 0.77, places=5)
        self.assertEqual(get(right_modifier, "Zone").attribute_name, "Pin R")
        bake = next(b for b in right_modifier.bakes if b.node.name == "Result Cache Out")
        self.assertEqual((bake.frame_start, bake.frame_end), (3, 9))

    # Collisions fill the Collection inputs with the collision cages not deformed by the item
    def test_collisions(self):
        hand = new_mesh_object("Hand Collider", armature=self.model["armature"], size=0.3)
        hand.modifiers.new("Collision", "COLLISION")
        body = new_mesh_object("Body Collision", armature=self.model["armature"], size=0.6)
        body.modifiers.new("Deform", "SURFACE_DEFORM").target = self.cage
        body.modifiers.new("Collision", "COLLISION")
        for obj in (hand, body):
            item = self.physics_settings.items.add()
            item.object, item.type = obj, "COLLISION"
        free = self.motion()

        colliders = definitions_nodes.modifier_input(self.modifier, "Colliders")
        self.assertFalse(definitions_nodes.modifier_input(self.modifier, "Collisions").value)
        item = self.physics_settings.items[0]
        item.collisions = True
        self.assertTrue(definitions_nodes.modifier_input(self.modifier, "Collisions").value)
        self.assertEqual(set(colliders.value.objects), {hand})
        self.assertTrue(
            any(
                m.node_group.name.startswith("Collider")
                for m in hand.modifiers
                if m.type == "NODES"
            )
        )
        self.assertGreater(np.abs(self.motion() - free).max(), 1e-3)

        # Off with the Collisions input of the node group, the colliders kept for the next time
        item.collisions = False
        self.assertFalse(definitions_nodes.modifier_input(self.modifier, "Collisions").value)
        self.assertEqual(set(colliders.value.objects), {hand})
        self.assertLess(np.abs(self.motion() - free).max(), 1e-6)

    # An older Jiggle Dynamics in the file is replaced by the bundled one, keeping the values
    def test_node_group_update(self):
        old = self.modifier.node_group
        old["MustardUI Version"] = 1
        definitions_nodes.modifier_input(self.modifier, "Softness").value = 0.66

        group = definitions_nodes.jiggle_dynamics_node_group()
        self.assertNotEqual(group, old)
        self.assertEqual(group.name, definitions_nodes.JIGGLE_DYNAMICS_NODE_GROUP)
        self.assertEqual(self.modifier.node_group, group)
        self.assertAlmostEqual(
            definitions_nodes.modifier_input(self.modifier, "Softness").value, 0.66, places=5
        )
        self.assertEqual(definitions_nodes.jiggle_dynamics_node_group(), group)
