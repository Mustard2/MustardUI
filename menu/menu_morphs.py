import bpy
from . import MainPanel
from ..model_selection.active_object import *
from ..warnings.ops_fix_old_UI import check_old_UI
from ..settings.rig import *
from ..misc.ui_collapse import ui_collapse_prop
from ..morphs.misc import get_section_by_diffeomorphic_id, get_cp_source


def morph_filter(morph, rig_settings, morphs_settings):
    # Check null filter
    val = None

    cp_source = get_cp_source(morph.custom_property_source, rig_settings)
    if cp_source and morph.custom_property and hasattr(cp_source,
                                         f'["{bpy.utils.escape_identifier(morph.path)}"]'):
        val = cp_source[bpy.utils.escape_identifier(morph.path)]
    elif morph.shape_key and morph.path in rig_settings.model_body.data.shape_keys.key_blocks.keys():
        val = rig_settings.model_body.data.shape_keys.key_blocks[morph.path].value

    check1 = False
    if isinstance(val, float):
        check1 = (morphs_settings.diffeomorphic_filter_null and val != 0.) or not morphs_settings.diffeomorphic_filter_null
    elif isinstance(val, bool):
        check1 = (morphs_settings.diffeomorphic_filter_null and not val) or not morphs_settings.diffeomorphic_filter_null

    # Check search filter
    check2 = morphs_settings.diffeomorphic_search.lower() in morph.name.lower()

    return check1 and check2


class PANEL_PT_MustardUI_Morphs(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_Morphs"
    bl_label = "Morphs"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):

        if check_old_UI():
            return False

        res, arm = mustardui_active_object(context, config=0)

        if arm is None:
            return False

        morphs_settings = arm.MustardUI_MorphsSettings

        if morphs_settings.type == "GENERIC":
            return res and morphs_settings.enable_ui and morphs_settings.morphs_number > 0

        if not get_section_by_diffeomorphic_id(morphs_settings, 0):
            return False

        # Check if at least one panel is available in the Diffeomiorphic case
        panels = (get_section_by_diffeomorphic_id(morphs_settings, 0).morphs
                  or get_section_by_diffeomorphic_id(morphs_settings, 1).morphs
                  or get_section_by_diffeomorphic_id(morphs_settings, 2).morphs
                  or get_section_by_diffeomorphic_id(morphs_settings, 3).morphs
                  or get_section_by_diffeomorphic_id(morphs_settings, 4).morphs)

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

            row = layout.row()
            row.prop(morphs_settings, 'diffeomorphic_search', icon="VIEWZOOM")
            row2 = row.row(align=True)
            row2.prop(morphs_settings, 'diffeomorphic_filter_null', icon="FILTER", text="")
            row2.operator('mustardui.morphs_defaultvalues', icon="LOOP_BACK", text="")
            row2.prop(morphs_settings, 'diffeomorphic_enable_settings', icon="PREFERENCES", text="")
            if morphs_settings.diffeomorphic_enable_settings:
                box = layout.box()
                col = box.column(align=True)
                col.prop(morphs_settings, 'diffeomorphic_enable_shapekeys')
                col.prop(morphs_settings, 'diffeomorphic_enable_pJCM')
                col.prop(morphs_settings, 'diffeomorphic_enable_facs')
                row = col.row(align=True)
                row.enabled = not morphs_settings.diffeomorphic_enable_facs
                row.prop(morphs_settings, 'diffeomorphic_enable_facs_bones')
        # Generic panel
        else:
            for section in [x for x in morphs_settings.sections if x.morphs]:
                if ui_collapse_prop(layout, section, 'collapse', section.name, icon=section.icon):
                    layout.template_list("MUSTARDUI_UL_Morphs_UIList_Menu", "The_List",
                                      section, "morphs",
                                      obj, "mustardui_morphs_uilist_menu_index")

            row = layout.row()
            row.operator('mustardui.morphs_defaultvalues', icon="LOOP_BACK")

        row.operator("mustardui.morphs_presets_ui", text="", icon="PRESET")


