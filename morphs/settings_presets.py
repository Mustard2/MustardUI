import bpy

from ..model_selection.active_object import mustardui_active_object
from .misc import get_cp_source


def morphs_to_json(morph_settings, rig_settings):
    data = {"morphs": []}

    for section in morph_settings.sections:
        for morph in section.morphs:
            cp_source = get_cp_source(morph.custom_property_source, rig_settings)

            val = 0.0
            if cp_source and morph.custom_property:
                cp = cp_source.get(morph.path)
                if cp is not None:
                    val = cp
            elif morph.shape_key:
                kb = rig_settings.data.shape_keys.key_blocks.get(morph.path)
                if kb:
                    val = kb.value

            if abs(float(val)) > 0.001:
                data["morphs"].append(
                    {
                        "name": morph.name,
                        "path": morph.path,
                        "section_name": section.name,
                        "shape_key": morph.shape_key,
                        "custom_property": morph.custom_property,
                        "custom_property_source": morph.custom_property_source,
                        "value": float(val),
                    }
                )

    return data


def apply_morphs_preset(context, arm, settings, data, force=False):
    rig_settings = arm.MustardUI_RigSettings
    errors = 0

    morphs = data.get("morphs", [])

    for m in morphs:
        cp_source = get_cp_source(m.get("custom_property_source"), rig_settings)
        val = m.get("value", 0.0)

        if cp_source and m.get("custom_property"):
            cp = cp_source.get(m.get("path"))

            if cp is None:
                errors += 1
                continue

            if isinstance(cp, bool):
                cp_source[m["path"]] = abs(float(val)) > 0.001
            elif isinstance(cp, int) and not isinstance(cp, bool):
                cp_source[m["path"]] = int(val)
            else:
                cp_source[m["path"]] = val

        elif m.get("shape_key") and rig_settings.data and rig_settings.data.shape_keys:
            kb = rig_settings.model_body.data.shape_keys.key_blocks.get(m.get("path"))
            if kb is None:
                errors += 1
                continue
            kb.value = val

    return errors


def morph_preset_default_update(self, context):
    if not self.default:
        return

    res, arm = mustardui_active_object(context, config=0)
    morphs_settings = arm.MustardUI_MorphsSettings

    for preset in morphs_settings.presets:
        if preset is None:
            continue
        if preset != self and preset.default:
            preset.default = False


class MustardUI_Morph_Preset(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Name")

    # Preset data in Json format
    data: bpy.props.StringProperty()

    default: bpy.props.BoolProperty(
        name="",
        description="Flag this preset as Default.\nWhen Morphs are reset in the Morphs "
        "panel, the values will be restored to this preset morph rather than 0",
        update=morph_preset_default_update,
    )


class MUSTARDUI_UL_Morphs_Presets_UIList(bpy.types.UIList):
    """UIList for Morph Presets"""

    def poll(cls, context):
        res, obj = mustardui_active_object(context, config=0)
        return res if obj is not None else False

    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname, index
    ):
        row = layout.row(align=True)
        row.prop(
            item,
            "name",
            text="",
            emboss=False,
            translate=False,
        )
        row.separator()
        row.prop(
            item,
            "default",
            text="",
            emboss=False,
            icon="RADIOBUT_ON" if item.default else "RADIOBUT_OFF",
        )


def register():
    bpy.utils.register_class(MustardUI_Morph_Preset)
    bpy.utils.register_class(MUSTARDUI_UL_Morphs_Presets_UIList)

    bpy.types.Armature.mustardui_morphs_preset_uilist_index = bpy.props.IntProperty(
        name="",
        default=0,
        override={"LIBRARY_OVERRIDABLE"},
        options={"LIBRARY_EDITABLE"},
    )


def unregister():
    del bpy.types.Armature.mustardui_morphs_preset_uilist_index

    bpy.utils.unregister_class(MUSTARDUI_UL_Morphs_Presets_UIList)
    bpy.utils.unregister_class(MustardUI_Morph_Preset)
