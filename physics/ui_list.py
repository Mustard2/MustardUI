import bpy
from bpy.props import *
from ..model_selection.active_object import *
from.settings_item import mustardui_physics_item_type_dict


class MustardUI_PhysicsItems_UIList_Switch(bpy.types.Operator):
    """Move the selected property in the list"""

    bl_idname = "mustardui.physics_items_switch"
    bl_label = "Move Physics Item"

    direction: bpy.props.EnumProperty(items=(('UP', 'Up', ""),
                                             ('DOWN', 'Down', ""),))

    @classmethod
    def poll(cls, context):
        res, obj = mustardui_active_object(context, config=1)
        return obj is not None

    def move_index(self, uilist, index):
        """ Move index of an item render queue while clamping it. """

        list_length = len(uilist) - 1  # (index starts at 0)
        new_index = index + (-1 if self.direction == 'UP' else 1)

        return max(0, min(new_index, list_length))

    def execute(self, context):
        res, obj = mustardui_active_object(context, config=1)
        physics_settings = obj.MustardUI_PhysicsSettings
        uilist = physics_settings.items
        index = context.scene.mustardui_physics_items_uilist_index

        if len(uilist) <= index:
            return {'FINISHED'}

        neighbour = index + (-1 if self.direction == 'UP' else 1)
        uilist.move(neighbour, index)
        index = self.move_index(uilist, index)
        context.scene.mustardui_physics_items_uilist_index = index

        return {'FINISHED'}


class MUSTARDUI_UL_PhysicsItems_UIList(bpy.types.UIList):
    """UIList for Physics Items"""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.prop(item.object, 'name', text="", emboss=False, translate=False)
        layout.label(text="", icon=mustardui_physics_item_type_dict[item.type])
        if item.type == "CAGE":
            found_cloth = False
            found_soft = False
            for mod in item.object.modifiers:
                if mod.type in ["CLOTH"]:
                    found_cloth = True
                elif mod.type in ["SOFT_BODY"]:
                    found_soft = True

            row = layout.row(align=True)
            row.label(text="", icon="MOD_CLOTH" if found_cloth else "BLANK1")
            row.label(text="", icon="MOD_SOFT" if found_soft else "BLANK1")
        elif item.type == "COLLISION":
            found = False
            for mod in item.object.modifiers:
                if mod.type in ["COLLISION"]:
                    found = True
                    break

            row = layout.row(align=True)
            row.label(text="", icon="BLANK1")
            row.label(text="", icon="MOD_PHYSICS" if found else "BLANK1")
        else:
            row = layout.row(align=True)
            row.label(text="", icon="BLANK1")
            row.label(text="", icon="BLANK1")


def register():
    bpy.utils.register_class(MUSTARDUI_UL_PhysicsItems_UIList)
    bpy.utils.register_class(MustardUI_PhysicsItems_UIList_Switch)

    bpy.types.Scene.mustardui_physics_items_uilist_index = IntProperty(name="", default=0)


def unregister():
    del bpy.types.Scene.mustardui_physics_items_uilist_index

    bpy.utils.unregister_class(MustardUI_PhysicsItems_UIList_Switch)
    bpy.utils.unregister_class(MUSTARDUI_UL_PhysicsItems_UIList)
