import bpy
from fake_ui import addon_classes, draw_all
from helpers import ADDON, BlenderTestCase, build_model, configure_model, set_active


class TestUI(BlenderTestCase):
    def assertDrawsCleanly(self, expected_panel):
        drawer = draw_all(bpy.context)
        self.assertIn(expected_panel, drawer.drawn)
        self.assertEqual(drawer.errors, [], "\n" + "\n".join(drawer.errors))
        return drawer

    # Panels and UI lists are registered
    def test_classes_registered(self):
        self.assertGreater(len(addon_classes(bpy.types.Panel)), 20)
        self.assertGreater(len(addon_classes(bpy.types.UIList)), 10)

    # Quick Setup panels draw before and after the scan
    def test_draw_quick_setup(self):
        model = build_model()
        rig_settings = model["armature"].data.MustardUI_RigSettings
        set_active(model["armature"])
        bpy.context.preferences.addons[ADDON].preferences.quick_setup = True
        self.assertDrawsCleanly("PANEL_PT_MustardUI_QuickSetup")

        rig_settings.model_name = "Tester"
        rig_settings.model_body = model["body"]
        bpy.ops.mustardui.quick_setup_smart_check()
        self.assertDrawsCleanly("PANEL_PT_MustardUI_QuickSetup_Outfits")

    # Configuration panels draw before and after the first configuration
    def test_draw_configuration(self):
        model = build_model()
        set_active(model["armature"])
        prefs = bpy.context.preferences.addons[ADDON].preferences
        prefs.developer = True
        self.assertDrawsCleanly("PANEL_PT_MustardUI_InitPanel")

        configure_model(model)
        bpy.ops.mustardui.configuration()
        prefs.debug = True
        self.assertDrawsCleanly("PANEL_PT_MustardUI_InitPanel_Outfit")

    # User panels draw for a configured model
    def test_draw_user(self):
        model = build_model()
        configure_model(model)
        drawer = self.assertDrawsCleanly("PANEL_PT_MustardUI_Outfits")
        self.assertIn("PANEL_PT_MustardUI_Hair", drawer.drawn)

    # User panels draw with morphs and physics enabled
    def test_draw_user_with_features(self):
        model = build_model()
        arm = model["armature"].data
        configure_model(model)
        bpy.ops.mustardui.configuration()
        morphs = arm.MustardUI_MorphsSettings
        morphs.enable_ui = True
        morphs.type = "GENERIC"
        bpy.ops.mustardui.morphs_section_add()
        morphs.sections[0].string = "Blink"
        morphs.sections[0].shape_keys = True
        bpy.ops.mustardui.morphs_check()
        arm.MustardUI_PhysicsSettings.enable_ui = True
        bpy.ops.mustardui.configuration()
        self.assertDrawsCleanly("PANEL_PT_MustardUI_Morphs")

    # User panels draw with panel model selection
    def test_draw_panel_model_selection(self):
        model = build_model()
        configure_model(model)
        settings = bpy.context.scene.MustardUI_Settings
        settings.viewport_model_selection = False
        settings.panel_model_selection_armature = model["armature"].data
        self.assertDrawsCleanly("PANEL_PT_MustardUI_Outfits")
