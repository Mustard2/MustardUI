import bpy
from helpers import BlenderTestCase, build_model, configure_model, new_mesh_object, set_active


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

    # A mesh can be added as physics item
    def test_add_item(self):
        self.assertEqual([x.object for x in self.physics_settings.items], [self.cage])

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
