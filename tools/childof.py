import bpy
from bpy.props import *
from ..model_selection.active_object import *
from .. import __package__ as base_package


class MustardUI_Tools_ChildOf(bpy.types.Operator):
    """Apply Child Of modifier"""
    bl_idname = "mustardui.tools_childof"
    bl_label = "Child Of Apply"
    bl_options = {'REGISTER', 'UNDO'}

    clean: IntProperty(name='CLEAN',
                       description="Clean action",
                       default=0)

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        if bpy.context.selected_pose_bones is not None:
            return res and len(bpy.context.selected_pose_bones) == 2
        return False

    def execute(self, context):

        settings = bpy.context.scene.MustardUI_Settings

        poll, arm = mustardui_active_object(context, config=0)
        tools_settings = arm.MustardUI_ToolsSettings
        addon_prefs = context.preferences.addons[base_package].preferences

        if self.clean == 0:

            ob = bpy.context.active_object

            if len(bpy.context.selected_pose_bones) == 2:

                if bpy.context.selected_pose_bones[0].id_data == bpy.context.selected_pose_bones[1].id_data:
                    parent_bone = bpy.context.selected_pose_bones[0]
                    child_bone = bpy.context.selected_pose_bones[1]
                else:
                    parent_bone = bpy.context.selected_pose_bones[1]
                    child_bone = bpy.context.selected_pose_bones[0]

                if ob == child_bone.id_data:

                    constr = child_bone.constraints.new('CHILD_OF')
                    constr.name = tools_settings.childof_constr_name

                    constr.target = parent_bone.id_data
                    constr.subtarget = parent_bone.name

                    context_py = bpy.context.copy()
                    context_py["constraint"] = constr

                    saved_info = {}
                    for c in ob.data.collections:
                        saved_info[c.name] = c.is_visible
                        c.is_visible = True

                    ob.data.bones.active = child_bone.id_data.pose.bones[child_bone.name].bone

                    for key, value in saved_info.items():
                        try:
                            ob.data.collections[key].is_visible = value
                        except:
                            pass

                    constr.influence = tools_settings.childof_influence

                    self.report({'INFO'}, 'MustardUI - The two selected Bones has been parented.')

                else:
                    self.report({'ERROR'}, 'MustardUI - You should select two Bones. No modifier has been added.')

            else:
                self.report({'ERROR'}, 'MustardUI - You should select two Bones. No modifier has been added.')

        else:

            mod_cont = 0
            for obj in bpy.data.objects:
                if obj.type == "ARMATURE":
                    for bone in obj.pose.bones:
                        for constr in bone.constraints:
                            if tools_settings.childof_constr_name in constr.name:
                                bone.constraints.remove(constr)
                                if addon_prefs.debug:
                                    print(
                                        'MustardUI - Constraint of ' + bone.name + ' in ' + obj.name + ' successfully removed.')
                                mod_cont = mod_cont + 1

            if mod_cont > 0:
                self.report({'INFO'}, 'MustardUI - ' + str(mod_cont) + " modifiers successfully removed.")
            else:
                self.report({'WARNING'}, 'MustardUI - No modifier was found. None was removed.')

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_Tools_ChildOf)


def unregister():
    bpy.utils.unregister_class(MustardUI_Tools_ChildOf)
