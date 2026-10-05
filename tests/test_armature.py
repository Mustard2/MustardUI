import math

import bpy
from helpers import BlenderTestCase, build_model, configure_model, new_object, set_active
from mathutils import Matrix


class TestTransferAnimation(BlenderTestCase):
    def rig(self, name):
        obj = new_object(name, bpy.data.armatures.new(name))
        set_active(obj)
        bpy.ops.object.mode_set(mode="EDIT")
        obj.data.edit_bones.new("bone").tail = (0, 0, 1)
        bpy.ops.object.mode_set(mode="OBJECT")
        return obj

    def action(self, obj, name, keys):
        obj.animation_data.action = bpy.data.actions.new(name)
        bone = obj.pose.bones["bone"]
        for frame, value in keys:
            bone.location.x = value
            bone.keyframe_insert("location", index=0, frame=frame)
        return obj.animation_data.action

    # Actions, NLA strips and their animated influence and time are copied, drivers are kept
    def test_transfer(self):
        source, target = self.rig("Source"), self.rig("Target")
        target.pose.bones["bone"].constraints.new("COPY_ROTATION").driver_add("influence")

        ad = source.animation_data_create()
        base = self.action(source, "Base", [(1, 0.0), (21, 2.0)])
        layer = self.action(source, "Layer", [(1, 0.0), (11, -1.0)])
        self.action(source, "Active", [(1, 0.0), (41, 0.5)])
        ad.action_blend_type = "ADD"
        ad.action_influence = 0.5
        ad.action_extrapolation = "NOTHING"

        strip = ad.nla_tracks.new().strips.new("Base", 5, base)
        strip.scale = 1.5
        strip.repeat = 1.5
        strip.use_auto_blend = False
        strip.blend_in, strip.blend_out = 3.0, 4.0
        strip.extrapolation = "HOLD_FORWARD"
        strip.use_animated_influence = True
        for frame, value in ((5, 0.2), (30, 1.0)):
            strip.influence = value
            strip.keyframe_insert("influence", frame=frame)

        track = ad.nla_tracks.new()
        strip = track.strips.new("Layer", 10, layer)
        strip.blend_type = "ADD"
        strip.use_animated_time = True
        for frame, value in ((10, 11.0), (20, 1.0)):
            strip.strip_time = value
            strip.keyframe_insert("strip_time", frame=frame)
        track.is_solo = True

        set_active(target)
        source.select_set(True)
        bpy.ops.mustardui.armature_transfer_animation()

        tgt_ad = target.animation_data
        self.assertEqual(len(tgt_ad.drivers), 1)
        self.assertNotEqual(tgt_ad.action, ad.action)
        for attr in ("action_blend_type", "action_influence", "action_extrapolation", "use_nla"):
            self.assertEqual(getattr(tgt_ad, attr), getattr(ad, attr), attr)
        for src_track, tgt_track in zip(ad.nla_tracks, tgt_ad.nla_tracks, strict=True):
            self.assertEqual(tgt_track.is_solo, src_track.is_solo)
            for src_strip, tgt_strip in zip(src_track.strips, tgt_track.strips, strict=True):
                self.assertNotEqual(tgt_strip.action, src_strip.action)
                for attr in (
                    "frame_start",
                    "frame_end",
                    "action_frame_start",
                    "action_frame_end",
                    "scale",
                    "repeat",
                    "blend_in",
                    "blend_out",
                    "use_auto_blend",
                    "blend_type",
                    "extrapolation",
                    "use_animated_influence",
                    "use_animated_time",
                ):
                    self.assertEqual(getattr(tgt_strip, attr), getattr(src_strip, attr), attr)

        # Both rigs move the same over the whole animation, also with all the tracks evaluated
        scene = bpy.context.scene
        for solo in (True, False):
            ad.nla_tracks[1].is_solo = tgt_ad.nla_tracks[1].is_solo = solo
            for frame in range(0, 50, 3):
                scene.frame_set(frame)
                src_loc = source.pose.bones["bone"].matrix_basis.translation
                tgt_loc = target.pose.bones["bone"].matrix_basis.translation
                for a, b in zip(src_loc, tgt_loc, strict=True):
                    self.assertAlmostEqual(a, b, places=5, msg=f"frame {frame}, solo {solo}")


class TestSplineIK(BlenderTestCase):
    def setUp(self):
        super().setUp()
        self.model = build_model()
        configure_model(self.model)
        self.arm = self.model["armature"]

        # Tail chain of 5 connected bones, posed by rotating its root
        set_active(self.arm)
        bpy.ops.object.mode_set(mode="EDIT")
        parent = self.arm.data.edit_bones["root"]
        self.chain = []
        for i in range(5):
            bone = self.arm.data.edit_bones.new(f"Tail.{i}")
            bone.head, bone.tail = (0, 0.2 * i, 0.3), (0, 0.2 * (i + 1), 0.3)
            bone.parent = parent
            bone.use_connect = i > 0
            parent = bone
            self.chain.append(bone.name)
        bpy.ops.object.mode_set(mode="POSE")
        for pose_bone in self.arm.pose.bones:
            selectable = pose_bone if bpy.app.version >= (5, 0, 0) else pose_bone.bone
            selectable.select = pose_bone.name in self.chain
        tail = self.arm.pose.bones["Tail.0"]
        tail.rotation_mode = "XYZ"
        tail.rotation_euler = (math.radians(60), 0, 0)

    def assertVectorsEqual(self, a, b):
        for x, y in zip(a, b, strict=True):
            self.assertAlmostEqual(x, y, places=4)

    # Controllers and curve are built on the rest pose, also when the rig is posed
    def test_create_on_posed_rig(self):
        bpy.ops.mustardui.model_toolkit_ikspline()

        bones = self.arm.data.bones
        rest_heads = [bones[name].head_local for name in self.chain]
        controllers = [x for x in bones if x.name.startswith("MustardUI.IKSpline.Bone")]
        curve = next(x for x in self.arm.children if x.name.startswith("MustardUI.IKSpline.Curve"))
        points = curve.data.splines[0].bezier_points
        for i, k in enumerate((0, 2, 4)):
            self.assertVectorsEqual(controllers[i].head_local, rest_heads[k])
            self.assertVectorsEqual(points[i].co, rest_heads[k])

        # Back in rest pose, the chain follows the curve in its rest shape
        for pose_bone in self.arm.pose.bones:
            pose_bone.matrix_basis = Matrix()
        bpy.context.view_layer.update()
        for name, head in zip(self.chain, rest_heads, strict=True):
            self.assertVectorsEqual(self.arm.pose.bones[name].head, head)
