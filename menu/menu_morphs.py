import bpy
from . import MainPanel
from ..model_selection.active_object import *
from ..misc.prop_utils import *
from ..warnings.ops_fix_old_UI import check_old_UI
from ..settings.rig import *


def morph_filter(morph, rig_settings):
    # Check null filter
    check1 = (rig_settings.diffeomorphic_filter_null and evaluate_rna(
        f'rig_settings.model_armature_object["{bpy.utils.escape_identifier(morph.path)}"]') != 0.) or not rig_settings.diffeomorphic_filter_null

    # Check search filter
    check2 = rig_settings.diffeomorphic_search.lower() in morph.name.lower()

    return check1 and check2


class PANEL_PT_MustardUI_ExternalMorphs(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_ExternalMorphs"
    bl_label = "Morphs"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):

        if check_old_UI():
            return False

        res, arm = mustardui_active_object(context, config=0)

        if arm is not None:
            rig_settings = arm.MustardUI_RigSettings

            # Check if at least one panel is available
            panels = (rig_settings.diffeomorphic_emotions or rig_settings.diffeomorphic_emotions_units or
                      rig_settings.diffeomorphic_facs_emotions_units or rig_settings.diffeomorphic_facs_emotions or
                      rig_settings.diffeomorphic_body_morphs)

            return (res and rig_settings.diffeomorphic_support and panels and
                    rig_settings.diffeomorphic_morphs_number > 0)

        return res

    def draw_header(self, context):

        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings

        layout = self.layout
        layout.prop(rig_settings, "diffeomorphic_enable", text="", toggle=False)

    def draw(self, context):

        settings = bpy.context.scene.MustardUI_Settings

        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings

        layout = self.layout
        layout.enabled = rig_settings.diffeomorphic_enable

        row = layout.row()
        row.prop(rig_settings, 'diffeomorphic_search', icon="VIEWZOOM")
        row2 = row.row(align=True)
        row2.prop(rig_settings, 'diffeomorphic_filter_null', icon="FILTER", text="")
        row2.operator('mustardui.morphs_defaultvalues', icon="LOOP_BACK", text="")
        row2.operator('mustardui.morphs_clearpose', icon="OUTLINER_OB_ARMATURE", text="")
        row2.prop(rig_settings, 'diffeomorphic_enable_settings', icon="PREFERENCES", text="")
        if rig_settings.diffeomorphic_enable_settings:
            box = layout.box()
            col = box.column(align=True)
            col.prop(rig_settings, 'diffeomorphic_enable_shapekeys')
            col.prop(rig_settings, 'diffeomorphic_enable_pJCM')
            col.prop(rig_settings, 'diffeomorphic_enable_facs')
            row = col.row(align=True)
            row.enabled = not rig_settings.diffeomorphic_enable_facs
            row.prop(rig_settings, 'diffeomorphic_enable_facs_bones')


class PANEL_PT_MustardUI_ExternalMorphs_EmotionUnits(MainPanel, bpy.types.Panel):
    bl_label = "Emotion Units"
    bl_parent_id = "PANEL_PT_MustardUI_ExternalMorphs"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        if check_old_UI():
            return False

        res, arm = mustardui_active_object(context, config=0)
        if arm is not None:
            rig_settings = arm.MustardUI_RigSettings
            return res and rig_settings.diffeomorphic_support and rig_settings.diffeomorphic_emotions_units

        return res

    def draw_header(self, context):

        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings

        layout = self.layout
        emotion_units_morphs = [x for x in rig_settings.diffeomorphic_morphs_list if
                                x.type == 0 and morph_filter(x, rig_settings)]
        layout.label(text="(" + str(len(emotion_units_morphs)) + ")")

    def draw(self, context):

        settings = bpy.context.scene.MustardUI_Settings

        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings

        layout = self.layout
        layout.enabled = rig_settings.diffeomorphic_enable

        emotion_units_morphs = [x for x in rig_settings.diffeomorphic_morphs_list if
                                x.type == 0 and morph_filter(x, rig_settings)]

        for morph in emotion_units_morphs:
            if hasattr(rig_settings.model_armature_object, f'["{bpy.utils.escape_identifier(morph.path)}"]'):
                layout.prop(rig_settings.model_armature_object, f'["{bpy.utils.escape_identifier(morph.path)}"]',
                            text=morph.name)
            else:
                row = layout.row(align=False)
                row.label(text=morph.name)
                row.prop(settings, 'daz_morphs_error', text="", icon="ERROR", emboss=False, icon_only=True)


