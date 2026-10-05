import bpy

from ..misc.ui_collapse import ui_collapse_prop
from ..model_selection.active_object import ModelMode, mustardui_active_object
from ..morphs.misc import get_section_by_diffeomorphic_id, morph_filter_function
from . import MainPanel


# Each list needs its own id, or the lists would share their size and scrolling
def draw_morphs_list(layout, arm, section, list_id):
    row = layout.row()
    row.enabled = arm.MustardUI_MorphsSettings.diffeomorphic_enable or not section.can_disable
    row.template_list(
        "MUSTARDUI_UL_Morphs_UIList_Menu",
        list_id,
        section,
        "morphs",
        arm,
        "mustardui_morphs_uilist_menu_index",
    )


# Number of morphs matching the search, in the panel header, when enabled in the settings
def draw_morphs_count(layout, arm, diffeomorphic_id=None):
    morphs_settings = arm.MustardUI_MorphsSettings
    if not morphs_settings.diffeomorphic_show_count:
        return

    if diffeomorphic_id is None:
        sections = [x for x in morphs_settings.sections if not x.is_internal and not x.hidden]
    else:
        section = get_section_by_diffeomorphic_id(morphs_settings, diffeomorphic_id)
        sections = [section] if section is not None else []

    morph_filter = morph_filter_function(arm.MustardUI_RigSettings, morphs_settings)
    count = sum(1 for section in sections for morph in section.morphs if morph_filter(morph))
    layout.label(text=f"({count})")


# Draw header Morph buttons
def draw_morphs_buttons(layout, morphs_settings):
    row = layout.row()
    row.prop(morphs_settings, "diffeomorphic_search", icon="VIEWZOOM")
    buttons = row.row(align=True)
    buttons.prop(morphs_settings, "diffeomorphic_filter_null", icon="FILTER", text="")
    buttons.operator("mustardui.morphs_defaultvalues", text="", icon="LOOP_BACK")
    settings = buttons.row(align=True)
    settings.enabled = morphs_settings.diffeomorphic_enable
    settings.prop(morphs_settings, "diffeomorphic_enable_settings", icon="PREFERENCES", text="")
    buttons.separator()
    op = buttons.operator("mustardui.presets_ui", text="", icon="PRESET")
    op.preset_type = "MORPHS"


class PANEL_PT_MustardUI_Morphs(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Morphs"
    bl_label = "Morphs"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=ModelMode.USER)

        if arm is None:
            return False

        morphs_settings = arm.MustardUI_MorphsSettings

        if morphs_settings.type == "GENERIC":
            return res and morphs_settings.enable_ui and morphs_settings.morphs_number > 0

        if not get_section_by_diffeomorphic_id(morphs_settings, 0):
            return False

        # Check if at least one panel is available in the Diffeomorphic case
        sections = [get_section_by_diffeomorphic_id(morphs_settings, i) for i in range(5)]
        panels = any(section is not None and section.morphs for section in sections)

        return res and morphs_settings.enable_ui and panels and morphs_settings.morphs_number > 0

    def draw_header(self, context):

        poll, obj = mustardui_active_object(context, config=ModelMode.USER)
        self.layout.prop(obj.MustardUI_MorphsSettings, "diffeomorphic_enable", text="")

    def draw(self, context):

        poll, obj = mustardui_active_object(context, config=ModelMode.USER)
        morphs_settings = obj.MustardUI_MorphsSettings

        layout = self.layout
        diffeomorphic = morphs_settings.type != "GENERIC"

        has_morphs = diffeomorphic or any(
            x.morphs and not x.hidden for x in morphs_settings.sections
        )
        if has_morphs:
            draw_morphs_buttons(layout, morphs_settings)

        if has_morphs and morphs_settings.diffeomorphic_enable_settings:
            box = layout.box()
            col = box.column(align=True)
            row = col.row(align=True)
            row.label(text="Mute Shape Keys")
            row.prop(morphs_settings, "mute_shape_keys", expand=True)

            col.separator()

            if diffeomorphic:
                col.prop(morphs_settings, "diffeomorphic_enable_pJCM")
                col.prop(morphs_settings, "diffeomorphic_enable_facs")
                row = col.row(align=True)
                row.enabled = not morphs_settings.diffeomorphic_enable_facs
                row.prop(morphs_settings, "diffeomorphic_enable_facs_bones")
            col.separator()
            col.prop(morphs_settings, "diffeomorphic_show_count")

        # Generic panel
        if not diffeomorphic:
            morph_filter = (
                morph_filter_function(obj.MustardUI_RigSettings, morphs_settings)
                if morphs_settings.diffeomorphic_show_count
                else None
            )

            for index, section in enumerate(morphs_settings.sections):
                if not section.morphs or section.hidden:
                    continue
                # Count before the name, as in the Diffeomorphic panel headers
                label = section.name
                if morph_filter is not None:
                    label = f"({sum(1 for x in section.morphs if morph_filter(x))}) {label}"
                if ui_collapse_prop(layout, section, "collapse", label, icon=section.icon):
                    draw_morphs_list(layout, obj, section, f"Section_{index}")