class PANEL_PT_MustardUI_Morphs_EmotionUnits(MainPanel, bpy.types.Panel):
    bl_label = "Emotion Units"
    bl_parent_id = "PANEL_PT_MustardUI_Morphs"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        if check_old_UI():
            return False

        res, arm = mustardui_active_object(context, config=0)
        if arm is None:
            return False

        morphs_settings = arm.MustardUI_MorphsSettings

        if morphs_settings.type == "GENERIC":
            return False

        if not get_section_by_diffeomorphic_id(morphs_settings, 0).morphs:
            return False

        return (res and morphs_settings.enable_ui and morphs_settings.diffeomorphic_emotions_units and
                get_section_by_diffeomorphic_id(morphs_settings, 0).morphs)

    def draw_header(self, context):

        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings
        morphs_settings = obj.MustardUI_MorphsSettings

        layout = self.layout
        emotion_units_morphs = [x for x in get_section_by_diffeomorphic_id(morphs_settings, 0).morphs if morph_filter(x, rig_settings, morphs_settings)]
        layout.label(text="(" + str(len(emotion_units_morphs)) + ")")

    def draw(self, context):

        settings = bpy.context.scene.MustardUI_Settings

        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings
        morphs_settings = obj.MustardUI_MorphsSettings

        layout = self.layout
        layout.enabled = morphs_settings.diffeomorphic_enable

        emotion_units_morphs = [x for x in get_section_by_diffeomorphic_id(morphs_settings, 0).morphs if morph_filter(x, rig_settings, morphs_settings)]

        for morph in emotion_units_morphs:
            if hasattr(rig_settings.model_armature_object, f'["{bpy.utils.escape_identifier(morph.path)}"]'):
                layout.prop(rig_settings.model_armature_object, f'["{bpy.utils.escape_identifier(morph.path)}"]',
                            text=morph.name)
            else:
                row = layout.row(align=False)
                row.label(text=morph.name)
                row.prop(settings, 'daz_morphs_error', text="", icon="ERROR", emboss=False, icon_only=True)


class PANEL_PT_MustardUI_Morphs_Emotions(MainPanel, bpy.types.Panel):
    bl_label = "Emotions"
    bl_parent_id = "PANEL_PT_MustardUI_Morphs"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        if check_old_UI():
            return False

        res, arm = mustardui_active_object(context, config=0)
        if arm is None:
            return False

        morphs_settings = arm.MustardUI_MorphsSettings

        if morphs_settings.type == "GENERIC":
            return False

        if not get_section_by_diffeomorphic_id(morphs_settings, 1).morphs:
            return False

        return (res and morphs_settings.enable_ui and morphs_settings.diffeomorphic_emotions and
                get_section_by_diffeomorphic_id(morphs_settings, 1).morphs)

    def draw_header(self, context):

        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings
        morphs_settings = obj.MustardUI_MorphsSettings

        layout = self.layout
        emotion_morphs = [x for x in get_section_by_diffeomorphic_id(morphs_settings, 1).morphs if morph_filter(x, rig_settings, morphs_settings)]
        layout.label(text="(" + str(len(emotion_morphs)) + ")")

    def draw(self, context):

        settings = bpy.context.scene.MustardUI_Settings

        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings
        morphs_settings = obj.MustardUI_MorphsSettings

        layout = self.layout
        layout.enabled = morphs_settings.diffeomorphic_enable

        emotion_morphs = [x for x in get_section_by_diffeomorphic_id(morphs_settings, 1).morphs if morph_filter(x, rig_settings, morphs_settings)]

        for morph in emotion_morphs:
            if hasattr(rig_settings.model_armature_object, f'["{bpy.utils.escape_identifier(morph.path)}"]'):
                layout.prop(rig_settings.model_armature_object, f'["{bpy.utils.escape_identifier(morph.path)}"]',
                            text=morph.name)
            else:
                row = layout.row(align=False)
                row.label(text=morph.name)
                row.prop(settings, 'daz_morphs_error', text="", icon="ERROR", emboss=False, icon_only=True)