class PANEL_PT_MustardUI_ExternalMorphs_Emotions(MainPanel, bpy.types.Panel):
    bl_label = "Emotions"
    bl_parent_id = "PANEL_PT_MustardUI_ExternalMorphs"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        if check_old_UI():
            return False

        res, arm = mustardui_active_object(context, config=0)
        if arm is not None:
            rig_settings = arm.MustardUI_RigSettings
            return res and rig_settings.diffeomorphic_support and rig_settings.diffeomorphic_emotions

        return res

    def draw_header(self, context):

        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings

        layout = self.layout
        emotion_morphs = [x for x in rig_settings.diffeomorphic_morphs_list if
                          x.type == 1 and morph_filter(x, rig_settings)]
        layout.label(text="(" + str(len(emotion_morphs)) + ")")

    def draw(self, context):

        settings = bpy.context.scene.MustardUI_Settings

        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings

        layout = self.layout
        layout.enabled = rig_settings.diffeomorphic_enable

        emotion_morphs = [x for x in rig_settings.diffeomorphic_morphs_list if
                          x.type == 1 and morph_filter(x, rig_settings)]

        for morph in emotion_morphs:
            if hasattr(rig_settings.model_armature_object, f'["{bpy.utils.escape_identifier(morph.path)}"]'):
                layout.prop(rig_settings.model_armature_object, f'["{bpy.utils.escape_identifier(morph.path)}"]',
                            text=morph.name)
            else:
                row = layout.row(align=False)
                row.label(text=morph.name)
                row.prop(settings, 'daz_morphs_error', text="", icon="ERROR", emboss=False, icon_only=True)


class PANEL_PT_MustardUI_ExternalMorphs_FACSUnits(MainPanel, bpy.types.Panel):
    bl_label = "Advanced Emotion Units"
    bl_parent_id = "PANEL_PT_MustardUI_ExternalMorphs"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        if check_old_UI():
            return False

        res, arm = mustardui_active_object(context, config=0)
        if arm is not None:
            rig_settings = arm.MustardUI_RigSettings
            return res and rig_settings.diffeomorphic_support and rig_settings.diffeomorphic_facs_emotions_units

        return res

    def draw_header(self, context):

        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings

        layout = self.layout
        emotion_morphs = [x for x in rig_settings.diffeomorphic_morphs_list if
                          x.type == 2 and morph_filter(x, rig_settings)]
        layout.label(text="(" + str(len(emotion_morphs)) + ")")

    def draw(self, context):

        settings = bpy.context.scene.MustardUI_Settings

        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings

        layout = self.layout
        layout.enabled = rig_settings.diffeomorphic_enable

        facs_emotion_units_morphs = [x for x in rig_settings.diffeomorphic_morphs_list if
                                     x.type == 2 and morph_filter(x, rig_settings)]

        for morph in facs_emotion_units_morphs:
            if hasattr(rig_settings.model_armature_object, f'["{bpy.utils.escape_identifier(morph.path)}"]'):
                layout.prop(rig_settings.model_armature_object, f'["{bpy.utils.escape_identifier(morph.path)}"]',
                            text=morph.name)
            else:
                row = layout.row(align=False)
                row.label(text=morph.name)
                row.prop(settings, 'daz_morphs_error', text="", icon="ERROR", emboss=False, icon_only=True)


