import json

import bpy
from mathutils import Vector

from ..model_selection.active_object import mustardui_active_object


def make_json_serializable(value):
    # Handle Blender math types (Vector, Color, Euler, etc.)
    if hasattr(value, "to_tuple"):
        return list(value.to_tuple())

    # Handle generic iterables (but not strings)
    elif hasattr(value, "__iter__") and not isinstance(value, (str, bytes)):
        return [make_json_serializable(v) for v in value]

    # Handle basic types
    elif isinstance(value, (int, float, str, bool)) or value is None:
        return value

    # Fallback (last resort)
    else:
        return str(value)


class MustardUI_Physics_PresetCreate(bpy.types.Operator):
    """Create Morph preset"""

    bl_idname = "mustardui.physics_preset_create"
    bl_label = "Morph Preset Create"
    bl_options = {"UNDO"}

    new_preset_name: bpy.props.StringProperty()

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        physics_settings = arm.MustardUI_PhysicsSettings

        if arm is None:
            return False

        if (
            arm.mustardui_physics_items_uilist_index < 0
            or len(physics_settings.items) < 1
        ):
            return False

        obj = physics_settings.items[arm.mustardui_physics_items_uilist_index].object

        if obj is None or obj.type != "MESH":
            return False

        modifiers = obj.modifiers

        return res and len(modifiers) > 0

    def execute(self, context):

        if self.new_preset_name == "":
            self.report({"ERROR"}, "MustardUI - Invalid preset name")
            return {"FINISHED"}

        res, arm = mustardui_active_object(context, config=0)
        physics_settings = arm.MustardUI_PhysicsSettings

        presets = physics_settings.presets

        preset_names = [x.name for x in presets]
        if self.new_preset_name in preset_names:
            self.report({"ERROR"}, "MustardUI - Preset name already used")
            return {"FINISHED"}

        new_preset = presets.add()
        new_preset.name = self.new_preset_name

        obj = physics_settings.items[arm.mustardui_physics_items_uilist_index].object

        if obj.modifiers is None:
            return

        cloth = next((m for m in obj.modifiers if m.type == "CLOTH"), None)
        soft_body = next((m for m in obj.modifiers if m.type == "SOFT_BODY"), None)
        collision = next((m for m in obj.modifiers if m.type == "COLLISION"), None)

        if cloth is None and soft_body is None and collision is None:
            self.report({"WARNING"}, "No data to save in the preset.")
            return {"FINISHED"}

        data = []

        preset_data = {
            "name": new_preset.name,
            "cloth": {},
            "cloth_collision": {},
            "object_collision": {},
            "soft_body": {},
            "has_cloth": cloth is not None,
            "has_collision": obj.collision is not None and collision is not None,
            "has_soft_body": obj.soft_body is not None,
        }

        new_preset.has_cloth = cloth is not None
        new_preset.has_soft_body = obj.soft_body is not None
        new_preset.has_collision = obj.collision is not None and collision is not None

        # Cloth
        if cloth:
            for prop in cloth.settings.bl_rna.properties:
                if prop.is_readonly:
                    continue

                identifier = prop.identifier

                try:
                    value = getattr(cloth.settings, identifier)

                    if hasattr(value, "__iter__") and not isinstance(
                        value, (str, bytes)
                    ):
                        value = list(value)

                    preset_data["cloth"][identifier] = value
                except Exception:
                    pass

            # Cloth Collisions
            if cloth.collision_settings:
                for prop in cloth.collision_settings.bl_rna.properties:
                    if prop.is_readonly:
                        continue

                    identifier = prop.identifier

                    try:
                        value = getattr(cloth.collision_settings, identifier)

                        if hasattr(value, "__iter__") and not isinstance(
                            value, (str, bytes)
                        ):
                            value = list(value)

                        preset_data["cloth_collision"][identifier] = value
                    except Exception:
                        pass

        # Collisions
        if obj.collision and collision is not None:
            for prop in obj.collision.bl_rna.properties:
                if prop.is_readonly:
                    continue

                identifier = prop.identifier

                try:
                    value = getattr(obj.collision, identifier)

                    if hasattr(value, "__iter__") and not isinstance(
                        value, (str, bytes)
                    ):
                        value = list(value)

                    preset_data["object_collision"][identifier] = value
                except Exception:
                    pass

        # Soft Body
        if soft_body:
            for prop in soft_body.settings.bl_rna.properties:
                if prop.is_readonly:
                    continue

                identifier = prop.identifier

                try:
                    value = getattr(soft_body.settings, identifier)

                    if hasattr(value, "__iter__") and not isinstance(
                        value, (str, bytes)
                    ):
                        value = list(value)

                    preset_data["soft_body"][identifier] = value
                except Exception:
                    pass

        data.append(preset_data)

        # Write Json in the preset as a string
        json_string = json.dumps(
            data, ensure_ascii=False, indent=4, default=make_json_serializable
        )
        new_preset.data = json_string

        self.report({"INFO"}, "MustardUI - Preset '" + new_preset.name + "' created")

        return {"FINISHED"}


