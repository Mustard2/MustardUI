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

    # Morphs panels draw with the settings open and the morphs disabled, for each type
    def test_draw_morphs_settings(self):
        model = build_model()
        arm = model["armature"].data
        model["armature"]["body_bs_Wide"] = 0.0
        configure_model(model)
        bpy.context.preferences.addons[ADDON].preferences.developer = True
        morphs = arm.MustardUI_MorphsSettings
        for morphs_type in ("GENERIC", "DIFFEO_GENESIS_9"):
            with self.subTest(morphs_type):
                bpy.ops.mustardui.configuration()
                morphs.sections.clear()
                morphs.enable_ui = True
                morphs.type = morphs_type
                morphs.diffeomorphic_body_morphs = True
                # Diffeomorphic sections come first, as in the Configuration panel
                if morphs_type != "GENERIC":
                    bpy.ops.mustardui.morphs_check()
                bpy.ops.mustardui.morphs_section_add()
                arm.mustardui_morphs_section_uilist_index = len(morphs.sections) - 1
                morphs.sections[-1].string = "Blink"
                morphs.sections[-1].shape_keys = True
                bpy.ops.mustardui.morphs_check()
                self.assertDrawsCleanly("PANEL_PT_MustardUI_InitPanel_Morphs")
                bpy.ops.mustardui.configuration()
                morphs.diffeomorphic_enable_settings = True
                drawer = self.assertDrawsCleanly("PANEL_PT_MustardUI_Morphs")
                if morphs_type != "GENERIC":
                    self.assertIn("PANEL_PT_MustardUI_Morphs_Body", drawer.drawn)
                    self.assertIn("PANEL_PT_MustardUI_Morphs_Custom", drawer.drawn)
                morphs.diffeomorphic_enable = False
                self.assertDrawsCleanly("PANEL_PT_MustardUI_Morphs")
                morphs.diffeomorphic_enable = True

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
        arm.collections.active = arm.collections.new("Parent")
        arm.collections.new("Child", parent=arm.collections.active)

        scene = bpy.context.scene
        for owner, prop, panel in (
            (scene, "mustardui_outfits_uilist_index", "PANEL_PT_MustardUI_InitPanel_Outfit"),
            (scene, "mustardui_section_uilist_index", "PANEL_PT_MustardUI_InitPanel_Model"),
            (arm, "mustardui_morphs_section_uilist_index", "PANEL_PT_MustardUI_InitPanel_Morphs"),
            (arm, "mustardui_physics_items_uilist_index", "PANEL_PT_MustardUI_InitPanel_Physics"),
            (scene, "mustardui_armature_uilist_index", "PANEL_PT_MustardUI_InitPanel_Armature"),
        ):
            with self.subTest(prop):
                setattr(owner, prop, 5)
                self.assertDrawsCleanly(panel)
                setattr(owner, prop, 0)
        scene.mustardui_section_uilist_index = 5
        self.assertFalse(bpy.ops.mustardui.section_property_assign.poll())
