import bpy
from ..model_selection.active_object import *
import random
import math
from .. import __package__ as base_package


class MustardUI_Tools_AutoEyelid(bpy.types.Operator):
    """Automatically create keyframes for eyelid animation"""
    bl_idname = "mustardui.tools_autoeyelid"
    bl_label = "Auto Blink"
    bl_options = {'REGISTER', 'UNDO'}

    def blinkFrame(self, frame, value, blink_driver, obj, type):

        if type == "SHAPE_KEY":
            if blink_driver in obj.data.shape_keys.key_blocks.keys():
                obj.data.shape_keys.key_blocks[blink_driver].value = value
                obj.data.update_tag()
                obj.data.shape_keys.key_blocks[blink_driver].keyframe_insert(data_path='value', index=-1, frame=frame)
                return False
            else:
                return True
        else:
            if blink_driver in obj.keys():
                obj[blink_driver] = value
                obj.update_tag()
                obj.keyframe_insert(data_path='["' + blink_driver + '"]', index=-1, frame=frame)
                return False
            else:
                return True

    def execute(self, context):

        poll, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings
        tools_settings = arm.MustardUI_ToolsSettings
        addon_prefs = context.preferences.addons[base_package].preferences

        # Check scene settings
        frame_start = context.scene.frame_start
        frame_end = context.scene.frame_end
        fps = context.scene.render.fps / context.scene.render.fps_base
        context.scene.frame_current = frame_start

        blink_length_frames = [math.floor(fps * .1),
                               math.ceil(fps * .25 * tools_settings.autoeyelid_blink_length)]  # default: 100 - 250 ms
        blink_chance_per_half_second = 2. * tools_settings.autoeyelid_blink_rate_per_minute / (
                60 * 2)  # calculated every half second, default: 26

        blink_drivers = []
        if tools_settings.autoeyelid_driver_type == "SHAPE_KEY":
            for blink_driver in [tools_settings.autoeyelid_eyeL_shapekey, tools_settings.autoeyelid_eyeR_shapekey]:
                if blink_driver != "":
                    blink_drivers.append(blink_driver)
        else:
            blink_drivers.append(tools_settings.autoeyelid_morph)

        error = 0

        for frame in range(frame_start, frame_end):
            if frame % fps / 2 == 0:
                r = random.random()
                if r < blink_chance_per_half_second:
                    rl = random.randint(blink_length_frames[0], blink_length_frames[1])
                    blinkStart = frame
                    blinkMid = frame + math.floor(rl / 2)
                    blinkEnd = frame + rl
                    if addon_prefs.debug:
                        print("MustardUI Auto Blink: Frame: ", frame, " - Blinking start: ", blinkStart,
                              " - Blink Mid: ", blinkMid, " - Blink End:", blinkEnd)
                    for blink_driver in blink_drivers:
                        target_object = rig_settings.model_body if tools_settings.autoeyelid_driver_type == "SHAPE_KEY" else rig_settings.model_armature_object
                        error = error + self.blinkFrame(blinkStart, 0., blink_driver, target_object,
                                                        tools_settings.autoeyelid_driver_type)
                        error = error + self.blinkFrame(blinkMid, 1., blink_driver, target_object,
                                                        tools_settings.autoeyelid_driver_type)
                        error = error + self.blinkFrame(blinkEnd, 0., blink_driver, target_object,
                                                        tools_settings.autoeyelid_driver_type)

        if error < 1:
            self.report({'INFO'}, 'MustardUI - Auto Blink applied.')
        else:
            self.report({'ERROR'},
                        'MustardUI - Auto Blink shape keys/morph seems to be missing. Results might be corrupted.')

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_Tools_AutoEyelid)


def unregister():
    bpy.utils.unregister_class(MustardUI_Tools_AutoEyelid)
