import bpy

from ..model_selection.active_object import active_object_operator_poll, mustardui_active_object
from ..warnings.can_draw_ui import can_draw_ui
from . import MainPanel


class PANEL_PT_MustardUI_SettingsPanel(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_SettingsPanel"
    bl_label = "Settings & Maintenance"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        if can_draw_ui():
            return False
        return active_object_operator_poll(context, config=0)

    def draw(self, context):

        settings = bpy.context.scene.MustardUI_Settings
        poll, obj = mustardui_active_object(context, config=0)
        rig_settings = obj.MustardUI_RigSettings

        layout = self.layout

        box = layout.box()
        box.label(text="General", icon="PREFERENCES")
        col = box.column(align=True)
        col.prop(settings, "advanced")

        version_vector = tuple(rig_settings.model_version_vector)
        if version_vector > (0, 0, 0):
            version = ".".join(str(x) for x in version_vector)
            if rig_settings.model_version_type != "Standard":
                version = f"{version} {rig_settings.model_version_type}"
            prop = rig_settings.bl_rna.properties["model_version_type"]
            version_icon = prop.enum_items[rig_settings.model_version_type].icon
        else:
            # Left for old compatibility (Deprecated in MustardUI 2025.8)
            version = rig_settings.model_version
            version_icon = "BLANK1"

        if version != "":
            if rig_settings.model_version_date_enable and rig_settings.model_version_date != "":
                version = f"{version} - {rig_settings.model_version_date}"

            box = layout.box()
            box.label(text="Model Version", icon="INFO")
            box.label(text=version, icon=version_icon)
            if rig_settings.model_changelog_link != "":
                box.operator(
                    "wm.url_open", text="Changelog", icon="URL"
                ).url = rig_settings.model_changelog_link


class PANEL_PT_MustardUI_SettingsPanel_Maintenance(MainPanel, bpy.types.Panel):
    bl_idname = "PANEL_PT_MustardUI_SettingsPanel_Maintenance"
    bl_label = "Maintenance"
    bl_parent_id = "PANEL_PT_MustardUI_SettingsPanel"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        if can_draw_ui():
            return False
        return active_object_operator_poll(context, config=0)

    def draw(self, context):

        layout = self.layout

        layout.operator("mustardui.cleanmodel", text="Clean Model", icon="BRUSH_DATA")

        op = layout.operator("mustardui.update_ui", text="UI Update", icon="SORT_DESC")
        op.force = True
        op.ignore = False

        layout.separator()
        layout.operator("mustardui.remove", text="UI Removal", icon="X")


def register():
    bpy.utils.register_class(PANEL_PT_MustardUI_SettingsPanel)
    bpy.utils.register_class(PANEL_PT_MustardUI_SettingsPanel_Maintenance)


def unregister():
    bpy.utils.unregister_class(PANEL_PT_MustardUI_SettingsPanel_Maintenance)
    bpy.utils.unregister_class(PANEL_PT_MustardUI_SettingsPanel)
