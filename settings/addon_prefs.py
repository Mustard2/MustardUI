import bpy
from bpy.props import BoolProperty, EnumProperty

from .. import __package__ as base_package
from ..text_storage import storage as text_storage


class MustardUI_AddonPrefs(bpy.types.AddonPreferences):
    bl_idname = base_package

    def developer_update(self, context):
        if not self.developer:
            self.debug = False
        for arm in [x for x in bpy.data.armatures]:
            if not arm.MustardUI_enable and arm.MustardUI_created and not self.developer:
                arm.MustardUI_enable = True

    # Maintenance tools
    developer: BoolProperty(
        default=False,
        name="Developer Mode",
        description="Enable Developer Tools.\nVarious developer tools will be "
        "added to the UI and in the Settings panel",
        update=developer_update,
    )

    # Quick Setup
    quick_setup: BoolProperty(
        default=False,
        name="Enable Quick Setup",
        description="Enable a quick way to set up a UI for any model.\n"
        "This is a simpler alternative to the full Configuration, ideal for "
        "inexperienced users or when only a few features are needed "
        "(Outfits, Hair, Armature).\n"
        "To use it, just select any Armature that does not "
        "already have a UI configured.\n"
        "The full Configuration can still be used afterwards "
        "(enable it with Developer Tools).",
    )

    # Model Toolkit
    model_toolkit: BoolProperty(
        default=False,
        name="Model Toolkit",
        description="Show the Model Toolkit panel.\nIt contains tools to edit the model: "
        "armature, mesh, physics, naming and optimizations",
    )

    # Limits of new custom properties
    new_property_limits: EnumProperty(
        name="Limits of new Properties",
        default="AUTO",
        items=(
            (
                "AUTO",
                "Automatic",
                "Use the limits of the property, falling back to 0 and 1 when the "
                "property has no limits",
            ),
            ("NORMALIZED", "0 to 1", "Always use 0 and 1"),
            (
                "PROPERTY",
                "From Property",
                "Always use the limits of the property, even when it has none",
            ),
        ),
        description="Minimum and maximum values assigned to Float and Int custom "
        "properties when they are added to the UI.\nThe limits can always be changed "
        "later in the property settings",
    )

    # Debug mode
    debug: BoolProperty(
        default=False,
        name="Debug Mode",
        description="Unlock Debug Mode.\nMore messages are generated in the "
        "console.\nEnable it only if you encounter problems, as it might "
        "degrade general performance",
    )

    # Experimental features
    experimental: BoolProperty(
        default=False,
        name="Experimental Features",
        description="Unlock experimental features throughout the add-on.\nNote that "
        "experimental features might not work properly yet, or be changed/removed "
        "from future versions",
        update=lambda self, context: text_storage.apply(),
    )

    settings_storage: EnumProperty(
        name="Optimization",
        default="ARMATURE",
        items=(
            ("ARMATURE", "Standard", "Standard set of optimizations.\nTested to work in all models without breaking functionalities"),
            (
                "TEXT",
                "Aggressive",
                "More aggressive optimization.\nIt might break some functionalities. Please check the Limitations notice in the Addon settings",
            ),
        ),
        description="Optimization level",
        update=lambda self, context: text_storage.apply(),
    )

    settings_storage_startup: BoolProperty(
        default=True,
        name="Use Standard at Startup",
        description="Switch the Optimization setting to Standard at Startup",
    )

    settings_storage_in_menu: BoolProperty(
        default=False,
        name="Show Optimization in UI Panel",
        description="Show Optimization Status and Settings in the UI Panel",
    )

    url_MustardUI = "https://github.com/Mustard2/MustardUI"
    url_MustardUI_ReportBug = "https://github.com/Mustard2/MustardUI/issues"
    url_MustardUI_Tutorial = "https://github.com/Mustard2/MustardUI/wiki/User-Guide"

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.prop(self, "model_toolkit")
        col.prop(self, "quick_setup")

        col.separator()
        col.prop(self, "developer", text="Developer Tools (for Model creators)")
        row = col.row()
        row.enabled = self.developer
        row.prop(self, "debug")
        col.separator()
        col.prop(self, "experimental")

        row = layout.row(align=True)
        row.operator("wm.url_open", text="GitHub", icon="URL").url = self.url_MustardUI
        row.operator("wm.url_open", text="User Guide", icon="URL").url = self.url_MustardUI_Tutorial
        row.operator(
            "wm.url_open", text="Report Bug", icon="URL"
        ).url = self.url_MustardUI_ReportBug

        if self.developer:
            box = layout.box()
            box.label(text="Developer Settings", icon="PREFERENCES")
            box.prop(self, "new_property_limits")

        if self.experimental:
            box = layout.box()
            box.label(text="Optimization (Experimental)", icon="FORCE_WIND")
            row = box.row(align=True)
            row.prop(self, "settings_storage", expand=True)

            col = box.column(align=True)
            col.label(text="Limitations:", icon="ERROR")
            if self.settings_storage == "ARMATURE":
                col.label(
                    text="• Cycles also loads the textures of hidden outfits, which might increase "
                    "memory (VRAM) usage.",
                    icon="BLANK1",
                )
                col.label(
                    text="• Hidden outfits also slow down the viewport, e.g. when switching "
                    "outfits or posing.",
                    icon="BLANK1",
                )
            else:
                for text in (
                    "Older MustardUI versions can not read the models saved with this option",
                    "Linked or overridden models are not supported",
                    "Keyframes and drivers on MustardUI settings stop working",
                    "Every Armature in the file gets a hidden Text datablock",
                ):
                    col.label(text=f"• {text}", icon="BLANK1")

            col = box.column(align=True)
            col.prop(self, "settings_storage_startup")
            col.prop(self, "settings_storage_in_menu")

        if self.debug:
            box = layout.box()
            box.label(text="Debug", icon="QUESTION_LARGE")
            col = box.column(align=True)
            col.operator("mustardui.fix_missing_ui", icon="GHOST_ENABLED")
            col.operator("mustardui.debug_log", text="Create Log file", icon="FILE_TEXT")


def register():
    bpy.utils.register_class(MustardUI_AddonPrefs)


def unregister():
    bpy.utils.unregister_class(MustardUI_AddonPrefs)
