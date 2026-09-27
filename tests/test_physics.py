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
