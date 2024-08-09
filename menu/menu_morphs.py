import bpy
from . import MainPanel
from ..model_selection.active_object import *
from ..misc.prop_utils import *
from ..warnings.ops_fix_old_UI import check_old_UI
from ..settings.rig import *


class PANEL_PT_MustardUI_ExternalMorphs(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_ExternalMorphs"
    bl_label = "Morphs"
    bl_options = {"DEFAULT_CLOSED"}

    def morph_filter(self, morph, rig_settings):

        # Check null filter
        check1 = (rig_settings.diffeomorphic_filter_null and evaluate_rna(
            f'rig_settings.model_armature_object["{bpy.utils.escape_identifier(morph.path)}"]') != 0.) or not rig_settings.diffeomorphic_filter_null

        # Check search filter
        check2 = rig_settings.diffeomorphic_search.lower() in morph.name.lower()

        return check1 and check2

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

        settings = bpy.context.scene.MustardUI_Settings

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

        # Check Diffeomorphic version and inform the user about possible issues
        if (settings.status_diffeomorphic_version[0], settings.status_diffeomorphic_version[1],
            settings.status_diffeomorphic_version[2]) <= (1, 6, 0) and settings.status_diffeomorphic_version[0] > -1:
            box = layout.box()
            box.label(icon='ERROR', text="Diffeomorphic version not supported!")
            box.label(icon='BLANK1', text="Only 1.6 or above is supported.")
            return

        row = layout.row()
        row.prop(rig_settings, 'diffeomorphic_search', icon="VIEWZOOM")
        row2 = row.row(align=True)
        row2.prop(rig_settings, 'diffeomorphic_filter_null', icon="FILTER", text="")
        row2.operator('mustardui.dazmorphs_defaultvalues', icon="LOOP_BACK", text="")
        row2.operator('mustardui.dazmorphs_clearpose', icon="OUTLINER_OB_ARMATURE", text="")
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

        # Emotions Units
        if rig_settings.diffeomorphic_emotions_units:
            box = layout.box()
            row = box.row(align=False)
            row.prop(rig_settings, "diffeomorphic_emotions_units_collapse",
                     icon="TRIA_DOWN" if not rig_settings.diffeomorphic_emotions_units_collapse else "TRIA_RIGHT",
                     icon_only=True, emboss=False)

            emotion_units_morphs = [x for x in rig_settings.diffeomorphic_morphs_list if
                                    x.type == 0 and self.morph_filter(x, rig_settings)]
            row.label(text="Emotion Units (" + str(len(emotion_units_morphs)) + ")")

            if not rig_settings.diffeomorphic_emotions_units_collapse:

                for morph in emotion_units_morphs:
                    if hasattr(rig_settings.model_armature_object, f'["{bpy.utils.escape_identifier(morph.path)}"]'):
                        box.prop(rig_settings.model_armature_object, f'["{bpy.utils.escape_identifier(morph.path)}"]', text=morph.name)
                    else:
                        row = box.row(align=False)
                        row.label(text=morph.name)
                        row.prop(settings, 'daz_morphs_error', text="", icon="ERROR", emboss=False, icon_only=True)

        # Emotions
        if rig_settings.diffeomorphic_emotions:
            box = layout.box()
            row = box.row(align=False)
            row.prop(rig_settings, "diffeomorphic_emotions_collapse",
                     icon="TRIA_DOWN" if not rig_settings.diffeomorphic_emotions_collapse else "TRIA_RIGHT",
                     icon_only=True, emboss=False)
            emotion_morphs = [x for x in rig_settings.diffeomorphic_morphs_list if
                              x.type == 1 and self.morph_filter(x, rig_settings)]
            row.label(text="Emotions (" + str(len(emotion_morphs)) + ")")

            if not rig_settings.diffeomorphic_emotions_collapse:
                for morph in emotion_morphs:
                    if hasattr(rig_settings.model_armature_object, f'["{bpy.utils.escape_identifier(morph.path)}"]'):
                        box.prop(rig_settings.model_armature_object, f'["{bpy.utils.escape_identifier(morph.path)}"]', text=morph.name)
                    else:
                        row = box.row(align=False)
                        row.label(text=morph.name)
                        row.prop(settings, 'daz_morphs_error', text="", icon="ERROR", emboss=False, icon_only=True)

        # FACS Emotions Units
        if rig_settings.diffeomorphic_facs_emotions_units:
            box = layout.box()
            row = box.row(align=False)
            row.prop(rig_settings, "diffeomorphic_facs_emotions_units_collapse",
                     icon="TRIA_DOWN" if not rig_settings.diffeomorphic_facs_emotions_units_collapse else "TRIA_RIGHT",
                     icon_only=True, emboss=False)
            facs_emotion_units_morphs = [x for x in rig_settings.diffeomorphic_morphs_list if
                                         x.type == 2 and self.morph_filter(x, rig_settings)]
            row.label(text="Advanced Emotion Units (" + str(len(facs_emotion_units_morphs)) + ")")

            if not rig_settings.diffeomorphic_facs_emotions_units_collapse:

                for morph in facs_emotion_units_morphs:
                    if hasattr(rig_settings.model_armature_object, f'["{bpy.utils.escape_identifier(morph.path)}"]'):
                        box.prop(rig_settings.model_armature_object, f'["{bpy.utils.escape_identifier(morph.path)}"]', text=morph.name)
                    else:
                        row = box.row(align=False)
                        row.label(text=morph.name)
                        row.prop(settings, 'daz_morphs_error', text="", icon="ERROR", emboss=False, icon_only=True)

        # FACS Emotions
        if rig_settings.diffeomorphic_facs_emotions:
            box = layout.box()
            row = box.row(align=False)
            row.prop(rig_settings, "diffeomorphic_facs_emotions_collapse",
                     icon="TRIA_DOWN" if not rig_settings.diffeomorphic_facs_emotions_collapse else "TRIA_RIGHT",
                     icon_only=True, emboss=False)
            facs_emotion_morphs = [x for x in rig_settings.diffeomorphic_morphs_list if
                                   x.type == 3 and self.morph_filter(x, rig_settings)]
            row.label(text="Advanced Emotions (" + str(len(facs_emotion_morphs)) + ")")

            if not rig_settings.diffeomorphic_facs_emotions_collapse:

                for morph in facs_emotion_morphs:
                    if hasattr(rig_settings.model_armature_object, f'["{bpy.utils.escape_identifier(morph.path)}"]'):
                        box.prop(rig_settings.model_armature_object, f'["{bpy.utils.escape_identifier(morph.path)}"]', text=morph.name)
                    else:
                        row = box.row(align=False)
                        row.label(text=morph.name)
                        row.prop(settings, 'daz_morphs_error', text="", icon="ERROR", emboss=False, icon_only=True)

        # Body Morphs
        if rig_settings.diffeomorphic_body_morphs:
            box = layout.box()
            row = box.row(align=False)
            row.prop(rig_settings, "diffeomorphic_body_morphs_collapse",
                     icon="TRIA_DOWN" if not rig_settings.diffeomorphic_body_morphs_collapse else "TRIA_RIGHT",
                     icon_only=True, emboss=False)
            body_morphs = [x for x in rig_settings.diffeomorphic_morphs_list if
                           x.type == 4 and self.morph_filter(x, rig_settings)]
            row.label(text="Body (" + str(len(body_morphs)) + ")")

            if not rig_settings.diffeomorphic_body_morphs_collapse:

                for morph in body_morphs:
                    if hasattr(rig_settings.model_armature_object, f'["{bpy.utils.escape_identifier(morph.path)}"]'):
                        box.prop(rig_settings.model_armature_object, f'["{bpy.utils.escape_identifier(morph.path)}"]', text=morph.name)
                    else:
                        row = box.row(align=False)
                        row.label(text=morph.name)
                        row.prop(settings, 'daz_morphs_error', text="", icon="ERROR", emboss=False, icon_only=True)


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_ExternalMorphs)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_ExternalMorphs)
