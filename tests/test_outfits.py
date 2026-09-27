import bpy
from helpers import BlenderTestCase, build_model, configure_model


class TestOutfits(BlenderTestCase):
    def setUp(self):
        super().setUp()
        self.model = build_model()
        self.rig_settings = configure_model(self.model)

    def visible(self, name):
        obj = bpy.data.objects[name]
        return not obj.hide_viewport and not obj.hide_render

    # Outfit list has Nude plus the outfit collections
    def test_outfit_list(self):
        items = [x[0] for x in self.rig_settings.outfits_list_make(bpy.context)]
        self.assertEqual(items, ["Nude", "Tester Casual", "Tester Formal"])

    # Switching outfit shows only its pieces, Nude hides all
    def test_switch_outfit(self):
        self.rig_settings.outfits_list = "Tester Casual"
        self.assertTrue(self.visible("Casual - Shirt"))
        self.assertTrue(self.visible("Casual - Pants"))
        self.assertFalse(self.visible("Formal - Dress"))

        self.rig_settings.outfits_list = "Tester Formal"
        self.assertFalse(self.visible("Casual - Shirt"))
        self.assertTrue(self.visible("Formal - Dress"))

        self.rig_settings.outfits_list = "Nude"
        for name in ("Casual - Shirt", "Casual - Pants", "Formal - Dress"):
            self.assertFalse(self.visible(name))

    # Body masks follow the outfit and the global mask switch
    def test_outfit_masks(self):
        mask = self.model["body"].modifiers["Formal - Dress"]
        self.rig_settings.outfits_list = "Tester Formal"
        self.assertTrue(mask.show_viewport)
        self.rig_settings.outfits_list = "Tester Casual"
        self.assertFalse(mask.show_viewport)

        self.rig_settings.outfits_global_mask = False
        self.rig_settings.outfits_list = "Tester Formal"
        self.assertFalse(mask.show_viewport)

    # Single piece visibility toggles only that piece
    def test_piece_visibility(self):
        self.rig_settings.outfits_list = "Tester Casual"
        bpy.ops.mustardui.object_visibility(obj="Casual - Shirt")
        self.assertFalse(self.visible("Casual - Shirt"))
        self.assertTrue(self.visible("Casual - Pants"))
        bpy.ops.mustardui.object_visibility(obj="Casual - Shirt")
        self.assertTrue(self.visible("Casual - Shirt"))

    # Toggling a piece toggles its body mask
    def test_piece_visibility_drives_mask(self):
        mask = self.model["body"].modifiers["Formal - Dress"]
        self.rig_settings.outfits_list = "Tester Formal"
        bpy.ops.mustardui.object_visibility(obj="Formal - Dress")
        self.assertFalse(mask.show_viewport)
        bpy.ops.mustardui.object_visibility(obj="Formal - Dress")
        self.assertTrue(mask.show_viewport)

    # Extras visibility can be toggled
    def test_extras_visibility(self):
        bpy.ops.mustardui.object_visibility(obj="Extras - Glasses")
        glasses = self.visible("Extras - Glasses")
        bpy.ops.mustardui.object_visibility(obj="Extras - Glasses")
        self.assertNotEqual(glasses, self.visible("Extras - Glasses"))

    # Outfit global switch toggles the Smooth Corrective modifiers
    def test_global_modifier_switch(self):
        shirt = bpy.data.objects["Casual - Shirt"]
        smooth = shirt.modifiers.new("Smooth", "CORRECTIVE_SMOOTH")
        self.rig_settings.outfits_enable_global_smoothcorrection = True
        self.rig_settings.outfits_global_smoothcorrection = False
        self.assertFalse(smooth.show_viewport)
        self.rig_settings.outfits_global_smoothcorrection = True
        self.assertTrue(smooth.show_viewport)

    # Deleting an outfit removes it and its objects
    def test_delete_outfit(self):
        bpy.ops.mustardui.configuration()
        bpy.context.scene.mustardui_outfits_uilist_index = 1
        bpy.ops.mustardui.delete_outfit(is_config=True)
        self.assertEqual(
            [x.collection.name for x in self.rig_settings.outfits_collections], ["Tester Casual"]
        )
        self.assertNotIn("Formal - Dress", bpy.data.objects)