class PANEL_PT_MustardUI_Morphs_EmotionUnits(MainPanel, bpy.types.Panel):
    bl_label = "Emotion Units"
    bl_parent_id = "PANEL_PT_MustardUI_Morphs"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=ModelMode.USER)
        if arm is None:
            return False

        morphs_settings = arm.MustardUI_MorphsSettings

        if morphs_settings.type == "GENERIC":
            return False

        section = get_section_by_diffeomorphic_id(morphs_settings, 0)
        if section is None or not section.morphs:
            return False

        return res and morphs_settings.enable_ui and morphs_settings.diffeomorphic_emotions_units

    def draw_header(self, context):
        poll, obj = mustardui_active_object(context, config=ModelMode.USER)
        draw_morphs_count(self.layout, obj, 0)

    def draw(self, context):

        poll, obj = mustardui_active_object(context, config=ModelMode.USER)
        morphs_settings = obj.MustardUI_MorphsSettings

        section = get_section_by_diffeomorphic_id(morphs_settings, 0)
        draw_morphs_list(self.layout, obj, section, "Diffeomorphic_0")


class PANEL_PT_MustardUI_Morphs_Emotions(MainPanel, bpy.types.Panel):
    bl_label = "Emotions"
    bl_parent_id = "PANEL_PT_MustardUI_Morphs"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=ModelMode.USER)
        if arm is None:
            return False

        morphs_settings = arm.MustardUI_MorphsSettings

        if morphs_settings.type == "GENERIC":
            return False

        section = get_section_by_diffeomorphic_id(morphs_settings, 1)
        if section is None or not section.morphs:
            return False

        return res and morphs_settings.enable_ui and morphs_settings.diffeomorphic_emotions

    def draw_header(self, context):
        poll, obj = mustardui_active_object(context, config=ModelMode.USER)
        draw_morphs_count(self.layout, obj, 1)

    def draw(self, context):

        poll, obj = mustardui_active_object(context, config=ModelMode.USER)
        morphs_settings = obj.MustardUI_MorphsSettings

        section = get_section_by_diffeomorphic_id(morphs_settings, 1)
        draw_morphs_list(self.layout, obj, section, "Diffeomorphic_1")


class PANEL_PT_MustardUI_Morphs_FACSUnits(MainPanel, bpy.types.Panel):
    bl_label = "Advanced Emotion Units"
    bl_parent_id = "PANEL_PT_MustardUI_Morphs"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=ModelMode.USER)
        if arm is None:
            return False

        morphs_settings = arm.MustardUI_MorphsSettings

        if morphs_settings.type == "GENERIC":
            return False

        section = get_section_by_diffeomorphic_id(morphs_settings, 2)
        if section is None or not section.morphs:
            return False

        return (
            res and morphs_settings.enable_ui and morphs_settings.diffeomorphic_facs_emotions_units
        )

    def draw_header(self, context):
        poll, obj = mustardui_active_object(context, config=ModelMode.USER)
        draw_morphs_count(self.layout, obj, 2)

    def draw(self, context):

        poll, obj = mustardui_active_object(context, config=ModelMode.USER)
        morphs_settings = obj.MustardUI_MorphsSettings

        section = get_section_by_diffeomorphic_id(morphs_settings, 2)
        draw_morphs_list(self.layout, obj, section, "Diffeomorphic_2")


