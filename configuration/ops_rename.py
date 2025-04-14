import bpy
from bpy.props import *
from ..custom_properties.misc import mustardui_clean_prop
from ..model_selection.active_object import *
from .. import __package__ as base_package


class MustardUI_RenameModel(bpy.types.Operator):
    """Rename the model. This also changes the name of objects, collections and physics items associated to the model.\nThe renaming tool only works if MustardUI Naming Convention is active"""
    bl_idname = "mustardui.rename_model"
    bl_label = "Rename Model"
    bl_options = {'UNDO'}

    name: StringProperty(default="",
                         name="Delete Settings",
                         description="All Settings of the UI will be removed.\nA clean Configuration is "
                                     "necessary after using this option")

    @classmethod
    def poll(cls, context):

        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings

        if arm is not None:
            return res and rig_settings.model_name != "" and rig_settings.model_MustardUI_naming_convention
        return False

    def change_modifiers_name(self, obj, old_name):
        if obj.modifiers is None:
            return

        for modifier in obj.modifiers:
            if old_name in modifier.name:
                modifier.name = modifier.name.replace(old_name, self.name)

    def execute(self, context):

        if self.name == "":
            self.report({'WARNING'}, 'MustardUI - Renaming not performed: the name should be not null')

        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings
        physics_settings = arm.MustardUI_PhysicsSettings

        old_name = rig_settings.model_name

        # Armature
        rig_settings.model_armature_object.name = rig_settings.model_armature_object.name.replace(old_name, self.name)

        # Body and children of the armature
        for obj in [x for x in rig_settings.model_armature_object.children if x is not None]:
            if old_name in obj.name:
                obj.name = obj.name.replace(old_name, self.name)
            self.change_modifiers_name(obj, old_name)

        # Physics items
        for pi in [x for x in physics_settings.items if x.object is not None]:
            if old_name in pi.object.name:
                pi.object.name = pi.object.name.replace(old_name, self.name)
            self.change_modifiers_name(pi.object, old_name)

        # Outfits
        for coll in [x.collection for x in rig_settings.outfits_collections if x.collection is not None]:
            items = coll.all_objects
            for obj in [x for x in items if x is not None]:
                obj.name = obj.name.replace(old_name, self.name)
                self.change_modifiers_name(obj, old_name)
            coll.name = coll.name.replace(old_name, self.name)

        # Extras
        if rig_settings.extras_collection is not None:
            for obj in [x for x in rig_settings.extras_collection.all_objects if x is not None]:
                obj.name = obj.name.replace(old_name, self.name)
                self.change_modifiers_name(obj, old_name)
            rig_settings.extras_collection.name = rig_settings.extras_collection.name.replace(old_name, self.name)

        # Hair
        if rig_settings.hair_collection is not None:
            for obj in [x for x in rig_settings.hair_collection.all_objects if x is not None]:
                obj.name = obj.name.replace(old_name, self.name)
                self.change_modifiers_name(obj, old_name)
            rig_settings.hair_collection.name = rig_settings.hair_collection.name.replace(old_name, self.name)

        # Finally change the model name
        rig_settings.model_name = self.name

        self.report({'INFO'}, f'MustardUI - Model renamed from {repr(old_name)} to {repr(rig_settings.model_name)}')

        return {'FINISHED'}

    def invoke(self, context, event):
        addon_prefs = context.preferences.addons[base_package].preferences
        return context.window_manager.invoke_props_dialog(self, width=550 if addon_prefs.debug else 450)

    def draw(self, context):

        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings

        layout = self.layout

        box = layout.box()
        col = box.column(align=True)
        row = col.row(align=True)
        row.label(text="Current Name")
        row.label(text=f"{repr(rig_settings.model_name)}")
        row = col.row(align=True)
        row.label(text="New Name")
        row.prop(self, "name", text="")


def register():
    bpy.utils.register_class(MustardUI_RenameModel)


def unregister():
    bpy.utils.unregister_class(MustardUI_RenameModel)