def restore_value(current_value, loaded_value):
    if isinstance(current_value, Vector) and isinstance(loaded_value, list):
        return Vector(loaded_value)
    return loaded_value


def apply_settings(target, data, errors):
    if not target or not data:
        return errors

    props = target.bl_rna.properties.keys()

    for key, value in data.items():
        if key not in props:
            errors += 1
            continue

        try:
            current = getattr(target, key)
            value = restore_value(current, value)
            setattr(target, key, value)
        except Exception:
            errors += 1

    return errors


class MustardUI_Physics_PresetApply(bpy.types.Operator):
    """Apply Physics preset"""

    bl_idname = "mustardui.physics_preset_apply"
    bl_label = "Apply Physics Preset"
    bl_options = {"UNDO"}

    preset_id: bpy.props.IntProperty(default=-1)
    force_modifiers_creation: bpy.props.BoolProperty(default=False)

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)

        if not arm:
            return False

        physics_settings = arm.MustardUI_PhysicsSettings

        if arm.mustardui_physics_items_uilist_index < 0:
            return False

        if len(physics_settings.items) == 0:
            return False

        obj = physics_settings.items[arm.mustardui_physics_items_uilist_index].object

        return obj and obj.type == "MESH"

    def execute(self, context):
        res, arm = mustardui_active_object(context, config=0)
        rig_settings = arm.MustardUI_RigSettings
        physics_settings = arm.MustardUI_PhysicsSettings

        presets = physics_settings.presets
        obj = physics_settings.items[arm.mustardui_physics_items_uilist_index].object

        errors = 0

        raw = json.loads(presets[self.preset_id].data)
        preset = raw[0] if isinstance(raw, list) else raw
        preset_name = preset.get("name", "Unnamed")

        # Force creation of modifiers
        if self.force_modifiers_creation:
            cloth = next((m for m in obj.modifiers if m.type == "CLOTH"), None)
            soft_body = next((m for m in obj.modifiers if m.type == "SOFT_BODY"), None)

            if not cloth and preset.get("cloth"):
                obj.modifiers.new(name="Cloth", type="CLOTH")

            if preset.get("object_collision") and not obj.collision:
                obj.modifiers.new(name="Collision", type="COLLISION")

            if preset.get("soft_body") and not soft_body:
                obj.modifiers.new(name="Softbody", type="SOFT_BODY")

        cloth = next((m for m in obj.modifiers if m.type == "CLOTH"), None)
        soft_body = next((m for m in obj.modifiers if m.type == "SOFT_BODY"), None)
        collision = next((m for m in obj.modifiers if m.type == "COLLISION"), None)

        if cloth:
            errors = apply_settings(cloth.settings, preset.get("cloth"), errors)

            if cloth.collision_settings:
                errors = apply_settings(
                    cloth.collision_settings, preset.get("cloth_collision"), errors
                )

        if obj.collision and collision is not None:
            errors = apply_settings(
                obj.collision, preset.get("object_collision"), errors
            )

        if soft_body:
            errors = apply_settings(soft_body.settings, preset.get("soft_body"), errors)

        # Update Objects
        if arm:
            arm.update_tag()
        if rig_settings.model_armature_object:
            rig_settings.model_armature_object.update_tag()
        if rig_settings.model_body:
            rig_settings.model_body.update_tag()
            if rig_settings.model_body.data:
                rig_settings.model_body.data.update_tag()
                rig_settings.model_body.data.update()

        context.view_layer.update()

        if errors == 0:
            self.report({"INFO"}, f"MustardUI - Preset '{preset_name}' applied.")
        else:
            self.report(
                {"WARNING"},
                f"MustardUI - Preset '{preset_name}' applied with {errors} issues.",
            )

        return {"FINISHED"}


