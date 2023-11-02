import bpy
from . import MainPanel
from ..model_selection.active_object import *
from ..settings.rig import *


class PANEL_PT_MustardUI_Armature(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Armature"
    bl_label = "Armature"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_mirror(self, bcoll, bcoll_settings, bcolls, layout):

        for b in bcolls:
            if bcoll.name.endswith(".L") and b.name == bcoll.name[:-2] + ".R":
                layout.prop(bcoll, "is_visible",
                            text=bcoll.name,
                            toggle=True,
                            icon=bcoll_settings.icon if bcoll_settings.icon != "NONE" else "BLANK1")
                r_icon = b.MustardUI_ArmatureBoneCollection.icon
                layout.prop(b, "is_visible",
                            text=b.name,
                            toggle=True,
                            icon=r_icon if r_icon != "NONE" else "BLANK1")
                return
            elif bcoll.name.endswith(".R") and b.name == bcoll.name[:-2] + ".L":
                return

        layout.prop(bcoll, "is_visible",
                    text=bcoll.name,
                    toggle=True,
                    icon=bcoll_settings.icon if bcoll_settings.icon != "NONE" else "BLANK1")

    @classmethod
    def poll(cls, context):

        res, obj = mustardui_active_object(context, config=0)

        if obj is not None:
            rig_settings = obj.MustardUI_RigSettings
            armature_settings = obj.MustardUI_ArmatureSettings
            bcolls = obj.collections

            if len(bcolls) < 1:
                return False

            enabled_colls = [x for x in obj.collections if x.MustardUI_ArmatureBoneCollection.is_in_UI]

            if rig_settings.hair_collection is not None:
                return res and (len(enabled_colls) > 0 or (len([x for x in rig_settings.hair_collection.objects if
                                                                x.type == "ARMATURE"]) > 1 and armature_settings.enable_automatic_hair))
            else:
                return res and len(enabled_colls) > 0
        else:
            return res

    def draw(self, context):

        settings = bpy.context.scene.MustardUI_Settings
        poll, obj = mustardui_active_object(context, config=0)
        armature_settings = obj.MustardUI_ArmatureSettings
        rig_settings = obj.MustardUI_RigSettings

        box = self.layout

        draw_separator = False
        if rig_settings.hair_collection is not None and armature_settings.enable_automatic_hair:
            if len([x for x in rig_settings.hair_collection.objects if x.type == "ARMATURE"]) > 0:
                box.prop(armature_settings, "hair", toggle=True, icon="CURVES")
                draw_separator = True

        if len(rig_settings.outfits_list) > 0:
            if len([x for x in obj.collections if x.MustardUI_ArmatureBoneCollection.outfit_switcher_enable]):
                box.prop(armature_settings, "outfits", toggle=True, icon="MOD_CLOTH")
                draw_separator = True

        if draw_separator:
            box.separator()

        enabled_colls = [x for x in obj.collections if x.MustardUI_ArmatureBoneCollection.is_in_UI]

        for bcoll in enabled_colls:
            bcoll_settings = bcoll.MustardUI_ArmatureBoneCollection
            if (bcoll_settings.advanced and settings.advanced) or not bcoll_settings.advanced:
                row = box.row()
                if bcoll.name.endswith(".L"):
                    self.draw_mirror(bcoll, bcoll_settings, enabled_colls, row)
                else:
                    row.prop(bcoll, "is_visible",
                             text=bcoll.name,
                             toggle=True,
                             icon=bcoll_settings.icon if bcoll_settings.icon != "NONE" else "BLANK1")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_Armature)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Armature)
