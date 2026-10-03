import math

import bpy
from helpers import BlenderTestCase, build_model, configure_model, set_active
from mathutils import Matrix


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