class PANEL_PT_MustardUI_Morphs_FACSUnits(MainPanel, bpy.types.Panel):
    bl_label = "Advanced Emotion Units"
    bl_parent_id = "PANEL_PT_MustardUI_Morphs"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        if check_old_UI():
            return False

        res, arm = mustardui_active_object(context, config=0)
        if arm is None:
            return False

        morphs_settings = arm.MustardUI_MorphsSettings

        if morphs_settings.type == "GENERIC":
            return False

        if not get_section_by_diffeomorphic_id(morphs_settings, 2).morphs:
            return False

        return (res and morphs_settings.enable_ui and morphs_settings.diffeomorphic_facs_emotions_units and
                get_section_by_diffeomorphic_id(morphs_settings, 2).morphs)

    def draw_header(self, context):

        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings
        morphs_settings = obj.MustardUI_MorphsSettings

        layout = self.layout
        emotion_morphs = [x for x in get_section_by_diffeomorphic_id(morphs_settings, 2).morphs if morph_filter(x, rig_settings, morphs_settings)]
        layout.label(text="(" + str(len(emotion_morphs)) + ")")

    def draw(self, context):

        settings = bpy.context.scene.MustardUI_Settings

        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings
        morphs_settings = obj.MustardUI_MorphsSettings

        layout = self.layout
        layout.enabled = morphs_settings.diffeomorphic_enable

        facs_emotion_units_morphs = [x for x in get_section_by_diffeomorphic_id(morphs_settings, 2).morphs if morph_filter(x, rig_settings, morphs_settings)]

        for morph in facs_emotion_units_morphs:
            if hasattr(rig_settings.model_armature_object, f'["{bpy.utils.escape_identifier(morph.path)}"]'):
                layout.prop(rig_settings.model_armature_object, f'["{bpy.utils.escape_identifier(morph.path)}"]',
                            text=morph.name)
            else:
                row = layout.row(align=False)
                row.label(text=morph.name)
                row.prop(settings, 'daz_morphs_error', text="", icon="ERROR", emboss=False, icon_only=True)


class PANEL_PT_MustardUI_Morphs_FACS(MainPanel, bpy.types.Panel):
    bl_label = "Advanced Emotion"
    bl_parent_id = "PANEL_PT_MustardUI_Morphs"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        if check_old_UI():
            return False

        res, arm = mustardui_active_object(context, config=0)
        if arm is None:
            return False

        morphs_settings = arm.MustardUI_MorphsSettings

        if morphs_settings.type == "GENERIC":
            return False

        if not get_section_by_diffeomorphic_id(morphs_settings, 3).morphs:
            return False

        return (res and morphs_settings.enable_ui and morphs_settings.diffeomorphic_facs_emotions and
                get_section_by_diffeomorphic_id(morphs_settings, 3).morphs)

    def draw_header(self, context):

        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings
        morphs_settings = obj.MustardUI_MorphsSettings

        layout = self.layout
        emotion_morphs = [x for x in get_section_by_diffeomorphic_id(morphs_settings, 3).morphs if morph_filter(x, rig_settings, morphs_settings)]
        layout.label(text="(" + str(len(emotion_morphs)) + ")")

    def draw(self, context):

        settings = bpy.context.scene.MustardUI_Settings

        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings
        morphs_settings = obj.MustardUI_MorphsSettings

        layout = self.layout
        layout.enabled = morphs_settings.diffeomorphic_enable

        facs_emotion_morphs = [x for x in get_section_by_diffeomorphic_id(morphs_settings, 3).morphs if morph_filter(x, rig_settings, morphs_settings)]

        for morph in facs_emotion_morphs:
            if hasattr(rig_settings.model_armature_object, f'["{bpy.utils.escape_identifier(morph.path)}"]'):
                layout.prop(rig_settings.model_armature_object, f'["{bpy.utils.escape_identifier(morph.path)}"]',
                            text=morph.name)
            else:
                row = layout.row(align=False)
                row.label(text=morph.name)
                row.prop(settings, 'daz_morphs_error', text="", icon="ERROR", emboss=False, icon_only=True)


