import importlib
import math

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

    # The armature keeps its pose position
    def test_rest_position_kept(self):
        self.model["armature"].data.pose_position = "REST"
        bpy.ops.mustardui.physics_outfits_setup()
        self.assertEqual(self.model["armature"].data.pose_position, "REST")

    # A failure halfway restores the scene state
    def test_state_restored_on_failure(self):
        def fail(*args):
            raise ValueError("Bind failed")

        scene = bpy.context.scene
        scene.frame_current = 5
        self.physics_settings.enable_physics = True
        original_bind = ops_outfits_setup.MustardUI_Physics_OutfitsSetup.bind
        ops_outfits_setup.MustardUI_Physics_OutfitsSetup.bind = fail
        try:
            with self.assertRaisesRegex(RuntimeError, "Bind failed"):
                bpy.ops.mustardui.physics_outfits_setup()
        finally:
            ops_outfits_setup.MustardUI_Physics_OutfitsSetup.bind = original_bind
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
