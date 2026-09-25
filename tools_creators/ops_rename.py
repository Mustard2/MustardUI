import bpy
from bpy.props import StringProperty

from .. import __package__ as base_package
from ..custom_properties.misc import assign_pointers
from ..custom_properties.ops_rebuild import fix_custom_property_path
from ..model_selection.active_object import mustardui_active_object


class MustardUI_ToolsCreators_RenameModel(bpy.types.Operator):
    """Rename the model. This also changes the name of objects, collections and physics items associated to the model.\nThe renaming tool only works if MustardUI Naming Convention is active"""  # noqa: E501

    bl_idname = "mustardui.rename_model"
    bl_label = "Rename Model"
    bl_options = {"UNDO"}

    name: StringProperty(default="", name="New Name", description="")

    @classmethod
    def poll(cls, context):

        res, arm = mustardui_active_object(context, config=1)
        if arm is None:
            return False

        rig_settings = arm.MustardUI_RigSettings
        return (
            res and rig_settings.model_name != "" and rig_settings.model_MustardUI_naming_convention
        )

    def change_modifiers_name(self, obj, old_name):
        if obj.modifiers is None:
            return

        for modifier in obj.modifiers:
            if old_name in modifier.name:
                modifier.name = modifier.name.replace(old_name, self.name)

    def change_materials_name(self, obj, old_name, shared_materials):
        if obj.type != "MESH":
            return
        if obj.data is None:
            return
        if obj.data.materials is None:
            return

        for mat in [x for x in obj.data.materials if x is not None]:
            if old_name in mat.name and mat not in shared_materials:
                mat.name = mat.name.replace(old_name, self.name)

    def shared_materials(self, rig_settings, physics_settings):
        """Materials also used by meshes outside the model, which are not renamed."""
        arm_obj = rig_settings.model_armature_object
        objects = set(arm_obj.children) if arm_obj else set()
        objects.update(x.object for x in physics_settings.items if x.object)
        for coll in [x.collection for x in rig_settings.outfits_collections] + [
            rig_settings.extras_collection,
            rig_settings.hair_collection,
            rig_settings.hair_extras_collection,
        ]:
            if coll is not None:
                objects.update(coll.all_objects)
        model_meshes = {x.data for x in objects if x is not None and x.type == "MESH"}

        shared = set()
        for obj in bpy.data.objects:
            if obj.type != "MESH" or obj.data in model_meshes:
                continue
            shared.update(x.material for x in obj.material_slots if x.material)
        return shared

    def execute(self, context):

        if self.name == "":
            self.report(
                {"WARNING"},
                "MustardUI - Renaming not performed: the name should be not null",
            )
            return {"FINISHED"}

        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings
        physics_settings = arm.MustardUI_PhysicsSettings

        old_name = rig_settings.model_name
        addon_prefs = context.preferences.addons[base_package].preferences

        # Store pointers to the IDs, to fix the custom property paths after renaming
        custom_properties_lists = [
            arm.MustardUI_CustomProperties,
            arm.MustardUI_CustomPropertiesOutfit,
            arm.MustardUI_CustomPropertiesHair,
        ]
        for custom_properties in custom_properties_lists:
            assign_pointers(custom_properties, addon_prefs)

        shared_materials = self.shared_materials(rig_settings, physics_settings)

        # Armature
        rig_settings.model_armature_object.name = rig_settings.model_armature_object.name.replace(
            old_name, self.name
        )

        # Body and children of the armature
        for obj in [x for x in rig_settings.model_armature_object.children if x is not None]:
            if old_name in obj.name:
                obj.name = obj.name.replace(old_name, self.name)
            self.change_modifiers_name(obj, old_name)
            self.change_materials_name(obj, old_name, shared_materials)

        # Physics items
        for pi in [x for x in physics_settings.items if x.object is not None]:
            if old_name in pi.object.name:
                pi.object.name = pi.object.name.replace(old_name, self.name)
            self.change_modifiers_name(pi.object, old_name)

        # Outfits
        for coll in [
            x.collection for x in rig_settings.outfits_collections if x.collection is not None
        ]:
            items = coll.all_objects
            for obj in [x for x in items if x is not None]:
                obj.name = obj.name.replace(old_name, self.name)
                self.change_modifiers_name(obj, old_name)
                self.change_materials_name(obj, old_name, shared_materials)
            coll.name = coll.name.replace(old_name, self.name)

        # Extras
        if rig_settings.extras_collection is not None:
            for obj in [x for x in rig_settings.extras_collection.all_objects if x is not None]:
                obj.name = obj.name.replace(old_name, self.name)
                self.change_modifiers_name(obj, old_name)
                self.change_materials_name(obj, old_name, shared_materials)
            rig_settings.extras_collection.name = rig_settings.extras_collection.name.replace(
                old_name, self.name
            )

        # Hair
        if rig_settings.hair_collection is not None:
            for obj in [x for x in rig_settings.hair_collection.all_objects if x is not None]:
                obj.name = obj.name.replace(old_name, self.name)
                self.change_modifiers_name(obj, old_name)
                self.change_materials_name(obj, old_name, shared_materials)
            rig_settings.hair_collection.name = rig_settings.hair_collection.name.replace(
                old_name, self.name
            )

        # Hair Extras
        if rig_settings.hair_extras_collection is not None:
            for obj in [
                x for x in rig_settings.hair_extras_collection.all_objects if x is not None
            ]:
                obj.name = obj.name.replace(old_name, self.name)
                self.change_modifiers_name(obj, old_name)
                self.change_materials_name(obj, old_name, shared_materials)
            rig_settings.hair_extras_collection.name = (
                rig_settings.hair_extras_collection.name.replace(old_name, self.name)
            )

        # Finally change the model name
        rig_settings.model_name = self.name

        fixed = 0
        for custom_properties in custom_properties_lists:
            for custom_prop in custom_properties:
                res = fix_custom_property_path(arm, custom_properties, custom_prop, addon_prefs)
                fixed += res == "FIXED"

        self.report(
            {"INFO"},
            f"MustardUI - Model renamed from {repr(old_name)} to {repr(rig_settings.model_name)}"
            f" ({fixed} custom property paths updated)",
        )

        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=250)

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
    bpy.utils.register_class(MustardUI_ToolsCreators_RenameModel)


def unregister():
    bpy.utils.unregister_class(MustardUI_ToolsCreators_RenameModel)