class PANEL_PT_MustardUI_ExternalMorphs_FACS(MainPanel, bpy.types.Panel):
    bl_label = "Advanced Emotion"
    bl_parent_id = "PANEL_PT_MustardUI_ExternalMorphs"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        if check_old_UI():
            return False

        res, arm = mustardui_active_object(context, config=0)
        if arm is not None:
            rig_settings = arm.MustardUI_RigSettings
            return res and rig_settings.diffeomorphic_support and rig_settings.diffeomorphic_facs_emotions_units

        return res

    def draw_header(self, context):

        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings

        layout = self.layout
        emotion_morphs = [x for x in rig_settings.diffeomorphic_morphs_list if
                          x.type == 3 and morph_filter(x, rig_settings)]
        layout.label(text="(" + str(len(emotion_morphs)) + ")")

    def draw(self, context):

        settings = bpy.context.scene.MustardUI_Settings

        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings

        layout = self.layout
        layout.enabled = rig_settings.diffeomorphic_enable

        facs_emotion_morphs = [x for x in rig_settings.diffeomorphic_morphs_list if
                               x.type == 3 and morph_filter(x, rig_settings)]

        for morph in facs_emotion_morphs:
            if hasattr(rig_settings.model_armature_object, f'["{bpy.utils.escape_identifier(morph.path)}"]'):
                layout.prop(rig_settings.model_armature_object, f'["{bpy.utils.escape_identifier(morph.path)}"]',
                            text=morph.name)
            else:
                row = layout.row(align=False)
                row.label(text=morph.name)
                row.prop(settings, 'daz_morphs_error', text="", icon="ERROR", emboss=False, icon_only=True)


class PANEL_PT_MustardUI_ExternalMorphs_Body(MainPanel, bpy.types.Panel):
    bl_label = "Body"
    bl_parent_id = "PANEL_PT_MustardUI_ExternalMorphs"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        if check_old_UI():
            return False

        res, arm = mustardui_active_object(context, config=0)
        if arm is not None:
            rig_settings = arm.MustardUI_RigSettings
            return res and rig_settings.diffeomorphic_support and rig_settings.diffeomorphic_facs_emotions_units

        return res

    def draw_header(self, context):

        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings

        layout = self.layout
        emotion_morphs = [x for x in rig_settings.diffeomorphic_morphs_list if
                          x.type == 4 and morph_filter(x, rig_settings)]
        layout.label(text="(" + str(len(emotion_morphs)) + ")")

    def draw(self, context):

        settings = bpy.context.scene.MustardUI_Settings

        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings

        layout = self.layout
        layout.enabled = rig_settings.diffeomorphic_enable

        # Body Morphs
        body_morphs = [x for x in rig_settings.diffeomorphic_morphs_list if
                       x.type == 4 and morph_filter(x, rig_settings)]

        for morph in body_morphs:
            if hasattr(rig_settings.model_armature_object, f'["{bpy.utils.escape_identifier(morph.path)}"]'):
                layout.prop(rig_settings.model_armature_object, f'["{bpy.utils.escape_identifier(morph.path)}"]',
                         text=morph.name)
            else:
                row = layout.row(align=False)
                row.label(text=morph.name)
                row.prop(settings, 'daz_morphs_error', text="", icon="ERROR", emboss=False, icon_only=True)


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_ExternalMorphs)
    bpy.utils.register_class(PANEL_PT_MustardUI_ExternalMorphs_EmotionUnits)
    bpy.utils.register_class(PANEL_PT_MustardUI_ExternalMorphs_Emotions)
    bpy.utils.register_class(PANEL_PT_MustardUI_ExternalMorphs_FACSUnits)
    bpy.utils.register_class(PANEL_PT_MustardUI_ExternalMorphs_FACS)
    bpy.utils.register_class(PANEL_PT_MustardUI_ExternalMorphs_Body)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ExternalMorphs_Body)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ExternalMorphs_FACS)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ExternalMorphs_FACSUnits)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ExternalMorphs_Emotions)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ExternalMorphs_EmotionUnits)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ExternalMorphs)
