import importlib

import bpy
from fake_ui import draw_all
from helpers import ADDON, BlenderTestCase, build_model, configure_model

lipsync = importlib.import_module(ADDON + ".tools.lipsync")

PREFIX = "facs_ctrl_v"


class TestLipSync(BlenderTestCase):
    def setUp(self):
        super().setUp()
        self.model = build_model()
        self.body = self.model["body"]
        self.arm_obj = self.model["armature"]
        for vis in lipsync.VISEMES:
            self.body.shape_key_add(name=PREFIX + vis, from_mix=False)
        configure_model(self.model)
        self.tools = self.arm_obj.data.MustardUI_ToolsSettings
        self.tools.lipsync_enable = True
        bpy.context.scene.frame_current = 10

    def fcurves(self, id_data):
        return {fc.data_path: fc for fc in lipsync._action_fcurves(id_data)}

    # Text lip sync keys shape keys in a new action, or merges into it
    def test_shape_keys_from_text(self):
        self.assertEqual(bpy.ops.mustardui.tools_lipsync(), {"FINISHED"})

        action = self.body.data.shape_keys.animation_data.action
        self.assertEqual(action.name, "HelloWorldThisIsALipSyncTest")
        fcurves = self.fcurves(self.body.data.shape_keys)
        self.assertIn(f'key_blocks["{PREFIX}M"].value', fcurves)
        # No keyframe before the playhead, values stay in range
        for fc in fcurves.values():
            for kp in fc.keyframe_points:
                self.assertGreaterEqual(kp.co[0], 10 - 1e-4)
                self.assertGreaterEqual(kp.co[1], 0.0)
                self.assertLessEqual(kp.co[1], 1.0 + 1e-4)

        # A new run creates a new action
        self.tools.lipsync_text = "Second one"
        bpy.ops.mustardui.tools_lipsync()
        self.assertEqual(self.body.data.shape_keys.animation_data.action.name, "SecondOne")
        self.assertTrue(action.use_fake_user)

        # Merge into the current action when disabled
        self.tools.lipsync_new_action = False
        bpy.ops.mustardui.tools_lipsync()
        self.assertEqual(self.body.data.shape_keys.animation_data.action.name, "SecondOne")

    # Viseme substitutions apply, and an invalid one raises an error
    def test_substitution_and_missing(self):
        self.body.shape_key_remove(self.body.data.shape_keys.key_blocks[PREFIX + "AA"])
        self.tools.lipsync_substitutions = "AA:EH"
        self.tools.lipsync_input = "ARPABET"
        self.tools.lipsync_arpabet = "AA1 AA0"
        self.tools.lipsync_smoothing = 0.0
        self.assertEqual(bpy.ops.mustardui.tools_lipsync(), {"FINISHED"})

        fcurves = self.fcurves(self.body.data.shape_keys)
        fc = fcurves[f'key_blocks["{PREFIX}EH"].value']
        # EH driven at the AA peak strength
        self.assertAlmostEqual(max(kp.co[1] for kp in fc.keyframe_points), 1.0)

        self.tools.lipsync_substitutions = "AA:XX"
        with self.assertRaises(RuntimeError):
            bpy.ops.mustardui.tools_lipsync()

    # Timed segments land at the same time at any frame rate
    def test_timed_fps_independent(self):
        text = bpy.data.texts.new("segments")
        text.write("# label start end\nM 0.0 0.5\nAA 0.5 1.0\n")
        self.tools.lipsync_input = "TIMED"
        self.tools.lipsync_timed_text = text
        self.tools.lipsync_smoothing = 0.0
        scene = bpy.context.scene

        peaks = []
        for fps in (24, 60):
            scene.render.fps = fps
            bpy.ops.mustardui.tools_lipsync()
            fc = self.fcurves(self.body.data.shape_keys)[f'key_blocks["{PREFIX}AA"].value']
            peak = max(fc.keyframe_points, key=lambda kp: kp.co[1]).co[0]
            peaks.append((peak - 10) / fps)
        self.assertAlmostEqual(peaks[0], 0.75, places=3)
        self.assertAlmostEqual(peaks[1], 0.75, places=3)

    # Morph lip sync merges into the armature action without duplicates
    def test_morph_merges_into_armature_action(self):
        for vis in lipsync.VISEMES:
            self.arm_obj[PREFIX + vis] = 0.0
        self.arm_obj.location.x = 1.0
        self.arm_obj.keyframe_insert("location", index=0, frame=1)
        body_action = self.arm_obj.animation_data.action
        self.tools.lipsync_driver_type = "MORPH"

        for _ in range(2):
            self.assertEqual(bpy.ops.mustardui.tools_lipsync(), {"FINISHED"})

        self.assertIs(self.arm_obj.animation_data.action, body_action)
        fcurves = lipsync._action_fcurves(self.arm_obj)
        paths = [fc.data_path for fc in fcurves]
        self.assertIn("location", paths)
        self.assertIn(f'["{PREFIX}M"]', paths)
        # Re-running replaces the viseme curves instead of duplicating them
        self.assertEqual(len(paths), len(set(paths)))

    # Morph lip sync works with every custom property source
    def test_morph_sources(self):
        self.tools.lipsync_driver_type = "MORPH"
        for source, owner in (
            ("ARMATURE_DATA", self.arm_obj.data),
            ("BODY_OBJ", self.body),
            ("BODY_DATA", self.body.data),
        ):
            for vis in lipsync.VISEMES:
                owner[PREFIX + vis] = 0.0
            self.tools.lipsync_source = source
            self.assertEqual(bpy.ops.mustardui.tools_lipsync(), {"FINISHED"})
            self.assertIn(f'["{PREFIX}M"]', self.fcurves(owner))
            # Blender adds .001 to duplicate names
            self.assertTrue(owner.animation_data.action.name.startswith("HelloWorldThisIsALipSync"))

    # Lip sync panels draw cleanly for every driver type and input
    def test_draw_panels(self):
        for mode in ("SHAPE_KEY", "MORPH"):
            self.tools.lipsync_driver_type = mode
            for source in ("TEXT", "ARPABET", "TIMED"):
                self.tools.lipsync_input = source
                drawer = draw_all(bpy.context)
                self.assertIn("PANEL_PT_MustardUI_Tools_LipSync", drawer.drawn)
                self.assertEqual(drawer.errors, [])

        bpy.ops.mustardui.configuration()
        bpy.context.preferences.addons[ADDON].preferences.developer = True
        drawer = draw_all(bpy.context)
        self.assertIn("PANEL_PT_MustardUI_InitPanel_Tools", drawer.drawn)
        self.assertEqual(drawer.errors, [])

    # Substitution, timed segment and text parsers
    def test_parse_helpers(self):
        self.assertEqual(lipsync.parse_substitutions(" aa : eh ; IY=EE"), {"AA": "EH", "IY": "EE"})
        segs = lipsync.parse_timed("AH1 0.2 0.3\nM,0,0.2")
        self.assertEqual([s["vis"] for s in segs], ["M", "AA"])
        tokens, unknown = lipsync.text_to_tokens("Hi.")
        self.assertIn("<SENT>", tokens)

    # CMU dictionary lookup, apostrophes and the fallback speller
    def test_cmu_dictionary(self):
        # Dictionary words, including apostrophes; unknown words use the fallback speller
        tokens, unknown = lipsync.text_to_tokens("Thought, don't Zyxqwv!")
        self.assertEqual(tokens[:4], ["TH", "AO", "T", "<WORD>"])
        self.assertEqual(tokens[5:9], ["D", "OW", "N", "T"])
        self.assertEqual(unknown, ["Zyxqwv"])
        self.assertEqual(tokens[-1], "<SENT>")
