import addon_utils
import bpy
from helpers import ADDON, BlenderTestCase, build_model, configure_model, new_object


class TestRegister(BlenderTestCase):
    # Add-on unregisters cleanly and works again after re-enabling
    def test_disable_enable(self):
        addon_utils.disable(ADDON, default_set=True, handle_error=None)
        self.assertFalse(hasattr(bpy.types.Armature, "MustardUI_RigSettings"))
        self.assertFalse(hasattr(bpy.types, "PANEL_PT_MustardUI_Outfits"))

        addon_utils.enable(ADDON, default_set=True, handle_error=None)
        self.assertTrue(hasattr(bpy.types.Armature, "MustardUI_RigSettings"))
        self.assertTrue(hasattr(bpy.types, "PANEL_PT_MustardUI_Outfits"))

        # The add-on still works after being re-enabled
        rig_settings = configure_model(build_model())
        self.assertTrue(rig_settings.id_data.MustardUI_enable)


class TestSimplify(BlenderTestCase):
    def setUp(self):
        super().setUp()
        self.model = build_model()
        self.rig_settings = configure_model(self.model)
        self.simplify = self.model["armature"].data.MustardUI_SimplifySettings
        self.simplify.simplify_main_enable = True
        self.rig_settings.outfits_list = "Tester Casual"

    # Simplify hides hair and extras, switches to Nude, and restores on disable
    def test_simplify(self):
        glasses = bpy.data.objects["Extras - Glasses"]
        glasses_visible = glasses.MustardUI_outfit_visibility

        self.simplify.simplify_outfit_switch_nude = True
        self.simplify.simplify_enable = True
        self.assertTrue(self.model["hair"].hide_viewport)
        self.assertEqual(self.rig_settings.outfits_list, "Nude")
        self.assertTrue(glasses.hide_viewport)

        self.simplify.simplify_enable = False
        self.assertFalse(self.model["hair"].hide_viewport)
        self.assertEqual(glasses.MustardUI_outfit_visibility, glasses_visible)

    def check_armature_children(self):
        prop = new_object("Prop")
        prop.parent = self.model["armature"]
        self.simplify.simplify_enable = True
        self.assertTrue(prop.hide_viewport)
        self.assertFalse(bpy.data.objects["Casual - Shirt"].hide_viewport)
        self.simplify.simplify_enable = False
        self.assertFalse(prop.hide_viewport)

    # Simplify hides other armature children when a piece is in two outfits
    def test_simplify_shared_piece(self):
        self.model["outfits"][1].objects.link(bpy.data.objects["Casual - Shirt"])
        self.check_armature_children()

    # Simplify hides other armature children when an outfit collection was deleted
    def test_simplify_missing_outfit_collection(self):
        bpy.data.collections.remove(self.model["outfits"][1])
        self.check_armature_children()


class TestConfigurationLists(BlenderTestCase):
    def setUp(self):
        super().setUp()
        self.model = build_model()
        configure_model(self.model)
        self.arm = self.model["armature"].data
        bpy.ops.mustardui.configuration()

    # Body custom property sections can be added and removed
    def test_body_sections(self):
        sections = self.arm.MustardUI_RigSettings.body_custom_properties_sections
        bpy.ops.mustardui.section_add()
        bpy.ops.mustardui.section_add()
        self.assertEqual(len(sections), 2)
        bpy.context.scene.mustardui_section_uilist_index = 0
        bpy.ops.mustardui.section_delete()
        self.assertEqual(len(sections), 1)

    # Armature Smart Check adds the Rigify bone collections to the UI
    def test_armature_smartcheck_rigify(self):
        arm = self.model["armature"]
        arm.data["rig_id"] = "test"
        torso = arm.data.collections.new("Torso")
        torso.assign(arm.data.bones["spine"])
        bpy.ops.mustardui.armature_smartcheck(reset_current_collections=True)
        self.assertTrue(torso.MustardUI_ArmatureBoneCollection.is_in_UI)
        self.assertFalse(arm.data.collections_all["Body"].MustardUI_ArmatureBoneCollection.is_in_UI)

    # Bone collections named after a piece follow its visibility
    def test_outfit_switcher_bone_collection(self):
        arm = self.model["armature"].data
        shirt_bones = arm.collections.new("Casual - Shirt")
        shirt_bones.assign(arm.bones["head"])
        bpy.ops.mustardui.armature_smartcheck()
        settings = shirt_bones.MustardUI_ArmatureBoneCollection
        self.assertTrue(settings.outfit_switcher_enable)
        self.assertEqual(settings.outfit_switcher_object, bpy.data.objects["Casual - Shirt"])

        bpy.ops.mustardui.configuration()
        rig_settings = arm.MustardUI_RigSettings
        rig_settings.outfits_list = "Tester Casual"
        self.assertTrue(shirt_bones.is_visible)
        rig_settings.outfits_list = "Tester Formal"
        self.assertFalse(shirt_bones.is_visible)
        rig_settings.outfits_list = "Tester Casual"
        bpy.ops.mustardui.object_visibility(obj="Casual - Shirt")
        self.assertFalse(shirt_bones.is_visible)
