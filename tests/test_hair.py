import bpy
from helpers import BlenderTestCase, build_model, configure_model, new_mesh_object, new_object


class TestHair(BlenderTestCase):
    def setUp(self):
        super().setUp()
        self.model = build_model()
        self.rig_settings = configure_model(self.model)

    def visible(self, name):
        obj = bpy.data.objects[name]
        return not obj.hide_viewport and not obj.hide_render

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

    # Clean Model deletes the hair not in use and their rigs, keeping the rigs of the selected hair
    def test_clean_model_unselected_hair(self):
        hair = self.model["hair"]
        rigs = {}
        for name, users in (
            ("Short Rig", ("Hair Short",)),
            ("Long Rig", ("Hair Long",)),
            ("Shared Rig", ("Hair Short", "Hair Long")),
        ):
            rigs[name] = new_object(name, bpy.data.armatures.new(name), hair)
            for user in users:
                bpy.data.objects[user].modifiers.new(name, "ARMATURE").object = rigs[name]
        bpy.data.objects["Hair Long"].parent = rigs["Long Rig"]
        new_mesh_object("Hair Short Bangs", hair)
        self.rig_settings.hair_list = "Hair Short"

        bpy.ops.mustardui.cleanmodel(remove_unselected_hair=True)
        self.assertEqual(
            sorted(o.name for o in hair.objects), ["Hair Short", "Shared Rig", "Short Rig"]
        )

    # Deleting a hair before the selected one keeps the selection, and Clean Model the worn hair
    def test_selection_after_deleting_hair(self):
        new_mesh_object("Hair Bob", self.model["hair"])
        self.rig_settings.hair_list = "Hair Long"
        bpy.data.objects.remove(bpy.data.objects["Hair Short"])
        self.assertEqual(self.rig_settings.hair_list, "Hair Long")

        bpy.ops.mustardui.cleanmodel(remove_unselected_hair=True)
        self.assertEqual([o.name for o in self.model["hair"].objects], ["Hair Long"])
