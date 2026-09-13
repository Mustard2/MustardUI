import bpy

from ..misc.ui_collapse import ui_collapse_prop
from ..model_selection.active_object import mustardui_active_object
from ..morphs.misc import get_section_by_diffeomorphic_id, morph_filter_function
from ..warnings.can_draw_ui import can_draw_ui
from . import MainPanel


# Each list needs its own id, or the lists would share their size and scrolling
def draw_morphs_list(layout, arm, section, list_id):
    layout.template_list(
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
        sections = [get_section_by_diffeomorphic_id(morphs_settings, diffeomorphic_id)]

    morph_filter = morph_filter_function(arm.MustardUI_RigSettings, morphs_settings)
    count = sum(1 for section in sections for morph in section.morphs if morph_filter(morph))
    layout.label(text=f"({count})")


# Draw header Morph buttons
def draw_morphs_buttons(layout, morphs_settings, has_morphs=True, settings_button=False):
    freeze = morphs_settings.enable_freeze_morphs

    if has_morphs:
        row = layout.row(align=freeze)
        row.prop(morphs_settings, "diffeomorphic_search", icon="VIEWZOOM")
        buttons = row.row(align=True)
        buttons.prop(morphs_settings, "diffeomorphic_filter_null", icon="FILTER", text="")

    if freeze:
        row = layout.row()
        row.operator(
            "mustardui.morphs_optimize",
            text="Morphs Freeze",
            depress=morphs_settings.morphs_optimized,
            icon="FREEZE",
        )
        buttons = row.row(align=True)

    if has_morphs:
        buttons.operator("mustardui.morphs_defaultvalues", text="", icon="LOOP_BACK")
        if settings_button:
            buttons.prop(
                morphs_settings, "diffeomorphic_enable_settings", icon="PREFERENCES", text=""
            )
        if not freeze:
            buttons.separator()
        op = buttons.operator("mustardui.presets_ui", text="", icon="PRESET")
        op.preset_type = "MORPHS"


class PANEL_PT_MustardUI_Morphs(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Morphs"
    bl_label = "Morphs"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):

        if can_draw_ui():
            return False

        res, arm = mustardui_active_object(context, config=0)

        if arm is None:
            return False

        morphs_settings = arm.MustardUI_MorphsSettings

        if morphs_settings.type == "GENERIC":
            return res and morphs_settings.enable_ui and morphs_settings.morphs_number > 0

        if not get_section_by_diffeomorphic_id(morphs_settings, 0):
            return False

        # Check if at least one panel is available in the Diffeomorphic case
        panels = (
            get_section_by_diffeomorphic_id(morphs_settings, 0).morphs
            or get_section_by_diffeomorphic_id(morphs_settings, 1).morphs
            or get_section_by_diffeomorphic_id(morphs_settings, 2).morphs
            or get_section_by_diffeomorphic_id(morphs_settings, 3).morphs
            or get_section_by_diffeomorphic_id(morphs_settings, 4).morphs
        )

        return res and morphs_settings.enable_ui and panels and morphs_settings.morphs_number > 0

    def draw_header(self, context):

        poll, obj = mustardui_active_object(context, config=0)
        morphs_settings = obj.MustardUI_MorphsSettings

        if morphs_settings.type != "GENERIC":
            layout = self.layout
            layout.prop(morphs_settings, "diffeomorphic_enable", text="", toggle=False)

    def draw(self, context):

        poll, obj = mustardui_active_object(context, config=0)
        morphs_settings = obj.MustardUI_MorphsSettings

        layout = self.layout

        # Diffeomorphic panel
        if morphs_settings.type != "GENERIC":
            layout.enabled = morphs_settings.diffeomorphic_enable

            draw_morphs_buttons(layout, morphs_settings, settings_button=True)

            if morphs_settings.diffeomorphic_enable_settings:
                box = layout.box()
                col = box.column(align=True)
                col.prop(morphs_settings, "diffeomorphic_enable_shapekeys")
                col.prop(morphs_settings, "diffeomorphic_enable_pJCM")
                col.prop(morphs_settings, "diffeomorphic_enable_facs")
                row = col.row(align=True)
                row.enabled = not morphs_settings.diffeomorphic_enable_facs
                row.prop(morphs_settings, "diffeomorphic_enable_facs_bones")
                col.separator()
                col.prop(morphs_settings, "diffeomorphic_show_count")

        # Generic panel
        else:
            has_morphs = any(x.morphs and not x.hidden for x in morphs_settings.sections)
            draw_morphs_buttons(layout, morphs_settings, has_morphs, settings_button=True)

            if has_morphs and morphs_settings.diffeomorphic_enable_settings:
                box = layout.box()
                box.prop(morphs_settings, "diffeomorphic_show_count")

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
                    row = layout.row()
                    row.enabled = (
                        not morphs_settings.morphs_optimized if section.freezable else True
                    )
                    draw_morphs_list(row, obj, section, f"Section_{index}")


class PANEL_PT_MustardUI_Morphs_EmotionUnits(MainPanel, bpy.types.Panel):
    bl_label = "Emotion Units"
    bl_parent_id = "PANEL_PT_MustardUI_Morphs"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        if can_draw_ui():
            return False

        res, arm = mustardui_active_object(context, config=0)
        if arm is None:
            return False

        morphs_settings = arm.MustardUI_MorphsSettings

        if morphs_settings.type == "GENERIC":
            return False

        if not get_section_by_diffeomorphic_id(morphs_settings, 0).morphs:
            return False

        return (
            res
            and morphs_settings.enable_ui
            and morphs_settings.diffeomorphic_emotions_units
            and get_section_by_diffeomorphic_id(morphs_settings, 0).morphs
        )

    def draw_header(self, context):
        poll, obj = mustardui_active_object(context, config=0)
        draw_morphs_count(self.layout, obj, 0)

    def draw(self, context):

        poll, obj = mustardui_active_object(context, config=0)
        morphs_settings = obj.MustardUI_MorphsSettings

        layout = self.layout
        layout.enabled = morphs_settings.diffeomorphic_enable

        section = get_section_by_diffeomorphic_id(morphs_settings, 0)
        draw_morphs_list(layout, obj, section, "Diffeomorphic_0")


class PANEL_PT_MustardUI_Morphs_Emotions(MainPanel, bpy.types.Panel):
    bl_label = "Emotions"
    bl_parent_id = "PANEL_PT_MustardUI_Morphs"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        if can_draw_ui():
            return False

        res, arm = mustardui_active_object(context, config=0)
        if arm is None:
            return False

        morphs_settings = arm.MustardUI_MorphsSettings

        if morphs_settings.type == "GENERIC":
            return False

        if not get_section_by_diffeomorphic_id(morphs_settings, 1).morphs:
            return False

        return (
            res
            and morphs_settings.enable_ui
            and morphs_settings.diffeomorphic_emotions
            and get_section_by_diffeomorphic_id(morphs_settings, 1).morphs
        )

    def draw_header(self, context):
        poll, obj = mustardui_active_object(context, config=0)
        draw_morphs_count(self.layout, obj, 1)

    def draw(self, context):

        poll, obj = mustardui_active_object(context, config=0)
        morphs_settings = obj.MustardUI_MorphsSettings

        layout = self.layout
        layout.enabled = (
            morphs_settings.diffeomorphic_enable and not morphs_settings.morphs_optimized
        )

        section = get_section_by_diffeomorphic_id(morphs_settings, 1)
        draw_morphs_list(layout, obj, section, "Diffeomorphic_1")


class PANEL_PT_MustardUI_Morphs_FACSUnits(MainPanel, bpy.types.Panel):
    bl_label = "Advanced Emotion Units"
    bl_parent_id = "PANEL_PT_MustardUI_Morphs"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        if can_draw_ui():
            return False

        res, arm = mustardui_active_object(context, config=0)
        if arm is None:
            return False

        morphs_settings = arm.MustardUI_MorphsSettings

        if morphs_settings.type == "GENERIC":
            return False

        if not get_section_by_diffeomorphic_id(morphs_settings, 2).morphs:
            return False

        return (
            res
            and morphs_settings.enable_ui
            and morphs_settings.diffeomorphic_facs_emotions_units
            and get_section_by_diffeomorphic_id(morphs_settings, 2).morphs
        )

    def draw_header(self, context):
        poll, obj = mustardui_active_object(context, config=0)
        draw_morphs_count(self.layout, obj, 2)

    def draw(self, context):

        poll, obj = mustardui_active_object(context, config=0)
        morphs_settings = obj.MustardUI_MorphsSettings

        layout = self.layout
        layout.enabled = morphs_settings.diffeomorphic_enable

        section = get_section_by_diffeomorphic_id(morphs_settings, 2)
        draw_morphs_list(layout, obj, section, "Diffeomorphic_2")


class PANEL_PT_MustardUI_Morphs_FACS(MainPanel, bpy.types.Panel):
    bl_label = "Advanced Emotion"
    bl_parent_id = "PANEL_PT_MustardUI_Morphs"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        if can_draw_ui():
            return False

        res, arm = mustardui_active_object(context, config=0)
        if arm is None:
            return False

        morphs_settings = arm.MustardUI_MorphsSettings

        if morphs_settings.type == "GENERIC":
            return False

        if not get_section_by_diffeomorphic_id(morphs_settings, 3).morphs:
            return False

        return (
            res
            and morphs_settings.enable_ui
            and morphs_settings.diffeomorphic_facs_emotions
            and get_section_by_diffeomorphic_id(morphs_settings, 3).morphs
        )

    def draw_header(self, context):
        poll, obj = mustardui_active_object(context, config=0)
        draw_morphs_count(self.layout, obj, 3)

    def draw(self, context):

        poll, obj = mustardui_active_object(context, config=0)
        morphs_settings = obj.MustardUI_MorphsSettings

        layout = self.layout
        layout.enabled = (
            morphs_settings.diffeomorphic_enable and not morphs_settings.morphs_optimized
        )

        section = get_section_by_diffeomorphic_id(morphs_settings, 3)
        draw_morphs_list(layout, obj, section, "Diffeomorphic_3")


class PANEL_PT_MustardUI_Morphs_Body(MainPanel, bpy.types.Panel):
    bl_label = "Body"
    bl_parent_id = "PANEL_PT_MustardUI_Morphs"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        if can_draw_ui():
            return False

        res, arm = mustardui_active_object(context, config=0)
        if arm is None:
            return False

        morphs_settings = arm.MustardUI_MorphsSettings

        if morphs_settings.type == "GENERIC":
            return False

        if not get_section_by_diffeomorphic_id(morphs_settings, 4).morphs:
            return False

        return (
            res
            and morphs_settings.enable_ui
            and morphs_settings.diffeomorphic_body_morphs
            and get_section_by_diffeomorphic_id(morphs_settings, 4).morphs
        )

    def draw_header(self, context):
        poll, obj = mustardui_active_object(context, config=0)
        draw_morphs_count(self.layout, obj, 4)

    def draw(self, context):

        poll, obj = mustardui_active_object(context, config=0)
        morphs_settings = obj.MustardUI_MorphsSettings

        layout = self.layout
        layout.enabled = (
            morphs_settings.diffeomorphic_enable and not morphs_settings.morphs_optimized
        )

        section = get_section_by_diffeomorphic_id(morphs_settings, 4)
        draw_morphs_list(layout, obj, section, "Diffeomorphic_4")


class PANEL_PT_MustardUI_Morphs_Custom(MainPanel, bpy.types.Panel):
    bl_label = "Custom"
    bl_parent_id = "PANEL_PT_MustardUI_Morphs"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        if can_draw_ui():
            return False

        res, arm = mustardui_active_object(context, config=0)
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
        poll, obj = mustardui_active_object(context, config=0)
        draw_morphs_count(self.layout, obj)

    def draw(self, context):

        poll, obj = mustardui_active_object(context, config=0)
        morphs_settings = obj.MustardUI_MorphsSettings

        layout = self.layout
        layout.enabled = morphs_settings.diffeomorphic_enable

        for index, section in enumerate(morphs_settings.sections):
            if not section.morphs or section.is_internal or section.hidden:
                continue
            box = layout.box()
            box.enabled = not morphs_settings.morphs_optimized if section.freezable else True
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
