import bpy
from helpers import BlenderTestCase, build_model, configure_model


class TestHair(BlenderTestCase):
    def setUp(self):
        super().setUp()
        self.model = build_model()
        self.rig_settings = configure_model(self.model)

    def visible(self, name):
        obj = bpy.data.objects[name]
        return not obj.hide_viewport and not obj.hide_render

    # Hair list shows the objects of the hair collection
    def test_hair_list(self):
        items = {x[0] for x in self.rig_settings.hair_list_make(bpy.context)}
        self.assertEqual(items, {"Hair Short", "Hair Long"})

    # Switching hair shows only the selected one
    def test_switch_hair(self):
        self.rig_settings.hair_list = "Hair Long"
        self.assertTrue(self.visible("Hair Long"))
        self.assertFalse(self.visible("Hair Short"))

        self.rig_settings.hair_list = "Hair Short"
        self.assertTrue(self.visible("Hair Short"))
        self.assertFalse(self.visible("Hair Long"))

    # Hair global switch toggles the Subdivision modifiers
    def test_global_modifier_switch(self):
        subsurf = bpy.data.objects["Hair Long"].modifiers.new("Subdivision", "SUBSURF")
        self.rig_settings.hair_enable_global_subsurface = True
        bpy.ops.mustardui.hair_switchglobal(enable=0)
        self.assertFalse(subsurf.show_viewport)
        bpy.ops.mustardui.hair_switchglobal(enable=1)
        self.assertTrue(subsurf.show_viewport)
