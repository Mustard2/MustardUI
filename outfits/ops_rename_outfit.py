import bpy
from bpy.props import *
from ..model_selection.active_object import *
from .. import __package__ as base_package


def remove_common_prefix_suffix(strings):
    if not strings:
        return strings

    # -------- Find common prefix --------
    prefix = strings[0]
    for s in strings[1:]:
        i = 0
        while i < len(prefix) and i < len(s) and prefix[i] == s[i]:
            i += 1
        prefix = prefix[:i]

    # -------- Find common suffix --------
    suffix = strings[0]
    for s in strings[1:]:
        i = 0
        while i < len(suffix) and i < len(s) and suffix[-1 - i] == s[-1 - i]:
            i += 1
        suffix = suffix[-i:] if i > 0 else ""

    # -------- Remove prefix + suffix --------
    cleaned = []
    for s in strings:
        core = s[len(prefix):]
        if suffix:
            core = core[:-len(suffix)]
        cleaned.append(core)

    return cleaned


class MustardUI_RenameOutfit_Class(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Name",
                                   default="")
    object: bpy.props.PointerProperty(name="Object",
                                      type=bpy.types.Object)


class MustardUI_RenameOutfit_Update(bpy.types.Operator):
    bl_idname = "mustardui.rename_outfit_update"
    bl_label = "Update Names"
    bl_options = {'UNDO'}

    name: StringProperty()
    smart_rename: BoolProperty()

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=1)
        if arm is not None:
            return res
        return False

    def execute(self, context):

        settings = context.scene.MustardUI_Settings
        rename_outfits_class = settings.rename_outfits_temp_class

        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings

        name = self.name

        strings = [x.object.name for x in rename_outfits_class]
        strings = remove_common_prefix_suffix(strings)
        for i, pp in enumerate(rename_outfits_class):
            pp.name = strings[i]

        if rig_settings.model_MustardUI_naming_convention and rig_settings.model_name != "":
            for pp in rename_outfits_class:
                pp.name = rig_settings.model_name + ' ' + name + ' - ' + pp.name

        return {'FINISHED'}


class MustardUI_RenameOutfit(bpy.types.Operator):
    """Rename the outfit. This also changes the name of outfit pieces.\nThe renaming tool only works if MustardUI Naming Convention is active"""
    bl_idname = "mustardui.rename_outfit"
    bl_label = "Rename Outfit"
    bl_options = {'UNDO'}

    bl_space_type = 'OUTLINER'
    bl_region_type = 'WINDOW'

    # UI Settings
    name: StringProperty(default="",
                         name="Outfit Name",
                         description="")
    smart_rename: BoolProperty(default=True,
                               name="Smart Rename",
                               description="Attempt to rename the Objects")
    # Internal
    right_click_call: BoolProperty(default=True)

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings

        if arm is not None:
            return res and rig_settings.model_name != ""

        return False

    def execute(self, context):

        settings = context.scene.MustardUI_Settings
        rename_outfits_class = settings.rename_outfits_temp_class

        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings

        if self.right_click_call:
            outfit_coll = bpy.context.collection
        else:
            uilist = rig_settings.outfits_collections
            index = context.scene.mustardui_outfits_uilist_index
            if len(uilist) <= index:
                return {'FINISHED'}
            outfit_coll = uilist[index].collection

        # Rename Outfit pieces
        for pp in rename_outfits_class:
            pp.object.name = pp.name

        # Rename Collection
        outfit_coll.name = rig_settings.model_name + ' ' + self.name

        rename_outfits_class.clear()

        self.report({'INFO'}, f'MustardUI - Collection Objects renamed with MustardUI convention')

        return {'FINISHED'}

    def invoke(self, context, event):

        settings = context.scene.MustardUI_Settings
        rename_outfits_class = settings.rename_outfits_temp_class
        rename_outfits_class.clear()

        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings

        if self.right_click_call:
            outfit_coll = bpy.context.collection
        else:
            uilist = rig_settings.outfits_collections
            index = context.scene.mustardui_outfits_uilist_index
            if len(uilist) <= index:
                return {'FINISHED'}
            outfit_coll = uilist[index].collection

        if outfit_coll is None:
            return {'FINISHED'}

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
        row.prop(self, 'name', text="")

        row.separator()
        row = layout.row(align=True)
        op = row.operator('mustardui.rename_outfit_update',
                          text="Update Objects with Outfit Name",
                          icon="LOOP_FORWARDS")
        op.name = self.name
        op.smart_rename = self.smart_rename
        row.prop(self, 'smart_rename', text="", icon="SHADERFX")

        layout.separator()

        box = layout.box()
        row = box.row()
        row.label(text="Original Name", icon="LOOP_BACK")
        row.label(text="New Name", icon="LOOP_FORWARDS")

        box = layout.box()
        for pp in rename_outfits_class:
            row = box.row()
            row.label(text=pp.object.name, icon="OUTLINER_OB_" + pp.object.type)
            row.prop(pp, 'name', text='')


def register():
    bpy.utils.register_class(MustardUI_RenameOutfit_Class)
    bpy.utils.register_class(MustardUI_RenameOutfit_Update)
    bpy.utils.register_class(MustardUI_RenameOutfit)


def unregister():
    bpy.utils.unregister_class(MustardUI_RenameOutfit)
    bpy.utils.unregister_class(MustardUI_RenameOutfit_Update)
    bpy.utils.unregister_class(MustardUI_RenameOutfit_Class)
