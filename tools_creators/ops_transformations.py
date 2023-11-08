import bpy
from bpy.props import *
from ..model_selection.active_object import *


class MustardUI_ToolsCreators_AffectTransform(bpy.types.Operator):
    """Enable/disable the \'Affect Transform\' option for all limit transform (loc, rot, sca) constraints on the rig bones"""
    bl_idname = "mustardui.tools_creators_affect_transform"
    bl_label = "Change Affect Transform"
    bl_options = {'UNDO'}

    enable: BoolProperty(default=True)

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=1)
        addon_prefs = context.preferences.addons["MustardUI"].preferences
        return res and addon_prefs.experimental

    def execute(self, context):

        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings
        addon_prefs = context.preferences.addons["MustardUI"].preferences

        if rig_settings.model_armature_object is None:
            self.report({'ERROR'}, 'MustardUI - Error occurred while retrieving Armature Object.')
            return {'FINISHED'}

        if addon_prefs.debug:
            print(" MustardUI - Affect Transform Tool log\n")

        nc = 0
        for bone in rig_settings.model_armature_object.pose.bones:
            for constraint in bone.constraints:
                if constraint.type in ["LIMIT_LOCATION", "LIMIT_ROTATION", "LIMIT_SCALE"]:
                    if constraint.use_transform_limit != self.enable:
                        nc += 1
                    if addon_prefs.debug:
                        print(bone.name + "- Changing constraint (" + constraint.type + "): " + constraint.name)
                    constraint.use_transform_limit = self.enable

        if addon_prefs.debug:
            print("\n")

        if nc > 0:
            self.report({'INFO'}, 'MustardUI - Changed ' + str(nc) + ' constraints.')
        else:
            self.report({'WARNING'}, 'MustardUI - No constraint needed to be changed.')

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_ToolsCreators_AffectTransform)


def unregister():
    bpy.utils.unregister_class(MustardUI_ToolsCreators_AffectTransform)
