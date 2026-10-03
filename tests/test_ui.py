import bpy
from fake_ui import draw_all
from helpers import (
    ADDON,
    BlenderTestCase,
    build_model,
    configure_model,
    new_mesh_object,
    set_active,
)


class TestUI(BlenderTestCase):
    def assertDrawsCleanly(self, expected_panel):
        drawer = draw_all(bpy.context)
        self.assertIn(expected_panel, drawer.drawn)
        self.assertEqual(drawer.errors, [], "\n" + "\n".join(drawer.errors))
        return drawer

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

    # Configuration panels draw with list indices past the end, as left by another model
    def test_draw_configuration_stale_indices(self):
        model = build_model()
        arm = model["armature"].data
        configure_model(model)
        bpy.ops.mustardui.configuration()
        arm.MustardUI_MorphsSettings.enable_ui = True
        bpy.ops.mustardui.morphs_section_add()
        arm.MustardUI_PhysicsSettings.enable_ui = True
        set_active(new_mesh_object("Cage", armature=model["armature"]))
        bpy.ops.mustardui.physics_add_item()
        set_active(model["armature"])
        bpy.ops.mustardui.section_add()
        prefs = bpy.context.preferences.addons[ADDON].preferences
        prefs.developer = prefs.advanced = True

        scene = bpy.context.scene
        for owner, prop, panel in (
            (scene, "mustardui_outfits_uilist_index", "PANEL_PT_MustardUI_InitPanel_Outfit"),
            (scene, "mustardui_section_uilist_index", "PANEL_PT_MustardUI_InitPanel_Model"),
            (arm, "mustardui_morphs_section_uilist_index", "PANEL_PT_MustardUI_InitPanel_Morphs"),
            (arm, "mustardui_physics_items_uilist_index", "PANEL_PT_MustardUI_InitPanel_Physics"),
        ):
            with self.subTest(prop):
                setattr(owner, prop, 5)
                self.assertDrawsCleanly(panel)
                setattr(owner, prop, 0)
        scene.mustardui_section_uilist_index = 5
        self.assertFalse(bpy.ops.mustardui.section_property_assign.poll())
