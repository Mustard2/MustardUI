import bpy
from bpy.props import *
from ..model_selection.active_object import *
from ..misc.prop_utils import *
from .. import __package__ as base_package


class MustardUI_Armature_ResetCollections(bpy.types.Operator):
    """Reset the collections visibility to the default status"""
    bl_idname = "mustardui.armature_reset_bcoll"
    bl_label = "Armature Collections Reset"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):

        res, arm = mustardui_active_object(context, config=0)
        return res

    def execute(self, context):

        res, obj = mustardui_active_object(context, config=0)

        for coll in obj.collections_all:
            coll.is_visible = coll.MustardUI_ArmatureBoneCollection.is_in_UI and coll.MustardUI_ArmatureBoneCollection.default

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_Armature_ResetCollections)


def unregister():
    bpy.utils.unregister_class(MustardUI_Armature_ResetCollections)
