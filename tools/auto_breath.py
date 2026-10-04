import math
import random

import bpy

from ..model_selection.active_object import ModelMode, mustardui_active_object


class MustardUI_Tools_AutoBreath(bpy.types.Operator):
    """Automatically create keyframes for breathing animation"""

    bl_idname = "mustardui.tools_autobreath"
    bl_label = "Auto Breath"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=ModelMode.USER)
        if bpy.context.selected_pose_bones is not None:
            return res and len(bpy.context.selected_pose_bones) == 1
        return False

    def execute(self, context):

        poll, arm = mustardui_active_object(context, config=ModelMode.USER)
        tools_settings = arm.MustardUI_ToolsSettings

        if len(bpy.context.selected_pose_bones) != 1:
            self.report(
                {"ERROR"},
                "MustardUI - You should select one bone only. No key has been added.",
            )
            return {"FINISHED"}

        # Check scene settings
        frame_start = context.scene.frame_start
        frame_end = context.scene.frame_end
        fps = context.scene.render.fps / context.scene.render.fps_base
        context.scene.frame_current = frame_start

        # Selected bone
        breath_bone = bpy.context.selected_pose_bones[0]

        # Check which transformations are available, and save the rest pose
        lock_loc = [1, 1, 1]
        rest_loc = [0.0, 0.0, 0.0]
        lock_sca = [1, 1, 1]
        rest_sca = [0.0, 0.0, 0.0]
        for i in range(3):
            lock_loc[i] = not breath_bone.lock_location[i]
            rest_loc[i] = breath_bone.location[i]
            lock_sca[i] = not breath_bone.lock_scale[i]
            rest_sca[i] = breath_bone.scale[i]

        # Check if the bones are complying with definitions of rest pose (value = 1.)
        warning = False
        for i in range(3):
            if lock_loc[i]:
                if breath_bone.location[i] != 1.0:
                    warning = True
                    break
            if lock_sca[i]:
                if breath_bone.scale[i] != 1.0:
                    warning = True
                    break

        # Compute quantities
        period = fps * 60.0 / tools_settings.autobreath_frequency
        amplitude = tools_settings.autobreath_amplitude
        sampling = tools_settings.autobreath_sampling
        rand = tools_settings.autobreath_random

        # Inhale takes ~40% of each breath, exhale is the longer, passive part
        inhale_ratio = 0.4

        # Randomize period and depth per breath, not per frame
        breaths = []
        start = frame_start
        while start <= frame_end:
            length = period * (1.0 + random.uniform(-rand, rand))
            depth = amplitude * (1.0 + random.uniform(-rand, rand))
            breaths.append((start, length, depth))
            start += length

        # Create frames
        index = 0
        for frame in range(frame_start, frame_end + 1, sampling):
            while frame >= breaths[index][0] + breaths[index][1]:
                index += 1
            start, length, depth = breaths[index]

            t = (frame - start) / length
            if t < inhale_ratio:
                phase = t / inhale_ratio
            else:
                phase = 1.0 + (t - inhale_ratio) / (1.0 - inhale_ratio)
            factor = (1.0 - math.cos(math.pi * phase)) * 0.5 * depth

            for i in range(3):
                breath_bone.location[i] = rest_loc[i] * (1.0 + lock_loc[i] * factor)
                breath_bone.scale[i] = rest_sca[i] * (1 + lock_sca[i] * factor)

            if any(lock_loc):
                breath_bone.keyframe_insert(data_path="location", frame=frame)
            if any(lock_sca):
                breath_bone.keyframe_insert(data_path="scale", frame=frame)

        if warning:
            self.report(
                {"WARNING"},
                "MustardUI - Initial unlocked transformations should be = 1. Results "
                "might be incorrect",
            )
        else:
            self.report(
                {"INFO"},
                "MustardUI - Auto Breath applied with " + str(breath_bone.name) + ".",
            )

        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_Tools_AutoBreath)


def unregister():
    bpy.utils.unregister_class(MustardUI_Tools_AutoBreath)