class PANEL_PT_MustardUI_Morphs_Body(MainPanel, bpy.types.Panel):
    bl_label = "Body"
    bl_parent_id = "PANEL_PT_MustardUI_Morphs"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        if check_old_UI():
            return False

        res, arm = mustardui_active_object(context, config=0)
        if arm is None:
            return False

        morphs_settings = arm.MustardUI_MorphsSettings

        if morphs_settings.type == "GENERIC":
            return False

        if not get_section_by_diffeomorphic_id(morphs_settings, 4).morphs:
            return False

        return (res and morphs_settings.enable_ui and morphs_settings.diffeomorphic_body_morphs and
                get_section_by_diffeomorphic_id(morphs_settings, 4).morphs)

    def draw_header(self, context):

        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings
        morphs_settings = obj.MustardUI_MorphsSettings

        layout = self.layout
        emotion_morphs = [x for x in get_section_by_diffeomorphic_id(morphs_settings, 4).morphs if morph_filter(x, rig_settings, morphs_settings)]
        layout.label(text="(" + str(len(emotion_morphs)) + ")")

    def draw(self, context):

        settings = bpy.context.scene.MustardUI_Settings

        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings
        morphs_settings = obj.MustardUI_MorphsSettings

        layout = self.layout
        layout.enabled = morphs_settings.diffeomorphic_enable

        # Body Morphs
        body_morphs = [x for x in get_section_by_diffeomorphic_id(morphs_settings, 4).morphs if morph_filter(x, rig_settings, morphs_settings)]

        for morph in body_morphs:
            if hasattr(rig_settings.model_armature_object, f'["{bpy.utils.escape_identifier(morph.path)}"]'):
                layout.prop(rig_settings.model_armature_object, f'["{bpy.utils.escape_identifier(morph.path)}"]',
                         text=morph.name)
            else:
                row = layout.row(align=False)
                row.label(text=morph.name)
                row.prop(settings, 'daz_morphs_error', text="", icon="ERROR", emboss=False, icon_only=True)


class PANEL_PT_MustardUI_Morphs_Custom(MainPanel, bpy.types.Panel):
    bl_label = "Custom"
    bl_parent_id = "PANEL_PT_MustardUI_Morphs"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        if check_old_UI():
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
        rig_settings = obj.MustardUI_RigSettings
        morphs_settings = obj.MustardUI_MorphsSettings

        layout = self.layout
        count = 0
        for section in [x for x in morphs_settings.sections if x.morphs and not x.is_internal]:
            count += len([x for x in section.morphs if morph_filter(x, rig_settings, morphs_settings)])
        layout.label(text="(" + str(count) + ")")

    def draw(self, context):

        settings = bpy.context.scene.MustardUI_Settings

        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings
        morphs_settings = obj.MustardUI_MorphsSettings

        layout = self.layout
        layout.enabled = morphs_settings.diffeomorphic_enable

        for section in [x for x in morphs_settings.sections if x.morphs and not x.is_internal]:
            box = layout.box()
            if ui_collapse_prop(box, section, 'collapse', section.name, icon=section.icon):
                for morph in [x for x in section.morphs if morph_filter(x, rig_settings, morphs_settings)]:
                    cp_source = get_cp_source(morph.custom_property_source, rig_settings)
                    if cp_source and morph.custom_property and hasattr(cp_source, f'["{bpy.utils.escape_identifier(morph.path)}"]'):
                        box.prop(cp_source, f'["{bpy.utils.escape_identifier(morph.path)}"]', text=morph.name)
                    elif morph.shape_key and morph.path in rig_settings.model_body.data.shape_keys.key_blocks.keys():
                        box.prop(rig_settings.model_body.data.shape_keys.key_blocks[morph.path], 'value',
                                    text=morph.name)
                    else:
                        row = box.row(align=False)
                        row.label(text=morph.name)
                        row.prop(settings, 'daz_morphs_error', text="", icon="ERROR", emboss=False, icon_only=True)


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