class MustardUI_Physics_PresetDelete(bpy.types.Operator):
    """Delete Morph preset"""

    bl_idname = "mustardui.physics_preset_delete"
    bl_label = "Morph Preset Create"
    bl_options = {"UNDO"}

    preset_id: bpy.props.IntProperty(default=-1)

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        return res if arm is not None else False

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=0)
        physics_settings = arm.MustardUI_PhysicsSettings

        presets = physics_settings.presets

        preset = presets[self.preset_id]
        preset_name = preset.name

        presets.remove(self.preset_id)

        self.report({"INFO"}, "MustardUI - Preset '" + preset_name + "' deleted")

        return {"FINISHED"}


class MustardUI_Physics_PresetsUI(bpy.types.Operator):
    """Presets UI for Morphs"""

    bl_idname = "mustardui.physics_presets_ui"
    bl_label = "Morph Presets"
    bl_options = {"UNDO"}

    bl_space_type = "OUTLINER"
    bl_region_type = "WINDOW"

    new_preset_name: bpy.props.StringProperty(name="New Preset Name", default="Preset")

    force_modifiers_creation: bpy.props.BoolProperty(
        default=False,
        name="Create missing Modifiers",
        description="Modifiers are created if missing on the Physics Item"
        "to accommodate the data written in the modifier",
    )

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=0)
        return res if arm is not None else False

    def execute(self, context):
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=250)

    def draw(self, context):
        res, arm = mustardui_active_object(context, config=0)

        physics_settings = arm.MustardUI_PhysicsSettings

        presets = physics_settings.presets

        layout = self.layout

        if len(presets):
            box = layout.box()

        for pid, preset in enumerate(presets):
            row = box.row(align=True)
            row2 = row.row()
            if preset.has_cloth:
                row2.label(text="", icon="MOD_CLOTH")
            if preset.has_soft_body:
                row2.label(text="", icon="MOD_SOFT")
            if preset.has_collision:
                row2.label(text="", icon="MOD_PHYSICS")
            row2.operator(
                "mustardui.physics_preset_apply", text=preset.name
            ).preset_id = pid
            row.operator(
                "mustardui.physics_preset_delete", text="", icon="X"
            ).preset_id = pid
            row.separator()
            row.operator(
                "mustardui.physics_preset_export", text="", icon="COPYDOWN"
            ).preset_id = pid

        if len(presets):
            layout.separator()

        row = layout.row(align=True)
        row.prop(self, "new_preset_name", text="")
        row.operator(
            "mustardui.physics_preset_create", icon="ADD", text=""
        ).new_preset_name = self.new_preset_name

        layout.separator()
        row = layout.row(align=True)
        row.operator(
            "mustardui.physics_preset_import", text="Import Preset", icon="PASTEDOWN"
        )


def register():
    bpy.utils.register_class(MustardUI_Physics_PresetsUI)
    bpy.utils.register_class(MustardUI_Physics_PresetCreate)
    bpy.utils.register_class(MustardUI_Physics_PresetApply)
    bpy.utils.register_class(MustardUI_Physics_PresetDelete)


def unregister():
    bpy.utils.unregister_class(MustardUI_Physics_PresetDelete)
    bpy.utils.unregister_class(MustardUI_Physics_PresetApply)
    bpy.utils.unregister_class(MustardUI_Physics_PresetCreate)
    bpy.utils.unregister_class(MustardUI_Physics_PresetsUI)