class PANEL_PT_MustardUI_Morphs_FACS(MainPanel, bpy.types.Panel):
    bl_label = "Advanced Emotion"
    bl_parent_id = "PANEL_PT_MustardUI_Morphs"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=ModelMode.USER)
        if arm is None:
            return False

        morphs_settings = arm.MustardUI_MorphsSettings

        if morphs_settings.type == "GENERIC":
            return False

        section = get_section_by_diffeomorphic_id(morphs_settings, 3)
        if section is None or not section.morphs:
            return False

        return res and morphs_settings.enable_ui and morphs_settings.diffeomorphic_facs_emotions

    def draw_header(self, context):
        poll, obj = mustardui_active_object(context, config=ModelMode.USER)
        draw_morphs_count(self.layout, obj, 3)

    def draw(self, context):

        poll, obj = mustardui_active_object(context, config=ModelMode.USER)
        morphs_settings = obj.MustardUI_MorphsSettings

        section = get_section_by_diffeomorphic_id(morphs_settings, 3)
        draw_morphs_list(self.layout, obj, section, "Diffeomorphic_3")


class PANEL_PT_MustardUI_Morphs_Body(MainPanel, bpy.types.Panel):
    bl_label = "Body"
    bl_parent_id = "PANEL_PT_MustardUI_Morphs"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=ModelMode.USER)
        if arm is None:
            return False

        morphs_settings = arm.MustardUI_MorphsSettings

        if morphs_settings.type == "GENERIC":
            return False

        section = get_section_by_diffeomorphic_id(morphs_settings, 4)
        if section is None or not section.morphs:
            return False

        return res and morphs_settings.enable_ui and morphs_settings.diffeomorphic_body_morphs

    def draw_header(self, context):
        poll, obj = mustardui_active_object(context, config=ModelMode.USER)
        draw_morphs_count(self.layout, obj, 4)

    def draw(self, context):

        poll, obj = mustardui_active_object(context, config=ModelMode.USER)
        morphs_settings = obj.MustardUI_MorphsSettings

        section = get_section_by_diffeomorphic_id(morphs_settings, 4)
        draw_morphs_list(self.layout, obj, section, "Diffeomorphic_4")


class PANEL_PT_MustardUI_Morphs_Custom(MainPanel, bpy.types.Panel):
    bl_label = "Custom"
    bl_parent_id = "PANEL_PT_MustardUI_Morphs"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=ModelMode.USER)
        if arm is None:
            return False

        morphs_settings = arm.MustardUI_MorphsSettings

        if morphs_settings.type == "GENERIC":
            return False

        secs = [x for x in morphs_settings.sections if x.morphs and not x.is_internal]

        if not secs:
            return False

        if not any([x.morphs for x in secs]):
            return False

        return res and morphs_settings.enable_ui

    def draw_header(self, context):
        poll, obj = mustardui_active_object(context, config=ModelMode.USER)
        draw_morphs_count(self.layout, obj)

    def draw(self, context):

        poll, obj = mustardui_active_object(context, config=ModelMode.USER)
        morphs_settings = obj.MustardUI_MorphsSettings

        layout = self.layout

        for index, section in enumerate(morphs_settings.sections):
            if not section.morphs or section.is_internal or section.hidden:
                continue
            box = layout.box()
            if ui_collapse_prop(box, section, "collapse", section.name, icon=section.icon):
                draw_morphs_list(box, obj, section, f"Section_{index}")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_Morphs)
    bpy.utils.register_class(PANEL_PT_MustardUI_Morphs_EmotionUnits)
    bpy.utils.register_class(PANEL_PT_MustardUI_Morphs_Emotions)
    bpy.utils.register_class(PANEL_PT_MustardUI_Morphs_FACSUnits)
    bpy.utils.register_class(PANEL_PT_MustardUI_Morphs_FACS)
    bpy.utils.register_class(PANEL_PT_MustardUI_Morphs_Body)
    bpy.utils.register_class(PANEL_PT_MustardUI_Morphs_Custom)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Morphs_Custom)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Morphs_Body)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Morphs_FACS)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Morphs_FACSUnits)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Morphs_Emotions)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Morphs_EmotionUnits)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_Morphs)
