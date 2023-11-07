import bpy
from ..model_selection.active_object import *
import math
import random


class MustardUI_Tools_AutoBreath(bpy.types.Operator):
    """Automatically create keyframes for breathing animation"""
    bl_idname = "mustardui.tools_autobreath"
    bl_label = "Auto Breath"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        if bpy.context.selected_pose_bones is not None:
            return res and len(bpy.context.selected_pose_bones) == 1
        return False

    def execute(self, context):

        poll, arm = mustardui_active_object(context, config=0)
        tools_settings = arm.MustardUI_ToolsSettings

        if len(bpy.context.selected_pose_bones) != 1:
            self.report({'ERROR'}, 'MustardUI - You should select one bone only. No key has been added.')
            return {'FINISHED'}

        # Check scene settings
        frame_start = context.scene.frame_start
        frame_end = context.scene.frame_end
        fps = context.scene.render.fps / context.scene.render.fps_base
        context.scene.frame_current = frame_start

        # Selected bone
        breath_bone = bpy.context.selected_pose_bones[0]

        # Check which transformations are available, and save the rest pose
        lock_loc = [1, 1, 1]
        rest_loc = [0., 0., 0.]
        lock_sca = [1, 1, 1]
        rest_sca = [0., 0., 0.]
        for i in range(3):
            lock_loc[i] = not breath_bone.lock_location[i]
            rest_loc[i] = breath_bone.location[i]
            lock_sca[i] = not breath_bone.lock_scale[i]
            rest_sca[i] = breath_bone.scale[i]

        # Check if the bones are complying with definitions of rest pose (value = 1.)
        warning = False
        for i in range(3):
            if lock_loc[i]:
                if breath_bone.location[i] != 1.:
                    warning = True
                    break
            if lock_sca[i]:
                if breath_bone.scale[i] != 1.:
                    warning = True
                    break

        # Compute quantities
        freq = 2. * 3.14 * tools_settings.autobreath_frequency / (fps * 60)
        amplitude = tools_settings.autobreath_amplitude / 2.
        sampling = tools_settings.autobreath_sampling
        rand = tools_settings.autobreath_random

        # Create frames
        for frame in range(frame_start, frame_end, sampling):

            freq_eff = freq * (1. + random.uniform(-rand, rand))

            factor = (1. - math.cos(freq_eff * (frame - frame_start))) * amplitude

            for i in range(3):
                breath_bone.location[i] = rest_loc[i] * (1. + lock_loc[i] * factor)
                breath_bone.scale[i] = rest_sca[i] * (1 + lock_sca[i] * factor)

            if any(lock_loc):
                breath_bone.keyframe_insert(data_path="location", frame=frame)
            if any(lock_sca):
                breath_bone.keyframe_insert(data_path="scale", frame=frame)

        if warning:
            self.report({'WARNING'},
                        'MustardUI - Initial unlocked transformations should be = 1. Results might be uncorrect')
        else:
            self.report({'INFO'}, 'MustardUI - Auto Breath applied with ' + str(breath_bone.name) + ".")

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_Tools_AutoBreath)


def unregister():
    bpy.utils.unregister_class(MustardUI_Tools_AutoBreath)
