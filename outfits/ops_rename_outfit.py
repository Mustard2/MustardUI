import os

import bpy
from bpy.props import BoolProperty, StringProperty

from .. import __package__ as base_package
from ..model_selection.active_object import (
    ModelMode,
    active_object_operator_poll,
    mustardui_active_object,
)
from .helper_functions import rename_model_ids


def remove_common_prefix_suffix(strings):
    """Names without the parts they all share, cut between words"""
    if len(strings) < 2:
        # A single name keeps the part after the naming convention
        return [x.rsplit(" - ", 1)[-1] for x in strings]
    separators = " -_."
    prefix = os.path.commonprefix(strings)
    prefix = prefix[: max(prefix.rfind(c) for c in separators) + 1]
    suffix = os.path.commonprefix([x[::-1] for x in strings])[::-1]
    suffix = suffix[next((i for i, c in enumerate(suffix) if c in separators), len(suffix)) :]
    return [x[len(prefix) : len(x) - len(suffix)] or x for x in strings]


class MustardUI_RenameOutfit_Class(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Name", default="")
    object: bpy.props.PointerProperty(name="Object", type=bpy.types.Object)


class MustardUI_RenameOutfit_Update(bpy.types.Operator):
    bl_idname = "mustardui.rename_outfit_update"
    bl_label = "Update Names"
    bl_options = {"UNDO"}

    name: StringProperty()

    @classmethod
    def poll(cls, context):
        return active_object_operator_poll(context, config=ModelMode.CONFIG)

    def execute(self, context):

        settings = context.scene.MustardUI_Settings
        rename_outfits_class = settings.rename_outfits_temp_class

        res, arm = mustardui_active_object(context, config=ModelMode.CONFIG)
        rig_settings = arm.MustardUI_RigSettings

        name = self.name

        strings = [x.object.name for x in rename_outfits_class]
        strings = remove_common_prefix_suffix(strings)
        for i, pp in enumerate(rename_outfits_class):
            pp.name = strings[i]

        if rig_settings.model_MustardUI_naming_convention and rig_settings.model_name != "":
            for pp in rename_outfits_class:
                pp.name = rig_settings.model_name + " " + name + " - " + pp.name

        return {"FINISHED"}


class MustardUI_RenameOutfit(bpy.types.Operator):
    """Rename the outfit. This also changes the name of outfit pieces.\nThe renaming tool only works if MustardUI Naming Convention is active"""  # noqa: E501

    bl_idname = "mustardui.rename_outfit"
    bl_label = "Rename Outfit"
    bl_options = {"UNDO"}

    bl_space_type = "OUTLINER"
    bl_region_type = "WINDOW"

    # UI Settings
    name: StringProperty(default="", name="Outfit Name", description="")
    # Internal
    right_click_call: BoolProperty(default=True)

    @classmethod
    def poll(cls, context):
        if not active_object_operator_poll(context, config=ModelMode.CONFIG):
            return False

        res, arm = mustardui_active_object(context, config=ModelMode.CONFIG)
        return arm.MustardUI_RigSettings.model_name != ""

    def execute(self, context):

        settings = context.scene.MustardUI_Settings
        rename_outfits_class = settings.rename_outfits_temp_class

        res, arm = mustardui_active_object(context, config=ModelMode.CONFIG)
        rig_settings = arm.MustardUI_RigSettings

        if self.right_click_call:
            outfit_coll = bpy.context.collection
        else:
            uilist = rig_settings.outfits_collections
            index = context.scene.mustardui_outfits_uilist_index
            if len(uilist) <= index:
                return {"FINISHED"}
            outfit_coll = uilist[index].collection

        # Rename Outfit pieces and Collection
        names = {pp.object: pp.name for pp in rename_outfits_class if pp.object is not None}
        if outfit_coll is not None:
            names[outfit_coll] = rig_settings.model_name + " " + self.name
        addon_prefs = context.preferences.addons[base_package].preferences
        fixed = rename_model_ids(arm, names, addon_prefs)

        rename_outfits_class.clear()

        self.report(
            {"INFO"},
            "MustardUI - Collection Objects renamed with MustardUI convention"
            f" ({fixed} custom property paths updated)",
        )

        return {"FINISHED"}

    def invoke(self, context, event):

        settings = context.scene.MustardUI_Settings
        rename_outfits_class = settings.rename_outfits_temp_class
        rename_outfits_class.clear()

        res, arm = mustardui_active_object(context, config=ModelMode.CONFIG)
        rig_settings = arm.MustardUI_RigSettings

        if self.right_click_call:
            outfit_coll = bpy.context.collection
        else:
            uilist = rig_settings.outfits_collections
            index = context.scene.mustardui_outfits_uilist_index
            if len(uilist) <= index:
                return {"FINISHED"}
            outfit_coll = uilist[index].collection

        if outfit_coll is None:
            return {"FINISHED"}

        for obj in outfit_coll.all_objects:
            add_item = rename_outfits_class.add()
            add_item.object = obj
            add_item.name = obj.name

        self.name = outfit_coll.name.replace(rig_settings.model_name + " ", "")

        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):

        settings = context.scene.MustardUI_Settings
        rename_outfits_class = settings.rename_outfits_temp_class

        layout = self.layout

        box = layout.box()
        row = box.row(align=True)
        row.label(text="Outfit Name", icon="MOD_CLOTH")
        row.prop(self, "name", text="")

        row.separator()
        row = layout.row(align=True)
        op = row.operator(
            "mustardui.rename_outfit_update",
            text="Update Objects with Outfit Name",
            icon="LOOP_FORWARDS",
        )
        op.name = self.name

        layout.separator()

        box = layout.box()
        row = box.row()
        row.label(text="Original Name", icon="LOOP_BACK")
        row.label(text="New Name", icon="LOOP_FORWARDS")

        box = layout.box()
        for pp in rename_outfits_class:
            row = box.row()
            row.label(text=pp.object.name, icon="OUTLINER_OB_" + pp.object.type)
            row.prop(pp, "name", text="")


def register():
    bpy.utils.register_class(MustardUI_RenameOutfit_Class)
    bpy.utils.register_class(MustardUI_RenameOutfit_Update)
    bpy.utils.register_class(MustardUI_RenameOutfit)


def unregister():
    bpy.utils.unregister_class(MustardUI_RenameOutfit)
    bpy.utils.unregister_class(MustardUI_RenameOutfit_Update)
    bpy.utils.unregister_class(MustardUI_RenameOutfit_Class)
